#!/usr/bin/env python3
"""Validate new commit messages locally and in CI."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Final

from ai_repo_sanitize.patterns import has_attribution

BODY_REQUIRED_TYPES: Final = frozenset(
    {
        "feat",
        "fix",
        "perf",
        "refactor",
        "build",
        "ci",
        "chore",
    }
)


def _requires_body(message: str) -> bool:
    """Return whether a conventional subject represents implementation work."""
    subject = message.splitlines()[0] if message.splitlines() else ""
    prefix = subject.split(":", maxsplit=1)[0].removesuffix("!")
    commit_type = prefix.split("(", maxsplit=1)[0]
    return commit_type in BODY_REQUIRED_TYPES


def _has_labeled_body(message: str, label: str) -> bool:
    """Return whether a non-empty labeled paragraph appears in a message."""
    prefix = f"{label}:"
    return any(
        line.strip().startswith(prefix) and line.strip() != prefix for line in message.splitlines()
    )


def findings(message: str, *, allow_bodyless: bool) -> list[str]:
    """Return policy violations for one complete commit message."""
    problems: list[str] = []
    if has_attribution(message.encode("utf-8")):
        problems.append("contains an AI-attribution trailer")
    if _requires_body(message) and not allow_bodyless:
        for label in ("what", "why"):
            if not _has_labeled_body(message, label):
                problems.append(f"requires a non-empty {label}: paragraph")
    return problems


def _run(arguments: list[str]) -> str:
    """Run git and return its text output or raise a concise failure."""
    completed = subprocess.run(arguments, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(detail or f"command failed: {' '.join(arguments)}")
    return completed.stdout


def _range_messages(base: str, head: str) -> list[tuple[str, str]]:
    """Read each commit introduced by base..head in chronological order."""
    revisions = _run(["git", "rev-list", "--reverse", f"{base}..{head}"]).splitlines()
    return [
        (revision, _run(["git", "show", "-s", "--format=%B", revision]))
        for revision in revisions
    ]


def _arguments() -> argparse.Namespace:
    """Parse the mutually exclusive local-file and CI-range inputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--message-file", type=Path)
    inputs.add_argument("--base")
    parser.add_argument("--head", help="range endpoint; required with --base")
    parser.add_argument(
        "--allow-bodyless",
        action="store_true",
        help="skip what/why enforcement for generated bot messages",
    )
    arguments = parser.parse_args()
    if (arguments.base is None) != (arguments.head is None):
        parser.error("--base and --head must be supplied together")
    return arguments


def main() -> int:
    """Print every violation and return a CI-friendly status code."""
    arguments = _arguments()
    try:
        messages = (
            [(str(arguments.message_file), arguments.message_file.read_text(encoding="utf-8"))]
            if arguments.message_file is not None
            else _range_messages(arguments.base, arguments.head)
        )
    except (OSError, RuntimeError) as error:
        print(f"check-commit-messages: could not read messages: {error}", file=sys.stderr)
        return 2

    problems = [
        f"{revision}: {problem}"
        for revision, message in messages
        for problem in findings(message, allow_bodyless=arguments.allow_bodyless)
    ]
    if problems:
        print("\n".join(f"FAIL: {problem}" for problem in problems), file=sys.stderr)
        return 1
    print(f"check-commit-messages: PASS: checked {len(messages)} commit(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
