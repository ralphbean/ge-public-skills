# Required Repository Settings

These settings must be configured for the sync automation to work correctly.

## 1. Allow GitHub Actions to create issues

**Settings > Actions > General > Workflow permissions**

- Enable "Read and write permissions"

The sync workflow pushes directly to main and opens GitHub issues for
skills that fail lint. It needs write access to contents and issues.

## 2. Branch ruleset on `main`

**Settings > Rules > Rulesets** — create a ruleset targeting `main`:

### Required status checks

- Add `lint` as a required status check
- Add the GitHub Actions integration as a bypass actor

The lint check gates human PRs. The sync workflow bypasses it because
it runs lint internally before committing (using the same `lint_skill()`
function from `scripts/lint.py`).

### Bypass actors

- Repository admin role (for manual pushes during setup)
- GitHub Actions integration (for automated sync pushes)

On personal repos, GitHub Actions cannot be added as a bypass actor via
the API. This works on organization repos.
