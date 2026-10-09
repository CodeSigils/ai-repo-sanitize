"""Unit tests for scripts/check-doc-coverage.py (the warn-only diff rule)."""
from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path
from types import ModuleType

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "check-doc-coverage.py"


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_doc_coverage", _SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


module = _load_module()


class DocCoverageWarningsTests(unittest.TestCase):
    def test_no_changes_warns_nothing(self) -> None:
        self.assertEqual(module.doc_coverage_warnings([]), [])

    def test_docs_only_change_warns_nothing(self) -> None:
        self.assertEqual(module.doc_coverage_warnings(["README.md"]), [])

    def test_code_with_docs_change_warns_nothing(self) -> None:
        changed = ["src/ai_repo_sanitize/patterns.py", "README.md"]
        self.assertEqual(module.doc_coverage_warnings(changed), [])

    def test_code_only_change_warns(self) -> None:
        warnings = module.doc_coverage_warnings(["src/ai_repo_sanitize/patterns.py"])
        self.assertEqual(len(warnings), 1)
        self.assertIn("src/ai_repo_sanitize/patterns.py", warnings[0])

    def test_repo_infra_paths_count_as_code(self) -> None:
        for path in (
            "scripts/validate-docs.py",
            ".github/workflows/ci.yml",
            ".githooks/pre-commit",
            "pyproject.toml",
            "uv.lock",
            "tests/test_cli.py",
        ):
            with self.subTest(path=path):
                self.assertEqual(len(module.doc_coverage_warnings([path])), 1)

    def test_mixed_change_list_silent_when_docs_present(self) -> None:
        changed = ["src/patterns.py", "README.md", "scripts/some.py"]
        self.assertEqual(module.doc_coverage_warnings(changed), [])


if __name__ == "__main__":
    unittest.main()