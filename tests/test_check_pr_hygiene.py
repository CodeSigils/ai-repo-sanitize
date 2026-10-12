"""Unit tests for the read-only pull-request hygiene rules."""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from unittest import mock

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check-pr-hygiene.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_pr_hygiene", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


module = _load_module()
NOW = datetime(2026, 10, 9, tzinfo=timezone.utc)


def pull(
    *,
    author: str = "dependabot[bot]",
    created: str = "2026-10-09T00:00:00Z",
    updated: str = "2026-10-09T00:00:00Z",
    review: str = "APPROVED",
    base: str = "master",
) -> object:
    return module.PullRequest(
        number=1,
        url="https://github.com/CodeSigils/ai-repo-sanitize/pull/1",
        author=author,
        created_at=module._timestamp(created),
        updated_at=module._timestamp(updated),
        review_decision=review,
        base_ref=base,
        head_ref="dependabot/ruff",
    )


class PullRequestHygieneTests(unittest.TestCase):
    def test_fresh_dependabot_pull_has_no_finding(self) -> None:
        self.assertEqual(module.findings([pull()], "master", NOW), [])

    def test_old_dependabot_pull_fails(self) -> None:
        findings = module.findings([pull(created="2026-10-02T00:00:00Z")], "master", NOW)
        self.assertEqual(len(findings), 1)
        self.assertIn("Dependabot PR open for 7 day(s)", findings[0])

    def test_old_unreviewed_pull_fails(self) -> None:
        findings = module.findings(
            [pull(author="alice", created="2026-09-25T00:00:00Z", review="")], "master", NOW
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("no review after 14 day(s)", findings[0])

    def test_stale_pull_fails(self) -> None:
        findings = module.findings(
            [pull(author="alice", updated="2026-09-25T00:00:00Z")], "master", NOW
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("no update for 14 day(s)", findings[0])

    def test_stacked_pull_fails(self) -> None:
        findings = module.findings([pull(author="alice", base="feature")], "master", NOW)
        self.assertEqual(len(findings), 1)
        self.assertIn("targets 'feature', not 'master'", findings[0])

    def test_parser_rejects_incomplete_pull_metadata(self) -> None:
        with self.assertRaises(ValueError):
            module.parse_pull_requests('[{"number": 1}]')

    def test_open_pull_limit_fails_instead_of_silently_omitting_pull_requests(self) -> None:
        # Given: the CLI returns the maximum number of pull requests requested.
        rows = [
            {
                "number": number,
                "url": f"https://github.com/CodeSigils/ai-repo-sanitize/pull/{number}",
                "author": {"login": "alice"},
                "createdAt": "2026-10-09T00:00:00Z",
                "updatedAt": "2026-10-09T00:00:00Z",
                "reviewDecision": "APPROVED",
                "baseRefName": "master",
                "headRefName": f"feature/{number}",
            }
            for number in range(module._MAX_OPEN_PULLS)
        ]

        # When: the hygiene audit asks GitHub for its open pull requests.
        # Then: it fails safely rather than claiming the partial audit passed.
        with (
            mock.patch.object(module, "_run", return_value=json.dumps(rows)),
            self.assertRaisesRegex(RuntimeError, "reached the open pull-request limit"),
        ):
            module._open_pulls("CodeSigils/ai-repo-sanitize")


if __name__ == "__main__":
    unittest.main()
