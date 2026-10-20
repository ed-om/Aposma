// ============================================================================
// Aposma Analyzer (Refactored with using namespace std)
// ============================================================================

#include <algorithm>
#include <map>
#include <memory>
#include <regex>
#include <set>
#include <string>
#include <utility>
#include <vector>

// Clang AST headers
#include "clang/AST/ASTConsumer.h"
#include "clang/AST/ASTContext.h"
#include "clang/AST/DeclCXX.h"
#include "clang/AST/Expr.h"
#include "clang/AST/Type.h"
#include "clang/ASTMatchers/ASTMatchFinder.h"

// Clang frontend headers
#include "clang/Frontend/CompilerInstance.h"
#include "clang/Frontend/FrontendActions.h"
#include "clang/Lex/Lexer.h"

// Clang index & tooling headers
#include "clang/Index/USRGeneration.h"
#include "clang/Tooling/ArgumentsAdjusters.h"
#include "clang/Tooling/CommonOptionsParser.h"
#include "clang/Tooling/Tooling.h"

// LLVM utility headers
#include "llvm/ADT/SmallString.h"
#include "llvm/Support/CommandLine.h"
#include "llvm/Support/FormatVariadic.h"
#include "llvm/Support/JSON.h"
#include "llvm/Support/raw_ostream.h"

using namespace std;
using namespace clang;
using namespace clang::ast_matchers;
using namespace clang::tooling;

// ============================================================================
// COMMAND-LINE OPTIONS
// ============================================================================

static llvm::cl::OptionCategory AposmaCategory("aposma-analyzer options");

static llvm::cl::opt<string> OutputFile(
    "o",
    llvm::cl::desc("Write JSON to this file instead of stdout"),
    llvm::cl::value_desc("filename"),
    llvm::cl::init(""),
    llvm::cl::cat(AposmaCategory));

static llvm::cl::opt<string> GCCToolchain(
    "gcc-toolchain",
    llvm::cl::desc("GCC toolchain root passed to Clang, e.g. /usr"),
    llvm::cl::value_desc("path"),
    llvm::cl::init(""),
    llvm::cl::cat(AposmaCategory));

// ============================================================================
// DATA STRUCTURES
// ============================================================================

struct FunctionInfo {
  string key;            // Canonical Clang USR (Unified Symbol Resolution)
  string name;
  string qualifiedName;
  string file;
  unsigned line = 0;
  unsigned endLine = 0;
  string returnType;
  unsigned parameterCount = 0;
  unsigned controlCount = 0;  // Accurate Cyclomatic Complexity metric
  unsigned arrowMemberCount = 0;
  set<string> calls;
  set<string> pointerVariables;
  vector<string> pointerUses;
  string sourceText;
};

struct RecordInfo {
  string name;
  string qualifiedName;
  string file;
  unsigned line = 0;
};

struct Finding {
  string id;
  string category;
  string severity;
  string message;
  string file;
  unsigned line = 0;
  double confidence = 0.0;
  string evidence;
};

struct GlobalState {
  map<string, FunctionInfo> functions;
  map<string, RecordInfo> records;
  vector<Finding> findings;
  set<pair<string, string>> callEdges;
};

// ============================================================================
// SOURCE & USR HELPERS
// ============================================================================

static string fileOf(SourceLocation Loc, SourceManager &SM) {
  if (Loc.isInvalid())
    return "";
  PresumedLoc Presumed = SM.getPresumedLoc(Loc);
  if (Presumed.isInvalid())
    return "";
  return Presumed.getFilename();
}

// Generates a canonical Clang USR identifier for functions
static string functionKey(const FunctionDecl &FD) {
  llvm::SmallString<128> Buff;
  if (!clang::index::generateUSRForDecl(&FD, Buff)) {
    return Buff.str().str();
  }
  return FD.getQualifiedNameAsString();
}

// Macro-safe source text extraction
static string sourceTextFor(const Decl &D, SourceManager &SM, const LangOptions &LO) {
  SourceRange Range = D.getSourceRange();
  CharSourceRange CharRange = Lexer::makeFileCharRange(
      CharSourceRange::getTokenRange(Range), SM, LO);

  if (CharRange.isInvalid())
    return "";

  return Lexer::getSourceText(CharRange, SM, LO).str();
}

// ============================================================================
// AST MATCH CALLBACK
// ============================================================================

class Collector : public MatchFinder::MatchCallback {
public:
  Collector(ASTContext &Ctx, shared_ptr<GlobalState> State)
      : Context(Ctx), State(move(State)) {}

  void run(const MatchFinder::MatchResult &Result) override {
    SourceManager &SM = *Result.SourceManager;

    // --- FUNCTION DEFINITIONS ---
    if (const auto *FD = Result.Nodes.getNodeAs<FunctionDecl>("function")) {
      if (!FD->isThisDeclarationADefinition() || FD->isImplicit() ||
          SM.isInSystemHeader(FD->getLocation()))
        return;

      const string Key = functionKey(*FD);
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

    // --- CLASS / STRUCT DEFINITIONS ---
    if (const auto *RD = Result.Nodes.getNodeAs<CXXRecordDecl>("record")) {
      if (!RD->isThisDeclarationADefinition() || RD->isImplicit() ||
          SM.isInSystemHeader(RD->getLocation()))
        return;

      RecordInfo Info;
      Info.name = RD->getNameAsString();
      Info.qualifiedName = RD->getQualifiedNameAsString();
      Info.file = fileOf(RD->getLocation(), SM);
      Info.line = SM.getSpellingLineNumber(RD->getBeginLoc());

      State->records[Info.qualifiedName + "@" + Info.file + ":" + to_string(Info.line)] = Info;
      return;
    }

    // --- LOCAL POINTER VARIABLES ---
    if (const auto *Var = Result.Nodes.getNodeAs<VarDecl>("localVar")) {
      if (SM.isInSystemHeader(Var->getLocation()) || !Var->getType()->isPointerType())
        return;

      if (const auto *Owner = Result.Nodes.getNodeAs<FunctionDecl>("varOwner")) {
        const string Key = functionKey(*Owner);
        State->functions[Key].pointerVariables.insert(Var->getNameAsString());
      }
      return;
    }

    // --- FUNCTION CALLS ---
    if (const auto *Call = Result.Nodes.getNodeAs<CallExpr>("call")) {
      const auto *Caller = Result.Nodes.getNodeAs<FunctionDecl>("caller");
      const auto *Callee = Result.Nodes.getNodeAs<FunctionDecl>("callee");

      if (!Caller || !Callee || Caller->isImplicit() || Callee->isImplicit() ||
          SM.isInSystemHeader(Call->getExprLoc()))
        return;

      const string CallerKey = functionKey(*Caller);
      State->functions[CallerKey].calls.insert(Callee->getQualifiedNameAsString());
      State->callEdges.insert({Caller->getQualifiedNameAsString(), Callee->getQualifiedNameAsString()});
      return;
    }

    // --- POINTER MEMBER ACCESSES (->) ---
    if (const auto *Arrow = Result.Nodes.getNodeAs<MemberExpr>("arrow")) {
      const auto *Owner = Result.Nodes.getNodeAs<FunctionDecl>("arrowOwner");
      if (!Owner || Owner->isImplicit() || SM.isInSystemHeader(Arrow->getExprLoc()))
        return;

      const string Key = functionKey(*Owner);
      auto &Info = State->functions[Key];
      Info.arrowMemberCount++;

      if (const auto *Base = Arrow->getBase()->IgnoreParenImpCasts()) {
        if (const auto *DRE = dyn_cast<DeclRefExpr>(Base)) {
          Info.pointerUses.push_back(DRE->getNameInfo().getAsString());
        }
      }
      return;
    }

    // --- CONTROL FLOW METRICS ---
    if (Result.Nodes.getNodeAs<Stmt>("control")) {
      if (const auto *Owner = Result.Nodes.getNodeAs<FunctionDecl>("controlOwner")) {
        if (!Owner->isImplicit()) {
          const string Key = functionKey(*Owner);
          State->functions[Key].controlCount++;
        }
      }
    }
  }

  ASTContext &Context;

private:
  shared_ptr<GlobalState> State;
};

// ============================================================================
// DETERMINISTIC FINDINGS
// ============================================================================

static void finalizeFindings(GlobalState &State) {
  for (const auto &Entry : State.functions) {
    const auto &F = Entry.second;
    if (F.file.empty())
      continue;

    unsigned lineCount = (F.endLine >= F.line) ? (F.endLine - F.line + 1) : 0;

    // Long Function Check
    if (lineCount > 80) {
      State.findings.push_back({
          "long-function-" + F.key,
          "maintainability",
          "MEDIUM",
          "Function is unusually long and may have multiple responsibilities.",
          F.file,
          F.line,
          0.96,
          "Function spans " + to_string(lineCount) + " source lines."
      });
    }

    // Excess Parameters Check
    if (F.parameterCount > 6) {
      State.findings.push_back({
          "too-many-params-" + F.key,
          "maintainability",
          "LOW",
          "Function accepts many parameters; consider introducing a parameter object.",
          F.file,
          F.line,
          0.93,
          "Parameter count: " + to_string(F.parameterCount) + "."
      });
    }

    // Cyclomatic Complexity Check
    if (F.controlCount > 12) {
      State.findings.push_back({
          "high-branching-" + F.key,
          "maintainability",
          "MEDIUM",
          "Function contains high decision point density (cyclomatic complexity).",
          F.file,
          F.line,
          0.90,
          "Counted branching constructs: " + to_string(F.controlCount) + "."
      });
    }

    // Heuristic Null Dereference Guard Check
    for (const auto &Used : F.pointerUses) {
      if (!F.pointerVariables.count(Used))
        continue;

      const string Guard1 = "if (" + Used + ")";
      const string Guard2 = "if(" + Used + ")";
      const string Guard3 = Used + " != nullptr";
      const string Guard4 = Used + " != NULL";

      const bool HasGuard = F.sourceText.find(Guard1) != string::npos ||
                            F.sourceText.find(Guard2) != string::npos ||
                            F.sourceText.find(Guard3) != string::npos ||
                            F.sourceText.find(Guard4) != string::npos;

      if (!HasGuard) {
        State.findings.push_back({
            "possible-null-" + F.key + "-" + Used,
            "correctness",
            "HIGH",
            "Pointer member access may dereference a null pointer without a visible guard.",
            F.file,
            F.line,
            0.78,
            "Raw pointer '" + Used + "' accessed via -> without an explicit null check."
        });
      }
    }
  }
}

// ============================================================================
// AST CONSUMER
// ============================================================================

class Consumer : public ASTConsumer {
public:
  Consumer(ASTContext &Ctx, shared_ptr<GlobalState> State)
      : CollectorImpl(Ctx, move(State)) {

    Finder.addMatcher(
        functionDecl(isDefinition(), unless(isExpansionInSystemHeader())).bind("function"),
        &CollectorImpl);

    Finder.addMatcher(
        cxxRecordDecl(isDefinition(), unless(isExpansionInSystemHeader())).bind("record"),
        &CollectorImpl);

    Finder.addMatcher(
        varDecl(unless(isExpansionInSystemHeader()),
                hasAncestor(functionDecl(isDefinition()).bind("varOwner"))).bind("localVar"),
        &CollectorImpl);

    Finder.addMatcher(
        callExpr(callee(functionDecl().bind("callee")),
                 hasAncestor(functionDecl(isDefinition()).bind("caller"))).bind("call"),
        &CollectorImpl);

    Finder.addMatcher(
        memberExpr(isArrow(),
                   hasAncestor(functionDecl(isDefinition()).bind("arrowOwner"))).bind("arrow"),
        &CollectorImpl);

    // Accurate Cyclomatic Complexity Matching
    Finder.addMatcher(
        stmt(
            anyOf(
                ifStmt(), forStmt(), whileStmt(), doStmt(), switchStmt(), cxxForRangeStmt(),
                conditionalOperator(),
                cxxCatchStmt(),
                binaryOperator(hasAnyOperatorName("&&", "||"))
            ),
            hasAncestor(functionDecl(isDefinition()).bind("controlOwner"))
        ).bind("control"),
        &CollectorImpl);
  }

  void HandleTranslationUnit(ASTContext &Context) override {
    Finder.matchAST(Context);
  }

private:
  Collector CollectorImpl;
  MatchFinder Finder;
};

// ============================================================================
// FRONTEND ACTION & FACTORY
// ============================================================================

class Action : public ASTFrontendAction {
public:
  explicit Action(shared_ptr<GlobalState> State) : State(move(State)) {}

  unique_ptr<ASTConsumer> CreateASTConsumer(CompilerInstance &CI, llvm::StringRef) override {
    return make_unique<Consumer>(CI.getASTContext(), State);
  }

private:
  shared_ptr<GlobalState> State;
};

class ActionFactory : public FrontendActionFactory {
public:
  explicit ActionFactory(shared_ptr<GlobalState> State) : State(move(State)) {}

  unique_ptr<FrontendAction> create() override {
    return make_unique<Action>(State);
  }

private:
  shared_ptr<GlobalState> State;
};

// ============================================================================
// SERIALIZATION HELPERS
// ============================================================================

static llvm::json::Array stringArray(const set<string> &Items) {
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
  O["pointer_uses"] = move(Uses);

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

// ============================================================================
// MAIN ENTRY POINT
// ============================================================================

int main(int argc, const char **argv) {
  auto ExpectedParser = CommonOptionsParser::create(argc, argv, AposmaCategory);
  if (!ExpectedParser) {
    llvm::errs() << ExpectedParser.takeError();
    return 2;
  }

  CommonOptionsParser &OptionsParser = ExpectedParser.get();
  auto State = make_shared<GlobalState>();
  ClangTool Tool(OptionsParser.getCompilations(), OptionsParser.getSourcePathList());

  if (!GCCToolchain.empty()) {
    const string Argument = "--gcc-toolchain=" + GCCToolchain;
    Tool.appendArgumentsAdjuster(
      getInsertArgumentAdjuster(Argument.c_str(), ArgumentInsertPosition::BEGIN));
    }

  ActionFactory Factory(State);
  const int Result = Tool.run(&Factory);
  if (Result != 0)
    return Result;

  finalizeFindings(*State);

  
// JSON Construction
  llvm::json::Object Root;
  Root["tool"] = "aposma-analyzer";
  Root["version"] = "0.2.0";

  llvm::json::Array Functions;
  for (const auto &Entry : State->functions) {
    Functions.push_back(functionJson(Entry.second));
  }
  Root["functions"] = move(Functions);
  llvm::json::Array Records;
  for (const auto &Entry : State->records) {
    Records.push_back(recordJson(Entry.second));
  }
  Root["records"] = move(Records);

  llvm::json::Array Findings;
  for (const auto &F : State->findings) {
    Findings.push_back(findingJson(F));
  }
  Root["findings"] = move(Findings);

  llvm::json::Array Edges;
  for (const auto &Edge : State->callEdges) {
    llvm::json::Object E;
    E["from"] = Edge.first;
    E["to"] = Edge.second;
    E["type"] = "calls";
    Edges.push_back(move(E));
  }
  Root["edges"] = move(Edges);

  // Output Dispatch
  if (!OutputFile.empty()) {
    error_code EC;
    llvm::raw_fd_ostream OS(OutputFile, EC);
    if (EC) {
      llvm::errs() << "Failed to open output file: " << EC.message() << "\n";
      return 3;
    }
    OS << llvm::formatv("{0:2}\n", llvm::json::Value(move(Root)));
    return 0;
  }

  llvm::outs() << llvm::formatv("{0:2}\n", llvm::json::Value(move(Root)));
  return 0;
}