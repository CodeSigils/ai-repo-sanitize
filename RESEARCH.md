# Research and Decisions (RESEARCH.md)

Last reviewed: 2026-10-09. Reference document: cites the external sources and records the
design decisions built on them. Per the [ANTIDRIFT code-changes rule](ANTIDRIFT.md), re-verify
this file when `patterns.py`, `cli.py`, or the canonical validation commands change.

## 1. Primary domain source

- **"When an AI Agent Signs Your Commits"** (Zensical blog, `when-an-ai-signs-your-commits.md`,
  October 2026): the incident and remediation this tool generalizes. Provides the validated
  rewrite flow — filter-repo `--message-callback`, origin-remote deletion, tree-SHA gate,
  residual scan, `--force-with-lease` push, and the last-resort default-branch cache nudge —
  plus its Sources section linking Claude Code issues (#48145, #7422, #53259, #79909, #64019,
  #83813), Codex (#19799), community discussions, declaudify (ParkerrDev), and
  Londopy/git-attribution.

## 2. Git and CI mechanics (empirically verified)

- **git-filter-repo `--message-callback`**: receives `message` as bytes (possibly multi-line),
  must `return` new bytes; `import re` inside the callback works; `--dry-run` does NOT preview
  message-only rewrites (unknown new commit IDs) — preview comes from `git log --grep` instead.
- **Origin deletion by design**: filter-repo intentionally removes the `origin` remote
  (newren, issue #282) so the operator re-adds it consciously. A `--mirror` clone is exempt
  (issue #347) — our mirror is only the backup; the working clone is a normal clone, so origin
  is re-added before any push.
- **Fresh-clone requirement**: filter-repo aborts outside a fresh clone unless `--force`
  (we pass `--force` on the scratch clone we own).
- **git-filter-branch man page**: explicitly recommends git-filter-repo.
- **`git log --grep`**: searches subject *and* body; `--format` only selects display. Flags
  `-i -E` are git's own and behave identically on Linux and macOS; `-E` is required (BRE makes
  `|` literal) and `-i` is required (misses `Co-authored-by:` capital C otherwise). `\b` is
  not POSIX-clean in git's engine, so `GIT_GREP_PATTERN` avoids it; the Python regex keeps it.
- **GitHub contributors cache**: the API/Insights surface may lag a force-push for hours; there
  is no supported flush command. `PATCH /repos/{owner}/{repo}` accepts `default_branch` — the
  basis for the opt-in `--nudge-cache` last resort, which is never automatic.
- **GitHub Actions does not support YAML anchors/aliases in workflow files.**
  Empirically verified 2026-10-09: run 37915474228 on this repo failed with
  "This run likely failed because of a workflow file issue" and *zero jobs*
  (`jobs: []`) after `x-checkout: &checkout ...` + `uses: *checkout` anchors
  were introduced; the workflow stayed `state: active` and no check runs or
  logs were created, so the failure is invisible in the Actions job list.
  Long-standing feature request actions/runner#1182 and the historical hard
  rejection "Anchors are not currently supported" (action-validator#7/#70)
  confirm the runner uses a partial YAML implementation; GitHub's docs
  (2025) now describe *basic* anchors/aliases but explicitly exclude merge
  keys (`<<:`), which is what makes anchors useful for composition.
  Dealing with it: pin actions explicitly per job with `# vX.Y.Z` comments
  and accept duplication; never centralize via anchors, and never trust a
  tag defined but not aliased to be meaningful. Detection pattern for this
  whole class: a failed run with no jobs and no logs is a workflow-file-
  level failure, not a step failure — check `gh run view <id>` and
  `gh api /repos/{owner}/{repo}/actions/workflows`.
- **Remote splitting (`split_remote`)** — scheme URLs (`https`/`ssh`-prefixed, with a host
  segment) and scp-style (`git@host:owner/repo`) parse to `(owner, repo)`;
  local paths return `None`. An earlier version returned a bogus pair such as `("tmp", "smoke")`
  for a `/tmp/...` remote — a doomed API call and a misleading 404 warning. Fixed 2026-10-09
  during the test-hardening pass and locked by `tests/test_platform.py`.

- **URL-checker backtick capture** — the naive `https?://[^\s)\]}>]+`
  extraction captured a closing markdown code-span backtick into the URL,
  producing a false `404` failure (first observed 2026-10-09). Fix: strip the
  backtick with the punctuation set — `url.rstrip(".,;:!?`")`. No documented
  URL contains a real trailing backtick, so the strip is safe.
- **GitHub Actions operational gotchas (2026-10-09)** — three things that
  bit this repo's workflows and are now encoded into them:
  - `gh` in a workflow ignores the auto-provisioned token unless passed
    explicitly: `env: GH_TOKEN: ${{ github.token }}`. The release job failed
    with exit code 4 ("To use GitHub CLI in a GitHub Actions workflow, set
    the GH_TOKEN environment variable") until the env line was added.
  - Pinned action SHAs must be verified against the action's release tag via
    the refs/tags API: a silent typo (setup-python `...c45a2b` vs real
    `...c90a2b`) and a nonexistent setup-uv SHA both died at "Set up job"
    before any step ran (run 37911302858). Pin by full-length commit SHA and
    re-verify on upgrades.
  - Tag pushes re-run the full ci.yml in practice even when the changed
    files would be filtered out by `paths`: the v0.1.0 annotated tag push
    fired the whole validate workflow (run 37927693277, green). We
    documented the opposite in MAINTENANCE.md first, then corrected it —
    trust the observation, not the assumption.

## 3. Anti-drift literature (2026)

| Source | Finding adopted | Decision |
| --- | --- | --- |
| sourcegraph.com/blog/documentation-as-code | docs-as-code = git + markdown + review + CI; the code-changer is the best doc-updater; agents read docs as input | one-change-one-commit rule; CI-checkable claims |
| lycheeverse/lychee | fast Rust link checker; schedule-friendly; anchor fragment support | rejected as binary dep — stdlib `verify-urls.py` suffices |
| cosmocoder/doc-freshness-checker | validate doc references (paths, URLs, versions, symbols) in CI | Layer-1 contract; semantic layers rejected as overkill |
| datadef.io docs-checks-in-ci | 4 checks: links (on a **schedule**), prose (Vale), freshness (`last_reviewed` window), diff-coverage warn-not-fail | schedule-based verify-urls; `last_reviewed` gate shipped 2026-10-09 (v0.2; 90-day window in validate-docs); warn-not-fail diff rule shipped 2026-10-09 (scripts/check-doc-coverage.py, warn-only) |
| Arthur920/Staleguard | deterministic Layer-1 drift checks; agent guardrail: run check after edits | our validate-docs.py + AGENTS.md gate mirror this |
| andimrob/docrot | `last_reviewed` frontmatter + interval / until_date / **code_changes** strategies | code-changes rule adopted now; interval gate queued for v0.2 |
| codocia (docs.rs) | docs drift checker FOR agents: `covers` patterns + snapshot hashes; "docs are source of truth" | patterns/checker idea adopted conceptually; tool itself overkill now |
| GitLab technical-writing/markdown-link-check | lychee-powered CI component, `--offline --include-fragments` | corroborates schedule-based link checking |

Key quote governing the whole strategy (datadef.io): *"CI detects proxies for outdatedness
rather than outdatedness itself."*

## 4. CodeSigils org conventions (evidence-based)

Inspected active repos (repo-health-scan, repo-architecture-skill, zensical-skill,
python-project-workflow-skill): AGENTS.md + SECURITY.md + LICENSE + pyproject + uv.lock +
docs/ minimums; `.githooks/` pre-commit everywhere (pre-push in heavier repos);
`scripts/verify-urls.py` in 3 of 4; a `validate*.py` contract + CI in every repo; roadmap kept
as a guarded root markdown file; check-the-checker tests (`test-validate-ci.py`); commit
convention guards at hook level.

## 5. Design decisions

1. **One pattern, everywhere.** `patterns.py` defines the attribution regex once; check,
   preview, rewrite-callback and the commit-msg hook all derive from it. Preview's
   `GIT_GREP_PATTERN` is the ERE form of `ATTRIBUTION_RE` minus `\b`.
2. **Human co-authors survive.** A `Co-authored-by` trailer is dropped only when one of the
   known agent names (`sisyphus, claude, opencode, codex, copilot, cursor, devin`) appears on
   the line; branded lines (`ultraworked|generated|assisted with`) are always removed. This is
   a documented trade-off, covered by tests.
3. **Minimal destructive rewrite.** Only matching lines are removed and trailing blanks
   trimmed; line-ending style (CRLF vs LF) is preserved — verified by test.
4. **Shell-free Python, POSIX-only shell.** Python paths invoke git with argv lists, never a
   shell. The commit-msg hook uses only POSIX grep flags (`-E -i`), never `-P` or `\b`.
   `git log --grep` means no external grep binary is needed for preview/check.
5. **Push is explicit.** The rewrite is local unless `--push` is given; publication uses
   `--force-with-lease`; the cache nudge requires `--nudge-cache` and is never automatic.
6. **filter-repo is a dev tool, not a runtime dep.** The package is stdlib-only; the CLI
   errors with an install hint when `git-filter-repo` is missing
   (`uv tool install git-filter-repo`).
7. **The docs contract.** `scripts/validate-docs.py` (logic rewritten from py-review-skill's
   `validate-readme.py` pattern, CC-BY-4.0 terms of that repo): README and CONTRIBUTING must
   list the 4 canonical commands verbatim; ci.yml must run them verbatim (a plain substring
   check — that is why ci.yml never uses `--no-sync`); required docs exist; internal links
   resolve.

## 6. Reference URLs

- man page: <https://manpages.debian.org/testing/git-filter-repo/git-filter-repo.1.en.html>
- filter-repo issue #282 (origin removal), #347 (mirror clone exception)
- git-filter-branch warning: <https://git-scm.com/docs/git-filter-branch>
- git log docs: <https://git-scm.com/docs/git-log>
- GitHub co-authored commits: <https://docs.github.com/en/pull-requests/committing-changes-to-your-project/creating-and-editing-commits/creating-a-commit-with-multiple-authors>
- GitHub repository API (default_branch): <https://docs.github.com/en/rest/repos/repos>
- sourcegraph docs-as-code: <https://sourcegraph.com/blog/documentation-as-code>
- datadef docs-checks-in-ci: <https://datadef.io/guides/en/docs-checks-in-ci>
- lychee: <https://github.com/lycheeverse/lychee>
- doc-freshness-checker: <https://github.com/cosmocoder/doc-freshness-checker>
- Staleguard: <https://github.com/Arthur920/Staleguard>
- docrot: <https://pkg.go.dev/github.com/andimrob/docrot> (GitHub source 404s since 2026-10; the pkg.go.dev snapshot of v0.1.1 is the durable reference)
- codocia: <https://docs.rs/codocia>
- GitLab markdown-link-check component: <https://gitlab.com/gitlab-org/technical-writing/markdown-link-check>
- declaudify: <https://github.com/ParkerrDev/declaudify>
- git-attribution: <https://github.com/Londopy/git-attribution>
- GitHub Actions YAML anchors feature request: <https://github.com/actions/runner/issues/1182>
- action-validator "anchors aren't allowed": <https://github.com/mpalmer/action-validator/issues/7>
- action-validator "YAML references aren't supported": <https://github.com/mpalmer/action-validator/issues/70>
- GitHub docs on anchors/aliases (reusing workflow configurations): <https://docs.github.com/en/actions/reference/workflows-and-actions/reusing-workflow-configurations#yaml-anchors-and-aliases>
- frenck.dev analysis of the partial anchor support (no merge keys, 2025-10): <https://frenck.dev/github-actions-yaml-anchors-aliases-merge-keys/>
- GitHub CLI environment variables (GH_TOKEN): <https://cli.github.com/manual/gh_help_environment>
- GitHub security hardening for GitHub Actions (pin third-party actions by full-length SHA): <https://docs.github.com/en/actions/security-guides/security-hardening-for-github-actions>
- GitHub Actions events that trigger workflows (push): <https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows#push>