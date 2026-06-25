# ge-public-skills

A curated, automatically-synced collection of AI coding assistant skills for use with [Claude Code](https://claude.ai/code), [Cursor](https://cursor.sh/), [Lola](https://github.com/LobsterTrap/lola), and other tools that support the [AgentSkills.io](https://agentskills.io/) standard.

Skills are drawn from upstream open-source repositories maintained by Red Hat teams. Automation syncs selected skills into this repo, where they're available for direct use or installation via plugin marketplaces.

## Using these skills

**Claude Code (plugin marketplace):**
```bash
/plugin marketplace add https://github.com/RedHatProductSecurity/ge-public-skills.git
/plugin install <skill-name>
```

**Clone directly:**
```bash
git clone https://github.com/RedHatProductSecurity/ge-public-skills.git
# Skills are in skills/<skill-name>/SKILL.md
```

**Lola:**
```bash
lola install https://github.com/RedHatProductSecurity/ge-public-skills.git
```

## How it works

1. [`sync-manifest.yaml`](sync-manifest.yaml) declares which skills to pull from which upstream repos
2. A daily GitHub Actions workflow clones each upstream, compares content, and opens a PR per changed skill
3. PRs are linted automatically — if checks pass, they auto-merge
4. Post-merge, [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) is regenerated

## Upstream sources

| Repository | Description |
|-----------|-------------|
| [prodsec-skills](https://github.com/RedHatProductSecurity/prodsec-skills) | Security guidance skills for AI coding assistants |
| [konflux-ci/skills](https://github.com/konflux-ci/skills) | Skills for the Konflux CI/CD platform |

## Requesting a skill

To add a skill from an upstream source, open a PR that adds an entry to [`sync-manifest.yaml`](sync-manifest.yaml):

```yaml
sources:
  - repo: https://github.com/org/repo
    ref: main
    skills:
      - path: path/to/skill-directory
```

The sync automation will pick it up on its next run.

## Layout

```
skills/<skill-name>/
├── SKILL.md              # Primary skill file (AgentSkills.io format)
├── references/           # Optional supporting docs
├── scripts/              # Optional helper scripts
└── evals/                # Optional evaluation cases
```

## License

[Apache-2.0](LICENSE)
