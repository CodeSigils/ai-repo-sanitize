# AGENTS.md

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
  to commit messages; the `.githooks/commit-msg` hook rejects them.
- Commit messages: lowercase conventional style (`feat:` / `docs:` / `fix:`),
  one line + optional body, no trailer attribution.
- External URLs in docs are checked weekly by CI (`scripts/verify-urls.py`).
- Pattern changes (the attribution regexes) must update `tests/test_patterns.py`
  in the same change - the pattern set is the contract of this tool.
- Read `.github/workflows/ci.yml` before changing behavior: it is the
  executable picture of what this repo validates. The docs mirror it, and
  `scripts/validate-docs.py` enforces the agreement between them.