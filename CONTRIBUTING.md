# Contributing

> Last reviewed: 2026-10-09

ai-repo-sanitize is a focused tool: it detects and removes AI-attribution
trailers from git history, exposing every step so a maintainer can audit the
rewrite before anything is pushed. Keep contributions small, tested, and
documented in the same change.

## Setup

Requires [uv](https://docs.astral.sh/uv/) and Python >= 3.10.

```bash
uv sync --all-groups
```

This installs the dev group (pytest, ruff, ty, git-filter-repo) and the package
in editable mode.

git-filter-repo is a *separate* tool that ai-repo-sanitize shells out to for
the rewrite. Install it in the environment the tool runs from, for example
`uv tool install git-filter-repo`, or note it in your own environment setup.

## Canonical validation gate

Run every command below before claiming a change is complete:

```bash
uv run ty check
uv run ruff check .
uv run pytest
uv run python scripts/validate-docs.py
```

The last one is the documentation drift guard: it fails when a documented
claim, a canonical command, or an internal link stops matching the repository.
If it fails after your change, the change is not complete.

## Exit codes

The CLI and the scripts use a small, documented exit-code contract:

- `0` — clean: `check` found no attribution; `rewrite` verified and published.
- `1` — attribution found, a safety gate stopped the run, or an operation failed.
- `2` — usage error (unknown subcommand or bad flags; argparse's default).

`scripts/validate-docs.py` and `scripts/verify-urls.py` also exit 0 on success
and 1 on findings. Keep the contract stable: adding a new code requires
updating this section, the README table, and `tests/test_cli.py` in the same
change.

## Code style

- Type-annotate everything; `ty` runs in strict mode and the package targets
  Python >= 3.10 (`from __future__ import annotations` is used throughout).
- `ruff` is configured in `pyproject.toml` (E, F, I, UP, B, SIM, C4, RUF,
  line length 100). Run `uv run ruff check . --fix` to auto-fix trivial
  findings, then fix the rest by hand.
- Prefer shell-free subprocess calls: `git_utils` passes explicit argv lists
  and never uses a shell. Shell appears only in the POSIX `.githooks`, kept
  portable on purpose (POSIX flags only: `-n -i -E`, never `-P` or `\b`).

## Tests

- New behavior ships with tests in `tests/`.
- The pattern set in `src/ai_repo_sanitize/patterns.py` is the single source
  of truth for every mode. **Changing it must update
  `tests/test_patterns.py` in the same commit**, and vice-versa: a test that
  documents different matching must first change the pattern.
- Run the suite with `uv run pytest`.

## Docs contract

`scripts/validate-docs.py` enforces a small docs-code contract:

- `README.md` and this file must list every canonical command verbatim.
- `.github/workflows/ci.yml` must run the same command strings (plain
  `uv run ...`; do not "optimize" with `--no-sync`).
- Required docs exist (README, CONTRIBUTING, SECURITY, MAINTENANCE, RESEARCH,
  ROADMAP, ANTIDRIFT, AGENTS.md).
- Internal relative links resolve to real files.

A behavior or command change therefore touches code *and* the docs that
describe it in one commit. This is deliberate.

## Commits

Follow the repository's commit style:

- Lowercase conventional subjects: `feat:`, `docs:`, `fix:`, `test:`,
  `chore:`. One line, plus a body only when it adds context.
- No AI-attribution trailers (`Co-authored-by: Some Agent <...>`,
  `Ultraworked with ...` lines). The `.githooks/commit-msg` hook rejects them.
- Install the hooks once per clone:

```bash
git config core.hooksPath .githooks
```

The pre-commit hook runs ruff and the docs validator on every commit; the
commit-msg hook rejects attribution trailers. `--no-verify` bypasses both but
should be reserved for emergencies.

## Reviewing

Reviewers verify the canonical gate, that tests and docs match behavior, and
that no change silently widens what counts as "AI attribution" (see
`SECURITY.md` for the matching trade-off).