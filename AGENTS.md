# AGENTS.md

> Last reviewed: 2026-11-22

This file is the first stop for any agent (or maintainer) working in this
repository. For git/VCS operations, read this file first, then follow
[MAINTENANCE.md](MAINTENANCE.md) for operational procedures and
[CONTRIBUTING.md](CONTRIBUTING.md) for the canonical validation gate and commit
workflow. It points at the single source of truth for what ships, how to
validate work, and which guardrails apply.

## What ships

- **Package**: `src/ai_repo_sanitize/` (console script: `ai-repo-sanitize`).
- **Runtime behavior**: `check`, `preview`, `rewrite` modes. Rewriting git
  history and pushing are *never* done implicitly - `rewrite` requires
  explicit `--push`. Narrative docs: `README.md`.
- **Repo-only infrastructure** (not shipped): `.github/`, `.githooks/`,
  `scripts/`, and the maintainer documentation set.

## Canonical validation gate

Before claiming completion of a change to `src/`, `tests/`, `scripts`, hooks,
or docs, run the [canonical validation gate](CONTRIBUTING.md#canonical-validation-gate).
`CONTRIBUTING.md` owns the commands and contributor-facing recommendations.

## Guardrails for agents

Use these guardrails as pre-flight checks. If a guardrail cannot be satisfied,
stop, report the blocker and evidence, and do not bypass hooks, checks, or
review gates.

### Docs and drift

- **Docs/code contract:** [`scripts/validate-docs.py`](scripts/validate-docs.py)
  enforces required docs, canonical command parity, and internal link/heading
  fragment resolution. Run it whenever you touch docs; completion signal: it
  reports `validate-docs: PASS - docs and gates agree`.
- **Repo-path claims:** [`scripts/check-doc-claims.py`](scripts/check-doc-claims.py)
  fails when a documented backticked repo path (`src/`, `scripts/`, `tests/`,
  `.githooks/`, `.github/`, `pyproject.toml`, `uv.lock`) does not exist. Run it
  with the gate; completion signal: it exits 0 with no missing-path findings.
- **External URLs:** [`scripts/verify-urls.py`](scripts/verify-urls.py) is the
  weekly/manual URL audit used by CI; for doc URL changes, prefer verifying the
  affected links before handoff.
- **Source of truth:** Read [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
  before changing behavior. For workflow changes, also read the
  [CI workflow-to-script map](docs/reference/ci-workflow-map.md); it is a
  discoverability/parity aid, while workflow YAML remains authoritative for
  triggers, permissions, conditions, and runner behavior.

### Commits and attribution

- **No AI attribution:** Do not add AI-attribution trailers (`Co-authored-by:`
  / "X with" branding) to commit messages. The local
  [`.githooks/commit-msg`](.githooks/commit-msg) hook and CI reject them via
  [`scripts/check-commit-messages.py`](scripts/check-commit-messages.py). Stop
  and rewrite the message; never use `--no-verify` to bypass the check.
- **Commit format:** Use lowercase conventional subjects (`feat:` / `docs:` /
  `fix:`). Implementation/configuration prefixes (`feat:`, `fix:`, `perf:`,
  `refactor:`, `build:`, `ci:`, `chore:`) require non-empty `what:` and `why:`
  paragraphs; CI validates the introduced commit range.
- **Pattern contract:** Attribution-regex changes in
  `src/ai_repo_sanitize/patterns.py` must update
  [`tests/test_patterns.py`](tests/test_patterns.py) in the same change; the
  pattern set is the tool contract.

### Evidence and CI

- **Remote CI is evidence:** Inspect remote CI state before and after pushing
  (`gh run list` or the Actions page). A run can fail with "workflow file issue"
  and *zero jobs*, leaving no logs; stop and treat the local gate as insufficient
  until the remote run is green or the workflow issue is diagnosed. See
  [RESEARCH.md §2](RESEARCH.md#2-git-and-ci-mechanics-empirically-verified).
- **External verification:** Before repeating external-repository verification,
  read [`reports/`](reports/) and follow the read-only temporary-clone procedure
  in [MAINTENANCE.md](MAINTENANCE.md#read-only-external-repository-verification).
  Record each observation as a dated report with a recommendation, link it from
  [RESEARCH.md](RESEARCH.md), and never run rewrite or push commands during
  evidence collection. Prefer `check`/`preview --format json` as raw evidence,
  but keep the reviewed Markdown report as the durable decision record.
- **Primary evidence first:** Base recommendations on primary official
  documentation and recorded empirical findings. When evidence conflicts with
  inference, preference, or speculation, prioritize documented evidence and
  report remaining uncertainty explicitly.
- **Record research:** When web search, official documentation, or another
  external source informs a decision, add the finding and source URL to
  [RESEARCH.md](RESEARCH.md) in the same change. Completion signal: the
  recommendation cites a recorded source, not memory.

### Roadmap and completion

- **Roadmap reconciliation:** Before declaring completion, re-read
  [ROADMAP.md](ROADMAP.md) queued sections and move any item whose evidence
  already exists (landed change, [`reports/`](reports/) entry, or
  [RESEARCH.md](RESEARCH.md) finding) into the completed list in the same
  change. Do not leave finished work queued; `Last reviewed:` is only a
  freshness proxy.

## Git and PR hygiene

- Before a write, record `git status --short`, the current branch, and its
  upstream. Preserve unrelated work; never stage it into the current change.
- Before staging, inspect the full diff and group only one reversible behavior
  per commit. Before committing, inspect the staged diff and run the relevant
  gate.
- Before pushing or merging a PR at the user's request, refresh remote state,
  inspect the PR's mergeability, review decision, and check rollup, and verify
  that its base is current. Run `uv run python scripts/check-pr-readiness.py
  <number>` immediately before merging; add `--require-approval` when the
  current maintainer policy requires one. Never merge a PR merely because it
  once passed CI.
- After a requested PR is merged, synchronize local `master` with its upstream,
  delete the merged local feature branch only when it is fully merged, delete
  the remote feature branch when repository policy allows, run `git fetch
  --prune`, and report the final `git branch -vv --all` and
  `git status --short --branch` state.
- During dependency work, list open Dependabot PRs and flag any that are
  nearing 30 days without a merge, rebase, or close decision. Native
  auto-merge is deferred pending the roadmap's PR-hygiene and branch-ruleset
  work; never create or use a new write-capable bot token solely to automate
  that choice.
