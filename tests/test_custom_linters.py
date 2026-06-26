"""Tests for custom skill linting checks."""

import textwrap

import pytest

from scripts.custom_linters import lint_skill_dir


@pytest.fixture
def skill_dir(tmp_path):
    """Create a valid skill directory with SKILL.md."""
    skill = tmp_path / "my-skill"
    skill.mkdir()
    skill_md = skill / "SKILL.md"
    skill_md.write_text(textwrap.dedent("""\
        ---
        name: my-skill
        description: A test skill
        ---
        Skill content here.
    """))
    return skill


class TestSkillMdPresence:
    def test_missing_skill_md(self, tmp_path):
        skill = tmp_path / "no-skill"
        skill.mkdir()
        errors = lint_skill_dir(skill)
        assert any("SKILL.md" in e for e in errors)

    def test_present_skill_md(self, skill_dir):
        errors = lint_skill_dir(skill_dir)
        assert not errors


class TestFrontmatterValidation:
    def test_no_frontmatter(self, tmp_path):
        skill = tmp_path / "bad-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text("No frontmatter here.")
        errors = lint_skill_dir(skill)
        assert any("frontmatter" in e.lower() for e in errors)

    def test_empty_name(self, tmp_path):
        skill = tmp_path / "bad-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(textwrap.dedent("""\
            ---
            name: ""
            description: Something
            ---
        """))
        errors = lint_skill_dir(skill)
        assert any("name" in e.lower() for e in errors)

    def test_empty_description(self, tmp_path):
        skill = tmp_path / "bad-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(textwrap.dedent("""\
            ---
            name: bad-skill
            description: ""
            ---
        """))
        errors = lint_skill_dir(skill)
        assert any("description" in e.lower() for e in errors)

    def test_missing_name_field(self, tmp_path):
        skill = tmp_path / "bad-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(textwrap.dedent("""\
            ---
            description: Something
            ---
        """))
        errors = lint_skill_dir(skill)
        assert any("name" in e.lower() for e in errors)

    def test_missing_description_field(self, tmp_path):
        skill = tmp_path / "bad-skill"
        skill.mkdir()
        (skill / "SKILL.md").write_text(textwrap.dedent("""\
            ---
            name: bad-skill
            ---
        """))
        errors = lint_skill_dir(skill)
        assert any("description" in e.lower() for e in errors)


class TestNameDirectoryMatch:
    def test_name_mismatch(self, tmp_path):
        skill = tmp_path / "actual-name"
        skill.mkdir()
        (skill / "SKILL.md").write_text(textwrap.dedent("""\
            ---
            name: wrong-name
            description: A skill
            ---
        """))
        errors = lint_skill_dir(skill)
        assert any("match" in e.lower() or "mismatch" in e.lower() for e in errors)

    def test_name_matches(self, skill_dir):
        errors = lint_skill_dir(skill_dir)
        assert not errors
