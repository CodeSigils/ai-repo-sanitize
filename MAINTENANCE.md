# Maintenance

> Last reviewed: 2026-10-09

Operational guide for maintainers of `ai-repo-sanitize`. For contribution
workflow see [CONTRIBUTING.md](CONTRIBUTING.md); for security matters see
[SECURITY.md](SECURITY.md); for the anti-drift strategy see
[ANTIDRIFT.md](ANTIDRIFT.md).

## Daily operations

### The canonical validation gate

Every change ships only when the four canonical commands pass:

```bash
uv run ty check
uv run ruff check .
uv run pytest
uv run python scripts/validate-docs.py
```

`scripts/validate-docs.py` is the drift guard: it fails when the required
documentation set is incomplete, when README.md or CONTRIBUTING.md no longer
list the canonical commands verbatim, when ci.yml stops running them in the
same spelling, or when an internal link points nowhere. A passing run looks
like:

```
PASS: all 8 required docs present
PASS: README.md and CONTRIBUTING.md list every canonical command
PASS: ci.yml runs every canonical command verbatim
PASS: .githooks/pre-commit runs ruff check and the docs validator
PASS: all internal relative links resolve
PASS: every required doc carries a current Last reviewed header
```

### Installing hooks

The `.githooks/` directory is repository-local and must be wired up in every
clone you commit from:

```bash
git config core.hooksPath .githooks
```

- `.githooks/pre-commit` runs `ruff check .`, `ty check`, and the docs validator.
- `.githooks/commit-msg` rejects commit messages that carry AI-attribution
  trailers (see the canonical pattern in `src/ai_repo_sanitize/patterns.py`).
  `--no-verify` is reserved for emergencies and never for routine work.

### Dependency refresh

Runtime dependencies are stdlib-only; the dev toolchain is pinned in
`pyproject.toml` (`dependency-groups.dev`) and locked in `uv.lock`. To bump:

```bash
uv sync --all-groups --upgrade
uv run ty check && uv run ruff check . && uv run pytest
```

Commit `pyproject.toml` and `uv.lock` together.

Dependabot proposes grouped weekly updates for the uv toolchain and GitHub
Actions per `.github/dependabot.yml`; merge its PRs only after the canonical
gate passes.

### Weekly URL re-check

ci.yml runs `scripts/verify-urls.py` on the weekly schedule and on manual
dispatch. It checks every external URL found in the documentation set: HEAD
by default, a GET fallback for servers that reject HEAD (405/501), a single
retry for transient network errors, and a small thread pool. Duplicate URLs
are checked once and reported per document. On failure, update the dead
links and commit.

## CI layout

The executable picture of this repository is
[.github/workflows/ci.yml](.github/workflows/ci.yml) — read it before changing
behavior. The workflow validates on every push to `master` and on every pull
request, and re-checks external URLs on a weekly schedule: ubuntu-latest
migrates to Ubuntu 26 on 2026-10-19; the `${{ vars.RUNNER_X86_64 || 'ubuntu-latest' }}` pin is the escape hatch if that breaks anything.

- **quality** — `uv sync --locked`, shellcheck the hooks, then the
  canonical gate: `ruff check .`, `ty check`, `pytest`, `validate-docs.py`;
  a datadef-style doc-coverage step warns (never fails) when a code change
  ships without a matching docs change; a codocia-class claims check fails
  when a doc references a backticked repo path that does not exist;
  `verify-urls.py` runs only on schedule or manual dispatch.
- **Action pins** — the checkout/setup-python/setup-uv SHAs are pinned
  explicitly in each job. GitHub Actions does not support YAML anchors or
  aliases in workflow files (empirically verified 2026-10-09; see
  RESEARCH.md §2), so a pin update means updating every occurrence and
  keeping the `# vX.Y.Z` comments in lock-step.
- **python-compat** — the same tests run with the stdlib runner across Python
  3.10 through 3.14, matching `requires-python`. The end-to-end rewrite test
  skips here (no uv/venv, so no git-filter-repo); everything else runs.

The docs mirror the workflow, and `scripts/validate-docs.py` enforces the
agreement: if ci.yml stops running a canonical command verbatim, the gate
fails. Agents and maintainers should treat the workflow file as the source of
truth for what is validated and when.

## Releasing

Releases are tag-driven and mostly automatic:

1. From `master` with the canonical gate green, create an annotated tag:
   `git tag -a vX.Y.Z -m "..."` and push it: `git push origin vX.Y.Z`.
2. The tag push fires `.github/workflows/release.yml`
   (`on: push tags: v*.*.*`), which syncs the locked environment, builds
   distributions with `uv build`, and creates the GitHub Release from
   `dist/*` with auto-generated notes.
3. The tag push re-runs `.github/workflows/ci.yml` as well — path filters do
   not block tag pushes in practice (verified 2026-10-09: the v0.1.0 tag push
   ran the full validate workflow to success). The canonical gate therefore
   runs twice: once on the master push and once on the tag; both must stay
   green.
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

## Logging and state

The tool prints progress to stdout and errors to stderr; it keeps no state
files of its own. All durable state is git history — the mirror backup, the
rewritten clone, and the branch that was force-pushed. Clean up scratch
directories (`/tmp/attribution-cleanup*`-style paths) after a successful run.