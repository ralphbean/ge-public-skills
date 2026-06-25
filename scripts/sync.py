#!/usr/bin/env python3
"""Sync skills from upstream repositories per sync-manifest.yaml.

Clones each declared upstream, detects changes, and mirrors skill
directories into skills/. This script does local work only — no git
commits, no PRs. See open_sync_prs.py for the CI-side PR management.
"""
import filecmp
import os
import shutil
import subprocess
import sys
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


def sync_skills(repo_root, manifest_path):
    """Sync all skills declared in the manifest.

    Returns a list of dicts describing changed skills:
        [{"name": str, "repo": str, "upstream_sha": str}, ...]
    """
    sources = parse_manifest(manifest_path)
    changed = []

    if not sources:
        print("No sources declared in sync-manifest.yaml")
        return changed

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
            result = _run(["git", "-C", clone_dir, "rev-parse", "HEAD"])
            upstream_sha = result.stdout.strip()
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

                local_skill_dir = os.path.join(
                    repo_root, "skills", skill_name,
                )
                if not detect_changes(upstream_skill_dir, local_skill_dir):
                    print(f"  {skill_name}: no changes")
                    continue

                print(f"  {skill_name}: changes detected, mirroring...")
                mirror_directory(upstream_skill_dir, local_skill_dir)
                changed.append({
                    "name": skill_name,
                    "repo": repo_url,
                    "upstream_sha": upstream_sha,
                })

    return changed


def main():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    manifest_path = os.path.join(repo_root, "sync-manifest.yaml")
    changed = sync_skills(repo_root, manifest_path)

    if changed:
        print(f"\nSynced {len(changed)} skill(s):")
        for skill in changed:
            print(f"  - {skill['name']} from {skill['repo']}")
    else:
        print("\nNo changes detected.")


if __name__ == "__main__":
    main()
