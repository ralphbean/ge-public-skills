#!/usr/bin/env python3
"""Sync skills from upstream repositories per sync-manifest.yaml.

Clones each declared upstream, detects changes, lints each skill, and
either commits passing skills directly to main or opens a GitHub issue
for skills that fail lint.
"""
import filecmp
import json
import os
import shutil
import subprocess
import sys
import tempfile

import yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.lint import lint_skill


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
    result = subprocess.run(cmd, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        print(f"Command failed: {cmd}", file=sys.stderr)
        if result.stdout:
            print(f"stdout: {result.stdout}", file=sys.stderr)
        if result.stderr:
            print(f"stderr: {result.stderr}", file=sys.stderr)
        result.check_returncode()
    return result


def _repo_short_name(repo_url):
    """Extract short name from repo URL (e.g., 'prodsec-skills')."""
    return os.path.basename(repo_url.rstrip("/").removesuffix(".git"))


def _find_existing_issue(skill_name):
    """Find an open issue for a sync failure of this skill."""
    result = subprocess.run(
        [
            "gh", "issue", "list",
            "--state", "open",
            "--label", "sync-failure",
            "--search", f"sync: {skill_name} lint failure",
            "--json", "number,title",
        ],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    issues = json.loads(result.stdout)
    for issue in issues:
        if skill_name in issue["title"]:
            return issue["number"]
    return None


def _open_or_update_issue(skill_name, repo_url, upstream_sha, lint_errors):
    """Open or update a GitHub issue for a lint failure."""
    title = f"sync: {skill_name} lint failure"
    body = (
        f"Automated sync of `{skill_name}` failed lint checks.\n\n"
        f"**Source:** {repo_url}\n"
        f"**Upstream commit:** {upstream_sha}\n\n"
        f"**Lint errors:**\n"
    )
    for err in lint_errors:
        body += f"- {err}\n"

    existing = _find_existing_issue(skill_name)
    if existing:
        subprocess.run(
            [
                "gh", "issue", "comment", str(existing),
                "--body", body,
            ],
            capture_output=True, text=True,
        )
        print(f"  {skill_name}: updated issue #{existing}")
    else:
        # Ensure the sync-failure label exists
        subprocess.run(
            ["gh", "label", "create", "sync-failure",
             "--description", "Automated sync failed lint",
             "--color", "d73a4a"],
            capture_output=True, text=True,
        )
        subprocess.run(
            [
                "gh", "issue", "create",
                "--title", title,
                "--body", body,
                "--label", "sync-failure",
            ],
            capture_output=True, text=True,
        )
        print(f"  {skill_name}: opened new issue")


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

    if not changed:
        print("\nNo changes detected.")
        return

    # Lint each changed skill, separate into pass/fail
    passed = []
    failed = []
    for skill in changed:
        errors = lint_skill(repo_root, skill["name"])
        if errors:
            print(f"  {skill['name']}: LINT FAILED")
            for err in errors:
                print(f"    {err}")
            failed.append((skill, errors))
            # Revert the mirror so we don't commit a broken skill
            skill_dir = os.path.join(repo_root, "skills", skill["name"])
            shutil.rmtree(skill_dir)
        else:
            print(f"  {skill['name']}: lint passed")
            passed.append(skill)

    # Commit and push all passing skills in one commit
    if passed:
        for skill in passed:
            _run(["git", "add", f"skills/{skill['name']}"], cwd=repo_root)

        lines = [f"  - {s['name']} from {_repo_short_name(s['repo'])}"
                 for s in passed]
        commit_msg = "sync: update skills from upstream\n\n" + "\n".join(
            f"- {s['name']} from {_repo_short_name(s['repo'])} "
            f"({s['upstream_sha'][:12]})"
            for s in passed
        )
        _run(["git", "commit", "-m", commit_msg], cwd=repo_root)
        _run(["git", "push", "origin", "main"], cwd=repo_root)
        print(f"\nPushed {len(passed)} skill(s) to main:")
        for skill in passed:
            print(f"  - {skill['name']}")

    # File issues for failures
    for skill, errors in failed:
        _open_or_update_issue(
            skill["name"], skill["repo"],
            skill["upstream_sha"], errors,
        )

    if failed:
        print(f"\n{len(failed)} skill(s) failed lint — issues filed.")


if __name__ == "__main__":
    main()
