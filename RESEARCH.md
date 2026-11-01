# Research and Decisions (RESEARCH.md)

Last reviewed: 2026-11-01. Reference document: cites the external sources and records the
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
   backtick with the punctuation set — ``url.rstrip(".,;:!?")``. No documented
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
    fired the whole validate workflow (run 37927693277, green). Workflows
    run independently, however, so a successful validation run cannot gate a
    same-event release job. The release workflow therefore owns its own
    canonical-gate preflight and checks that the tag commit is reachable from
    `master` before granting the publishing job `contents: write`.
  - **Workflow scope, ordering, and privilege** — GitHub documents that a
    push using both branch and path filters must satisfy both, so a path filter
    could suppress the documentation contract. The validation workflow now
    runs for every `master` push. GitHub also documents `needs` as a job
    dependency within one workflow; consequently, the release workflow owns a
    `verify-release` job and makes the write-permitted publisher depend on it,
    instead of assuming the separately triggered validation workflow gates a
    release. The workflow defaults to `contents: read` and elevates only the
    publisher to `contents: write`. Finally, `git merge-base --is-ancestor`
    has the exact zero/non-zero ancestry contract needed to reject a tag that
    is not reachable from `master`.
  - **Branch-policy recommendation (future evaluation)** — retain the current
    deletion and force-push protections, then require pull requests, the
    uniquely named quality and compatibility checks, and an up-to-date branch.
    GitHub rulesets support those controls and a "for pull requests only"
    bypass, which preserves an auditable PR path without granting a direct
    push exception. Require one approval only when a second maintainer can
    supply it; a sole maintainer would otherwise deadlock. This is a
    maintainer-governance decision, not a workflow change.

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
| CodeSigils skill-catalogue / Addy Osmani agent-skills / GitHub Docs | no catalogue entry yet covered Markdown fragments; the local `agent-skills` validator checks GitHub-style heading slugs and duplicate suffixes; GitHub documents the same lowercasing, punctuation removal, spacing, and duplicate-heading rules | extend the stdlib docs validator with GitHub-compatible fragment checks and regression tests; retain no additional dependency |
| GitHub section-link rules / github-slugger / CommonMark fences (follow-up 2026-11-01) | GitHub slugs rendered heading text: link markup contributes its visible text, HTML tags disappear, entities are decoded, and both backtick and tilde fences hide heading-like lines | render reference-style links and entities before slugging; skip both fence styles; keep the stdlib implementation and add regression tests |
| Diátaxis how-to and reference guides | how-to guides are action-oriented procedures for real work; reference is information-oriented and should describe rather than instruct | file the canonical validation gate under **Do**, not **Look up**; keep the index a navigation layer over existing docs |

Key quote governing the whole strategy (datadef.io): *"CI detects proxies for outdatedness
rather than outdatedness itself."*

## 4. CodeSigils org conventions (evidence-based)

Inspected active repos (repo-health-scan, repo-architecture-skill, zensical-skill,
python-project-workflow-skill): AGENTS.md + SECURITY.md + LICENSE + pyproject + uv.lock +
docs/ minimums; `.githooks/` pre-commit everywhere (pre-push in heavier repos);
`scripts/verify-urls.py` in 3 of 4; a `validate*.py` contract + CI in every repo; roadmap kept
as a guarded root markdown file; check-the-checker tests (`test-validate-ci.py`); commit
convention guards at hook level.

Dependency-update practice (2026-10-09): four of five inspected repos carry
a GitHub-native `.github/dependabot.yml` (repo-health-scan,
python-project-workflow-skill, repo-architecture-skill, awesome-agent-trust);
py-review-skill instead relies on a scheduled dependency-freshness workflow,
and repo-health-scan adds a cron-driven dependency-backlog script that
comments on stale dependency PRs. repo-architecture-skill's config
implements its research note (docs/research/automation-bots-and-workflows.md):
disjoint update-type groups (actions-maintenance minor+patch,
uv-maintenance patch, ruff-minor-review and ty-minor-review minors isolated
because zero-major toolchain minors break the locked contract), a two-PR cap
per ecosystem, group labels, no exclude-patterns (excluded deps resurface as
ungrouped PRs and double review load), no auto-merge. Hook practice varies:
python-project-workflow-skill's pre-commit is the richest (hook-integrity
self-check first, then a conditional uv guard that skips lint when uv is
absent); awesome-agent-trust has no hooks at all.

## 5. Design decisions

1. **One pattern, everywhere.** `patterns.py` defines the attribution regex once; check,
   preview, rewrite-callback and the commit-msg hook all derive from it. Preview's
   `GIT_GREP_PATTERN` expresses the Python detector's `with\b` boundary with the
   POSIX ERE suffix `([^[:alnum:]_]|$)`, which git accepts without using `\b`.
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
   check — that is why ci.yml never uses `--no-sync`); the hook runs its defined fast suite;
   required docs exist; internal links and GitHub-style heading fragments resolve.

8. **Dependency updates stay GitHub-native and group-gated** — Dependabot
   (`.github/dependabot.yml`) proposes weekly grouped updates: action pins
   under `actions-maintenance` (minor+patch), uv patches under
   `uv-maintenance`, ruff/ty minor releases isolated for separate review
   (`ruff-minor-review`, `ty-minor-review`); no
   exclude-patterns, no auto-merge; the protect-master ruleset and the
   canonical 4-command gate govern every Dependabot PR. Rationale: the org
   research note automation-bots-and-workflows.md (repo-architecture-skill)
   plus the empirical GITHUB_TOKEN/permissions model recorded in §2.
9. **PR freshness and merge automation need separate controls** — Dependabot
   stops rebasing an unmerged PR after 30 days, so a passing PR can silently
   become stale. The optimal fit here is a separate daily, read-only
   `pr-hygiene.yml` workflow, offset from the hour and manually dispatchable:
   it queries only open PR metadata, writes a job summary, and fails at seven
   days for Dependabot PRs and 14 days for unreviewed, stale, or stacked PRs.
   A dedicated job bounds detection to about one day after the threshold
   without running the full validation matrix daily. It needs only `contents: read` and
   `pull-requests: read`; comments, labels, closure, approval, and merge are
   deliberately out of scope. Each finding must be explicitly merged,
   rebased, or closed. Keep autonomous auto-merge disabled:
   Dependabot-triggered workflows receive a read-only token by default, and a
   write-capable GitHub App or PAT would be a separate security decision.
   Reconsider GitHub native auto-merge only after the branch ruleset is
   established, a maintainer explicitly opts in to a patch-only PR, and a
   documented recurring failure shows the benefit outweighs the added
   authority. Minor, major, security-sensitive, and non-Dependabot PRs remain
   manual review work.

10. **Agent Git hygiene is an execution gate, not a reminder** — before a
    write, the agent records the branch, upstream, and worktree state. Before
    staging, it separates unrelated changes; before a push or a user-requested
    merge, it refreshes the remote state and inspects the PR's review,
    mergeability, and required-check status. This catches stale bases and
    accidental mixed commits before they become a remote recovery problem.

11. **Local comparator evidence (2026-10-09)** — three recent repositories
    document the same recurring class of failure. `repo-health-scan` found two
    mergeable Dependabot PRs left for 12 days and now runs a seven-day
    dependency-backlog detector that comments once and fails its scheduled
    run, while retaining disabled auto-merge. `python-project-workflow` treats
    PRs without a review after three days, PRs untouched for 14 days, stacked
    PRs, and stale branches as hygiene errors. `zensical-skill` requires a
    stale-state preflight and a roadmap after-action gate. Decision: adopt the
    common read-only preflight and a dedicated daily scheduled report first;
    defer comments, write permissions, and auto-merge until a later policy
    review proves they are necessary.

12. **Commit-message policy needs a server-visible check** — a local
    `commit-msg` hook is valuable fast feedback but can be skipped, so it
    cannot be the sole control. `scripts/check-commit-messages.py` now uses
    the runtime's canonical attribution matcher for both the local hook and
    CI. CI validates commits introduced by the exact push/PR range, requires
    non-empty `what:` and `why:` paragraphs for implementation and workflow
    prefixes, and permits Dependabot's generated format to omit those labels
    without exempting it from the attribution rule. This detects bypasses
    before a PR merge. It cannot prevent an authorized direct push; moving to
    PR-only rules remains the separate maintainer-governance choice recorded
    in ROADMAP.md.

13. **Freshness checks and merge checks operate at different times** — a daily
    hygiene report identifies neglected PRs, but it cannot establish that a PR
    is still mergeable when a maintainer acts. The companion
    `check-pr-readiness.py` checks one PR's live default-base target, draft
    state, merge-state status, status-check rollup, and optional approved
    review immediately before a requested merge. It is exposed as a manual,
    read-only workflow so agents can perform the chore consistently without
    receiving permission to merge. This preserves the evidence-before-action
    workflow while branch protection remains a maintainer policy decision.

14. **Attribution scans must cover all fetched refs** — adopt all-ref scope
    for `check`, `preview`, and residual verification. In the 2026-10-11
    `python-project-workflow-skill` observation, the checked-out `main`
    ancestry held 138 commits while the clone held 241 commits across fetched
    refs; the prior `git log` calls examined only the former. Git's official
    documentation defines `git log` as walking commits reachable from supplied
    commits and defines `--all` as supplying every ref plus `HEAD`.
    <https://git-scm.com/docs/git-log#Documentation/git-log.txt---all>
    All-ref scope therefore fulfills the existing “every commit” promise and
    prevents a clean result from overlooking a trailer found only on a remote,
    local, or tag ref. The implementation adds `--all` to the shared log
    calls, tests a trailer reachable only from a second ref, and documents
    that scope precisely; all three actions landed 2026-10-11. This read-only
    inspection does not expand rewrite or publishing authority: both remain
    controlled by the explicit branch and push plan. Evidence and the exact
    alternatives are in
    `reports/python-project-workflow-skill-sanitizer-check.md`.

15. **Evidence outranks speculation** — recommendations must follow primary
    official documentation and recorded empirical observations. When those
    sources conflict with an inference, preference, or unverified assumption,
    state the uncertainty and retain the evidence-backed conclusion. This
    keeps agent and maintainer decisions reviewable and makes the provenance
    of a recommendation discoverable in the research record.

16. **Structured read-only output is evidence, not a report writer** — `check`
    and `preview` offer `--format json` for agents and automation. Both retain
    their text-mode exit codes and all-ref scope; their versioned payloads are
    a stable raw-evidence interface. The CLI does not write report files:
    reports require a maintainer or agent to add context, a recommendation, and
    a research link. Limiting the initial structured interface to read-only
    commands avoids conflating evidence capture with rewrite or publish
    authority.

17. **Structured payload keys name the value's shape** — the `check` payload
    exposes the scanned total as `scanned_commit_count` (an integer) beside
    `offending_commits` (a list), and `preview` exposes `matching_commits` (a
    list). Naming a count apart from a commit list keeps the read-only evidence
    unambiguous for agents. The key predates release (`v0.1.0` shipped before
    `--format json`), so it was renamed without a `schema_version` bump; the
    version stays `1` until the feature ships.

18. **External-verification reports record the scanned scope** — a dated report
    from the read-only procedure must state the scanned ref scope and the
    scanned commit count, adding the checked-ref count only when it differs.
    This replaced an earlier "both counts" rule that fit only the observation
    which prompted the all-ref change; mandating a count pair for every
    repository would record numbers the evidence does not need.

19. **A downstream consumer runs `check` as one isolated step** — the ephemeral
    `uvx --from git+<repository-url>@<version|sha> ai-repo-sanitize check`
    form installs nothing persistently and needs no git-filter-repo, so the
    bare exit code (0 clean / 1 found) gates the downstream job directly. A
    standalone step, not a custom composite action, preserves the read-only
    boundary: a consumer who only asked for `check` receives no rewrite
    capability alongside it. Recorded 2026-10-11;
    `.github/workflows/downstream-check.yml` exercises the shape on every push
    against disposable clean and attributed repositories.

20. **Source-pinned `uvx` is the distribution policy** — this is a focused
    maintainer tool, so the verified `uvx --from git+<repository-url>@<version|sha>`
    route remains the supported way to consume it. It provides a reproducible
    GitHub release tag or commit SHA without taking on a PyPI package's broader
    support and compatibility commitment. Reconsider a registry release only
    if recorded downstream use shows source-pinned consumption is materially
    insufficient. Decided 2026-10-12; this is an owner-maintenance policy,
    informed by the existing verified `uvx` workflow and uv tools guide.

21. **External-link checks ignore non-documentation examples** — inline code
    spans (with any backtick delimiter), backtick- or tilde-fenced blocks, and hidden Markdown
    paths may contain illustrative URL-shaped placeholders or generated data,
    not navigable references. `verify-urls.py` excludes them before extraction
    and treats a malformed URL as an ordinary unreachable finding rather than
    crashing the scheduled audit. Regression tests cover both cases. The fence
    and code-span rules follow the CommonMark specification (a fenced code block
    may use backticks or tildes; the closing fence is the same character and at
    least as long as the opener; a code span is closed by a backtick run of equal
    length). Excluding hidden (dot-prefixed) paths is a repository scoping
    decision, not a spec rule. Sources:
    <https://spec.commonmark.org/0.31.2/#fenced-code-blocks> and
    <https://spec.commonmark.org/0.31.2/#code-spans>. Decided 2026-10-12.

22. **External-link audit is isolated from push validation** — GitHub scheduled
    workflows run against the default branch, while `concurrency.cancel-in-progress:
    true` cancels currently running or queued jobs in the same concurrency group.
    `url-audit.yml` therefore owns the weekly/manual URL check with a non-canceling
    group; `ci.yml` remains the fast push/PR validation gate. The hygiene query
    requests up to 1,000 open PRs and fails at that cap instead of silently
    certifying a partial audit. Sources: the `schedule` trigger (runs on the
    default branch), <https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule>;
    the `concurrency`/`cancel-in-progress` reference, <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency>;
    and `gh pr list` (its fetch limit), <https://cli.github.com/manual/gh_pr_list>.
    Decided 2026-10-12.

23. **Configuration audit (Python + CI): findings and follow-ups** — a
    correctness/efficiency/duplication/coverage audit of the Python sources,
    scripts, and workflows on 2026-10-12 produced the following findings. None
    is fixed by this entry; each is recorded here as the evidence base for a
    later change.

    Correctness:

    - `cli.py` prints the contributors snapshot with
      `"contributors snapshot: " + ", ".join(logins[:10]) or "… (empty)"`; `+`
      binds tighter than `or`, so the left operand is always a non-empty
      string and the `(empty)` fallback is unreachable. An empty snapshot
      prints a bare label instead of the intended message.
    - `git_utils.full_messages` is dead code (referenced only by `__all__` and
      its own definition) and `git_utils.branch_exists` has no references at
      all.
    - The `ci.yml` header comment states GitHub Actions "does not support YAML
      anchors/aliases". GitHub's own docs (2025-09-18) now describe *basic*
      anchor/alias support (merge keys `<<:` still excluded), which conflicts
      with this repository's direct observation (anchors rejected on
      2026-10-09, run 37915474228, "workflow file issue" and zero jobs). Per
      the evidence-priority rule the per-job pinning stance stands, but the
      comment is now only partially accurate and the feature is worth
      re-verifying before any attempt to de-duplicate pins.
    - `ty` gates every push while still Beta (0.0.x, latest 0.0.86, unstable
      diagnostics). The lockfile pins it; keep the version at or above 0.0.84
      (which fixed GHSA-vxvm-j4xq-q7m4) and gate upgrades through PRs.

    Efficiency and duplication:

    - Action pins repeat per job: `actions/checkout` in five workflow files,
      `actions/setup-python` in five, `astral-sh/setup-uv` in three. Anchors
      would centralize them but are empirically unreliable here (above).
    - The canonical gate runs twice on a release: `ci.yml` triggers on the
      `v*.*.*` tag *and* `release.yml`'s `verify-release` re-runs the gate.
    - `shellcheck` runs in `ci.yml` and `release.yml` but not in
      `.githooks/pre-commit`, so a shellcheck failure is invisible to the local
      gate and only surfaces in CI.
    - `downstream-check.yml` exercises a network `uvx --from git+…@sha` install
      on every push and pull request, adding cost and flakiness surface.

    Coverage: the repository configures no coverage tooling (no `pytest-cov`,
    no `[tool.coverage]` section). A measured run
    (`coverage run --source=ai_repo_sanitize,scripts`) reports 67% total (937
    statements, 313 missed). The largest untested surfaces are `cli.py` 64%
    (the whole `rewrite` CLI branch and the text output paths), `pipeline.py`
    79% (the safety-gate error paths), `platform.py` 69% (contributors API,
    token headers, `toggle_default_branch`), and the scripts at 35–73%. Since
    the runtime is stdlib-only, coverage measures the test thoroughness of this
    project's own logic. It is recorded here as a prioritization signal, not as
    a target: consistent with `ROADMAP.md` ("Behavior-completeness contract"),
    a blanket line-coverage percentage is deliberately not adopted because a
    percentage cannot prove the backup, unchanged-tree, residual-scan, or
    explicit-push guarantees. The untested surfaces above identify where that
    contract should focus.

    Sources: GitHub Actions secure use (pinning third-party actions to a
    full-length SHA), <https://docs.github.com/en/actions/reference/security/secure-use#using-third-party-actions>;
    OpenSSF Scorecard `Pinned-Dependencies`, <https://github.com/ossf/scorecard/blob/main/docs/checks.md#pinned-dependencies>;
    workflow concurrency, <https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency>;
    reusable workflows, <https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows>;
    Actions YAML-anchor changelog, <https://github.blog/changelog/2025-09-18-actions-yaml-anchors-and-non-public-workflow-templates/>;
    checkout credential handling changelog, <https://github.blog/changelog/2026-06-18-safer-pull_request_target-defaults-for-github-actions-checkout/>;
    Actions billing (matrix = one billed job per combination),
    <https://docs.github.com/en/billing/concepts/product-billing/github-actions>;
    preventing pwn requests (`persist-credentials: false`), <https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/>;
    coverage.py configuration, <https://coverage.readthedocs.io/en/latest/config.html>;
    pytest-cov, <https://pytest-cov.readthedocs.io/en/latest/>;
    GitHub code coverage, <https://docs.github.com/en/code-security/how-tos/maintain-quality-code/set-up-code-coverage>;
    ruff configuration, <https://docs.astral.sh/ruff/configuration/>;
    ruff rule selection, <https://docs.astral.sh/ruff/linter/#rule-selection>;
    ty installation, <https://docs.astral.sh/ty/installation/>;
    ty type checking, <https://docs.astral.sh/ty/type-checking/>;
    ty version policy (Beta), <https://github.com/astral-sh/ty#version-policy>;
    ty beta announcement, <https://astral.sh/blog/ty>. Audited 2026-10-12.

24. **Configuration audit dispositions (2026-10-12)** - the follow-up to item
    23, recording what changed and what was deliberately retained. Fixed:
    (a) the `contributors snapshot` line in `cli.py` no longer relies on `+`
    binding tighter than `or` (the `(empty)` branch was dead), so an empty
    snapshot now prints the `(empty)` marker with a regression test;
    (b) the unreferenced `git_utils.full_messages` and `git_utils.branch_exists`
    helpers were removed;
    (c) the `ci.yml` header and `MAINTENANCE.md` no longer assert that GitHub
    Actions does not support YAML anchors at all - they state that anchors are
    documented but empirically unreliable here (item 23c, RESEARCH.md §2);
    (g) `.githooks/pre-commit` now shellchecks the hooks when `shellcheck` is on
    `PATH`, guarded so the hook still adds no hard tool dependency (SECURITY.md
    limits the required binaries to `git` and `gh`). Retained after review:
    (d) `ty` stays the gate while pre-1.0 because the lockfile pins the exact
    build and the floor is above the GHSA-vxvm-j4xq-q7m4 fix;
    (e) action pins stay repeated per job (anchors are empirically unreliable
    here, see §2);
    (f) the canonical gate intentionally runs twice on a release - `ci.yml` on
    the tag and `release.yml` independently before it gets write permission
    (see §2);
    (h) `downstream-check.yml` intentionally exercises the published `uvx`
    entrypoint on every push and PR;
    (i) no coverage tooling is added - the 67% figure is a prioritization
    signal only, and `ROADMAP.md`'s behavior-completeness contract deliberately
    rejects a blanket line-coverage target.

## 6. Reference URLs

- man page: <https://manpages.debian.org/testing/git-filter-repo/git-filter-repo.1.en.html>
- filter-repo issue #282 (origin removal by design): <https://github.com/newren/git-filter-repo/issues/282>
- filter-repo issue #347 (`--mirror` clone is exempt from origin removal): <https://github.com/newren/git-filter-repo/issues/347>
- git-filter-branch warning: <https://git-scm.com/docs/git-filter-branch>
- git log docs: <https://git-scm.com/docs/git-log>
- git log `--all` scope: <https://git-scm.com/docs/git-log#Documentation/git-log.txt---all>
- git rev-list `--all` definition: <https://git-scm.com/docs/git-rev-list#Documentation/git-rev-list.txt---all>
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
- CodeSigils skill-catalogue review: no prior Markdown-fragment finding as of 2026-10-31
- Addy Osmani agent-skills fragment validator: <https://github.com/addyosmani/agent-skills/blob/main/scripts/validate-reference-links.js>
- GitHub Markdown heading-link rules: <https://docs.github.com/en/get-started/writing-on-github/getting-started-with-writing-and-formatting-on-github/basic-writing-and-formatting-syntax#section-links>
- github-slugger (rendered-text contract): <https://github.com/Flet/github-slugger>
- Diátaxis how-to guides: <https://diataxis.fr/how-to-guides/>
- Diátaxis reference: <https://diataxis.fr/reference/>
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
- GitHub token security (GITHUB_TOKEN): <https://docs.github.com/en/actions/concepts/security/github_token>
- GitHub Actions workflow syntax (permissions): <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax>
- GitHub Actions events and branch/path filter behavior: <https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows>
- GitHub Actions job dependencies (`needs`): <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idneeds>
- GitHub CLI pull-request listing and its fetch limit: <https://cli.github.com/manual/gh_pr_list>
- GitHub Actions scheduled events (runs on the default branch): <https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule>
- GitHub Actions concurrency and `cancel-in-progress`: <https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#concurrency>
- CommonMark spec, fenced code blocks (backtick or tilde fences): <https://spec.commonmark.org/0.31.2/#fenced-code-blocks>
- CommonMark spec, code spans (backtick-run delimiters): <https://spec.commonmark.org/0.31.2/#code-spans>
- Git ancestry checks (`merge-base --is-ancestor`): <https://git-scm.com/docs/git-merge-base>
- GitHub ruleset controls and required checks: <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets>
- GitHub ruleset bypass modes: <https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository>
- GitHub Actions choosing when your workflow runs: <https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run>
- GitHub Dependabot grouped version updates (PR optimization): <https://docs.github.com/en/code-security/tutorials/secure-your-dependencies/optimizing-pr-creation-version-updates>
- Dependabot configuration options reference: <https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-options-reference>
- Dependabot for GitHub Actions: <https://docs.github.com/en/code-security/reference/supply-chain-security/dependabot-on-actions>
- Managing aging Dependabot pull requests: <https://docs.github.com/en/code-security/how-tos/secure-your-supply-chain/manage-your-dependency-security/manage-dependabot-prs>
- Native pull-request auto-merge: <https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/automatically-merging-a-pull-request>
- Dependabot automation and token constraints: <https://docs.github.com/en/code-security/tutorials/secure-your-dependencies/automate-dependabot-with-actions>
- uv tools guide (`uvx` = `uv tool run`; `--from` sources): <https://docs.astral.sh/uv/guides/tools/>
- uv CLI reference (tool commands): <https://docs.astral.sh/uv/reference/cli/>
- astral-sh/setup-uv: <https://github.com/astral-sh/setup-uv>
- GitHub Actions secure use (pin third-party actions by full-length SHA): <https://docs.github.com/en/actions/reference/security/secure-use>
- OpenSSF Scorecard Pinned-Dependencies check: <https://github.com/ossf/scorecard/blob/main/docs/checks.md#pinned-dependencies>
- GitHub Actions control workflow concurrency: <https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency>
- GitHub Actions reusing workflow configurations (reusable workflows, composite actions): <https://docs.github.com/en/actions/how-tos/reuse-automations/reuse-workflows>
- GitHub Actions YAML anchors/aliases changelog (2025-09-18): <https://github.blog/changelog/2025-09-18-actions-yaml-anchors-and-non-public-workflow-templates/>
- GitHub Actions checkout safer pull_request_target defaults changelog (2026-06-18): <https://github.blog/changelog/2026-06-18-safer-pull_request_target-defaults-for-github-actions-checkout/>
- GitHub Actions billing (per-job matrix cost): <https://docs.github.com/en/billing/concepts/product-billing/github-actions>
- GitHub Security Lab, preventing pwn requests (`persist-credentials: false`): <https://securitylab.github.com/resources/github-actions-preventing-pwn-requests/>
- coverage.py configuration reference: <https://coverage.readthedocs.io/en/latest/config.html>
- pytest-cov: <https://pytest-cov.readthedocs.io/en/latest/>
- GitHub code coverage (upload-code-coverage): <https://docs.github.com/en/code-security/how-tos/maintain-quality-code/set-up-code-coverage>
- python-coverage-comment-action (alternative, no third-party server): <https://github.com/py-cov-action/python-coverage-comment-action>
- Ruff configuration (target-version inference, per-file-ignores): <https://docs.astral.sh/ruff/configuration/>
- Ruff rule selection (recommended rule set): <https://docs.astral.sh/ruff/linter/#rule-selection>
- ty installation: <https://docs.astral.sh/ty/installation/>
- ty type checking: <https://docs.astral.sh/ty/type-checking/>
- ty version policy (Beta): <https://github.com/astral-sh/ty#version-policy>
- ty beta announcement: <https://astral.sh/blog/ty>

## 7. Future research (queued 2026-10-09)

Research-first entries for the queued next steps; each is an inquiry that must
land *before* implementation so the change is informed, not improvised.

- **Real-history fixture testing** — completed 2026-10-11. The observed
  [awesome-agent-trust report](reports/awesome-agent-trust-sanitizer-check.md)
  records the contributor-preservation fixture and its matching regression
  test. The follow-up [repo-health-scan report](reports/repo-health-scan-sanitizer-check.md)
  repeats the read-only check on a second repository. Both scans found zero AI
  attributions. A third [python-project-workflow-skill report](reports/python-project-workflow-skill-sanitizer-check.md)
  records zero findings and the resolved scan-scope defect: `check` now
  follows every available local and fetched ref. These results confirm
  name-pattern behavior, not GitHub identity verification: a legitimate
  co-author whose trailer contains a configured agent name would still be
  flagged.
- **Third-party CI integration** — completed 2026-10-11. The downstream shape
  is the one-step `uvx --from git+<repository-url>@<version|sha> ai-repo-sanitize check`
  under setup-uv: a plain step, not a custom action, so a consumer who asked
  only for `check` receives no rewrite capability with it. The bare exit code
  (0 clean / 1 found) is the gate and `--format json` stays available for
  machine-readable evidence. `.github/workflows/downstream-check.yml` exercises
  the shape on every push against disposable clean and attributed
  repositories. Custom composite actions re-enter consideration only when
  recorded downstream use demonstrates that the plain source-pinned step is
  inadequate. References: <https://docs.astral.sh/uv/guides/tools/>,
  <https://github.com/astral-sh/setup-uv>.
