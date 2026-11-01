#!/usr/bin/env python3
"""Drift guard: keep the docs and the validation gates in agreement.

Inspired by the author's py-review-skill validate pattern (CC-BY-4.0 terms of
that repo; logic rewritten here). Enforces a small, verifiable contract:

* Every canonical validation command is listed in README.md and CONTRIBUTING.md.
* Every required documentation file exists (docs inventory never silently
  shrinks).
* Every internal relative link in the markdown docs resolves to a real file
  and heading fragment (title/angle-bracket destinations supported; backtick
  and tilde fenced code blocks are skipped).
* Every required doc carries a current `Last reviewed: YYYY-MM-DD` header
  (missing, unparseable, future, or older than the 90-day window fails).
* CI runs every canonical validation command. The pre-commit hook runs its
  documented fast local checks.

Supported Markdown subset: ATX headings; inline, reference, collapsed, and
shortcut links/images; HTML entities; emphasis/strong; backtick and tilde
fences. Known limits: no nested-parenthesis inline destinations, no indented
code blocks, no reference-style internal-link detection, and approximate
CommonMark closing-fence semantics.

Exit code 0 = contract holds; 1 = findings (printed with file references).
"""

from __future__ import annotations

import html
import re
import sys
import unicodedata
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from urllib.parse import unquote

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
    "docs/README.md",
    "docs/tutorial-first-scan.md",
)

#: Canonical commands. README, CONTRIBUTING, and ci.yml must all reference
#: these exact strings so the documented gate cannot drift from CI.
VALIDATION_COMMANDS: tuple[str, ...] = (
    "uv run ty check",
    "uv run ruff check .",
    "uv run pytest",
    "uv run python scripts/validate-docs.py",
)

#: Fast local checks run by .githooks/pre-commit. The hook deliberately omits
#: pytest; CI is the full canonical gate.
PRE_COMMIT_COMMANDS: tuple[str, ...] = (
    "uv run ruff check .",
    "uv run ty check",
    "uv run python scripts/validate-docs.py",
    "uv run python scripts/check-doc-claims.py",
)

_LINK_RE = re.compile(r"\]\(<?([^)>\s]+)>?(?:\s+[^)]*)?\)")
_REVIEW_RE = re.compile(r"Last reviewed:\s*(\d{4}-\d{2}-\d{2})")
_REVIEW_WINDOW_DAYS = 90


def _rendered_heading_text(heading: str) -> str:
    """Approximate the text GitHub renders before generating a heading slug.

    GitHub slugs rendered text, not raw Markdown. Inline and reference-style
    links contribute their visible text, images contribute their alt text,
    HTML tags disappear, and HTML entities are decoded. Order matters: tags are
    removed before entities are decoded so literal text such as ``&lt;div&gt;``
    survives.
    """
    rendered = re.sub(r"<!--.*?-->", "", heading, flags=re.DOTALL)
    rendered = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", rendered)
    rendered = re.sub(r"!?\[([^\]]*)\]\[[^\]]*\]", r"\1", rendered)
    rendered = re.sub(r"!?\[([^\]]*)\]", r"\1", rendered)
    rendered = re.sub(r"<[^>]+>", "", rendered)
    return html.unescape(rendered).strip()


def _slugify_heading(heading: str) -> str:
    """Return the GitHub-style fragment generated for an ATX heading."""
    rendered = _rendered_heading_text(heading).lower()
    rendered = re.sub(r"(?<!\w)_{1,2}([^_]+)_{1,2}(?!\w)", r"\1", rendered)
    kept = "".join(
        character
        for character in rendered
        if unicodedata.category(character)[0] in {"L", "M", "N"}
        or character in {"_", "-"}
        or character.isspace()
    )
    return re.sub(r"\s", "-", kept)


def _fence_marker(line: str) -> tuple[str, int, str] | None:
    stripped = line.strip()
    for marker in ("`", "~"):
        if stripped.startswith(marker * 3):
            length = len(stripped) - len(stripped.lstrip(marker))
            return marker, length, stripped[length:]
    return None


def _unfenced_lines(markdown: str) -> Iterator[str]:
    fence: tuple[str, int] | None = None
    for line in markdown.splitlines():
        marker = _fence_marker(line)
        if fence is None:
            if marker is not None:
                char, length, _ = marker
                fence = (char, length)
                continue
            yield line
        elif marker is not None:
            char, length, remainder = marker
            if char == fence[0] and length >= fence[1] and not remainder.strip():
                fence = None


def _heading_anchors(markdown: str) -> set[str]:
    """Return GitHub-style anchors for ATX headings outside fenced code blocks."""
    anchors: set[str] = set()
    seen: dict[str, int] = {}
    for line in _unfenced_lines(markdown):
        match = re.match(r"^ {0,3}#{1,6}[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$", line)
        if match is None:
            continue
        slug = _slugify_heading(match.group(1))
        count = seen.get(slug, 0)
        anchor = slug if count == 0 else f"{slug}-{count}"
        while anchor in anchors:
            count += 1
            anchor = f"{slug}-{count}"
        anchors.add(anchor)
        seen[slug] = count + 1
    return anchors


def findings(
    root: Path = ROOT,
    review_window_days: int = _REVIEW_WINDOW_DAYS,
    today: date | None = None,
) -> list[str]:
    """Return every drift finding; an empty list means docs and gates agree.

    *root* defaults to the repository root. *today* and *review_window_days*
    exist so tests/test_validate_docs.py can be deterministic.
    """
    problems: list[str] = []
    today = today or date.today()
    missing = [name for name in REQUIRED_DOCS if not (root / name).is_file()]
    if missing:
        problems.append("missing required docs: " + ", ".join(missing))

    readme_path = root / "README.md"
    readme = readme_path.read_text(encoding="utf-8") if readme_path.is_file() else ""
    contributing = (
        (root / "CONTRIBUTING.md").read_text(encoding="utf-8")
        if (root / "CONTRIBUTING.md").is_file()
        else ""
    )
    for command in VALIDATION_COMMANDS:
        if command not in readme:
            problems.append(f"README.md must list the command: {command}")
        if command not in contributing:
            problems.append(f"CONTRIBUTING.md must list the command: {command}")

    ci = (root / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    for command in VALIDATION_COMMANDS:
        # ci.yml runs the canonical commands verbatim (plain "uv run ..."),
        # so a simple substring check holds.
        if command not in ci:
            problems.append(f"ci.yml must run the canonical command: {command}")

    pre_commit = root / ".githooks" / "pre-commit"
    if pre_commit.is_file():
        hook = pre_commit.read_text(encoding="utf-8")
        for command in PRE_COMMIT_COMMANDS:
            if command not in hook:
                problems.append(f".githooks/pre-commit must run: {command}")

    for doc in REQUIRED_DOCS:
        path = root / doc
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for line in _unfenced_lines(text):
            for target in _LINK_RE.findall(line):
                if target.startswith(("http://", "https://", "mailto:")):
                    continue
                if target.startswith("#"):
                    if target == "#":
                        continue
                    if target[1:] not in _heading_anchors(text):
                        problems.append(f"{doc}: anchor does not exist: {target}")
                    continue
                relative_target, separator, fragment = target.partition("#")
                resolved = (path.parent / relative_target).resolve()
                if not resolved.exists():
                    problems.append(f"{doc}: internal link target does not exist: {target}")
                elif separator and resolved.suffix == ".md":
                    anchors = _heading_anchors(resolved.read_text(encoding="utf-8"))
                    if unquote(fragment).lower() not in anchors:
                        problems.append(
                            f"{doc}: anchor does not exist in {relative_target}: #{fragment}"
                        )
        match = _REVIEW_RE.search(text)
        if match is None:
            problems.append(f"{doc}: missing 'Last reviewed: YYYY-MM-DD' header")
            continue
        try:
            reviewed = date.fromisoformat(match.group(1))
        except ValueError:
            problems.append(f"{doc}: unparseable 'Last reviewed' date: {match.group(1)}")
            continue
        age = (today - reviewed).days
        if age < 0:
            problems.append(f"{doc}: 'Last reviewed' date is in the future: {reviewed}")
        elif age > review_window_days:
            problems.append(
                f"{doc}: last reviewed {age} days ago ({reviewed}); window is "
                f"{review_window_days} days"
            )
    return problems


def _parse_args(argv: list[str]) -> tuple[Path, date, int]:
    """--root DIR, --today YYYY-MM-DD, --review-window N; anything else fails.

    The default invocation stays byte-identical to the canonical command
    (`uv run python scripts/validate-docs.py`), so the CI and hook contracts
    can verify it directly.
    """
    root, today, window = ROOT, date.today(), _REVIEW_WINDOW_DAYS
    pending = list(argv)
    while pending:
        name, *rest = pending
        if name not in ("--root", "--today", "--review-window"):
            raise ValueError(f"unknown option: {name}")
        if not rest:
            raise ValueError(f"{name} requires a value")
        value, *pending = rest
        if name == "--root":
            root = Path(value).resolve()
        elif name == "--today":
            today = date.fromisoformat(value)
        else:
            window = int(value)
    return root, today, window


def main(argv: list[str] | None = None) -> int:
    try:
        root, today, window = _parse_args(list(sys.argv[1:] if argv is None else argv))
    except ValueError as exc:
        print(f"validate-docs: usage error: {exc}")
        return 1
    problems = findings(root=root, review_window_days=window, today=today)
    if not problems:
        print("validate-docs: PASS - docs and gates agree")
        return 0
    print("validate-docs: FAIL")
    for problem in problems:
        print(f"  - {problem}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
