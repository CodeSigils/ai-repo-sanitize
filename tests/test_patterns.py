"""Regression tests for the attribution pattern set.

Runnable by both ``pytest`` and ``python3 -m unittest discover -s tests``
(the python-compat CI job uses the latter so it exercises the stdlib runner).
"""

from __future__ import annotations

import unittest

from ai_repo_sanitize.patterns import (
    AGENT_NAMES,
    ATTRIBUTION_RE,
    GIT_GREP_PATTERN,
    has_attribution,
    strip_attribution,
)


class StripAttributionTests(unittest.TestCase):
    def test_removes_claude_co_author_trailer(self) -> None:
        # CRLF line endings in the commit message are preserved by design
        # (only matching lines are removed; trailing blanks are trimmed).
        message = b"fix: flaky retry\r\n\r\nCo-authored-by: Claude <noreply@anthropic.com>\n"
        self.assertEqual(strip_attribution(message), b"fix: flaky retry\r\n")

    def test_removes_ultraworked_branding_line(self) -> None:
        message = b"docs: explain caches\n\nUltraworked with [Sisyphus](https://sisyphuslabs.ai)\n"
        self.assertEqual(strip_attribution(message), b"docs: explain caches\n")

    def test_removes_generated_with_line(self) -> None:
        message = b"feat: add panel\n\nGenerated with [Claude Code]\n"
        self.assertEqual(strip_attribution(message), b"feat: add panel\n")

    def test_preserves_human_co_author(self) -> None:
        message = b"fix: clamp bounds\n\nCo-authored-by: Pat <pat@example.com>\n"
        self.assertEqual(strip_attribution(message), message)

    def test_trims_trailing_blank_lines_left_by_removal(self) -> None:
        message = b"chore: bump pin\n\nCo-authored-by: Claude <noreply@anthropic.com>\n\n\n"
        self.assertEqual(strip_attribution(message), b"chore: bump pin\n")

    def test_empty_result_is_empty_bytes(self) -> None:
        self.assertEqual(strip_attribution(b"\n"), b"")

    def test_agent_name_inside_trailer_still_matches(self) -> None:
        message = (
            b"fix: retry logic\n\nCo-authored-by: Alice <alice@example.com>\n"
            b"Co-authored-by: Claude <noreply@anthropic.com>\n"
        )
        self.assertEqual(
            strip_attribution(message),
            b"fix: retry logic\n\nCo-authored-by: Alice <alice@example.com>\n",
        )


class AttributionDetectionTests(unittest.TestCase):
    def test_detects_attribution(self) -> None:
        self.assertTrue(has_attribution(b"subject\n\nCo-authored-by: Devin <dev@example.com>\n"))
        self.assertFalse(has_attribution(b"subject\n\nCo-authored-by: Pat <pat@example.com>\n"))
        self.assertFalse(has_attribution(b"plain message without trailers\n"))

    def test_agents_are_all_escaped_in_pattern(self) -> None:
        # Names are re.escape()d so regex metacharacters cannot leak through.
        for name in AGENT_NAMES:
            self.assertIn(name, GIT_GREP_PATTERN)
            self.assertIn(name, ATTRIBUTION_RE.pattern.decode("ascii"))

    def test_git_grep_pattern_avoids_word_boundaries(self) -> None:
        # git's regex engine is not POSIX-clean about \b; keep the preview
        # pattern and the hook pattern free of it (POSIX-grep compatibility).
        self.assertNotIn("\\b", GIT_GREP_PATTERN)
        # (?...) captures are invalid in POSIX ERE (git log --grep rejects them)
        self.assertNotIn("(?:", GIT_GREP_PATTERN)

    def test_branded_line_without_trailing_content_matches(self) -> None:
        self.assertTrue(has_attribution(b"Ultraworked with Sisyphus\n"))
        self.assertTrue(has_attribution(b"Assisted with [Cursor]\n"))


if __name__ == "__main__":
    unittest.main()