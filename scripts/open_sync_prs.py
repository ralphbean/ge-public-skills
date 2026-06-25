#!/usr/bin/env python3
"""Create or update per-skill PRs for changed skills.

Runs sync.py first to detect and mirror changes, then creates a
separate branch and PR for each changed skill. Designed to run in CI
where git push and gh CLI are available.
"""
import json
import os
import subprocess
import sys

from scripts.sync import sync_skills, _repo_short_name


def _run(cmd, **kwargs):
    """Run a shell command, returning CompletedProcess."""
    return subprocess.run(
        cmd, capture_output=True, text=True, check=True, **kwargs
    )


def _open_pr_exists(branch_name):
    """Check if an open PR exists for the given branch."""
    result = subprocess.run(
        [
            "gh", "pr", "list",
            "--head", branch_name,
            "--state", "open",
            "--json", "number",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False
    prs = json.loads(result.stdout)
    return len(prs) > 0


def open_pr_for_skill(skill_info, repo_root):
    """Create or update a PR for a single changed skill."""
    skill_name = skill_info["name"]
    source_repo = skill_info["repo"]
    upstream_sha = skill_info["upstream_sha"]
    branch_name = f"sync/{skill_name}"
    repo_short = _repo_short_name(source_repo)

    # Start from main
    _run(["git", "checkout", "main"], cwd=repo_root)
    _run(["git", "pull", "--ff-only", "origin", "main"], cwd=repo_root)

    # Create or reset the sync branch
    _run(["git", "checkout", "-B", branch_name, "main"], cwd=repo_root)

    # Stage and commit the already-mirrored skill directory
    _run(["git", "add", f"skills/{skill_name}"], cwd=repo_root)

    commit_msg = (
        f"sync: update {skill_name} from {repo_short}\n\n"
        f"Source: {source_repo}\n"
        f"Upstream commit: {upstream_sha}\n"
    )
    _run(["git", "commit", "-m", commit_msg, "--allow-empty"], cwd=repo_root)

    # Push (force to handle branch updates)
    _run(["git", "push", "--force", "origin", branch_name], cwd=repo_root)

    # Create or update PR
    if _open_pr_exists(branch_name):
        print(f"  {skill_name}: updated existing PR on {branch_name}")
    else:
        pr_title = f"sync: update {skill_name} from {repo_short}"
        pr_body = (
            f"Automated sync of `{skill_name}` from upstream.\n\n"
            f"**Source:** {source_repo}\n"
            f"**Upstream commit:** {upstream_sha}\n"
        )
        _run([
            "gh", "pr", "create",
            "--title", pr_title,
            "--body", pr_body,
            "--head", branch_name,
            "--base", "main",
        ], cwd=repo_root)
        # Enable auto-merge
        subprocess.run(
            ["gh", "pr", "merge", branch_name, "--auto", "--squash"],
            capture_output=True, text=True, cwd=repo_root,
        )
        print(f"  {skill_name}: created PR on {branch_name} with auto-merge")

    # Return to main
    _run(["git", "checkout", "main"], cwd=repo_root)


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manifest_path = os.path.join(repo_root, "sync-manifest.yaml")

    changed = sync_skills(repo_root, manifest_path)
    if not changed:
        print("No changes to file PRs for.")
        return

    for skill_info in changed:
        print(f"Filing PR for {skill_info['name']}...")
        open_pr_for_skill(skill_info, repo_root)


if __name__ == "__main__":
    main()
