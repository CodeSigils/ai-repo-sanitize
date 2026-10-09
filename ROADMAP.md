# Roadmap

> Living document. Guarded by [ANTIDRIFT.md](ANTIDRIFT.md): every milestone
> below names the anti-drift check that keeps it honest, and the
> code-changes rule applies — a behavior change to `patterns.py`, `cli.py`,
> or the canonical command set must update this file, `RESEARCH.md`, and
> `ANTIDRIFT.md` in the same commit.
>
> Last reviewed: 2026-10-09 (owner: @CodeSigils)

## How to read this roadmap

Each item states its **goal**, the **anti-drift check** that prevents the
planned work from silently rotting, and a rough **landing** point. Items with
no check attached are deliberately excluded or parked — see
[ANTIDRIFT.md](ANTIDRIFT.md) § Non-goals.

## v0.1 — core flow (current)

Shipped: `check` / `preview` / `rewrite` modes, canonical validation gate,
`.githooks` + CI, and the guarded documentation set.

Completed for v0.1 (2026-10-09):

- **End-to-end rewrite test in CI** — `tests/test_integration.py` drives the full guarded arc:
  seeded trailer commits → `check` → `preview` → `rewrite` with mirror backup → push to a local
  bare remote → clone back and assert both safety invariants (same tree, no attribution) plus
  human co-author survival. Skips where git-filter-repo is absent (the stdlib matrix job).
- **Platform/publish unit tests** — `tests/test_platform.py` locks `split_remote`
  (https/ssh/scp forms; local paths → `None`, the bug class the audit caught), `resolve_token`,
  `get_json` retry-vs-HTTP-error semantics (mocked `urlopen`), and `publish` against a local
  bare remote (offline).
- **Python floor honored** — the python-compat matrix now tests 3.10 through 3.14, matching
  `requires-python`.
- **Docs validator tested (check-the-checker)** — `tests/test_validate_docs.py` drives
  `validate-docs.py` `findings()` over temporary fixtures (missing docs, command drift, broken
  links, freshness states) via `--root`/`--today`/`--review-window`. Org convention borrowed
  from python-project-workflow-skill (`validate-ci.py` + `test-validate-ci.py`).
- **Release machinery** — `.github/workflows/release.yml` accepts a `v*.*.*`
  tag only when its commit is reachable from `master`, reruns the canonical
  gate, then builds distributions (`uv build`) and creates the GitHub Release
  (`gh release create --generate-notes`). First annotated tag: `v0.1.0`
  (2026-10-09). SemVer: minor bump on the next behavior change; bugfix-only
  hardening stays a patch.
- **Citation metadata** — `CITATION.cff` (org convention: present in 3 of 4 inspected
  CodeSigils repos), mirroring the org shape (cff-version 1.2.0, family-names CodeSigils,
  license MIT, type software, repository-code https://github.com/CodeSigils/ai-repo-sanitize).

Anti-drift check for these: they live in `tests/` and `scripts/`, which the canonical
4-command gate runs on every push — they cannot rot silently.

## v0.2 — freshness and coverage gates

Completed for v0.2 (2026-10-09):

- **Freshness gate** — every required doc now carries `Last reviewed: YYYY-MM-DD`
  (headers added to README/CONTRIBUTING/MAINTENANCE/SECURITY/AGENTS.md; RESEARCH, ROADMAP
  and ANTIDRIFT already had them). `scripts/validate-docs.py` hard-fails on missing,
  unparseable, future, or >90-day-old reviews; `--review-window`/`--today`/`--root` flags
  make it testable. ANTIDRIFT.md §6 rewritten from roadmap to enforced.
- **Link extraction hardened** — `validate-docs.py` uses a destination-first
  pattern (titled and angle-bracket destinations parse cleanly) and skips
  fenced code blocks, so docs carrying such link forms or code samples cannot
  false-fail the internal-link check. Balanced-parens destinations remain a
  documented limitation (RESEARCH.md §2).
- **Doc-coverage WARN** — `scripts/check-doc-coverage.py` warns (never fails)
  when a code-path change ships without a matching docs change, using the
  triggering push/PR's exact before-and-after range (datadef warn-not-fail:
  "start as warnings; hard fail invites token edits"); the warning names the
  changed paths and points at ANTIDRIFT.md's code-changes rule.
- **Dependency freshness** — Dependabot enabled 2026-10-09: weekly grouped uv
  + GitHub Actions updates per the org research note; PRs run the canonical
  gate; merged by maintainers; no auto-merge.

| Item | Goal | Anti-drift check |
| --- | --- | --- |
| Optional: `evals/` + `schemas/` dirs | Org skill repos carry evals; only if we add behavior-parity evals for rewrite | Kept optional; if added, mirror the org's `validate-evals.py`-style gate |

## v0.3 — agent-side drift checks

**Completed for v0.3 (2026-10-09):**

- **Agent-side claims check (codocia-class)** — `scripts/check-doc-claims.py`
  fails when a doc references a backticked repo path (src/, scripts/, tests/,
  .githooks/, .github/, pyproject.toml, uv.lock) that does not exist; tested
  in `tests/test_check_doc_claims.py`; wired into pre-commit, CI, and an
  AGENTS.md guardrail.
- **Standing instruction shipped (Staleguard-class)** — the "run the gate
  and fix any drift before claiming completion" rule is concrete: the
  deterministic checker works inside the editing loop, so doc↔code drift
  cannot survive a commit. Heavy `covers` coverage + snapshot hashing remain
  non-goals (see Non-goals).

| Item | Goal | Anti-drift check |
| --- | --- | --- |
| Codocia-class `covers` coverage | Markdown docs declare which code symbols they cover; snapshot hashes of covered files; `check --base main` reports changed-code-without-docs-coverage | The checker runs in CI on the weekly schedule next to `verify-urls.py`, and its policy file is agent-readable (codocia.md pattern) |
| Staleguard-class standing instruction | AGENTS.md gains: "after editing code or docs, run the canonical gate and fix any drift" | Already half-there via AGENTS.md's validation gate; extension makes the re-verification of `RESEARCH`/`ROADMAP`/`ANTIDRIFT` mandatory |

## v0.4 — PR hygiene (current)

Completed for v0.4 (2026-10-09):

- **Read-only PR-hygiene gate** — `scripts/check-pr-hygiene.py` and
  `.github/workflows/pr-hygiene.yml` query only open PR metadata on a daily,
  off-hour schedule and on manual dispatch. The workflow has only
  `contents: read` and `pull-requests: read`, writes a job summary, and fails
  when a Dependabot PR reaches seven days or a PR has 14-day review debt (no
  review, no update, or a stacked base). It never comments, labels, closes,
  approves, or merges. Unit tests cover the findings; CI validates the script
  with the rest of the suite.
- **Commit-message policy gate** — `scripts/check-commit-messages.py` is run
  by the local `commit-msg` hook and across each introduced push/PR commit
  range in the `quality` CI job. It rejects AI-attribution trailers and
  requires a non-empty `what:` / `why:` rationale for implementation,
  configuration, and workflow prefixes. Dependabot may omit labels but is
  never exempt from attribution detection.
- **Live pre-merge readiness gate** — `scripts/check-pr-readiness.py` and the
  manual `pr readiness` workflow inspect one PR immediately before a requested
  merge. They are read-only and fail for stale merge conditions; approval is
  optional until the maintainer branch-policy decision is made.

Anti-drift check: the checker lives under `scripts/`, its behavior is locked in
`tests/test_check_pr_hygiene.py`, and the workflow is actionlint-validated.

## Next (queued 2026-10-09)

- **Behavior-completeness contract** — replace the aspirational claim that every
  code path has a test with a reviewed, machine-checked inventory of public
  command scenarios and rewrite safety invariants. First define stable scenario
  IDs for `check`, `preview`, and `rewrite`, map each to an observable test,
  and add a CI checker that fails when a required scenario loses its mapping.
  Do not adopt a blanket line-coverage target: a percentage cannot prove the
  backup, unchanged-tree, residual-scan, or explicit-push guarantees.
- **Branch-protection policy review** — the active `protect-master` ruleset
  blocks deletion and force-pushes but still permits ordinary direct pushes.
  Recommended baseline: require a pull request and the uniquely named
  `quality` plus `python-compat (3.10)` through `python-compat (3.14)` checks,
  require the branch to be current, and give any maintainer bypass only
  "for pull requests only." Require one approval when a second maintainer is
  available; a sole maintainer should retain PR-only auditability without a
  self-review deadlock. Confirm the owner, reviewer, and bypass policy before
  changing that external configuration.
- **PR-hygiene expansion review** — after 30 days of scheduled evidence,
  decide whether stale remote branches add actionable signal. Do not add a
  write scope, comments, or auto-merge unless the recorded failures show that
  the current read-only report is insufficient. The initial pattern combines
  `repo-health-scan`'s seven-day failure signal, `python-project-workflow`'s
  14-day PR debt criteria, and `zensical-skill`'s stale-state/roadmap gates.
- **Real-world verification session** — two throwaway-repository test legs,
  planned for the next working day:
  1. contributor recognition — run `check` over commits whose co-authors come
     from the awesome-agent-trust contributor list; genuine human
     `Co-authored-by:` lines must be recognized (zero false positives);
  2. intentional pollution — build a temp repository whose commit messages
     deliberately carry the common intrusive AI patterns and assert each one
     is flagged exactly.
  Evidence and outcomes land in RESEARCH.md §7 (future research).
- **PyPI publishing** — add a tag-triggered `uv publish` step to release.yml
  so `uv tool install ai-repo-sanitize` works from PyPI; research first
  (RESEARCH.md §7), trusted publishing preferred over long-lived tokens.
- **Third-party CI integration** — document and exercise the one-step
  `ai-repo-sanitize check` usage in downstream CI (RESEARCH.md §7 first).
- **Low-value fillers (back-burner)** — optional `evals/` + `schemas/` dirs
  (org convention), issue templates, PyPI README polish (only after the PyPI
  publish step exists).

## Non-goals

From [ANTIDRIFT.md](ANTIDRIFT.md) § Non-goals, restated so nobody re-proposes
them: no Vale prose linting, no static site generator, no MCP servers or
semantic/ML drift layers, no external link-checker binaries (stdlib
`verify-urls.py` suffices).

## How to update this file

1. Behavior changes to `patterns.py`, `cli.py`, or the canonical commands:
   update `RESEARCH.md` (mechanics/decisions), `ANTIDRIFT.md` (layers that
   defend it), and this file in the **same commit** — the CI doc-coverage
   warning exists to catch missing updates.
2. Bump `Last reviewed:` on any substantive edit; the v0.2 freshness gate
   will make that a hard requirement.
3. Run `uv run python scripts/validate-docs.py` before finishing any docs
   change; it is part of the canonical gate in
   [CONTRIBUTING.md](CONTRIBUTING.md).
