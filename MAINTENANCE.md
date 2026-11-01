# Maintenance

> Last reviewed: 2026-10-31

Operational guide for maintainers of `ai-repo-sanitize`. For contribution
workflow see [CONTRIBUTING.md](CONTRIBUTING.md); for security matters see
[SECURITY.md](SECURITY.md); for the anti-drift strategy see
[ANTIDRIFT.md](ANTIDRIFT.md).

## Sources of truth

- **Agent guidance:** [AGENTS.md](AGENTS.md)
- **Contribution workflow:** [CONTRIBUTING.md](CONTRIBUTING.md)
- **Security policy:** [SECURITY.md](SECURITY.md)
- **Anti-drift strategy:** [ANTIDRIFT.md](ANTIDRIFT.md)
- **Roadmap/research:** [ROADMAP.md](ROADMAP.md), [RESEARCH.md](RESEARCH.md)
- **CI/workflows:** [.github/workflows/](.github/workflows/)
- **Hooks:** [.githooks/](.githooks/)

## Daily operations

### The canonical validation gate

Every change ships only when the [canonical validation gate](CONTRIBUTING.md#canonical-validation-gate)
passes. `CONTRIBUTING.md` owns the command list; this guide owns the operational
meaning of the gate.

`scripts/validate-docs.py` is the drift guard: it fails when the required
documentation set is incomplete, when README.md or CONTRIBUTING.md no longer
mirror the canonical gate, when ci.yml stops running it in the same spelling,
or when an internal link or heading fragment points nowhere. It also verifies
the hook's defined fast suite, rather than claiming that the hook runs pytest.
A passing run confirms:

```
PASS: all 10 required docs present
PASS: README.md and CONTRIBUTING.md list every canonical command
PASS: ci.yml runs every canonical command verbatim
PASS: .githooks/pre-commit runs its documented fast suite
PASS: all internal relative links and Markdown heading fragments resolve
PASS: every required doc carries a current Last reviewed header
```

### Installing hooks

The `.githooks/` directory is repository-local and must be wired up in every
clone you commit from:

```bash
git config core.hooksPath .githooks
```

- `.githooks/pre-commit` runs `ruff check .`, `ty check`, the docs validator,
  and the doc-claims check.
- `.githooks/commit-msg` runs `scripts/check-commit-messages.py`, which
  rejects AI-attribution trailers using the canonical pattern and requires
  non-empty `what:` and `why:` paragraphs for implementation/configuration
  commit types. CI checks the same policy across each push or PR range; do not
  use `--no-verify` as a workaround.

### Dependency refresh

Runtime dependencies are stdlib-only; the dev toolchain is pinned in
`pyproject.toml` (`dependency-groups.dev`) and locked in `uv.lock`. To bump:

```bash
uv sync --all-groups --upgrade
uv run ty check && uv run ruff check . && uv run pytest
```

Commit `pyproject.toml` and `uv.lock` together.

`git-filter-repo` belongs in that development group because the end-to-end
rewrite test and CI quality environment need it. It remains outside normal
package installation: `check`, `preview`, and `hook` are stdlib-only, while
`rewrite` requires the separately installed external executable. This keeps
read-only users from receiving a history-rewrite tool they do not need.

Dependabot proposes grouped weekly updates for the uv toolchain and GitHub
Actions per `.github/dependabot.yml`; merge its PRs only after the canonical
gate passes. The two-PR cap bounds review load, but it is not a freshness
signal: an open PR can prevent newer updates without failing CI.

First merge cycle (2026-10-20): `setup-uv` 10.3.0, `ruff` 0.17.1, and
`ty` 0.0.89 landed as squash merges; Dependabot auto-closed the stale
single-`ty` PR and reopened the bump as one grouped PR, which is expected
regrouping after a mid-cycle merge, not an error. Squash-merging a bot PR
pushes a `dependabot[bot]`-authored commit, so the `quality` job's push-path
commit-message check now exempts that author from body labels (see the CI
layout section); master's validate run was red on 2026-10-20 until that
exemption landed. With Dependabot security updates enabled the same day,
watch whether security-update PRs actually appear — the sibling repository
went months with the feature on and zero security PRs.

### Code security posture

All platform security features were enabled on 2026-10-20 and should stay on:
Dependabot alerts and security updates, malware alerts, secret scanning with
push protection, CodeQL default setup (Python, GitHub Actions runner,
alerts-only), and private vulnerability reporting. [SECURITY.md](SECURITY.md)
directs reporters to the private form, so disabling private reporting would
break that promise. Scanning is platform-side (CodeQL default setup, secret
scanning, push protection, malware alerts); the repo-side layer is the
canonical gate itself. Non-provider secret patterns and validity checks stay
off. Grouped security updates stay off — the dev-tooling surface is small
enough that per-PR review is fine.

### Pull-request hygiene

[.github/workflows/pr-hygiene.yml](.github/workflows/pr-hygiene.yml) runs
daily at 09:29 UTC and on manual dispatch. It has only `contents: read` and
`pull-requests: read` permission. The workflow queries open PR metadata,
writes a job summary, and fails when a Dependabot PR has been open for seven
days or when a PR has 14-day review debt (no review, no update, or a non-default
base branch).

The workflow never comments, labels, closes, approves, or merges a PR. Treat a
failure as a maintainer decision: merge, rebase, or close the listed PR. Native
auto-merge remains disabled; a green bot PR is evidence, not approval.

### Pre-merge readiness

Before merging a requested PR, run the live, read-only readiness check:

```bash
uv run python scripts/check-pr-readiness.py 123
```

It fails for a draft, wrong base, non-clean merge state, missing or non-passing
checks, and—only when `--require-approval` is supplied—a missing approved
review. The same check is available through the manual `pr readiness` Actions
workflow. Neither path merges or modifies the PR; a maintainer still makes the
final merge decision.

### Weekly URL re-check

url-audit.yml runs `scripts/verify-urls.py` on the weekly schedule and on
manual dispatch. It checks every external URL found in non-hidden Markdown
documentation: HEAD by default, a GET fallback for servers that reject HEAD
(405/501), a single retry for transient network errors, and a small thread pool. Duplicate URLs
are checked once and reported per document. On failure, update the dead
links and commit.

### Read-only external repository verification

Use this procedure when a maintainer or agent needs to observe the sanitizer
against another repository. It creates only a disposable local clone; never
run `rewrite`, `--push`, or `--nudge-cache` during this evidence-gathering
workflow.

1. Start from a clean checkout of this repository and create a dedicated
   temporary directory. Keep the path printed by `mktemp` so cleanup cannot
   target a project directory:

   ```bash
   audit_dir=$(mktemp -d "${TMPDIR:-/tmp}/ai-repo-sanitize-audit.XXXXXX")
   git clone --filter=blob:none https://github.com/OWNER/REPOSITORY.git "$audit_dir/repository"
   ```

2. Capture the source state and the checked-ref versus all-ref counts before
   scanning, so the report can state the exact scope that was scanned:

   ```bash
   git -C "$audit_dir/repository" rev-parse HEAD
   git -C "$audit_dir/repository" rev-list --count HEAD
   git -C "$audit_dir/repository" rev-list --all --count
   uv run ai-repo-sanitize check --path "$audit_dir/repository" --format json > "$audit_dir/check.json"
   uv run ai-repo-sanitize preview --path "$audit_dir/repository" --format json > "$audit_dir/preview.json"
   ```

3. For GitHub repositories, optionally record the public contributor snapshot
   without changing the target repository:

   ```bash
   gh api "repos/OWNER/REPOSITORY/contributors?per_page=100"
   ```

4. Treat the JSON files as raw evidence, then add a dated Markdown report
   under `reports/` with the repository, source SHA, the scanned ref scope and
   commit count (also the checked-ref count when it differs), observations, and
   a `Recommendation` section. Link it from `RESEARCH.md`. A finding must state
   the concrete remediation and the tests/docs that must change; a clean run
   should say that no remediation is recommended. The CLI never writes the
   Markdown report.

5. Run the canonical validation gate, then run `uv run python
   scripts/check-doc-claims.py`. After the evidence is safely recorded, remove only the
   exact `audit_dir` created in step 1; do not reuse or recursively delete a
   workspace path.

## CI layout

The executable picture of this repository is
[.github/workflows/ci.yml](.github/workflows/ci.yml) — read it before changing
behavior. The workflow validates on every push to `master` and on every pull
request. [url-audit.yml](.github/workflows/url-audit.yml) separately re-checks
external URLs weekly and on manual dispatch, so a normal push cannot cancel
the scheduled audit: ubuntu-latest migrates to Ubuntu 26 on 2026-10-19; the
`${{ vars.RUNNER_X86_64 || 'ubuntu-latest' }}` pin is the escape hatch if that
breaks anything.

- **quality** — `uv sync --locked`, shellcheck the hooks, then the
  canonical gate: `ruff check .`, `ty check`, `pytest`, `validate-docs.py`;
  it checks each newly introduced commit for attribution trailers and required
  rationale labels (Dependabot is exempt from body labels on the push and
  pull-request paths alike, never from attribution checks);
  a datadef-style doc-coverage step warns (never fails) when a code change
  ships without a matching docs change; a codocia-class claims check fails
  when a doc references a backticked repo path that does not exist;
  `verify-urls.py` runs only on the dedicated URL-audit schedule or manual dispatch.
- **Action pins** — the checkout/setup-python/setup-uv SHAs are pinned
  explicitly in each job. GitHub's docs now describe basic YAML anchor/alias
  support, but anchors are empirically unreliable here (an anchor-based
  workflow was rejected with "workflow file issue" on 2026-10-09; see
  RESEARCH.md §2), so a pin update means updating every occurrence and
  keeping the `# vX.Y.Z` comments in lock-step.
- **python-compat** — the same tests run with the stdlib runner across Python
  3.10 through 3.14, matching `requires-python`. The end-to-end rewrite test
  skips here (no uv/venv, so no git-filter-repo); everything else runs.
- **pr hygiene** — a five-minute scheduled/manual, read-only job that checks
  open PR review debt without re-running the full validation matrix or adding
  write-capable bot automation.
- **pr readiness** — a manually dispatched, read-only pre-merge check for one
  PR's current base, mergeability, checks, and optional approval requirement.

The docs mirror the workflow, and `scripts/validate-docs.py` enforces the
agreement: if ci.yml stops running a canonical command verbatim, the gate
fails. Agents and maintainers should treat the workflow file as the source of
truth for what is validated and when.

## Releasing

Releases are tag-driven and mostly automatic:

1. From `master` with the canonical gate green, create an annotated tag:
   `git tag -a vX.Y.Z -m "..."` and push it: `git push origin vX.Y.Z`.
2. The tag push fires `.github/workflows/release.yml`
   (`on: push tags: v*.*.*`), first verifies that the tagged commit is
   reachable from `master`, then reruns the canonical gate before the
   write-permitted release job builds distributions with `uv build` and
   creates the GitHub Release from `dist/*` with auto-generated notes.
3. The tag push also re-runs `.github/workflows/ci.yml`; its result is useful
   independent evidence, while the release workflow's preflight is the
   release gate. Distributions are attached to the GitHub Release; the project
   does not publish packages to PyPI.
4. Refine the release notes afterwards with `gh release edit vX.Y.Z` (or the
   web UI).

Transport is SSH (`git@github.com:CodeSigils/ai-repo-sanitize.git`) — no token
machinery is needed locally. Tokens only appear inside workflows (`gh release
create` sets `GH_TOKEN` explicitly; auto-provisioned tokens are not picked up
otherwise) or as a one-off HTTPS fallback (see Troubleshooting).

SemVer: the next behavior change ships as `v0.2.0`; bugfix-only hardening
stays a patch.

## The rewrite flow, in summary

The tool's own `rewrite` command is the safe wrapper around `git filter-repo`.
Maintainers who run it on a real repository should remember:

1. A **mirror backup** is created before anything is rewritten — it is the
   escape hatch. Never skip it.
2. The rewrite is **message-only**; the gate compares the tree SHA before and
   after, and aborts when they differ.
3. A residual scan re-checks every rewritten message for the pattern; a
   non-empty result aborts before any push.
4. Publishing is **explicit** (`--push`) and uses `--force-with-lease` against
   a freshly fetched tracking ref.
5. GitHub's contributors surfaces cache independently; the optional
   `--nudge-cache` default-branch toggle is a last resort and never automatic.

## Troubleshooting

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| `validate-docs.py` fails on "missing" a doc | Docs set drifted | Recreate/rename the file; the validator lists what is missing |
| `validate-docs.py` fails on a canonical command | README/CONTRIBUTING/ci.yml spelling drifted | Restore the verbatim `uv run ...` spelling (no `--no-sync` in ci.yml) |
| `ty check` fails | Annotation drift in `src/` | Fix the annotations; ty is strict by design |
| A run fails with "workflow file issue", zero jobs, and no logs | Workflow-file-level validation failure (e.g. YAML anchors/aliases) — jobs never instantiate | `gh run view <id>` and `gh api /repos/{owner}/{repo}/actions/workflows`; fix the YAML; see RESEARCH.md §2 |
| Hook not running | `core.hooksPath` not set in the clone | `git config core.hooksPath .githooks` |
| commit-msg rejects a legit message | Message matches the AI-trailer pattern | If truly a human co-author, adjust the message so the name token differs (see the pattern trade-off in SECURITY.md); never blanket `--no-verify` |
| `git filter-repo` not found at runtime | Tool installed outside the active env | Install it: `uv tool install git-filter-repo` (or `pip install git-filter-repo`) |
| Push fails with SSH | SSH key not configured or rotated | Fall back to HTTPS + token once: `gh auth setup-git`, `git remote set-url origin https://github.com/CodeSigils/ai-repo-sanitize`, push, then restore the SSH URL |

## Automation

- **GitHub Actions:** [.github/workflows/ci.yml](.github/workflows/ci.yml)
  - `quality` (push to `master`/PR): runs canonical gate (`ruff check`, `ty check`, `pytest`, `validate-docs.py`), doc-claims check, commit-message/attribution checks (Dependabot exempt from body labels), and warns on doc-coverage gaps. Shellchecks hooks.
  - `python-compat` (push/PR): matrix Python 3.10–3.14 (stdlib runner); rewrite e2e skipped without uv/git-filter-repo.
  - `pr-hygiene` (schedule/manual): read-only, checks Dependabot PRs open ≥7 days or review debt ≥14 days; never comments/labels/closes/merges.
  - `pr-readiness` (manual `workflow_dispatch`): read-only pre-merge check per PR (mergeability/checks/approval optional).
- **URL audit:** [.github/workflows/url-audit.yml](.github/workflows/url-audit.yml) — weekly + manual dispatch; runs `scripts/verify-urls.py` (HEAD/GET fallback, retry, dedup).
- **Release:** [.github/workflows/release.yml](.github/workflows/release.yml) — tag-driven `v*.*.*`, verifies tag reachable from `master`, reruns canonical gate, builds with `uv build`, creates GitHub Release.
- **Dependency updates:** [.github/dependabot.yml](.github/dependabot.yml) — weekly grouped updates for `github-actions` and `uv` (2-PR cap). Security updates enabled separately (per-PR review).
- **Git hooks:** [.githooks/](.githooks/)
  - `pre-commit`: `ruff check`, `ty check`, docs validator, doc-claims check
  - `commit-msg`: `scripts/check-commit-messages.py` (rejects AI-attribution trailers; requires `what:`/`why:` for implementation/config types)
- **Branch protection:** `master` is PR-only with required status checks; direct pushes blocked. Read CI/workflows as source of truth.

## Volatility

**High** — enforce strict commit policy (no AI-attribution), gate drift, Dependabot grouping, PR hygiene/readiness, weekly URL audit, and tag-driven releases. Inspect CI and PRs daily; preflight high-volatility writes.

## Escalation

- **Policy/gates:** Changes to AI-attribution regex/policy, commit-message rules, canonical gate, or `scripts/validate-docs.py`/`check-doc-claims.py`
- **CI/workflows:** Workflow YAML issues (anchors/aliases), Action pin updates (must update all occurrences), runner changes, required check changes
- **Security/compliance:** Dependabot/security updates, secret scanning/push protection, CodeQL, private vulnerability reporting changes
- **Rewrite/safety:** `rewrite` flow changes, filter-repo behavior, backup/push safety, or contributor cache nudging
- **Dependencies:** `git-filter-repo` placement/grouping, `uv.lock`/`pyproject.toml` toolchain bumps affecting hooks/CI
- **Docs drift:** README/CONTRIBUTING/ci.yml desync detected by `validate-docs.py`

## Logging and state

The tool prints progress to stdout and errors to stderr; it keeps no state
files of its own. All durable state is git history — the mirror backup, the
rewritten clone, and the branch that was force-pushed. Clean up scratch
directories (`/tmp/attribution-cleanup*`-style paths) after a successful run.
