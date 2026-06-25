# ge-public-skills — agent context

## What this repo is

A curated, automatically-synced collection of generally-useful AI coding assistant skills drawn from upstream open-source repositories. Skills are declared in `sync-manifest.yaml` and synced by CI automation that opens per-skill PRs with auto-merge.

## Skill layout

Skills follow the [AgentSkills.io](https://agentskills.io/) standard:

```
skills/<skill-name>/
├── SKILL.md              # Primary skill file (required)
├── references/           # Optional supporting docs
├── scripts/              # Optional helper scripts
└── evals/                # Optional evaluation cases
```

The `name` field in SKILL.md frontmatter must match the directory name (kebab-case).

## How skills get here

1. A human adds an entry to `sync-manifest.yaml` pointing at an upstream repo + skill path
2. CI clones the upstream, copies the skill directory into `skills/`, and opens a PR
3. Linting runs on the PR; if it passes, the PR auto-merges
4. Post-merge, `.claude-plugin/marketplace.json` is regenerated

## What you should know when working here

- **Never modify files under `skills/` directly.** They are mirrors of upstream content and will be overwritten on the next sync. To change which skills are included, edit `sync-manifest.yaml`.
- **Linting rules** (enforced by `scripts/lint.py` on every PR):
  1. No duplicate skill directory names across all sources
  2. Every `skills/<name>/` directory contains a SKILL.md
  3. SKILL.md has valid YAML frontmatter with non-empty `name` and `description`
  4. Frontmatter `name` matches the directory name
  5. `sync-manifest.yaml` is valid: all entries have `repo`, `ref`, `path`; no duplicate paths
- **Future linting** (not yet implemented): `skillsaw lint --strict`, evals presence check

## Commands

```bash
# Lint all skills and the manifest
python scripts/lint.py

# Generate marketplace.json from current skills/
python scripts/generate_marketplace.py

# Run tests
pytest tests/
```

## What NOT to do

- Do not manually add skill directories under `skills/` — use `sync-manifest.yaml`
- Do not edit synced skill content — changes will be overwritten
- Do not manually edit `.claude-plugin/marketplace.json` — it is auto-generated
