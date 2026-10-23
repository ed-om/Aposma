from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Settings
from .docs import write_documents
from .review import docs_repo, persist_review, review_repo
from .storage import Database


def _settings() -> Settings:
    return Settings.from_env()


def cmd_review(args: argparse.Namespace) -> int:
    repo = Path(args.path).resolve()
    result, evidence = review_repo(repo, _settings(), args.base, not args.no_ai)
    analysis_id = persist_review(_settings(), repo, result, evidence)

    print(f"\nAposma Review — {repo.name}")
    print("=" * 60)
    print(result.summary)
    print(f"Stored analysis: #{analysis_id}")
    print()
    if not result.findings:
        print("No findings.")
        return 0
    for finding in result.findings:
        print(f"[{finding.severity.upper():6}] {finding.category:16} {finding.location}")
        print(f"  {finding.title}")
        print(f"  {finding.finding}")
        print(f"  Reason: {finding.reason}")
        if finding.evidence:
            for item in finding.evidence:
                print(f"  Evidence: {item}")
        print()
    return 0


def cmd_docs(args: argparse.Namespace) -> int:
    repo = Path(args.path).resolve()
    result = docs_repo(repo, _settings(), not args.no_ai)
    paths = write_documents(repo, result["documents"])
    print(result["summary"])
    print(f"Generated {len(paths)} document(s):")
    for path in paths:
        print(f" - {path}")
    return 0


def cmd_analyzer(args: argparse.Namespace) -> int:
    from .analyzer import run_analyzer
    analysis = run_analyzer(Path(args.path).resolve(), _settings())
    print(json.dumps(analysis.raw, indent=2))
    return 0


def cmd_history(args: argparse.Namespace) -> int:
    db = Database(_settings().db_path)
    for row in db.recent(args.limit):
        print(f"#{row['id']} {row['created_at']} {row['repository']} — {row['summary']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="aposma", description="Aposma local-first code intelligence tool")
    sub = parser.add_subparsers(dest="command", required=True)

    review = sub.add_parser("review", help="Analyze a repository and produce code-review findings")
    review.add_argument("path")
    review.add_argument("--base", default=None, help="Base Git ref/commit for the diff")
    review.add_argument("--no-ai", action="store_true", help="Skip the local SLM")
    review.set_defaults(func=cmd_review)

    docs = sub.add_parser("docs", help="Generate documentation")
    docs.add_argument("path")
    docs.add_argument("--no-ai", action="store_true", help="Use deterministic docs instead of the local SLM")
    docs.set_defaults(func=cmd_docs)

    analyzer = sub.add_parser("analyze", help="Print raw C++ analysis JSON")
    analyzer.add_argument("path")
    analyzer.set_defaults(func=cmd_analyzer)

    history = sub.add_parser("history", help="Show stored analyses")
    history.add_argument("--limit", type=int, default=20)
    history.set_defaults(func=cmd_history)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    try:
        raise SystemExit(args.func(args))
    except KeyboardInterrupt:
        raise SystemExit(130)
    except Exception as exc:  # noqa: BLE001
        print(f"Aposma error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
