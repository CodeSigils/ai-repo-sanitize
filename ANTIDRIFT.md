# Anti-Drift Strategy (ANTIDRIFT.md)

Last reviewed: 2026-10-09. Re-verify per the [code-changes rule](#the-code-changes-rule): when
`src/ai_repo_sanitize/patterns.py`, `src/ai_repo_sanitize/cli.py`, or the canonical validation
commands change, re-read this file and `RESEARCH.md` and update anything stale in the same commit.

## 1. Why this file exists

`ai-repo-sanitize` rewrites git history and must therefore be *extremely* honest about what it
does. The same honesty applies to its own documentation: AI agents read a repository's docs as
codebase input, and stale docs mislead them as badly as stale code does. This file is the
deliberate, evidence-backed strategy for keeping every doc in this repository truthful.

The core limit, stated plainly: **CI detects proxies for outdatedness, not outdatedness
itself.** Whether a paragraph still tells the truth is not machine-checkable from the text
alone. So this strategy makes every machine-checkable claim *actually checked*, and keeps human
re-review a scheduled, named duty for the rest.

## 2. Layered defenses (implemented)

| Layer | Mechanism | Catches |
| --- | --- | --- |
| 0. Hooks | `.githooks/commit-msg` (attribution patterns), `.githooks/pre-commit` (ruff + docs validator) | bad commit messages and doc regressions before they enter history |
| 1. Contract | `scripts/validate-docs.py`: README + CONTRIBUTING must list the 4 canonical commands verbatim; `ci.yml` must run them verbatim; required docs exist; internal links resolve | doc/command drift, missing or dead-linked docs |
| 2. Canonical gate | `uv run ty check` / `uv run ruff check .` / `uv run pytest` / `uv run python scripts/validate-docs.py` — referenced in AGENTS.md, CONTRIBUTING.md, MAINTENANCE.md and enforced in CI | any change that breaks the project's own contract |
| 3. CI | `ci.yml`: full gate on every push to `master`, tag push, and PR; weekly scheduled job runs `scripts/verify-urls.py` (external links). Its doc-coverage warning compares the triggering push/PR range rather than the checked-out branch tip. | stale external references, third-party rot |
| 4. Single source of truth | `src/ai_repo_sanitize/patterns.py` defines the attribution pattern once; check, preview, rewrite and the hook all derive from it | the check/rewrite/hook disagreeing with each other |

The two strongest rules, borrowed from CodeSigils practice and the docs-as-code literature:

- **One change, one commit.** The person changing the code is right there to change the doc.
  A behavior change that does not touch the relevant doc in the same commit is incomplete work.
- **Same-change test discipline.** A pattern change must update `tests/test_patterns.py` in the
  same commit; a validator change must update its own tests.

## 3. External-link policy

External links are checked on a **schedule, not per-PR** (`verify-urls.py` runs in the weekly CI
job, and on workflow_dispatch for humans). A third-party outage must never block a merge, but a
dead source must be found within a week. `verify-urls.py` is a stdlib-only HEAD checker — the
deliberate `lychee` alternative (see RESEARCH.md).

## 4. CodeSigils org evidence

The org's active repos (repo-health-scan, repo-architecture-skill, zensical-skill,
python-project-workflow-skill, and this one) all converge on the same guard stack:

1. `AGENTS.md` + `SECURITY.md` + `LICENSE` + `pyproject.toml` + `uv.lock` + `docs/` as minimums.
2. `.githooks/` with a `pre-commit`; `pre-push` where the hook set is heavier.
3. `scripts/verify-urls.py` in three of four (zensical-skill uses README-inventory +
   commit-message checks instead).
4. A `validate*.py` contract enforced in CI, in every repo.
5. Roadmap kept as a guarded markdown file at the root (repo-health-scan).
6. Check-the-checker: python-project-workflow-skill ships `validate-ci.py` +
   `test-validate-ci.py` — tests for the validator itself.
7. Commit-convention guards at hook level (`check-commit-convention.py`,
   `check_commit_messages.py`) — our `.githooks/commit-msg` matches this practice.

## 5. The code-changes rule

A doc is stale when the code it describes changes and the doc is not updated. Implement this as
a standing, mechanical rule (docrot's `code_changes` strategy; codocia's `covers` concept):

- Any change to `src/ai_repo_sanitize/patterns.py` or `src/ai_repo_sanitize/cli.py` triggers
  re-verification of ANTIDRIFT.md, RESEARCH.md and ROADMAP.md in the same commit.
- Any change to the canonical validation commands (CONTRIBUTING.md/validate-docs.py/ci.yml)
  triggers the same re-verification.
- CI warns (does not fail) when a change under `src/` or `scripts/` has no matching change under
  `docs/` or root `*.md` files — warnings first; a hard fail invites token edits (datadef).

## 6. Freshness metadata (enforced)

Every required doc (the `REQUIRED_DOCS` set in `scripts/validate-docs.py`) carries a
`Last reviewed: YYYY-MM-DD` header. The validator enforces a hard 90-day window: a missing
header, an unparseable date, a future date, or a review older than the window fails the
canonical gate (window configurable with `--review-window`; `--root`/`--today` keep tests
deterministic). The pure interval check is only a proxy, but a *named, dated* review beats an
unnamed, undated one — keep the header honest by bumping it in the same commit that
substantively edits the file.

## 7. Explicit non-goals

These are deliberately NOT adopted for this repo (evidence in RESEARCH.md):

- Prose style linting (Vale-style) — low signal for a CLI tool with terse docs.
- Static site generator — markdown + PR review is the org norm.
- MCP servers / semantic / vector-search freshness layers (Staleguard L2-L3,
  doc-freshness-checker) — real capability, heavy machinery; the deterministic Layer-1 checks
  are the ones that pay for themselves here.
- Replacing `verify-urls.py` with the lychee binary — stdlib satisfies the need.

## 8. Success metrics

- `uv run python scripts/validate-docs.py` passes on every change (it is part of the gate).
- The weekly CI run reports zero dead external links.
- The canonical commands listed in README.md and CONTRIBUTING.md never diverge from `ci.yml`
  or `.githooks/pre-commit` (enforced by Layer 1).
- Every roadmap item in ROADMAP.md names the ANTIDRIFT check that keeps it honest.
- No commit in this repository has ever carried an AI-attribution trailer (Layer 0).
