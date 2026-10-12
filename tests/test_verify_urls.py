"""Tests for external-URL extraction."""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from types import ModuleType
from unittest import mock


def _load_verifier() -> ModuleType:
    path = Path(__file__).resolve().parent.parent / "scripts" / "verify-urls.py"
    spec = importlib.util.spec_from_file_location("verify_urls", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class UrlCollectionTests(unittest.TestCase):
    def test_ignores_url_shaped_inline_code(self) -> None:
        # Given: docs with a real link and an illustrative command placeholder.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "README.md").write_text(
                "See <https://example.com/docs>. "
                "Run `uvx --from git+https://...@<version|sha> tool`.\n"
                "```text\nhttps://example.invalid/in-a-fence\n```\n",
                encoding="utf-8",
            )
            verifier = _load_verifier()

            # When: the URL checker collects external links.
            with mock.patch.object(verifier, "ROOT", root):
                urls, unreadable = verifier.collect_urls()

            # Then: only navigable documentation links are scheduled for requests.
            self.assertEqual(urls, {"https://example.com/docs": ["README.md"]})
            self.assertEqual(unreadable, [])

    def test_malformed_url_is_unreachable_not_an_exception(self) -> None:
        verifier = _load_verifier()
        self.assertFalse(verifier.check("https://..."))
