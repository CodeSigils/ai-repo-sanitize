"""End-to-end: the guarded rewrite sequence against a local bare remote.

The whole safety arc runs for real: a scratch repository is seeded with
attribution trailers, then the pipeline is driven (check -> preview -> rewrite
with a mirror backup -> push), the remote is cloned back, and both safety
invariants are asserted (same tree, attribution gone, human co-authors kept).

Skipped where git-filter-repo is unavailable (for example the stdlib matrix
job, which has no uv/venv); the dev environment and the CI quality job install
it via the dev dependency group.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from ai_repo_sanitize import pipeline
from ai_repo_sanitize.pipeline import RewritePlan


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def _filter_repo_available() -> bool:
    return shutil.which("git-filter-repo") is not None or Path(sys.executable).parent.joinpath(
        "git-filter-repo"
    ).is_file()


@unittest.skipUnless(_filter_repo_available(), "git-filter-repo is not installed")
class EndToEndRewriteTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.bare = self.root / "remote.git"
        _git(self.root, "init", "--bare", "--initial-branch", "master", str(self.bare))
        self.work = self.root / "work"
        _git(self.root, "clone", str(self.bare), str(self.work))
        _git(self.work, "config", "user.name", "Tester")
        _git(self.work, "config", "user.email", "t@example.com")
        (self.work / "guide.txt").write_text("first\n", encoding="utf-8")
        _git(self.work, "add", "guide.txt")
        _git(
            self.work,
            "commit",
            "-m",
            "feat: first commit",
            "-m",
            "Co-authored-by: Claude <noreply@anthropic.com>",
            "-m",
            "Ultraworked with [Sisyphus](https://sisyphuslabs.ai)",
        )
        # A human-only co-author commit that must survive the rewrite.
        (self.work / "guide.txt").write_text("first\nsecond\n", encoding="utf-8")
        _git(self.work, "add", "guide.txt")
        _git(
            self.work,
            "commit",
            "-m",
            "feat: second commit",
            "-m",
            "Co-authored-by: Pat <pat@example.com>",
        )
        _git(self.work, "push", "-u", "origin", "master")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_full_sequence(self) -> None:
        # check: exactly the agent commit is flagged, nothing else.
        result = pipeline.run_check(self.work)
        self.assertEqual(result.total, 2)
        self.assertEqual(len(result.offending), 1)
        self.assertFalse(result.clean)

        # preview: one commit would change.
        self.assertEqual(len(pipeline.preview_commits(self.work)), 1)

        # rewrite with a mirror backup and a push to the local bare remote.
        backup = self.root / "backup.git"
        plan = RewritePlan(
            work_dir=self.work,
            branch="master",
            remote_url=str(self.bare),
            backup_dir=backup,
            push=True,
        )
        report = pipeline.run_rewrite(plan)

        self.assertTrue(report.pushed)
        self.assertIsNotNone(report.before_tree)
        self.assertEqual(report.before_tree, report.after_tree)
        self.assertEqual(report.residual, [])
        self.assertTrue(backup.is_dir())  # escape hatch existed before the push

        # The rewritten remote: agent attribution gone, human co-author kept,
        # tree identical to the pre-rewrite tree.
        probe = self.root / "probe"
        _git(self.root, "clone", str(self.bare), str(probe))
        log = subprocess.run(
            ["git", "log", "--format=%B"], cwd=probe, capture_output=True, text=True, check=True
        ).stdout
        self.assertNotIn("Co-authored-by: Claude", log)
        self.assertNotIn("Ultraworked", log)
        self.assertIn("Co-authored-by: Pat <pat@example.com>", log)
        tree = subprocess.run(
            ["git", "rev-parse", "master^{tree}"],
            cwd=probe,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        self.assertEqual(tree, report.after_tree)


if __name__ == "__main__":
    unittest.main()