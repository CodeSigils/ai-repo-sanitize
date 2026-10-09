# ai-repo-sanitize

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![CI](https://github.com/CodeSigils/ai-repo-sanitize/actions/workflows/validate.yml/badge.svg)](https://github.com/CodeSigils/ai-repo-sanitize/actions/workflows/validate.yml)

Safely strip AI attribution trailers from git history — preview, rewrite,
verify, publish. A `check` mode for CI, a `rewrite` mode that never pushes
unless you say so, and a commit-msg hook that keeps new trailers out.

The default is **no**: nothing is rewritten and nothing is pushed unless you
pass the explicit flags.

## Why this repo

A live blog post documented what happens when an AI agent signs your commits:
GitHub's contributors widget listed the agent beside the author, the commit
history carried a `Co-authored-by:` trailer and a "Ultraworked with ..."
branding line, and hundreds of similar complaints were filed against coding
agents. The cleanup sequence the article develops — backup, preview,
message-only rewrite, tree verification, force-with-lease push — is exactly
what this tool automates, with the safety gates made mandatory instead of
optional.

- Article: [When an AI Agent Signs Your Commits](https://codesigils.github.io/AI/Agent-Work/when-an-ai-signs-your-commits/#the-whole-sequence-as-an-example)
- Local copy of the article's markdown: `~/labs/zensical-test/docs/AI/Agent-Work/when-an-ai-signs-your-commits.md`
- The removal pattern this tool applies is the single source of truth in
  `src/ai_repo_sanitize/patterns.py`, mirrored by the article's example.

## Modes

| Command | What it does | Safe by default |
| --- | --- | --- |
| `check` | Scans every commit message for AI attribution trailers; exit code 0 = clean, 1 = found | Read-only |
| `preview` | Lists the commits whose messages match the drop pattern | Read-only |
| `rewrite` | Rewrites messages only (filter-repo), verifies the tree is unchanged, then optionally pushes | Requires `--push` to touch the remote |

What gets removed (see `src/ai_repo_sanitize/patterns.py` — the single source
of truth):

- `Co-authored-by:` trailers that name a known agent
  (`sisyphus`, `claude`, `opencode`, `codex`, `copilot`, `cursor`, `devin`).
  Human `Co-authored-by:` trailers are preserved.
- `(ultraworked|generated|assisted) with ...` branding lines.

Only the matching lines are dropped; subjects, bodies, and line-ending style
(CRLF included) are preserved.

## Install

```bash
uv tool install .            # or: pip install .
uv tool install git-filter-repo   # external tool, used only by `rewrite`
```

`git-filter-repo` is deliberately a dev-tool dependency, not a runtime one:
the rewrite path fails with an install hint if it is missing.

## Quickstart

```bash
ai-repo-sanitize check --path .        # exit 1 if attribution is found
ai-repo-sanitize preview --path .      # list matching commits, subject only
ai-repo-sanitize rewrite --path . \
  --remote-url your-owner/your-repo --backup-dir /tmp/copy \
  --branch master                       # rewrite messages, push nothing
ai-repo-sanitize rewrite --path . --remote-url ... --backup-dir ... --push
```

Run `ai-repo-sanitize --help` for every flag (including `--nudge-cache`, the
opt-in GitHub sidebar-cache refresh, documented in RESEARCH.md).

## Hooks

```bash
git config core.hooksPath .githooks
```

- `pre-commit` runs the fast gates (ruff, docs validator).
- `commit-msg` rejects AI-attribution trailers at commit time. Use
  `--no-verify` only in a documented emergency.

## Validation

The canonical gate — run all four, in this order, before claiming completion:

```bash
uv run ty check
uv run ruff check .
uv run pytest
uv run python scripts/validate-docs.py
```

`validate-docs.py` is the drift guard: it fails when README or CONTRIBUTING
stop listing these commands, when the required docs disappear, when ci.yml or
the pre-commit hook drift from the canonical commands, or when an internal
link breaks. If a command above stops being the truth, the repository tells
you instead of the docs silently rotting.

### Exit codes

| Code | Meaning |
| --- | --- |
| `0` | Clean: no attribution found (`check`), or the rewrite verified and published |
| `1` | Attribution found, a safety gate stopped the run, or an operation failed |
| `2` | Usage error (unknown subcommand or bad flags — argparse's default) |

`scripts/validate-docs.py` and `scripts/verify-urls.py` also exit 0/1.

## Architecture

```text
src/ai_repo_sanitize/
  patterns.py    the one attribution pattern set — the contract of this tool
  git_utils.py   thin shell-free wrappers around git subprocesses
  verify.py      the two invariants: same tree, no attribution remains
  rewrite.py     git-filter-repo wrapper; callback generated from patterns.py
  publish.py     re-add origin, fetch, --force-with-lease push
  platform.py    GitHub contributors snapshot + the opt-in cache nudge
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