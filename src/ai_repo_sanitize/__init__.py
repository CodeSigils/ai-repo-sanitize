"""ai-repo-sanitize: strip AI attribution trailers from git history safely.

Three modes, one pattern library:

- ``check``    CI gate: fail when attribution trailers appear in a ref/range
- ``preview``  list commits a rewrite would change, before changing anything
- ``rewrite``  mirror-backup, filter-repo message rewrite, verify, and
               force-with-lease push (push only when explicitly requested)
- ``hook``     emit commit-msg / pre-commit templates derived from the same
               patterns used by every other mode
"""

__version__ = "0.1.0"