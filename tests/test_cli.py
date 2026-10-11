"""CLI parsing, output, and exit-code tests."""

from __future__ import annotations

import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from ai_repo_sanitize import cli


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _repo_with_attributed_side_ref(root: Path) -> Path:
    work = root / "work"
    _git(root, "init", "--initial-branch", "main", str(work))
    _git(work, "config", "user.name", "Tester")
    _git(work, "config", "user.email", "t@example.com")
    _git(work, "commit", "--allow-empty", "-m", "docs: main history")
    _git(work, "checkout", "-b", "side")
    _git(
        work,
        "commit",
        "--allow-empty",
        "-m",
        "docs: side history",
        "-m",
        "Co-authored-by: Claude <noreply@anthropic.com>",
    )
    _git(work, "checkout", "main")
    return work


class ParserTests(unittest.TestCase):
    def test_rewrite_defaults_branch_to_master(self) -> None:
        ns = cli.build_parser().parse_args(["rewrite", "--path", "/tmp/x"])
        self.assertEqual(ns.command, "rewrite")
        self.assertEqual(ns.branch, "master")
        self.assertFalse(ns.push)

    def test_rewrite_flags_parse(self) -> None:
        ns = cli.build_parser().parse_args(
            ["rewrite", "--path", "/tmp/x", "--branch", "main", "--push", "--nudge-cache"]
        )
        self.assertEqual(ns.branch, "main")
        self.assertTrue(ns.push)
        self.assertTrue(ns.nudge_cache)

    def test_subcommands_present(self) -> None:
        ns = cli.build_parser().parse_args(["preview", "--path", "/tmp/x"])
        self.assertEqual(ns.command, "preview")

    def test_rewrite_rejects_json_format(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            cli.build_parser().parse_args(["rewrite", "--format", "json"])
        self.assertEqual(ctx.exception.code, 2)


class ExitCodeTests(unittest.TestCase):
    def test_check_inside_non_repo_exits_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(cli.main(["check", "--path", tmp]), 1)

    def test_version_flag_exits_zero(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            cli.main(["--version"])
        self.assertEqual(ctx.exception.code, 0)

    def test_usage_error_exits_2(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            cli.main(["bogus-command"])
        self.assertEqual(ctx.exception.code, 2)


class JsonOutputTests(unittest.TestCase):
    def test_check_json_reports_all_ref_finding_and_preserves_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Given: an attribution reachable only from a non-checked-out ref.
            work = _repo_with_attributed_side_ref(Path(tmp))
            output = io.StringIO()
            expected_sha = subprocess.run(
                ["git", "rev-parse", "side"],
                cwd=work,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

            # When: check emits its structured read-only result.
            with contextlib.redirect_stdout(output):
                exit_code = cli.main(["check", "--path", str(work), "--format", "json"])

            # Then: the result is machine-readable and retains check's failure signal.
            self.assertEqual(exit_code, 1)
            self.assertEqual(
                json.loads(output.getvalue()),
                {
                    "command": "check",
                    "offending_commits": [
                        {
                            "sha": expected_sha,
                            "subject": "docs: side history",
                        }
                    ],
                    "scanned_commits": 2,
                    "schema_version": 1,
                    "scope": "all_refs",
                },
            )

    def test_preview_json_reports_all_ref_finding_and_preserves_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            # Given: an attribution reachable only from a non-checked-out ref.
            work = _repo_with_attributed_side_ref(Path(tmp))
            output = io.StringIO()

            # When: preview emits its structured read-only result.
            with contextlib.redirect_stdout(output):
                exit_code = cli.main(["preview", "--path", str(work), "--format", "json"])

            # Then: the result is machine-readable and retains preview's clean exit.
            self.assertEqual(exit_code, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["command"], "preview")
            self.assertEqual(payload["scope"], "all_refs")
            self.assertEqual(len(payload["matching_commits"]), 1)
            self.assertEqual(len(payload["matching_commits"][0]["sha"]), 40)
            self.assertEqual(payload["matching_commits"][0]["subject"], "docs: side history")


if __name__ == "__main__":
    unittest.main()
