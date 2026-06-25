# Required Repository Settings

These settings must be configured for the sync automation to work correctly.

## 1. Allow GitHub Actions to create PRs

**Settings > Actions > General > Workflow permissions**

- Enable "Allow GitHub Actions to create and approve pull requests"

Without this, the sync workflow cannot open PRs for new/updated skills.

## 2. Branch ruleset on `main`

**Settings > Rules > Rulesets** — create a ruleset targeting `main`:

### Required status checks

- Add `lint` as a required status check

This ensures synced skills pass linting before merging.

### Merge queue

- Enable merge queue with squash merge method

The sync automation files one PR per skill. A merge queue ensures they
merge sequentially without conflicts (each skill PR rebases on the
latest `main` before merging). Without this, the second PR in a batch
may fail to auto-merge because the first PR changed `main` under it.

## 3. Auto-merge

The sync script calls `gh pr merge --auto --squash` on each PR. This
requires the merge queue (or at minimum required status checks) to be
configured — otherwise auto-merge has no requirements to wait for and
the behavior is unpredictable.
