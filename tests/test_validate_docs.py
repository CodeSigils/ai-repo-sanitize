"""Tests for the docs validator (check-the-checker).

Org pattern borrowed from python-project-workflow-skill (validate-ci.py plus
test-validate-ci.py): the validator that guards docs-vs-code drift must itself
be tested, or the guard can rot silently. We drive
scripts/validate-docs.py's findings() over temporary doc fixtures using the
--root/--today/--review-window knobs it exposes for determinism.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from datetime import date
from pathlib import Path
from types import ModuleType

_COMMANDS = (
    "uv run ty check",
    "uv run ruff check .",
    "uv run pytest",
    "uv run python scripts/validate-docs.py",
)


def _load_validator() -> ModuleType:
    path = Path(__file__).resolve().parent.parent / "scripts" / "validate-docs.py"
    spec = importlib.util.spec_from_file_location("validate_docs", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ValidatorFixture(unittest.TestCase):
    """Minimal repo-shaped tree the validator can read (offline, tmp dir)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.validate_docs = _load_validator()
        cls.REQUIRED = cls.validate_docs.REQUIRED_DOCS

    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp(prefix="vdocs-"))
        workflows = self.root / ".github" / "workflows"
        workflows.mkdir(parents=True)
        ci_body = "\n".join(f"run: {command}" for command in _COMMANDS)
        (workflows / "ci.yml").write_text(
            f"name: validate\n\njobs:\n  quality:\n    steps:\n{ci_body}\n",
            encoding="utf-8",
        )
        hooks = self.root / ".githooks"
        hooks.mkdir()
        (hooks / "pre-commit").write_text(
            "uv run ruff check .\nuv run python scripts/validate-docs.py\n",
            encoding="utf-8",
        )

    def _write_docs(
        self,
        *,
        stale: set[str] | None = None,
        missing: set[str] | None = None,
        broken_link: bool = False,
    ) -> None:
        stale = stale or set()
        missing = missing or set()
        today = date.today().isoformat()
        for name in self.REQUIRED:
            if name in missing:
                continue
            reviewed = "2000-01-01" if name in stale else today
            body = [f"> Last reviewed: {reviewed}", "", "# Doc", ""]
            if name in ("README.md", "CONTRIBUTING.md"):
                for command in _COMMANDS:
                    body.append(f"```sh\n{command}\n```")
            if broken_link and name == "README.md":
                body.append("See [missing-file](nonexistent-target.md).")
            body.append("")
            (self.root / name).write_text("\n".join(body), encoding="utf-8")

    def run_findings(
        self,
        *,
        today: date | None = None,
        review_window_days: int | None = None,
    ) -> list[str]:
        kwargs: dict[str, object] = {"root": self.root}
        if today is not None:
            kwargs["today"] = today
        if review_window_days is not None:
            kwargs["review_window_days"] = review_window_days
        return self.validate_docs.findings(**kwargs)


class FindingsTest(ValidatorFixture):
    def test_clean_tree_no_findings(self) -> None:
        self._write_docs()
        self.assertEqual(self.run_findings(today=date.today()), [])

    def test_stale_doc_fails(self) -> None:
        self._write_docs(stale={"MAINTENANCE.md"})
        problems = self.run_findings(today=date.today())
        self.assertTrue(
            any("MAINTENANCE.md" in p and "last reviewed" in p for p in problems),
            problems,
        )

    def test_missing_header_fails(self) -> None:
        self._write_docs()
        (self.root / "SECURITY.md").write_text("# Doc\n", encoding="utf-8")
        problems = self.run_findings(today=date.today())
        self.assertTrue(
            any("SECURITY.md" in p and "missing 'Last reviewed" in p for p in problems),
            problems,
        )

    def test_missing_required_doc_fails(self) -> None:
        self._write_docs(missing={"ANTIDRIFT.md"})
        problems = self.run_findings(today=date.today())
        self.assertTrue(
            any("missing required docs" in p and "ANTIDRIFT.md" in p for p in problems),
            problems,
        )

    def test_review_window_override_changes_verdict(self) -> None:
        today = date(2026, 10, 9)
        self._write_docs()
        path = self.root / "RESEARCH.md"
        text = path.read_text(encoding="utf-8").replace(
            "Last reviewed:", "Last reviewed: 2026-07-11"
        )
        path.write_text(text, encoding="utf-8")
        problems_90 = self.run_findings(today=today, review_window_days=90)
        self.assertFalse(
            any("RESEARCH.md" in p and "last reviewed" in p for p in problems_90),
            problems_90,
        )
        problems_30 = self.run_findings(today=today, review_window_days=30)
        self.assertTrue(
            any("RESEARCH.md" in p and "last reviewed" in p for p in problems_30),
            problems_30,
        )

    def test_broken_internal_link_fails(self) -> None:
        self._write_docs(broken_link=True)
        problems = self.run_findings(today=date.today())
        self.assertTrue(
            any(
                "internal link target does not exist: nonexistent-target.md" in p
                for p in problems
            ),
            problems,
        )

    def test_usage_error_returns_one(self) -> None:
        self.assertEqual(self.validate_docs.main(["--bogus"]), 1)


if __name__ == "__main__":
    unittest.main()