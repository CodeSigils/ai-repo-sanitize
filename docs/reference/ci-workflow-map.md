# CI workflow-to-script map

> Last reviewed: 2026-11-08

This reference makes the local script wiring in GitHub Actions discoverable to
humans and navigation tools. The workflow YAML remains authoritative for
triggers, permissions, matrices, conditions, caches, artifacts, and shell
control flow. This map only records checked-in Python scripts invoked by a
workflow.

`scripts/validate-docs.py` checks this map in both directions: every observed
workflow script must be mapped, every mapped pair must still occur in its
workflow, its script must exist, and the stable marker beneath each entry must
remain present. Add or remove the map entry in the same change as its workflow
wiring.

## Evidence routing

Use this order when a question is about CI wiring, and stop at the first source
that answers it. No summary below overrides the source it points to.

| Question | Canonical source | What it is |
| --- | --- | --- |
| What CI actually does | [`.github/workflows/`](../../.github/workflows/) | Executable source; authoritative wherever this page or the README describes workflow behavior |
| Which script a workflow runs | this page | Navigation layer; completeness is limited to what the parity check can verify |
| Why the wiring is YAML-first and what Graphify can see | [`RESEARCH.md` §5 decision 11](../../RESEARCH.md#5-design-decisions) | Dated decision record with pinned sources |
| What drift the controls cannot detect | [`ANTIDRIFT.md`](../../ANTIDRIFT.md) | Explanation of the guard stack and its limits |
| What policy governs `master` | [`ROADMAP.md`](../../ROADMAP.md) completed baseline and the live GitHub ruleset | Adopted intent in the roadmap; the live ruleset wins |

- **Reusable mechanism:** YAML stays authoritative, a curated workflow-to-script
  map sits beside it, and a validator enforces parity in both directions. Those
  three pieces transfer to another repository.
- **Local only:** workflow, job, step, and script names, the required checks,
  and the `protect-master` ruleset describe this repository; verify them here
  rather than copying a sibling repository's policy.
- **Re-check when:** a workflow script is added, removed, or renamed (parity
  forces the map to change); a trigger, permission, matrix, condition, or runner
  changes (parity does **not** see this, so re-read the YAML and refresh this
  page's review date in the same change); or the pinned Graphify extractor
  commit named in `RESEARCH.md` changes.
- **Supersession:** a newer dated `reports/` entry or `RESEARCH.md` finding
  replaces an older claim on this page; correct the page in that change instead
  of keeping both.
- **Routing failure avoided:** an agent no longer has to read `AGENTS.md`,
  `ANTIDRIFT.md`, `RESEARCH.md`, `ROADMAP.md`, and this page in an arbitrary
  order and guess which statement is current. This order names the owner and
  the re-check trigger for each fact without repeating the facts themselves.

## Validation and release workflows

| Workflow | Job or step | Local script | Purpose |
| --- | --- | --- | --- |
| [ci.yml](../../.github/workflows/ci.yml) | `quality` / Commit-message policy | [`scripts/check-commit-messages.py`](../../scripts/check-commit-messages.py) | Reject attribution trailers and missing required rationale labels. |
| [ci.yml](../../.github/workflows/ci.yml) | `quality` / Docs contract | [`scripts/validate-docs.py`](../../scripts/validate-docs.py) | Enforce documentation and CI-map contracts. |
| [ci.yml](../../.github/workflows/ci.yml) | `quality` / Doc coverage warning | [`scripts/check-doc-coverage.py`](../../scripts/check-doc-coverage.py) | Warn when code changes lack related documentation changes. |
| [ci.yml](../../.github/workflows/ci.yml) | `quality` / Doc claims check | [`scripts/check-doc-claims.py`](../../scripts/check-doc-claims.py) | Reject documented backticked repo paths that do not exist. |
| [release.yml](../../.github/workflows/release.yml) | `verify-release` / Docs contract | [`scripts/validate-docs.py`](../../scripts/validate-docs.py) | Re-run the documentation contract before publishing a tag. |
| [release.yml](../../.github/workflows/release.yml) | `verify-release` / Doc claims check | [`scripts/check-doc-claims.py`](../../scripts/check-doc-claims.py) | Re-run path-claim validation before publishing a tag. |

<!-- ci-script-map: workflow=.github/workflows/ci.yml script=scripts/check-commit-messages.py -->
<!-- ci-script-map: workflow=.github/workflows/ci.yml script=scripts/check-doc-claims.py -->
<!-- ci-script-map: workflow=.github/workflows/ci.yml script=scripts/check-doc-coverage.py -->
<!-- ci-script-map: workflow=.github/workflows/ci.yml script=scripts/validate-docs.py -->
<!-- ci-script-map: workflow=.github/workflows/release.yml script=scripts/check-doc-claims.py -->
<!-- ci-script-map: workflow=.github/workflows/release.yml script=scripts/validate-docs.py -->

## Scheduled and manual maintenance workflows

| Workflow | Job or step | Local script | Purpose |
| --- | --- | --- | --- |
| [pr-hygiene.yml](../../.github/workflows/pr-hygiene.yml) | `hygiene` / Report pull-request hygiene | [`scripts/check-pr-hygiene.py`](../../scripts/check-pr-hygiene.py) | Report stale or review-debt PRs without write automation. |
| [pr-readiness.yml](../../.github/workflows/pr-readiness.yml) | `readiness` / Verify pull-request readiness | [`scripts/check-pr-readiness.py`](../../scripts/check-pr-readiness.py) | Check a requested PR’s live merge conditions. |
| [url-audit.yml](../../.github/workflows/url-audit.yml) | `verify-urls` / Verify external documentation URLs | [`scripts/verify-urls.py`](../../scripts/verify-urls.py) | Audit external documentation links weekly or on demand. |

<!-- ci-script-map: workflow=.github/workflows/pr-hygiene.yml script=scripts/check-pr-hygiene.py -->
<!-- ci-script-map: workflow=.github/workflows/pr-readiness.yml script=scripts/check-pr-readiness.py -->
<!-- ci-script-map: workflow=.github/workflows/url-audit.yml script=scripts/verify-urls.py -->
