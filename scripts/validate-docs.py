#!/usr/bin/env python3
"""Drift guard: keep the docs and the validation gates in agreement.

Inspired by the author's py-review-skill validate pattern (CC-BY-4.0 terms of
that repo; logic rewritten here). Enforces a small, verifiable contract:

* Every canonical validation command is listed in README.md and CONTRIBUTING.md.
* Every required documentation file exists (docs inventory never silently
  shrinks).
* Every internal relative link in the markdown docs resolves to a real file.
* The CI workflow and the pre-commit hook actually run the canonical commands
  they claim to run.

Exit code 0 = contract holds; 1 = findings (printed with file references).
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_DOCS: tuple[str, ...] = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "MAINTENANCE.md",
    "RESEARCH.md",
    "ROADMAP.md",
    "ANTIDRIFT.md",
    "AGENTS.md",
)

#: Canonical commands. README, CONTRIBUTING, ci.yml and .githooks/pre-commit
#: must all reference these exact strings so the docs cannot drift from what
#: CI and local hooks really execute.
VALIDATION_COMMANDS: tuple[str, ...] = (
    "uv run ty check",
    "uv run ruff check .",
    "uv run pytest",
    "uv run python scripts/validate-docs.py",
)

_LINK_RE = re.compile(r"\]\(([^)]+)\)")


def findings() -> list[str]:
    problems: list[str] = []
    missing = [name for name in REQUIRED_DOCS if not (ROOT / name).is_file()]
    if missing:
        problems.append("missing required docs: " + ", ".join(missing))

    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
    contributing = (
        (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        if (ROOT / "CONTRIBUTING.md").is_file()
        else ""
    )
    for command in VALIDATION_COMMANDS:
        if command not in readme:
            problems.append(f"README.md must list the command: {command}")
        if command not in contributing:
            problems.append(f"CONTRIBUTING.md must list the command: {command}")

    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for command in VALIDATION_COMMANDS:
        # ci.yml runs the canonical commands verbatim (plain "uv run ..."),
        # so a simple substring check holds.
        if command not in ci:
            problems.append(f"ci.yml must run the canonical command: {command}")

    pre_commit = ROOT / ".githooks" / "pre-commit"
    if pre_commit.is_file():
        hook = pre_commit.read_text(encoding="utf-8")
        if "uv run ruff check ." not in hook:
            problems.append(".githooks/pre-commit must run: uv run ruff check .")
        if "validate-docs.py" not in hook:
            problems.append(".githooks/pre-commit must run scripts/validate-docs.py")

    for doc in REQUIRED_DOCS:
        path = ROOT / doc
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for target in _LINK_RE.findall(text):
            href = target.split(" ", 1)[0]
            if href.startswith(("http://", "https://", "#", "mailto:")):
                continue
            resolved = (path.parent / href).resolve()
            if not resolved.exists():
                problems.append(f"{doc}: internal link target does not exist: {href}")
    return problems


def main() -> int:
    problems = findings()
    if not problems:
        print("validate-docs: PASS - docs and gates agree")
        return 0
    print("validate-docs: FAIL")
    for problem in problems:
        print(f"  - {problem}")
    return 1


if __name__ == "__main__":
    sys.exit(main())