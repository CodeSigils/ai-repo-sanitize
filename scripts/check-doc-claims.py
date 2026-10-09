"""codocia-class claims check: every backticked repo path in the docs must exist.

If a documentation file points at a source file that does not exist, the doc
and the code have already drifted. This is the deterministic half of the
codocia/Staleguard class of checks: it runs inside the editing loop (AGENTS.md
standing instruction, pre-commit) and in CI, and it only ever reports facts.

Exit 0 when every claimed path exists; 1 when a doc references a missing path.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

REQUIRED_DOCS = (
    "README.md",
    "CONTRIBUTING.md",
    "SECURITY.md",
    "MAINTENANCE.md",
    "RESEARCH.md",
    "ROADMAP.md",
    "ANTIDRIFT.md",
    "AGENTS.md",
)

ROOT = Path(__file__).resolve().parent.parent

_TOKEN_RE = re.compile(r"`([^`]+)`")
_CODE_PREFIXES = ("src/", "scripts/", "tests/", ".githooks/", ".github/")
_BARE_FILES = ("pyproject.toml", "uv.lock", ".python-version", ".gitignore")
_TRAILING_PUNCT = ".,;:!?"


def claimed_paths(doc_text: str) -> list[str]:
    """Backticked relative-path tokens in *doc_text* that name repo files."""
    claimed: list[str] = []
    for token in _TOKEN_RE.findall(doc_text):
        token = token.strip()
        if not token or token.endswith("/"):
            continue
        if any(needle in token for needle in (" ", "$", "{", "http")):
            continue
        if not (token.startswith(_CODE_PREFIXES) or token in _BARE_FILES):
            continue
        claimed.append(token.rstrip(_TRAILING_PUNCT))
    return claimed


def findings(docs: tuple[str, ...] = REQUIRED_DOCS, root: Path = ROOT) -> list[str]:
    """Return one finding per documented path that does not exist under *root*."""
    problems: list[str] = []
    for doc in docs:
        path = root / doc
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for token in claimed_paths(text):
            if not (root / token).resolve().exists():
                problems.append(f"{doc}: documented path does not exist: {token}")
    return problems


def _parse_args(argv: list[str]) -> Path:
    root = ROOT
    index = 0
    while index < len(argv):
        if argv[index] == "--root":
            if index + 1 >= len(argv):
                raise ValueError("--root requires a directory argument")
            root = Path(argv[index + 1])
            index += 2
        else:
            raise ValueError(f"unexpected argument: {argv[index]}")
    return root


def main(argv: list[str] | None = None) -> int:
    try:
        root = _parse_args([] if argv is None else argv)
    except ValueError as exc:
        print(f"check-doc-claims: usage error: {exc}")
        return 1
    problems = findings(root=root)
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        print(f"check-doc-claims: FAIL ({len(problems)} documented path(s) missing)")
        return 1
    print("check-doc-claims: PASS — every documented path exists")
    return 0


if __name__ == "__main__":
    sys.exit(main())