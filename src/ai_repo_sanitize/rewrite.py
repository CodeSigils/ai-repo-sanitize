"""The rewrite pass: ``git filter-repo`` with a generated ``--message-callback``.

Filter-repo is the tool Git itself recommends over ``filter-branch``; we wrap
it rather than reimplement history rewriting. The callback body is derived
from the one canonical pattern set, so the rewrite can never disagree with
the preview or the check mode.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from .git_utils import GitError
from .patterns import ATTRIBUTION_RE

__all__ = ["callback_source", "rewrite_messages"]

#: Function body embedded by filter-repo (it wraps the code as a function of
#: ``message`` that must return the new message). Shape verified against
#: git-filter-repo 2.47: a multi-line body (import + list comprehension +
#: trailing-blank trim + return) is supported.
_CALLBACK_TEMPLATE = """\
import re
_PATTERN = re.compile({pattern!r})
kept = [line for line in message.split(b"\\n") if not _PATTERN.search(line)]
while kept and not kept[-1].strip():
    kept.pop()
return b"\\n".join(kept) + (b"\\n" if kept else b"")
"""


def callback_source() -> str:
    """Return the self-contained Python body for ``--message-callback``."""
    return _CALLBACK_TEMPLATE.format(pattern=ATTRIBUTION_RE.pattern)


def _find_filter_repo() -> str:
    """Locate the git-filter-repo executable, PATH then the active env bin."""
    executable = shutil.which("git-filter-repo")
    if executable is not None:
        return executable
    candidate = Path(sys.executable).parent / "git-filter-repo"
    if candidate.is_file():
        return str(candidate)
    raise GitError(
        "git-filter-repo not found; install it first, e.g. "
        "`uv tool install git-filter-repo` or `pip install git-filter-repo`"
    )


def rewrite_messages(work: Path) -> subprocess.CompletedProcess[str]:
    """Rewrite commit messages in the clone at *work* (no push happens here).

    ``--force`` is required because filter-repo refuses to run outside a
    fresh clone; the clone is fresh by construction, so the flag only guards
    against the check being fooled by a reused directory.
    """
    executable = _find_filter_repo()
    result = subprocess.run(
        [executable, "--force", f"--message-callback={callback_source()}"],
        cwd=work,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip()
        raise GitError("git filter-repo failed" + (f": {detail}" if detail else ""))
    return result