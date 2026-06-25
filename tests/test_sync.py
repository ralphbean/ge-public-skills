"""tests/test_sync.py"""
from scripts.sync import (
    parse_manifest,
    extract_skill_name,
    mirror_directory,
    detect_changes,
)


class TestParseManifest:
    def test_empty_sources(self, tmp_path):
        manifest = tmp_path / "sync-manifest.yaml"
        manifest.write_text("sources: []\n")
        result = parse_manifest(str(manifest))
        assert result == []

    def test_parses_sources(self, tmp_path):
        manifest = tmp_path / "sync-manifest.yaml"
        manifest.write_text(
            "sources:\n"
            "  - repo: https://github.com/org/repo\n"
            "    ref: main\n"
            "    skills:\n"
            "      - path: module/skills/my-skill\n"
        )
        result = parse_manifest(str(manifest))
        assert len(result) == 1
        assert result[0]["repo"] == "https://github.com/org/repo"
        assert result[0]["ref"] == "main"
        assert len(result[0]["skills"]) == 1


class TestExtractSkillName:
    def test_simple_path(self):
        assert extract_skill_name("skills/my-skill") == "my-skill"

    def test_nested_path(self):
        assert extract_skill_name("module/skills/my-skill") == "my-skill"

    def test_trailing_slash(self):
        assert extract_skill_name("skills/my-skill/") == "my-skill"


class TestMirrorDirectory:
    def test_copies_files(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        (src / "SKILL.md").write_text("# Skill")
        mirror_directory(str(src), str(dst))
        assert (dst / "SKILL.md").read_text() == "# Skill"

    def test_copies_subdirectories(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        (src / "references").mkdir(parents=True)
        (src / "references" / "doc.md").write_text("# Doc")
        mirror_directory(str(src), str(dst))
        assert (dst / "references" / "doc.md").read_text() == "# Doc"

    def test_removes_old_files(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()
        (dst / "old-file.md").write_text("stale")
        (src / "SKILL.md").write_text("# Skill")
        mirror_directory(str(src), str(dst))
        assert not (dst / "old-file.md").exists()
        assert (dst / "SKILL.md").exists()

    def test_overwrites_changed_content(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()
        (src / "SKILL.md").write_text("# Updated")
        (dst / "SKILL.md").write_text("# Original")
        mirror_directory(str(src), str(dst))
        assert (dst / "SKILL.md").read_text() == "# Updated"


class TestDetectChanges:
    def test_new_skill(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        (src / "SKILL.md").write_text("# Skill")
        assert detect_changes(str(src), str(dst)) is True

    def test_no_changes(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()
        (src / "SKILL.md").write_text("# Skill")
        (dst / "SKILL.md").write_text("# Skill")
        assert detect_changes(str(src), str(dst)) is False

    def test_content_changed(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()
        (src / "SKILL.md").write_text("# Updated")
        (dst / "SKILL.md").write_text("# Original")
        assert detect_changes(str(src), str(dst)) is True

    def test_file_removed_upstream(self, tmp_path):
        src = tmp_path / "src"
        dst = tmp_path / "dst"
        src.mkdir()
        dst.mkdir()
        (src / "SKILL.md").write_text("# Skill")
        (dst / "SKILL.md").write_text("# Skill")
        (dst / "old.md").write_text("stale")
        assert detect_changes(str(src), str(dst)) is True
