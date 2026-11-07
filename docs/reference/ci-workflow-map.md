# CI workflow-to-script map

> Last reviewed: 2026-11-07

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
