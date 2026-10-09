"""check-the-checker for scripts/check-doc-claims.py (codocia-class checks)."""
from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import ModuleType


def _load_checker() -> ModuleType:
    script = Path(__file__).resolve().parent.parent / "scripts" / "check-doc-claims.py"
    spec = importlib.util.spec_from_file_location("check_doc_claims", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    assert module is not None
    spec.loader.exec_module(module)
    return module


class ClaimsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.checker = _load_checker()

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="claims-"))
        (self.tmp / "src").mkdir()
        (self.tmp / "scripts").mkdir()
        (self.tmp / "src" / "mod.py").write_text("", encoding="utf-8")
        self.doc = self.tmp / "README.md"

    def test_existing_path_no_finding(self) -> None:
        self.doc.write_text("see `src/mod.py`\n", encoding="utf-8")
        self.assertEqual(self.checker.findings(root=self.tmp), [])

    def test_missing_path_finding(self) -> None:
        self.doc.write_text("see `src/gone.py`\n", encoding="utf-8")
        result = self.checker.findings(root=self.tmp)
        self.assertEqual(len(result), 1)
        self.assertIn("README.md", result[0])
        self.assertIn("src/gone.py", result[0])

    def test_space_token_skipped(self) -> None:
        self.doc.write_text("run `uv sync --locked`\n", encoding="utf-8")
        self.assertEqual(self.checker.findings(root=self.tmp), [])

    def test_http_token_skipped(self) -> None:
        self.doc.write_text("see `https://example.com/x`\n", encoding="utf-8")
        self.assertEqual(self.checker.findings(root=self.tmp), [])

    def test_bare_project_files_exist(self) -> None:
        (self.tmp / "pyproject.toml").write_text("", encoding="utf-8")
        (self.tmp / "uv.lock").write_text("", encoding="utf-8")
        self.doc.write_text("uses `pyproject.toml` and `uv.lock`\n", encoding="utf-8")
        self.assertEqual(self.checker.findings(root=self.tmp), [])

    def test_bare_project_file_missing(self) -> None:
        self.doc.write_text("uses `pyproject.toml`\n", encoding="utf-8")
        self.assertEqual(len(self.checker.findings(root=self.tmp)), 1)

    def test_no_false_positives_on_realistic_text(self) -> None:
        self.doc.write_text(
            "# Workflow\n"
            "`uv run ty check` and `uv run pytest` pass.\n"
            "${{ github.ref }} is the ref. See src/mod.py and src/gone.py.\n",
            encoding="utf-8",
        )
        # Plain prose paths and command spans are not claimed; only backticked
        # repo-path tokens are.
        self.assertEqual(self.checker.findings(root=self.tmp), [])


if __name__ == "__main__":
    unittest.main()