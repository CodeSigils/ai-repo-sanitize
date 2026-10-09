"""Detection patterns for AI attribution trailers.

One canonical pattern set drives *every* mode of ai-repo-sanitize: preview,
rewrite, check, and the commit-msg hook. Keeping the patterns in exactly one
place is what makes the modes agree with one another.

Two representations are derived from the same constants:

* ``ATTRIBUTION_RE`` - a compiled byte regex used by the Python code paths
  (check, rewrite callback, residual scan). It matches a whole attribution
  line when one of ``AGENT_NAMES`` appears in a ``Co-authored-by`` trailer or
  when the line is an ``Ultraworked with`` / ``Generated with`` /
  ``Assisted with`` branding line.
* ``GIT_GREP_PATTERN`` - the equivalent POSIX extended regular expression for
  ``git log --grep`` (git's own engine, so the flags ``-i -E`` behave the same
  on Linux and macOS). Used only for the preview listing.
"""

from __future__ import annotations

import re

__all__ = [
    "AGENT_NAMES",
    "ATTRIBUTION_RE",
    "GIT_GREP_PATTERN",
    "has_attribution",
    "strip_attribution",
]

#: Tool/agent names that mark a ``Co-authored-by`` trailer as AI-generated
#: rather than a human co-author. A trailer is only dropped when one of these
#: names appears on the same line.
AGENT_NAMES: tuple[str, ...] = (
    "sisyphus",
    "claude",
    "opencode",
    "codex",
    "copilot",
    "cursor",
    "devin",
)

_AGENTS: str = "|".join(re.escape(name) for name in AGENT_NAMES)

#: Matches a line that is an AI attribution trailer: either a
#: ``Co-authored-by`` line naming one of AGENT_NAMES or an
#: ``(ultraworked|generated|assisted) with ...`` branding line.
#:
#: Trade-off, documented and tested: a human ``Co-authored-by`` trailer is
#: preserved unless one of the agent names appears in it; a branded line is
#: always treated as AI attribution.
ATTRIBUTION_RE: re.Pattern[bytes] = re.compile(
    rb"(?i)(?:co-authored-by:[^\r\n]*(?:"
    + _AGENTS.encode("ascii")
    + rb")|(?:ultraworked|generated|assisted)\s+with\b[^\r\n]*)"
)

#: Extended-regex form for ``git log -i -E --grep``. Deliberately avoids
#: ``\b`` (git's regex engine is not POSIX-clean about it) and mirrors
#: ATTRIBUTION_RE's alternatives.
GIT_GREP_PATTERN: str = (
    rf"co-authored-by:.*({_AGENTS})|(ultraworked|generated|assisted) with"
)


def has_attribution(message: bytes) -> bool:
    """Return True when *message* contains at least one attribution line."""
    return any(ATTRIBUTION_RE.search(line) for line in message.split(b"\n"))


def strip_attribution(message: bytes) -> bytes:
    """Remove attribution lines from *message*, trimming trailing blanks.

    Line-based (not substring-based): a multi-line message keeps its subject
    and body intact, only matching lines are dropped, and any blank lines
    left dangling at the end are removed. The result always ends with exactly
    one newline when non-empty.
    """
    kept = [line for line in message.split(b"\n") if not ATTRIBUTION_RE.search(line)]
    while kept and not kept[-1].strip():
        kept.pop()
    return b"\n".join(kept) + (b"\n" if kept else b"")