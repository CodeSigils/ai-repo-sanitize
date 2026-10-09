#!/usr/bin/env python3
"""Verify the live state of one pull request before a requested merge."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Check:
    name: str
    state: str


@dataclass(frozen=True, slots=True)
class PullRequest:
    url: str
    draft: bool
    base_ref: str
    merge_state: str
    review_decision: str | None
    checks: tuple[Check, ...]


def _run(arguments: list[str]) -> str:
    """Run GitHub CLI and return its output or raise a concise failure."""
    completed = subprocess.run(arguments, check=False, capture_output=True, text=True)
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout).strip()
        raise RuntimeError(detail or f"command failed: {' '.join(arguments)}")
    return completed.stdout


def _checks(value: list[object]) -> tuple[Check, ...]:
    """Parse GitHub's two status-check variants into one stable shape."""
    checks: list[Check] = []
    for item in value:
        if not isinstance(item, dict):
            raise ValueError("pull-request status check is not an object")
        kind = item.get("__typename")
        match kind:
            case "CheckRun":
                name = item.get("name")
                conclusion = item.get("conclusion")
                status = item.get("status")
                if not isinstance(name, str) or not isinstance(status, str):
                    raise ValueError("check run metadata is incomplete")
                state = conclusion if isinstance(conclusion, str) else status
            case "StatusContext":
                name = item.get("context")
                state = item.get("state")
                if not isinstance(name, str) or not isinstance(state, str):
                    raise ValueError("status context metadata is incomplete")
            case _:
                raise ValueError("unknown pull-request status-check type")
        checks.append(Check(name=name, state=state))
    return tuple(checks)


def parse_pull_request(payload: str) -> PullRequest:
    """Parse the exact read-only pull-request shape requested from GitHub."""
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError("GitHub CLI did not return a pull-request object")
    url = value.get("url")
    draft = value.get("isDraft")
    base_ref = value.get("baseRefName")
    merge_state = value.get("mergeStateStatus")
    review_decision = value.get("reviewDecision")
    status_checks = value.get("statusCheckRollup")
    if (
        not isinstance(url, str)
        or not isinstance(draft, bool)
        or not isinstance(base_ref, str)
        or not isinstance(merge_state, str)
        or not isinstance(status_checks, list)
        or (review_decision is not None
        and not isinstance(review_decision, str))
    ):
        raise ValueError("pull-request metadata is incomplete")
    return PullRequest(
        url=url,
        draft=draft,
        base_ref=base_ref,
        merge_state=merge_state,
        review_decision=review_decision,
        checks=_checks(status_checks),
    )


def findings(pull: PullRequest, default_branch: str, *, require_approval: bool) -> list[str]:
    """Return live conditions that make a requested merge unsafe to perform."""
    problems: list[str] = []
    if pull.draft:
        problems.append("is still a draft")
    if pull.base_ref != default_branch:
        problems.append(f"targets {pull.base_ref!r}, not {default_branch!r}")
    if pull.merge_state != "CLEAN":
        problems.append(f"merge state is {pull.merge_state!r}, not 'CLEAN'")
    if not pull.checks:
        problems.append("has no reported status checks")
    for check in pull.checks:
        if check.state not in {"SUCCESS", "NEUTRAL", "SKIPPED"}:
            problems.append(f"check {check.name!r} is {check.state!r}")
    if require_approval and pull.review_decision != "APPROVED":
        problems.append("does not have an approved review")
    return problems


def _default_branch() -> str:
    """Return the remote repository's current default branch."""
    value = json.loads(_run(["gh", "repo", "view", "--json", "defaultBranchRef"]))
    if not isinstance(value, dict) or not isinstance(value.get("defaultBranchRef"), dict):
        raise ValueError("repository default branch is missing")
    name = value["defaultBranchRef"].get("name")
    if not isinstance(name, str):
        raise ValueError("repository default branch is missing")
    return name


def _pull_request(number: int) -> PullRequest:
    """Fetch fresh merge-relevant metadata for one numbered pull request."""
    fields = "url,isDraft,baseRefName,mergeStateStatus,reviewDecision,statusCheckRollup"
    return parse_pull_request(_run(["gh", "pr", "view", str(number), "--json", fields]))


def main() -> int:
    """Check readiness and return a non-zero status without merging anything."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("number", type=int, help="pull-request number")
    parser.add_argument("--require-approval", action="store_true")
    arguments = parser.parse_args()
    try:
        pull = _pull_request(arguments.number)
        problems = findings(pull, _default_branch(), require_approval=arguments.require_approval)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as error:
        print(f"check-pr-readiness: could not query pull request: {error}", file=sys.stderr)
        return 2
    if problems:
        print("\n".join(f"FAIL: {pull.url}: {problem}" for problem in problems), file=sys.stderr)
        return 1
    print(f"check-pr-readiness: PASS: {pull.url} is ready for a maintainer merge")
    return 0


if __name__ == "__main__":
    sys.exit(main())
