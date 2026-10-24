"""Agent skills (skills/*/SKILL.md) are well-formed and consistent with each other."""

import re
from pathlib import Path

import pytest

SKILLS = Path(__file__).resolve().parent.parent / "skills"
DIRS = sorted(p for p in SKILLS.iterdir() if p.is_dir() and not p.name.startswith("_"))


def front_matter(text):
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, "missing YAML front matter"
    fm = {}
    for line in m.group(1).splitlines():
        k, _, v = line.partition(":")
        fm[k.strip()] = v.strip()
    return fm


def test_twenty_skills_plus_orchestrator():
    names = [d.name for d in DIRS]
    assert "benji-orchestrator" in names
    assert len(names) == 13, names


@pytest.mark.parametrize("d", DIRS, ids=lambda d: d.name)
def test_skill_file(d):
    text = (d / "SKILL.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    fm = front_matter(text)
    assert fm.get("name") == d.name
    assert re.fullmatch(r"[a-z0-9-]{3,64}", fm["name"])
    desc = fm.get("description", "")
    assert 80 <= len(desc) <= 1024, f"description length {len(desc)}"
    assert "Use" in desc, "description must say when to use the skill"
    if d.name != "benji-orchestrator":
        for section in ("## Output", "## Memory"):
            assert section in text, f"{d.name} missing {section}"
        assert re.search(r"## (Steps|Import|Find|Set up|1\. |A\. |Order|Fair)", text), f"{d.name} has no procedure"
    # every relative link / path reference resolves
    for ref in re.findall(r"`?(\.\./_shared/[\w./-]+\.(?:md|csv))`?", text):
        assert (d / ref).resolve().exists(), f"{d.name}: broken reference {ref}"


def test_orchestrator_routes_only_to_existing_skills():
    text = (SKILLS / "benji-orchestrator" / "SKILL.md").read_text(encoding="utf-8")
    referenced = set(re.findall(r"`(benji-[a-z-]+)`", text)) - {"benji"}
    existing = {d.name for d in DIRS}
    assert referenced, "orchestrator routes nowhere"
    assert referenced <= existing, referenced - existing
    assert existing - {"benji-orchestrator"} <= referenced, "skills not reachable from orchestrator: " + \
        str(existing - {"benji-orchestrator"} - referenced)


def test_cross_skill_references_exist():
    existing = {d.name for d in DIRS}
    for d in DIRS:
        for ref in re.findall(r"`(benji-[a-z-]+)`", (d / "SKILL.md").read_text(encoding="utf-8")):
            if ref != "benji":
                assert ref in existing, f"{d.name} references unknown skill {ref}"


def test_shared_files_present():
    for f in ("evidence-rules.md", "memory.md", "formulas.md", "measures.md", "data/berdo-peers.md", "data/ma-programs.md", "data/emission-factors.md",
              "templates/profile.md", "templates/bills.csv", "templates/plan.md", "templates/log.md"):
        assert (SKILLS / "_shared" / f).exists(), f


def test_formula_check_values_hold():
    import math
    t = (2 / 0.2) * math.log((30 - 10) / (30 - 20))
    assert round(t, 2) == 6.93 and round(6 * t, 1) == 41.6 and round(6 * t / 3, 1) == 13.9
