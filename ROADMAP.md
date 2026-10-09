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

In-flight polish for v0.1:

| Item | Goal | Anti-drift check |
| --- | --- | --- |
| `.githooks/pre-push` | Run the canonical gate before push (org uses pre-push in 2 of 4 repos) | Hook lists the same 4 canonical commands, so the substring contract in `validate-docs.py` extends naturally |

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
- **Release machinery** — `.github/workflows/release.yml` syncs, builds distributions
  (`uv build`), and creates the GitHub Release on any `v*.*.*` tag push
  (`gh release create --generate-notes`). First annotated tag: `v0.1.0` (2026-10-09).
  SemVer: minor bump on the next behavior change; bugfix-only hardening stays a patch.
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

| Item | Goal | Anti-drift check |
| --- | --- | --- |
| Git-diff doc-coverage warning | CI step warns (does not fail) when a `src/` or `.githooks/` change ships without a matching docs change (datadef §4 Danger rule: "start as warnings; hard fail invites token edits") | Warning text points at `ANTIDRIFT.md` § code-changes rule so the fix is mechanical |
| Optional: `evals/` + `schemas/` dirs | Org skill repos carry evals; only if we add behavior-parity evals for rewrite | Kept optional; if added, mirror the org's `validate-evals.py`-style gate |

## v0.3 — agent-side drift checks

| Item | Goal | Anti-drift check |
| --- | --- | --- |
| Codocia-class `covers` coverage | Markdown docs declare which code symbols they cover; snapshot hashes of covered files; `check --base main` reports changed-code-without-docs-coverage | The checker runs in CI on the weekly schedule next to `verify-urls.py`, and its policy file is agent-readable (codocia.md pattern) |
| Staleguard-class standing instruction | AGENTS.md gains: "after editing code or docs, run the canonical gate and fix any drift" | Already half-there via AGENTS.md's validation gate; extension makes the re-verification of `RESEARCH`/`ROADMAP`/`ANTIDRIFT` mandatory |

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