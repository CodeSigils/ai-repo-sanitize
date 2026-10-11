# `python-project-workflow-skill` sanitizer check

> Observed: 2026-10-11

## Source

- Repository: `CodeSigils/python-project-workflow-skill`
- Checked-out commit: `7844627f6e16c5d2b522ed909b90b5a6ba249276`
- GitHub contributor identities: `CodeSigils` and `dependabot[bot]`

## Observation

`ai-repo-sanitize check --path .` reported `138 commit(s) scanned, 0 with AI
attribution`; `preview` reported `0 commit(s) would change`.

The clone contained 241 commits across all fetched refs, while `HEAD`/`main`
contained 138. Diagnostic inspection found no attribution pattern in any
fetched ref, so no false negative was observed for this repository.

## Finding

The tool's `git log` calls do not pass `--all`, so `check` and `preview` scan
the checked-out ref's ancestry rather than every fetched ref. This conflicts
with the README claim that `check` scans every commit. Record this as a
follow-up defect: decide whether the intended contract is the selected branch
or all refs, then align implementation, tests, and documentation.

The required product decision is which guarantee the tool should make:

- **Selected-branch scope:** Keep current behavior, change “every commit” to
  “commits reachable from the checked-out/selected branch,” and make that
  scope visible in output.
- **All-ref scope:** Add `--all` to the `git log` calls used by `check`,
  `preview`, and residual verification; test a trailer existing only on a
  second ref; document that all local and fetched refs are checked.

## Recommendation

Adopt all-ref scope. It preserves the documented whole-repository contract:
add `--all` to the `git log` invocations used by `commit_messages` and
`preview_matches`, so `check`, `preview`, and the rewrite residual scan share
the same all-ref coverage. Add tests with an attribution trailer reachable
only from a second ref, then update the user-facing scope documentation to
state that all local and fetched refs are scanned. Keep rewrite publication
scoped to its explicit `--branch`/`--push` plan.

## Resolution

Implemented 2026-10-11: the shared `git log` paths now pass `--all`, and an
integration test verifies that `check` and `preview` find a trailer reachable
only from a second local ref. CLI output and README now state the all-ref
scope. Manual CLI verification against a disposable repository with a clean
`main` and an attributed `side` ref reported `2 commit(s) scanned across all
refs, 1 with AI attribution` (exit 1) and listed the side commit in `preview`
(exit 0). Rewrite publication remains explicit and branch-scoped.
