# AGENTS.md

> Last reviewed: 2026-10-09

This file is the first stop for any agent (or maintainer) working in this
repository. It points at the single source of truth for what ships, how to
validate work, and which guardrails apply.

## What ships

- **Package**: `src/ai_repo_sanitize/` (console script: `ai-repo-sanitize`).
- **Runtime behavior**: `check`, `preview`, `rewrite` modes. Rewriting git
  history and pushing are *never* done implicitly - `rewrite` requires
  explicit `--push`. Narrative docs: `README.md`.
- **Repo-only infrastructure** (not shipped): `.github/`, `.githooks/`,
  `scripts/`, the documentation set (`RESEARCH.md`, `ROADMAP.md`,
  `ANTIDRIFT.md`, `MAINTENANCE.md`, `SECURITY.md`, `CONTRIBUTING.md`).

## Canonical validation gate

Run the full gate below **before claiming completion** of any change that
touches `src/`, `tests/`, `scripts/`, hooks, or docs:

```sh
uv run ty check
uv run ruff check .
uv run pytest
uv run python scripts/validate-docs.py
```

Interactive version with recommendations: `CONTRIBUTING.md`.

## Guardrails for agents

- Docs and code must never drift apart: `scripts/validate-docs.py` enforces
  that README/CONTRIBUTING list every canonical command and that internal
  links resolve. Run it whenever you touch docs.
- Do not add AI-attribution trailers (`Co-authored-by:` / "X with" branding)
  to commit messages; the local hook and CI reject them.
- Commit messages: lowercase conventional style (`feat:` / `docs:` / `fix:`),
  no trailer attribution. Implementation/configuration prefixes (`feat:`,
  `fix:`, `perf:`, `refactor:`, `build:`, `ci:`, `chore:`) require non-empty
  `what:` and `why:` paragraphs; CI validates the introduced commit range.
- External URLs in docs are checked weekly by CI (`scripts/verify-urls.py`).
- Pattern changes (the attribution regexes) must update `tests/test_patterns.py`
  in the same change - the pattern set is the contract of this tool.
- Read `.github/workflows/ci.yml` before changing behavior: it is the
  executable picture of what this repo validates. The docs mirror it, and
  `scripts/validate-docs.py` enforces the agreement between them.
- Inspect the remote CI state before and after pushing (`gh run list` or the
  Actions page). A run can fail with "workflow file issue" and *zero jobs*,
  leaving no logs — the local gate alone does not prove CI is green. See
  `RESEARCH.md` §2 for the detection pattern.

- Agent-side claims check: `scripts/check-doc-claims.py` fails when a
  documented backticked repo path (src/, scripts/, tests/, .githooks/,
  .github/, pyproject.toml, uv.lock) does not exist. Run it with the gate —
  it is the codocia-class half that works inside the editing loop.

## Git and PR hygiene

- Before a write, record `git status --short`, the current branch, and its
  upstream. Preserve unrelated work; never stage it into the current change.
- Before staging, inspect the full diff and group only one reversible behavior
  per commit. Before committing, inspect the staged diff and run the relevant
  gate.
- Before pushing or merging a PR at the user's request, refresh remote state,
  inspect the PR's mergeability, review decision, and check rollup, and verify
  that its base is current. Never merge a PR merely because it once passed CI.
- During dependency work, list open Dependabot PRs and flag any that are
  nearing 30 days without a merge, rebase, or close decision. Native
  auto-merge is deferred pending the roadmap's PR-hygiene and branch-ruleset
  work; never create or use a new write-capable bot token solely to automate
  that choice.
