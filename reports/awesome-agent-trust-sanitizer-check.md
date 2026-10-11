# `awesome-agent-trust` sanitizer check

> Observed: 2026-10-11

## Source

- Repository: `CodeSigils/awesome-agent-trust`
- Commit: `1071322896a5387f0fabfb6ab64ace8551987b2c`
- History scanned: 114 commits
- GitHub contributor identities: `CodeSigils`, `InsightFactoryAPP`,
  `dependabot[bot]`, and `piiiico`

## Observation

`ai-repo-sanitize check --path .` reported `114 commit(s) scanned, 0 with AI
attribution`; `preview` reported `0 commit(s) would change`.

The history contains genuine `Co-authored-by` trailers for `CodeSigils` and
`dependabot[bot]`; neither was flagged. A disposable fixture then verified
that trailers for all four listed contributor identities are preserved, while
a separate `Co-authored-by: Codex` trailer is flagged.

## Result

No false positive was observed. The fixture is now a regression test in
[`tests/test_patterns.py`](../tests/test_patterns.py). This demonstrates the
tool's configured name-pattern matching; it does not establish GitHub
identity verification.

## Recommendation

No production change is recommended from this clean run. Retain the named
contributor regression test and repeat this procedure when the attribution
pattern set changes.
