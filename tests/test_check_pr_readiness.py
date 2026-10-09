"""Unit tests for the live pull-request readiness gate."""
from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from types import ModuleType

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check-pr-readiness.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_pr_readiness", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


module = _load_module()


def payload(**overrides: object) -> str:
    value = {
        "url": "https://github.com/CodeSigils/ai-repo-sanitize/pull/1",
        "isDraft": False,
        "baseRefName": "master",
        "mergeStateStatus": "CLEAN",
        "reviewDecision": "APPROVED",
        "statusCheckRollup": [
            {
                "__typename": "CheckRun",
                "name": "quality",
                "status": "COMPLETED",
                "conclusion": "SUCCESS",
            },
            {"__typename": "StatusContext", "context": "external", "state": "SUCCESS"},
        ],
    }
    value.update(overrides)
    return json.dumps(value)


class PullRequestReadinessTests(unittest.TestCase):
    def test_clean_pull_with_passing_checks_is_ready(self) -> None:
        pull = module.parse_pull_request(payload())
        self.assertEqual(module.findings(pull, "master", require_approval=True), [])

    def test_pending_check_blocks_merge(self) -> None:
        pull = module.parse_pull_request(
            payload(
                statusCheckRollup=[
                    {
                        "__typename": "CheckRun",
                        "name": "quality",
                        "status": "IN_PROGRESS",
                        "conclusion": None,
                    }
                ]
            )
        )
        self.assertEqual(
            module.findings(pull, "master", require_approval=False),
            ["check 'quality' is 'IN_PROGRESS'"],
        )

    def test_missing_approval_blocks_only_when_requested(self) -> None:
        pull = module.parse_pull_request(payload(reviewDecision=None))
        self.assertEqual(module.findings(pull, "master", require_approval=False), [])
        self.assertEqual(
            module.findings(pull, "master", require_approval=True),
            ["does not have an approved review"],
        )

    def test_draft_wrong_base_and_dirty_merge_block_merge(self) -> None:
        pull = module.parse_pull_request(
            payload(isDraft=True, baseRefName="feature", mergeStateStatus="DIRTY")
        )
        self.assertEqual(
            module.findings(pull, "master", require_approval=False),
            [
                "is still a draft",
                "targets 'feature', not 'master'",
                "merge state is 'DIRTY', not 'CLEAN'",
            ],
        )

    def test_parser_rejects_unknown_status_check_type(self) -> None:
        with self.assertRaises(ValueError):
            module.parse_pull_request(payload(statusCheckRollup=[{"__typename": "Unknown"}]))


if __name__ == "__main__":
    unittest.main()
