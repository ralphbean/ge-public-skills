#!/usr/bin/env python3
"""Sync skills from upstream repositories per sync-manifest.yaml.

For each declared skill, compares upstream content against local skills/<name>/
and creates or updates a per-skill PR if content has changed.
"""
import filecmp
import json
import os
import shutil
import subprocess
import tempfile

import yaml


def parse_manifest(manifest_path):
    """Parse sync-manifest.yaml and return the sources list."""
    with open(manifest_path) as f:
        data = yaml.safe_load(f)
    return data.get("sources") or []


def extract_skill_name(path):
    """Extract skill directory name from an upstream path."""
    return os.path.basename(path.rstrip("/"))


def detect_changes(src_dir, dst_dir):
    """Return True if src_dir content differs from dst_dir."""
    if not os.path.isdir(dst_dir):
        return True

    cmp = filecmp.dircmp(src_dir, dst_dir)
    return _dircmp_has_changes(cmp)


def _dircmp_has_changes(cmp):
    if cmp.left_only or cmp.right_only or cmp.diff_files:
        return True
    for sub in cmp.subdirs.values():
        if _dircmp_has_changes(sub):
            return True
    return False


def mirror_directory(src_dir, dst_dir):
    """Replace dst_dir contents with an exact copy of src_dir."""
    if os.path.exists(dst_dir):
        shutil.rmtree(dst_dir)
    shutil.copytree(src_dir, dst_dir)


def _run(cmd, **kwargs):
    """Run a shell command, returning CompletedProcess."""
    return subprocess.run(
        cmd, capture_output=True, text=True, check=True, **kwargs
    )


def _repo_short_name(repo_url):
    """Extract short name from repo URL (e.g., 'prodsec-skills')."""
    return os.path.basename(repo_url.rstrip("/").removesuffix(".git"))


def _get_upstream_sha(clone_dir):
    """Get HEAD SHA of a cloned repo."""
    result = _run(["git", "-C", clone_dir, "rev-parse", "HEAD"])
    return result.stdout.strip()


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


def sync_skill(
    skill_name, upstream_skill_dir, repo_root,
    source_repo, upstream_sha,
):
    """Create or update a PR for a single skill."""
    local_skill_dir = os.path.join(repo_root, "skills", skill_name)
    branch_name = f"sync/{skill_name}"
    repo_short = _repo_short_name(source_repo)

    if not detect_changes(upstream_skill_dir, local_skill_dir):
        print(f"  {skill_name}: no changes")
        return

    print(f"  {skill_name}: changes detected, syncing...")

    # Ensure we're on a clean main first
    _run(["git", "checkout", "main"], cwd=repo_root)
    _run(["git", "pull", "--ff-only", "origin", "main"], cwd=repo_root)

    # Create or reset the sync branch
    try:
        _run(["git", "checkout", "-B", branch_name, "main"], cwd=repo_root)
    except subprocess.CalledProcessError:
        _run(["git", "checkout", "-b", branch_name], cwd=repo_root)

    # Mirror the skill directory
    mirror_directory(upstream_skill_dir, local_skill_dir)

    # Stage and commit
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
    sources = parse_manifest(manifest_path)

    if not sources:
        print("No sources declared in sync-manifest.yaml")
        return

    with tempfile.TemporaryDirectory() as tmp_dir:
        for source in sources:
            repo_url = source["repo"]
            ref = source["ref"]
            repo_short = _repo_short_name(repo_url)
            clone_dir = os.path.join(tmp_dir, repo_short)

            print(f"Cloning {repo_url} (ref: {ref})...")
            _run([
                "git", "clone", "--depth", "1",
                "--branch", ref, repo_url, clone_dir,
            ])
            upstream_sha = _get_upstream_sha(clone_dir)
            print(f"  HEAD: {upstream_sha}")

            for skill_entry in source.get("skills", []):
                skill_path = skill_entry["path"]
                skill_name = extract_skill_name(skill_path)
                upstream_skill_dir = os.path.join(clone_dir, skill_path)

                if not os.path.isdir(upstream_skill_dir):
                    print(
                        f"  WARNING: {skill_path} not found in "
                        f"{repo_short}, skipping"
                    )
                    continue

                sync_skill(
                    skill_name, upstream_skill_dir,
                    repo_root, repo_url, upstream_sha,
                )


if __name__ == "__main__":
    main()
