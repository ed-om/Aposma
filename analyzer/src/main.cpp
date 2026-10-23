#include <algorithm>
#include <memory>
#include <regex>
#include <set>
#include <string>
#include <vector>
#include <map>

#include "clang/AST/ASTConsumer.h"
#include "clang/AST/ASTContext.h"
#include "clang/AST/DeclCXX.h"
#include "clang/AST/Expr.h"
#include "clang/AST/Type.h"
#include "clang/ASTMatchers/ASTMatchFinder.h"
#include "clang/Frontend/CompilerInstance.h"
#include "clang/Frontend/FrontendActions.h"
#include "clang/Lex/Lexer.h"
#include "clang/Tooling/CommonOptionsParser.h"
#include "clang/Tooling/Tooling.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/JSON.h"
#include "llvm/Support/raw_ostream.h"

using namespace clang;
using namespace clang::ast_matchers;
using namespace clang::tooling;

static llvm::cl::OptionCategory AposmaCategory("aposma-analyzer options");
static llvm::cl::opt<std::string> OutputFile(
    "o", llvm::cl::desc("Write JSON to this file instead of stdout"),
    llvm::cl::value_desc("filename"), llvm::cl::init(""),
    llvm::cl::cat(AposmaCategory));

struct FunctionInfo {
  std::string key;
  std::string name;
  std::string qualifiedName;
  std::string file;
  unsigned line = 0;
  unsigned endLine = 0;
  std::string returnType;
  unsigned parameterCount = 0;
  unsigned controlCount = 0;
  unsigned arrowMemberCount = 0;
  std::set<std::string> calls;
  std::set<std::string> pointerVariables;
  std::vector<std::string> pointerUses;
  std::string sourceText;
};

struct RecordInfo {
  std::string name;
  std::string qualifiedName;
  std::string file;
  unsigned line = 0;
};

struct Finding {
  std::string id;
  std::string category;
  std::string severity;
  std::string message;
  std::string file;
  unsigned line = 0;
  double confidence = 0.0;
  std::string evidence;
};

struct GlobalState {
  std::map<std::string, FunctionInfo> functions;
  std::map<std::string, RecordInfo> records;
  std::vector<Finding> findings;
  std::set<std::pair<std::string, std::string>> callEdges;
};

static std::string fileOf(SourceLocation Loc, SourceManager &SM) {
  if (Loc.isInvalid()) return "";
  PresumedLoc Presumed = SM.getPresumedLoc(Loc);
  if (Presumed.isInvalid()) return "";
  return Presumed.getFilename();
}

static std::string functionKey(const FunctionDecl &FD, SourceManager &SM) {
  const std::string File = fileOf(FD.getLocation(), SM);
  const unsigned Line = SM.getSpellingLineNumber(FD.getBeginLoc());
  return FD.getQualifiedNameAsString() + "@" + File + ":" + std::to_string(Line);
}

static std::string sourceTextFor(const Decl &D, SourceManager &SM, const LangOptions &LO) {
  CharSourceRange Range = CharSourceRange::getTokenRange(D.getSourceRange());
  return Lexer::getSourceText(Range, SM, LO).str();
}

class Collector : public MatchFinder::MatchCallback {
public:
  Collector(ASTContext &Ctx, std::shared_ptr<GlobalState> State)
      : Context(Ctx), State(std::move(State)) {}

  void run(const MatchFinder::MatchResult &Result) override {
    SourceManager &SM = *Result.SourceManager;

    if (const auto *FD = Result.Nodes.getNodeAs<FunctionDecl>("function")) {
      if (!FD->isThisDeclarationADefinition() || FD->isImplicit()) return;
      if (SM.isInSystemHeader(FD->getLocation())) return;

      const std::string Key = functionKey(*FD, SM);
      auto &Info = State->functions[Key];
      Info.key = Key;
      Info.name = FD->getNameAsString();
      Info.qualifiedName = FD->getQualifiedNameAsString();
      Info.file = fileOf(FD->getLocation(), SM);
      Info.line = SM.getSpellingLineNumber(FD->getBeginLoc());
      Info.endLine = SM.getSpellingLineNumber(FD->getEndLoc());
      Info.returnType = FD->getReturnType().getAsString();
      Info.parameterCount = FD->getNumParams();
      Info.sourceText = sourceTextFor(*FD, SM, Context.getLangOpts());
      return;
    }

    if (const auto *RD = Result.Nodes.getNodeAs<CXXRecordDecl>("record")) {
      if (!RD->isThisDeclarationADefinition() || RD->isImplicit()) return;
      if (SM.isInSystemHeader(RD->getLocation())) return;
      RecordInfo Info;
      Info.name = RD->getNameAsString();
      Info.qualifiedName = RD->getQualifiedNameAsString();
      Info.file = fileOf(RD->getLocation(), SM);
      Info.line = SM.getSpellingLineNumber(RD->getBeginLoc());
      State->records[RD->getQualifiedNameAsString() + "@" + Info.file + ":" + std::to_string(Info.line)] = Info;
      return;
    }

    if (const auto *Var = Result.Nodes.getNodeAs<VarDecl>("localVar")) {
      if (SM.isInSystemHeader(Var->getLocation())) return;
      if (!Var->getType()->isPointerType()) return;
      const auto *Owner = Result.Nodes.getNodeAs<FunctionDecl>("varOwner");
      if (!Owner) return;
      const std::string Key = functionKey(*Owner, SM);
      State->functions[Key].pointerVariables.insert(Var->getNameAsString());
      return;
    }

    if (const auto *Call = Result.Nodes.getNodeAs<CallExpr>("call")) {
      const auto *Caller = Result.Nodes.getNodeAs<FunctionDecl>("caller");
      const auto *Callee = Result.Nodes.getNodeAs<FunctionDecl>("callee");
      if (!Caller || !Callee || Caller->isImplicit() || Callee->isImplicit()) return;
      if (SM.isInSystemHeader(Call->getExprLoc())) return;
      const std::string CallerKey = functionKey(*Caller, SM);
      State->functions[CallerKey].calls.insert(Callee->getQualifiedNameAsString());
      State->callEdges.insert({Caller->getQualifiedNameAsString(), Callee->getQualifiedNameAsString()});
      return;
    }

    if (const auto *Arrow = Result.Nodes.getNodeAs<MemberExpr>("arrow")) {
      const auto *Owner = Result.Nodes.getNodeAs<FunctionDecl>("arrowOwner");
      if (!Owner || Owner->isImplicit()) return;
      if (SM.isInSystemHeader(Arrow->getExprLoc())) return;
      const std::string Key = functionKey(*Owner, SM);
      auto &Info = State->functions[Key];
      Info.arrowMemberCount++;
      if (const auto *Base = Arrow->getBase()->IgnoreParenImpCasts()) {
        if (const auto *DRE = dyn_cast<DeclRefExpr>(Base)) {
          Info.pointerUses.push_back(DRE->getNameInfo().getAsString());
        }
      }
      return;
    }

    if (Result.Nodes.getNodeAs<Stmt>("control")) {
      const auto *Owner = Result.Nodes.getNodeAs<FunctionDecl>("controlOwner");
      if (!Owner || Owner->isImplicit()) return;
      const std::string Key = functionKey(*Owner, SM);
      State->functions[Key].controlCount++;
    }
  }

  void finalizeFindings() {
    for (const auto &Entry : State->functions) {
      const auto &F = Entry.second;
      if (F.file.empty()) continue;
      unsigned lineCount = F.endLine >= F.line ? F.endLine - F.line + 1 : 0;

      if (lineCount > 80) {
        State->findings.push_back({
            "long-function-" + F.key,
            "maintainability",
            "MEDIUM",
            "Function is unusually long and may have multiple responsibilities.",
            F.file,
            F.line,
            0.96,
            "Function spans " + std::to_string(lineCount) + " source lines."});
      }

      if (F.parameterCount > 6) {
        State->findings.push_back({
            "too-many-params-" + F.key,
            "maintainability",
            "LOW",
            "Function accepts many parameters and may benefit from a smaller interface or parameter object.",
            F.file,
            F.line,
            0.93,
            "Parameter count: " + std::to_string(F.parameterCount) + "."});
      }

      if (F.controlCount > 12) {
        State->findings.push_back({
            "high-branching-" + F.key,
            "maintainability",
            "MEDIUM",
            "Function contains many branching/control-flow constructs and may be difficult to reason about.",
            F.file,
            F.line,
            0.90,
            "Counted control-flow statements: " + std::to_string(F.controlCount) + "."});
      }

      for (const auto &Used : F.pointerUses) {
        if (!F.pointerVariables.count(Used)) continue;
        // Heuristic: do not call this a proof. We only flag raw pointer member access
        // when we cannot find a common visible guard for the same identifier.
        const std::string Guard1 = "if (" + Used + ")";
        const std::string Guard2 = "if(" + Used + ")";
        const std::string Guard3 = Used + " != nullptr";
        const std::string Guard4 = Used + " != NULL";
        const bool HasGuard = F.sourceText.find(Guard1) != std::string::npos ||
                              F.sourceText.find(Guard2) != std::string::npos ||
                              F.sourceText.find(Guard3) != std::string::npos ||
                              F.sourceText.find(Guard4) != std::string::npos;
        if (HasGuard) continue;

        State->findings.push_back({
            "possible-null-" + F.key + "-" + Used,
            "correctness",
            "HIGH",
            "Pointer member access may dereference a null pointer; this heuristic did not find a visible guard for the pointer in the function text.",
            F.file,
            F.line,
            0.78,
            "Raw pointer '" + Used + "' is used with ->. This is a heuristic finding, not a proof of nullness."});
      }
    }
  }

public:
  ASTContext &Context;

private:
  std::shared_ptr<GlobalState> State;
};

class Consumer : public ASTConsumer {
public:
  explicit Consumer(ASTContext &Ctx, std::shared_ptr<GlobalState> State)
      : CollectorImpl(Ctx, std::move(State)) {
    Finder.addMatcher(
        functionDecl(isDefinition(), unless(isExpansionInSystemHeader())).bind("function"),
        &CollectorImpl);

    Finder.addMatcher(
        cxxRecordDecl(isDefinition(), unless(isExpansionInSystemHeader())).bind("record"),
        &CollectorImpl);

    Finder.addMatcher(
        varDecl(isLocalVariable(), unless(isExpansionInSystemHeader()),
                hasAncestor(functionDecl(isDefinition()).bind("varOwner")))
            .bind("localVar"),
        &CollectorImpl);

    Finder.addMatcher(
        callExpr(callee(functionDecl().bind("callee")),
                 hasAncestor(functionDecl(isDefinition()).bind("caller")))
            .bind("call"),
        &CollectorImpl);

    Finder.addMatcher(
        memberExpr(isArrow(), hasAncestor(functionDecl(isDefinition()).bind("arrowOwner")))
            .bind("arrow"),
        &CollectorImpl);

    Finder.addMatcher(
        stmt(anyOf(ifStmt(), forStmt(), whileStmt(), doStmt(), switchStmt(), cxxForRangeStmt()),
                  hasAncestor(functionDecl(isDefinition()).bind("controlOwner")))
            .bind("control"),
        &CollectorImpl);
  }

  void HandleTranslationUnit(ASTContext &) override { Finder.matchAST(CollectorImpl.Context); }

private:
  Collector CollectorImpl;
  MatchFinder Finder;
};

class Action : public ASTFrontendAction {
public:
  explicit Action(std::shared_ptr<GlobalState> State) : State(std::move(State)) {}

  std::unique_ptr<ASTConsumer> CreateASTConsumer(CompilerInstance &CI,
                                                  llvm::StringRef) override {
    return std::make_unique<Consumer>(CI.getASTContext(), State);
  }

private:
  std::shared_ptr<GlobalState> State;
};

class ActionFactory : public FrontendActionFactory {
public:
  explicit ActionFactory(std::shared_ptr<GlobalState> State) : State(std::move(State)) {}

  std::unique_ptr<FrontendAction> create() override {
    return std::make_unique<Action>(State);
  }

private:
  std::shared_ptr<GlobalState> State;
};

static llvm::json::Array stringArray(const std::set<std::string> &Items) {
  llvm::json::Array A;
  for (const auto &Item : Items) A.push_back(Item);
  return A;
}

static llvm::json::Object functionJson(const FunctionInfo &F) {
  llvm::json::Object O;
  O["key"] = F.key;
  O["name"] = F.name;
  O["qualified_name"] = F.qualifiedName;
  O["file"] = F.file;
  O["line"] = F.line;
  O["end_line"] = F.endLine;
  O["return_type"] = F.returnType;
  O["parameter_count"] = F.parameterCount;
  O["control_count"] = F.controlCount;
  O["arrow_member_count"] = F.arrowMemberCount;
  O["calls"] = stringArray(F.calls);
  O["pointer_variables"] = stringArray(F.pointerVariables);
  llvm::json::Array Uses;
  for (const auto &Use : F.pointerUses) Uses.push_back(Use);
  O["pointer_uses"] = std::move(Uses);
  return O;
}

static llvm::json::Object recordJson(const RecordInfo &R) {
  llvm::json::Object O;
  O["name"] = R.name;
  O["qualified_name"] = R.qualifiedName;
  O["file"] = R.file;
  O["line"] = R.line;
  return O;
}

static llvm::json::Object findingJson(const Finding &F) {
  llvm::json::Object O;
  O["id"] = F.id;
  O["category"] = F.category;
  O["severity"] = F.severity;
  O["message"] = F.message;
  O["file"] = F.file;
  O["line"] = F.line;
  O["confidence"] = F.confidence;
  O["evidence"] = F.evidence;
  return O;
}

int main(int argc, const char **argv) {
  auto ExpectedParser = CommonOptionsParser::create(argc, argv, AposmaCategory);
  if (!ExpectedParser) {
    llvm::errs() << ExpectedParser.takeError();
    return 2;
  }

  CommonOptionsParser &OptionsParser = ExpectedParser.get();
  auto State = std::make_shared<GlobalState>();
  ClangTool Tool(OptionsParser.getCompilations(), OptionsParser.getSourcePathList());
  ActionFactory Factory(State);
  const int Result = Tool.run(&Factory);
  if (Result != 0) return Result;

  // Finalize deterministic findings after all translation units have populated the shared state.
  // Reuse a tiny helper context-independent pass below.
  for (const auto &Entry : State->functions) {
    const auto &F = Entry.second;
    if (F.file.empty()) continue;
    unsigned lineCount = F.endLine >= F.line ? F.endLine - F.line + 1 : 0;

    if (lineCount > 80) {
      State->findings.push_back({
          "long-function-" + F.key, "maintainability", "MEDIUM",
          "Function is unusually long and may have multiple responsibilities.",
          F.file, F.line, 0.96,
          "Function spans " + std::to_string(lineCount) + " source lines."});
    }

    if (F.parameterCount > 6) {
      State->findings.push_back({
          "too-many-params-" + F.key, "maintainability", "LOW",
          "Function accepts many parameters and may benefit from a smaller interface or parameter object.",
          F.file, F.line, 0.93,
          "Parameter count: " + std::to_string(F.parameterCount) + "."});
    }

    if (F.controlCount > 12) {
      State->findings.push_back({
          "high-branching-" + F.key, "maintainability", "MEDIUM",
          "Function contains many branching/control-flow constructs and may be difficult to reason about.",
          F.file, F.line, 0.90,
          "Counted control-flow statements: " + std::to_string(F.controlCount) + "."});
    }

    for (const auto &Used : F.pointerUses) {
      if (!F.pointerVariables.count(Used)) continue;
      const std::string Guard1 = "if (" + Used + ")";
      const std::string Guard2 = "if(" + Used + ")";
      const std::string Guard3 = Used + " != nullptr";
      const std::string Guard4 = Used + " != NULL";
      const bool HasGuard = F.sourceText.find(Guard1) != std::string::npos ||
                            F.sourceText.find(Guard2) != std::string::npos ||
                            F.sourceText.find(Guard3) != std::string::npos ||
                            F.sourceText.find(Guard4) != std::string::npos;
      if (HasGuard) continue;
      State->findings.push_back({
          "possible-null-" + F.key + "-" + Used, "correctness", "HIGH",
          "Pointer member access may dereference a null pointer; this heuristic did not find a visible guard for the pointer in the function text.",
          F.file, F.line, 0.78,
          "Raw pointer '" + Used + "' is used with ->. This is a heuristic finding, not a proof of nullness."});
    }
  }

  llvm::json::Object Root;
  Root["tool"] = "aposma-analyzer";
  Root["version"] = "0.1.0";

  llvm::json::Array Functions;
  for (const auto &Entry : State->functions) Functions.push_back(functionJson(Entry.second));
  Root["functions"] = std::move(Functions);

  llvm::json::Array Records;
  for (const auto &Entry : State->records) Records.push_back(recordJson(Entry.second));
  Root["records"] = std::move(Records);

  llvm::json::Array Findings;
  for (const auto &F : State->findings) Findings.push_back(findingJson(F));
  Root["findings"] = std::move(Findings);

  llvm::json::Array Edges;
  for (const auto &Edge : State->callEdges) {
    llvm::json::Object E;
    E["from"] = Edge.first;
    E["to"] = Edge.second;
    E["type"] = "calls";
    Edges.push_back(std::move(E));
  }
  Root["edges"] = std::move(Edges);

  if (!OutputFile.empty()) {
    std::error_code EC;
    llvm::raw_fd_ostream OS(OutputFile, EC);
    if (EC) {
      llvm::errs() << "Failed to open output file: " << EC.message() << "\n";
      return 3;
    }
    OS << llvm::formatv("{0:2}\n", llvm::json::Value(std::move(Root)));
    return 0;
  }

  llvm::outs() << llvm::formatv("{0:2}\n", llvm::json::Value(std::move(Root)));
  return 0;
}
