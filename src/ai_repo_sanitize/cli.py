"""Command-line interface: ``check``, ``preview`` and ``rewrite``.

Exit codes: 0 = clean success, 1 = attribution found or operation failed,
2 = usage error (argparse default).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__, pipeline

__all__ = ["build_parser", "main"]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ai-repo-sanitize",
        description=(
            "Safely strip AI attribution trailers from git history: preview, "
            "rewrite, verify, publish; plus a read-only check mode for CI."
        ),
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="scan a repo for AI attribution without changing anything")
    check.add_argument("--path", type=Path, default=Path("."), help="work tree (default: .)")
    check.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )

    preview = sub.add_parser("preview", help="list the commits a rewrite would change")
    preview.add_argument("--path", type=Path, default=Path("."), help="work tree (default: .)")
    preview.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="output format (default: text)",
    )

    rewrite = sub.add_parser(
        "rewrite",
        help="strip AI attribution from history with mandatory safety gates",
    )
    rewrite.add_argument("--path", type=Path, default=Path("."), help="work tree (default: .)")
    rewrite.add_argument("--branch", default="master", help="branch to rewrite (default: master)")
    rewrite.add_argument(
        "--remote-url", help="remote for mirror backup and push (owner/name or full URL)"
    )
    rewrite.add_argument("--backup-dir", type=Path, help="mirror backup path (required for --push)")
    rewrite.add_argument(
        "--push",
        action="store_true",
        help="publish the rewrite with --force-with-lease after verification",
    )
    rewrite.add_argument(
        "--nudge-cache",
        action="store_true",
        help="last-resort sidebar-cache nudge via the gh CLI (undocumented, unsupported)",
    )
    return parser


def _print_commits(header: str, commits: list[tuple[str, str]]) -> None:
    print(header)
    for full_sha, subject in commits:
        print(f"  {full_sha[:12]} {subject}")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "check":
            result = pipeline.run_check(args.path)
            if args.format == "json":
                print(
                    json.dumps(
                        {
                            "command": "check",
                            "offending_commits": [
                                {
                                    "sha": full_sha,
                                    "subject": message.splitlines()[0].decode("utf-8", "replace")
                                    if message.splitlines()
                                    else "",
                                }
                                for full_sha, message in result.offending
                            ],
                            "scanned_commit_count": result.total,
                            "schema_version": 1,
                            "scope": "all_refs",
                        },
                        sort_keys=True,
                    )
                )
            else:
                print(
                    f"{result.total} commit(s) scanned across all refs, "
                    f"{len(result.offending)} with AI attribution"
                )
                for full_sha, message in result.offending:
                    first = message.splitlines()[0] if message.splitlines() else b""
                    print(f"  {full_sha[:12]} {first.decode('utf-8', 'replace')}")
            return 1 if result.offending else 0

        if args.command == "preview":
            commits = pipeline.preview_commits(args.path)
            if args.format == "json":
                print(
                    json.dumps(
                        {
                            "command": "preview",
                            "matching_commits": [
                                {"sha": full_sha, "subject": subject}
                                for full_sha, subject in commits
                            ],
                            "schema_version": 1,
                            "scope": "all_refs",
                        },
                        sort_keys=True,
                    )
                )
            else:
                _print_commits(f"{len(commits)} commit(s) would change across all refs:", commits)
            return 0

        if args.command == "rewrite":
            plan = pipeline.RewritePlan(
                work_dir=args.path,
                branch=args.branch,
                remote_url=args.remote_url,
                backup_dir=args.backup_dir,
                push=args.push,
                nudge_cache=args.nudge_cache,
            )
            report = pipeline.run_rewrite(plan)
            print(f"preview: {len(report.preview)} commit(s) flagged")
            if report.before_tree and report.after_tree == report.before_tree:
                print(f"verify: tree unchanged ({report.before_tree[:12]}...), messages only")
            if report.residual:
                print(f"verify: FAILED - {len(report.residual)} commit(s) still match")
            else:
                print("verify: clean - no attribution found")
            if report.pushed:
                print(f"pushed: {plan.branch} via --force-with-lease")
            if report.contributors is not None:
                print(
                    "contributors snapshot: "
                    + ", ".join(report.contributors.logins[:10])
                    or "contributors snapshot: (empty)"
                )
            return 1 if report.residual else 0

    except pipeline.PipelineError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
