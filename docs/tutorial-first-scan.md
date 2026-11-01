# Tutorial: inspect a disposable repository

> Last reviewed: 2026-11-01

This tutorial gives you one safe, complete first experience: create a tiny Git
repository with an attribution trailer, detect it, and preview the affected
commit. It does not rewrite history or contact a remote.

## Before you begin

You need Git and [uv](https://docs.astral.sh/uv/), plus a checkout of this
repository. Start in that checkout. The first command records its location so
you can return to it after creating a disposable repository.

```bash
REPO_ROOT="$(pwd)"
TUTORIAL_DIR="$(mktemp -d)"
cd "$TUTORIAL_DIR"
git init
git config user.name "Tutorial User"
git config user.email "tutorial@example.invalid"
git commit --allow-empty -m "docs: demonstrate a trailer" -m "Co-authored-by: Claude <noreply@anthropic.com>"
```

You now have a one-commit repository. The commit message intentionally carries
an attribution trailer that the tool should find.

## Check the history

Return to the repository checkout, then run the check against the disposable
repository:

```bash
cd "$REPO_ROOT"
uv run ai-repo-sanitize check --path "$TUTORIAL_DIR"
```

The command reports the matching commit and exits with code `1`: it found
attribution, not a tool failure. See the [exit-code reference](../README.md#exit-codes)
for the complete contract.

## Preview the affected commit

```bash
uv run ai-repo-sanitize preview --path "$TUTORIAL_DIR"
```

The output identifies the same commit without changing the repository. You
have now completed the read-only inspection path.

## What to do next

Do not treat this disposable example as permission to rewrite a real project.
For the deliberate rewrite procedure, read the [maintenance guide](../MAINTENANCE.md)
and its safety checks first. Delete the temporary tutorial repository when you
are done. Return to the [documentation index](README.md) to choose the next
guide.
