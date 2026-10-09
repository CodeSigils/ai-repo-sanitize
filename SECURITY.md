# Security Policy

> Last reviewed: 2026-10-09

## Scope

ai-repo-sanitize manipulates commit history — a high-trust operation. Treat
any defect as a security defect if it could cause a repository owner to
believe attribution was removed when it was not, or to lose data.

In particular, the matching trade-off in `src/ai_repo_sanitize/patterns.py`
matters here:

- A `Co-authored-by` line is only removed when one of the known agent names
  appears on it (so human co-authors are preserved by design).
- A branded line (`Ultraworked with`, `Generated with`, `Assisted with`) is
  always treated as AI attribution.

A finding that a name on the agent list matches an innocent human trailer, or
that a variant phrasing bypasses the brand-line rule, is a legitimate security
report against the pattern set — and a test change is the fix.

## Reporting

- Do **not** open a public issue for suspected vulnerabilities.
- Report privately via GitHub's private vulnerability reporting on this
  repository (Security -> Report a vulnerability).
- Include the ai-repo-sanitize version, the git version, the exact trailers
  involved, and a minimal reproduction (prefer a `git log` excerpt over
  actual history).
- You will get an acknowledgment within five working days and a timeline for
  a fix and release.

## Handling

- Fixes land with a regression test in `tests/test_patterns.py` and an update
  to `docs/` in the same commit, per `CONTRIBUTING.md`.
- Security fixes are released promptly and announced in the release notes.

## Commit and release integrity

- Releases require a `v*.*.*` tag whose commit is reachable from `master`; the
  release workflow reruns the canonical gate before it receives write
  permission to publish.
- CI (`validate` workflow) runs the canonical gate on every push to `master`,
  tag push, and pull request; scheduled runs also re-check external URLs
  documented in the repository.
- No maintainer commit carries an AI-attribution trailer; the
  `.githooks/commit-msg` hook rejects them on every clone that installed the
  hooks.

## Dependency policy

- Runtime dependencies are intentionally minimal (the stdlib). The only
  external binary invoked is `git` (and `gh` for the optional cache-nudge).
- Dev dependencies are pinned via `uv.lock`; keep them current with
  dependency updates through the standard review process.
