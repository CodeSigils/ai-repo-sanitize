#!/usr/bin/env python3
"""Fail scheduled CI when pull-request review debt needs a maintainer decision."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Final

DEPENDABOT_DAYS: Final = 7
REVIEW_DEBT_DAYS: Final = 14


@dataclass(frozen=True, slots=True)
class PullRequest:
    number: int
    url: str
    author: str
    created_at: datetime
    updated_at: datetime
    review_decision: str
    base_ref: str
    head_ref: str


def _timestamp(value: str) -> datetime:
    """Parse GitHub's ISO-8601 timestamp into an aware UTC value."""
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def parse_pull_requests(payload: str) -> list[PullRequest]:
    """Parse the narrow, typed PR shape requested from the GitHub CLI."""
    rows = json.loads(payload)
    if not isinstance(rows, list):
        raise ValueError("GitHub CLI did not return a pull-request list")
    pulls: list[PullRequest] = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("GitHub CLI returned a non-object pull request")
        author = row.get("author")
        if not isinstance(author, dict) or not isinstance(author.get("login"), str):
            raise ValueError("pull request author is missing")
        values = (
            row.get("number"),
            row.get("url"),
            row.get("createdAt"),
            row.get("updatedAt"),
            row.get("reviewDecision"),
            row.get("baseRefName"),
            row.get("headRefName"),
        )
        strings_complete = all(isinstance(value, str) for value in values[1:])
        if not isinstance(values[0], int) or not strings_complete:
            raise ValueError("pull request metadata is incomplete")
        pulls.append(
            PullRequest(
                number=values[0],
                url=values[1],
                author=author["login"],
                created_at=_timestamp(values[2]),
                updated_at=_timestamp(values[3]),
                review_decision=values[4],
                base_ref=values[5],
                head_ref=values[6],
            )
        )
    return pulls


def _age_days(value: datetime, now: datetime) -> int:
    return max(0, (now - value).days)


def _is_dependabot(pull: PullRequest) -> bool:
    return "dependabot" in pull.author.lower()


def findings(pulls: list[PullRequest], default_branch: str, now: datetime) -> list[str]:
    """Return actionable review debt without mutating GitHub state."""
    problems: list[str] = []
    for pull in pulls:
        created_days = _age_days(pull.created_at, now)
        updated_days = _age_days(pull.updated_at, now)
        if _is_dependabot(pull) and created_days >= DEPENDABOT_DAYS:
            problems.append(f"{pull.url}: Dependabot PR open for {created_days} day(s)")
        if pull.base_ref != default_branch:
            problems.append(f"{pull.url}: targets {pull.base_ref!r}, not {default_branch!r}")
        if created_days >= REVIEW_DEBT_DAYS and not pull.review_decision:
            problems.append(f"{pull.url}: no review after {created_days} day(s)")
        if updated_days >= REVIEW_DEBT_DAYS:
            problems.append(f"{pull.url}: no update for {updated_days} day(s)")
    return problems


def _run(arguments: list[str]) -> str:
    completed = subprocess.run(arguments, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(detail or f"command failed: {' '.join(arguments)}")
    return completed.stdout


def _repository() -> tuple[str, str]:
    payload = _run(["gh", "repo", "view", "--json", "nameWithOwner,defaultBranchRef"])
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError("GitHub CLI did not return repository metadata")
    name = value.get("nameWithOwner")
    branch = value.get("defaultBranchRef")
    if not isinstance(name, str) or not isinstance(branch, dict):
        raise ValueError("repository metadata is incomplete")
    branch_name = branch.get("name")
    if not isinstance(branch_name, str):
        raise ValueError("repository default branch is missing")
    return name, branch_name


def _open_pulls(repository: str) -> list[PullRequest]:
    fields = "number,url,author,createdAt,updatedAt,reviewDecision,baseRefName,headRefName"
    command = [
        "gh",
        "pr",
        "list",
        "--repo",
        repository,
        "--state",
        "open",
        "--limit",
        "50",
        "--json",
        fields,
    ]
    return parse_pull_requests(_run(command))


def _write_summary(lines: list[str]) -> None:
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary is None:
        return
    with open(summary, "a", encoding="utf-8") as file:
        file.write("## Pull-request hygiene\n\n")
        file.write("\n".join(f"- {line}" for line in lines))
        file.write("\n")


def main() -> int:
    try:
        repository, default_branch = _repository()
        problems = findings(_open_pulls(repository), default_branch, datetime.now(timezone.utc))
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"check-pr-hygiene: could not query pull requests: {error}", file=sys.stderr)
        return 2
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}", file=sys.stderr)
        _write_summary([f"FAIL: {problem}" for problem in problems])
        return 1
    message = "PASS: no pull-request hygiene findings"
    print(f"check-pr-hygiene: {message}")
    _write_summary([message])
    return 0


if __name__ == "__main__":
    sys.exit(main())
