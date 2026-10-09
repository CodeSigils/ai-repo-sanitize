"""Unit tests for publish, platform helpers and the remote splitter.

No network: ``urlopen`` is mocked for the API-call paths; the publish tests
run against a local bare repository.
"""

from __future__ import annotations

import http.client
import json
import subprocess
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest import mock

from ai_repo_sanitize import publish
from ai_repo_sanitize.pipeline import split_remote
from ai_repo_sanitize.platform import get_json, resolve_token


def _git(cwd: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


class _FakeResponse:
    """Minimal stand-in for an ``urllib`` response: json.load only calls read()."""

    def __init__(self, payload: object) -> None:
        self._data = json.dumps(payload).encode()

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def read(self) -> bytes:
        return self._data


class SplitRemoteTests(unittest.TestCase):
    def test_https_owner_repo(self) -> None:
        self.assertEqual(
            split_remote("https://github.com/CodeSigils/ai-repo-sanitize.git"),
            ("CodeSigils", "ai-repo-sanitize"),
        )

    def test_https_without_git_suffix(self) -> None:
        self.assertEqual(split_remote("https://github.com/o/r"), ("o", "r"))

    def test_scp_style(self) -> None:
        self.assertEqual(
            split_remote("git@github.com:CodeSigils/ai-repo-sanitize.git"),
            ("CodeSigils", "ai-repo-sanitize"),
        )

    def test_ssh_url(self) -> None:
        self.assertEqual(
            split_remote("ssh://git@github.com/CodeSigils/ai-repo-sanitize.git"),
            ("CodeSigils", "ai-repo-sanitize"),
        )

    def test_local_path_is_rejected(self) -> None:
        # Regression: a local-path remote used to produce a bogus (tmp, repo)
        # pair and a doomed API call; it must be treated as unparseable.
        self.assertIsNone(split_remote("/tmp/scratch/bare.git"))
        self.assertIsNone(split_remote("relative/path/repo.git"))
        self.assertIsNone(split_remote("plain-name.git"))


class ResolveTokenTests(unittest.TestCase):
    def test_none_when_unset(self) -> None:
        with mock.patch.dict("os.environ", {}, clear=True):
            self.assertIsNone(resolve_token())

    def test_github_token_fallback(self) -> None:
        with mock.patch.dict("os.environ", {"GITHUB_TOKEN": "tok"}, clear=True):
            self.assertEqual(resolve_token(), "tok")

    def test_gh_token_wins(self) -> None:
        with mock.patch.dict(
            "os.environ", {"GH_TOKEN": "gh", "GITHUB_TOKEN": "actions"}, clear=True
        ):
            self.assertEqual(resolve_token(), "gh")


class GetJsonTests(unittest.TestCase):
    def test_returns_decoded_json(self) -> None:
        with mock.patch("urllib.request.urlopen", return_value=_FakeResponse({"a": 1})) as urlopen:
            self.assertEqual(get_json("https://api.github.com/x", None), {"a": 1})
        urlopen.assert_called_once()

    def test_http_error_is_not_retried(self) -> None:
        error = urllib.error.HTTPError(
            "https://api.github.com/x", 404, "not found", http.client.HTTPMessage(), None
        )
        with (
            mock.patch("urllib.request.urlopen", side_effect=error) as urlopen,
            self.assertRaises(urllib.error.HTTPError),
        ):
            get_json("https://api.github.com/x", None)
        urlopen.assert_called_once()

    def test_transient_error_retried_once_then_raises(self) -> None:
        error = urllib.error.URLError("boom")
        with (
            mock.patch("urllib.request.urlopen", side_effect=error) as urlopen,
            self.assertRaises(urllib.error.URLError),
        ):
            get_json("https://api.github.com/x", None)
        self.assertEqual(urlopen.call_count, 2)

    def test_transient_error_then_success(self) -> None:
        error = urllib.error.URLError("boom")
        with mock.patch(
            "urllib.request.urlopen",
            side_effect=[error, _FakeResponse({"ok": True})],
        ) as urlopen:
            self.assertEqual(get_json("https://api.github.com/x", None), {"ok": True})
        self.assertEqual(urlopen.call_count, 2)


class PublishTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.bare = self.root / "remote.git"
        _git(self.root, "init", "--bare", "--initial-branch", "master", str(self.bare))
        self.work = self.root / "work"
        _git(self.root, "clone", str(self.bare), str(self.work))
        _git(self.work, "config", "user.name", "Tester")
        _git(self.work, "config", "user.email", "t@example.com")
        (self.work / "file.txt").write_text("hello\n", encoding="utf-8")
        _git(self.work, "add", "file.txt")
        _git(self.work, "commit", "-m", "feat: seed")
        _git(self.work, "push", "-u", "origin", "master")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_add_origin_is_idempotent(self) -> None:
        # origin exists after the clone: must stay untouched.
        publish.add_origin(self.work, str(self.bare))
        url = self._origin_url()
        self.assertEqual(url, str(self.bare))
        # after removal it must be re-added (the filter-repo flow).
        _git(self.work, "remote", "remove", "origin")
        publish.add_origin(self.work, str(self.bare))
        self.assertEqual(self._origin_url(), str(self.bare))

    def test_publish_pushes_rewritten_history(self) -> None:
        (self.work / "file.txt").write_text("hello\nsecond\n", encoding="utf-8")
        _git(self.work, "add", "file.txt")
        _git(self.work, "commit", "-m", "feat: second")
        publish.publish(self.work, str(self.bare), "master")
        probe = self.root / "probe"
        _git(self.root, "clone", str(self.bare), str(probe))
        subject = subprocess.run(
            ["git", "log", "-1", "--format=%s"],
            cwd=probe,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        self.assertEqual(subject, "feat: second")

    def _origin_url(self) -> str:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=self.work,
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()


if __name__ == "__main__":
    unittest.main()