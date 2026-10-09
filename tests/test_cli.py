"""CLI parsing and exit-code tests (no network, no live git history)."""

from __future__ import annotations

import tempfile
import unittest

from ai_repo_sanitize import cli


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


if __name__ == "__main__":
    unittest.main()