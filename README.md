# ai-repo-sanitize

> Last reviewed: 2026-10-28

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/CodeSigils/ai-repo-sanitize/actions/workflows/ci.yml/badge.svg)](https://github.com/CodeSigils/ai-repo-sanitize/actions/workflows/ci.yml)

Safely strip AI attribution trailers from git history — preview, rewrite,
verify, publish. A `check` mode supports CI, and a `rewrite` mode never pushes
unless you say so. This repository's contributor tooling also has a
commit-message hook that keeps new trailers out of its own commits.

An *attribution trailer* is a line such as
`Co-authored-by: Claude <noreply@anthropic.com>` or `Generated with ...`
appended to a commit message, which credits an AI agent as a contributor.

The default is **no**: nothing is rewritten and nothing is pushed unless you
pass the explicit flags.

## Why this repo

A live blog post documented what happens when an AI agent signs your commits:
GitHub's contributors widget listed the agent beside the author, and the commit
history carried a `Co-authored-by:` trailer plus an "Ultraworked with ..."
branding line. This tool is the supported, repeatable remedy for that incident:
it makes backup, preview, message-only rewrite, tree verification, and an
explicit force-with-lease push decision part of one checked process.

- Article: [When an AI Agent Signs Your Commits](https://codesigils.github.io/AI/Agent-Work/when-an-ai-signs-your-commits/#a-safer-recovery-process)
- The removal pattern this tool applies is the single source of truth in
  [`src/ai_repo_sanitize/patterns.py`](src/ai_repo_sanitize/patterns.py).

## Design principles

- **Tested, not trusted** — the test suite runs on every push to `master` and
  every pull request across Python 3.10-3.14, including an end-to-end rewrite
  exercised against a local bare remote. A tag release repeats the canonical
  gate before publishing, and only accepts a tag reachable from `master`.
- **Research-based** — every mechanism traces to a RESEARCH.md decision and
  an empirical verification: the silent parser bug, the bad action SHAs, the
  missing PYTHONPATH, the remote-URL parsing bug, the YAML-anchor failure, the
  URL-checker backtick capture (RESEARCH.md §2).
- **Check-the-checker** — the docs validator, the freshness gate, the
  doc-coverage checker, and the doc-claims checker are themselves
  unit-tested, so the guards cannot rot.
- **Portable** — stdlib-only runtime, POSIX-only hooks and greps (never `-P`
  or `\b`), macOS/BSD-safe, Python 3.10+.

## Modes

| Command | What it does | Safe by default |
| --- | --- | --- |
| `check` | Scans every commit reachable from all local and fetched refs for AI attribution trailers; exit code 0 = clean, 1 = found | Read-only |
| `preview` | Lists matching commits reachable from all local and fetched refs | Read-only |
| `rewrite` | Rewrites messages only (filter-repo), verifies the tree is unchanged, then optionally pushes | Requires `--push` to touch the remote |

What gets removed (see [`src/ai_repo_sanitize/patterns.py`](src/ai_repo_sanitize/patterns.py) — the single source
of truth):

- `Co-authored-by:` trailers that name a known agent
  (`sisyphus`, `claude`, `opencode`, `codex`, `copilot`, `cursor`, `devin`).
  Human `Co-authored-by:` trailers are preserved.
- `(ultraworked|generated|assisted) with ...` branding lines.

Only the matching lines are dropped; subjects, bodies, and line-ending style
(CRLF included) are preserved.

## Run without installing

Requirements: `git`, Python 3.10 or newer, and
[uv](https://docs.astral.sh/uv/). Download and run a chosen release temporarily
with this command:

```bash
uvx --from git+https://github.com/CodeSigils/ai-repo-sanitize@v0.1.0 \
  ai-repo-sanitize check --path .
```

`uvx` downloads the named GitHub revision (a release tag in this example),
runs `ai-repo-sanitize` in a temporary isolated environment, then leaves no
persistent tool installation. Replace `@v0.1.0` with a later released tag or a
full 40-character commit SHA; do not track `master` in automation.

## Run from source

For local development, run `uv tool install .` (or `pip install .`) from a
clone. Install `git-filter-repo` separately with `uv tool install
git-filter-repo` only if you will use `rewrite`.

The sanitizer's runtime is stdlib-only: `check` and `preview` do not
need [git-filter-repo](https://github.com/newren/git-filter-repo).
`rewrite` delegates its history rewrite to that external executable, so it is
the supported rewrite mechanism and fails with an install hint when absent.
It is intentionally outside the package's runtime dependencies, so read-only
users do not receive a history-rewrite tool unnecessarily. It is included in
the development dependency group for the end-to-end rewrite test and CI quality
environment.

## Quickstart

```bash
ai-repo-sanitize check --path .        # exit 1 if attribution is found
ai-repo-sanitize preview --path .      # list matching commits, subject only
ai-repo-sanitize check --path . --format json  # structured read-only result
ai-repo-sanitize preview --path . --format json
ai-repo-sanitize rewrite --path . \
  --remote-url your-owner/your-repo --backup-dir /tmp/copy \
  --branch master                       # rewrite messages, push nothing
ai-repo-sanitize rewrite --path . --remote-url ... --backup-dir ... --push
```

`rewrite` is the only mode that changes history: it rewrites commit messages
in place, verifies the resulting tree is byte-identical to the original, and
touches the remote only when you pass `--push` (via `--force-with-lease`).
`--backup-dir` names a mirror clone the tool creates for you, so its path must
not already exist, and `--remote-url` accepts either `owner/name` or a full
URL. Run `check` and `preview` first to see exactly what would change.

Run `ai-repo-sanitize --help` for every flag (including `--nudge-cache`, the
opt-in GitHub sidebar-cache refresh, documented in [RESEARCH.md](RESEARCH.md)).

Only the read-only `check` and `preview` commands accept `--format json` for
agent and automation use; `rewrite` intentionally remains text-only. The
schema is versioned (`schema_version: 1`), names the command and `all_refs`
scope, and exposes the commits: `check` reports the scanned commit count and
the offending commits, while `preview` lists the matching commits. JSON changes
only stdout; the existing exit-code contract is unchanged. It does not create
report files or alter any repository. Use the human-readable default for
interactive work.

## Use in downstream CI

A downstream workflow runs the whole read-only scan as one step — no persistent
install, no git-filter-repo, and a bare exit code that fails the job when
history carries an AI attribution trailer. `uvx` builds and runs the tool in an
isolated environment without installing anything:

```yaml
steps:
  - uses: actions/checkout@<full-sha>            # the repository being checked
  - uses: astral-sh/setup-uv@<full-sha>          # official uv installer; pin at v10
    with:
      version: "0.11.7"
  - name: Fail on AI attribution trailers
    run: uvx --from git+https://github.com/CodeSigils/ai-repo-sanitize@v0.1.0 ai-repo-sanitize check --path .
```

Pin both actions to the reviewed commits — this repository uses full-SHA pins
with a `# vX.Y.Z` comment, as in [ci.yml](.github/workflows/ci.yml) — and pin
the tool instead of tracking `master`: `@v0.1.0` is a released tag, and a full
40-character SHA works too. The exit code is the contract: `check` returns 0 on
clean history and 1 when attribution is found, so the bare step gates the job.
Add `--format json` in a later step if you want machine-readable evidence for a
report. For a persistent source install instead of the ephemeral `uvx` run:

```bash
uv tool install git+https://github.com/CodeSigils/ai-repo-sanitize@v0.1.0
export PATH="$PATH:$(uv tool dir --bin)"
ai-repo-sanitize check --path .
```

This repository exercises the exact one-step flow in
[`downstream-check.yml`](.github/workflows/downstream-check.yml) on fresh
runners against disposable clean and attributed repositories, so the documented
shape is verified with every push, not just documented.

## Hooks

This repository keeps its git hooks in `.githooks/`. They are opt-in,
per-clone, and belong to this repo's contributor tooling: `pip install` does
not install them, and they never travel to the repositories you sanitize.
Enable them once per clone:

```bash
git config core.hooksPath .githooks
```

- `pre-commit` runs before each commit and blocks it if any fast gate fails:
  `ruff` (lint), `ty` (types),
  [`scripts/validate-docs.py`](scripts/validate-docs.py) (the docs contract),
  and [`scripts/check-doc-claims.py`](scripts/check-doc-claims.py) (documented
  paths exist). It runs the same set CI runs, so a commit accepted here is
  unlikely to be rejected later.
- `commit-msg` inspects the message you just wrote and rejects the commit when
  it carries an AI-attribution trailer, or when an implementation,
  configuration, or workflow subject (`feat:`, `fix:`, `ci:`, ...) lacks a
  non-empty `what:` or `why:` paragraph. CI rechecks every newly introduced
  commit, so the hook is a fast first line of defence, not the only control.

Both hooks call `uv run`, so [uv](https://docs.astral.sh/uv/) must be on your
`PATH`; if it is missing, the hook fails and the commit is blocked. Because
`core.hooksPath` is a local git setting, every new clone must repeat the
`git config` command above.

## Validation

The canonical gate — run all four, in this order, before claiming completion:

```bash
uv run ty check
uv run ruff check .
uv run pytest
uv run python scripts/validate-docs.py
```

[`scripts/validate-docs.py`](scripts/validate-docs.py) is the drift guard: it fails when README or CONTRIBUTING
stop listing these commands, when the required docs disappear, when ci.yml or
the pre-commit hook drift from the canonical commands, or when an internal
link breaks. If a command above stops being the truth, the repository tells
you instead of the docs silently rotting.

Additional hook and CI checks have different triggers and inputs; they are not
all part of the local gate above:

```bash
uv run python scripts/check-commit-messages.py --base "$BASE" --head "$HEAD"  # CI commit range
uv run python scripts/check-doc-claims.py  # pre-commit and CI
uv run python scripts/check-doc-coverage.py --base "$BASE" --head "$HEAD"  # CI advisory
python3 scripts/verify-urls.py  # scheduled/manual external URL audit
python3 scripts/check-pr-hygiene.py  # scheduled/manual PR report
python3 scripts/check-pr-readiness.py "$PR_NUMBER"  # manual check before a requested merge
```

Set `BASE` and `HEAD` to the commit range and `PR_NUMBER` to the pull request
number. PR checks require GitHub access; the readiness check supports
`--require-approval` when maintainer policy requires it.

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Clean: no attribution found (`check`), or the rewrite verified and published |
| `1` | Attribution found, a safety gate stopped the run, or an operation failed |
| `2` | Usage error (unknown subcommand or bad flags — argparse's default) |

[`scripts/validate-docs.py`](scripts/validate-docs.py) and [`scripts/verify-urls.py`](scripts/verify-urls.py) also exit 0/1.

## Architecture

```text
src/ai_repo_sanitize/
  patterns.py    the one attribution pattern set — the contract of this tool
  git_utils.py   thin shell-free wrappers around git subprocesses
  verify.py      the two invariants: same tree, no attribution remains
  rewrite.py     git-filter-repo wrapper; callback generated from patterns.py
  publish.py     re-add origin, fetch, --force-with-lease push
  platform.py    token-aware GitHub contributors snapshot + opt-in cache nudge
  pipeline.py    run_check / preview / run_rewrite — every mode shares the checks
  cli.py         argparse front end; exit codes 0/1/2
```

Every mode reuses the same checks from `verify.py`; the pipeline never
re-implements an invariant a second way.

## Documentation

| Doc | Read it to learn |
| --- | --- |
| [CONTRIBUTING.md](CONTRIBUTING.md) | How to contribute, commit, and review |
| [MAINTENANCE.md](MAINTENANCE.md) | Daily ops: gate, hooks, dependency refresh, troubleshooting |
| [SECURITY.md](SECURITY.md) | Vulnerability reporting and handling |
| [RESEARCH.md](RESEARCH.md) | Sources and design decisions behind every behavior |
| [ROADMAP.md](ROADMAP.md) | Milestones, each tied to the anti-drift checks that keep it honest |
| [ANTIDRIFT.md](ANTIDRIFT.md) | The layered strategy that keeps this repo's docs from going stale |
| [AGENTS.md](AGENTS.md) | First stop for agents (and humans) working in this repo |

## Maintainer ownership

| Doc | Owns |
| --- | --- |
| README.md | Positioning, quickstart, the exit-code contract, docs index |
| CONTRIBUTING.md | Contribution workflow and the canonical validation gate |
| MAINTENANCE.md | Daily operations and the rewrite-flow summary |
| SECURITY.md | Vulnerability reporting and the matching trade-off |
| RESEARCH.md | Sources and design decisions; update when behavior changes |
| ROADMAP.md | Milestones; each references the anti-drift check keeping it honest |
| ANTIDRIFT.md | The layered anti-drift strategy; update when a layer changes |
| AGENTS.md | First-stop instructions for agents (and humans) in this repo |

## See also

- [py-review-skill](https://github.com/CodeSigils/py-review-skill) — the
  Python review checklist this project's quality gates are modelled on.
- [repo-architecture-skill](https://github.com/CodeSigils/repo-architecture-skill)
  — the documentation conventions this README follows.

## License

MIT — see [LICENSE](LICENSE).
