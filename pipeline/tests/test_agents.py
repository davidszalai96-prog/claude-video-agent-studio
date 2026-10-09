"""The agent files stay consistent: valid frontmatter, a flat studio, preloaded skills that exist."""
import re
from pathlib import Path

import pytest
import yaml

import studio_lib as lib

AGENTS = sorted((lib.REPO / ".claude" / "agents").glob("*.md"))
FIELDS = {"name", "description", "tools", "disallowedTools", "model", "permissionMode", "maxTurns", "skills", "mcpServers",
          "hooks", "memory", "background", "omitClaudeMd", "effort", "isolation", "color", "initialPrompt", "experimental"}
PROJECT_SKILLS = {p.parent.name for p in (lib.REPO / ".claude" / "skills").glob("*/SKILL.md")}
USER_SKILLS = {p.parent.name for p in (Path.home() / ".claude" / "skills").glob("*/SKILL.md")}


def frontmatter(path):
    m = re.match(r"---\n(.*?)\n---\n", path.read_text("utf-8"), re.S)
    return yaml.safe_load(m.group(1))


def test_fifteen_agents_and_a_flat_studio():
    fms = {frontmatter(p)["name"]: frontmatter(p) for p in AGENTS}
    assert len(fms) == 15
    listed = set(x.strip() for x in re.search(r"Agent\((.*?)\)", fms["producer"]["tools"]).group(1).split(","))
    assert listed == set(fms) - {"producer"}
    for name, fm in fms.items():
        if name != "producer":
            assert "Agent" not in fm.get("tools", ""), f"{name} must not start agents"


@pytest.mark.parametrize("path", AGENTS, ids=[p.stem for p in AGENTS])
def test_frontmatter_fields_and_skills(path):
    fm = frontmatter(path)
    assert set(fm) <= FIELDS, set(fm) - FIELDS
    assert fm["model"] in ("opus", "sonnet", "haiku")
    assert fm["skills"][0] == "studio-conventions"
    for s in fm["skills"]:
        assert s in PROJECT_SKILLS or s in USER_SKILLS or s in ("comfy-bridge", "vram-watch"), f"missing skill {s}"
    if "video-use" in fm["skills"]:
        assert "video-use-studio" in fm["skills"], "video-use always comes with the studio's rules for it"
        assert "Skill" in fm["tools"]


@pytest.mark.skipif(not (Path.home() / ".claude" / "skills" / "video-use" / "SKILL.md").exists(), reason="video-use not installed")
def test_video_use_is_installed_for_the_user():
    assert "video-use" in USER_SKILLS
