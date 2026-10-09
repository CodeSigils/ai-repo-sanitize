"""Unit tests for the commit-message policy checker."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from types import ModuleType

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check-commit-messages.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_commit_messages", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


module = _load_module()


class CommitMessageTests(unittest.TestCase):
    def test_implementation_commit_with_labeled_body_passes(self) -> None:
        message = (
            "fix: enforce commit policy\n\nwhat: add CI validation\n\n"
            "why: local hooks are bypassable\n"
        )
        self.assertEqual(module.findings(message, allow_bodyless=False), [])

    def test_implementation_commit_requires_what_and_why(self) -> None:
        findings = module.findings("ci: add policy check\n", allow_bodyless=False)
        self.assertEqual(
            findings,
            ["requires a non-empty what: paragraph", "requires a non-empty why: paragraph"],
        )

    def test_scoped_implementation_commit_requires_what_and_why(self) -> None:
        findings = module.findings("fix(hooks): add policy check\n", allow_bodyless=False)
        self.assertEqual(
            findings,
            ["requires a non-empty what: paragraph", "requires a non-empty why: paragraph"],
        )

    def test_docs_commit_does_not_require_a_body(self) -> None:
        self.assertEqual(module.findings("docs: clarify policy\n", allow_bodyless=False), [])

    def test_generated_bot_commit_can_skip_body_requirement(self) -> None:
        self.assertEqual(module.findings("Bump ruff from 0.1 to 0.2\n", allow_bodyless=True), [])

    def test_attribution_is_rejected_even_for_generated_bot_commit(self) -> None:
        findings = module.findings("Bump ruff\n\nGenerated with Codex\n", allow_bodyless=True)
        self.assertEqual(findings, ["contains an AI-attribution trailer"])

    def test_empty_labeled_body_is_rejected(self) -> None:
        findings = module.findings("fix: guard commits\n\nwhat:\nwhy:\n", allow_bodyless=False)
        self.assertEqual(
            findings,
            ["requires a non-empty what: paragraph", "requires a non-empty why: paragraph"],
        )


if __name__ == "__main__":
    unittest.main()
