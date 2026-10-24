"""Package Benji skills for upload (Claude.ai / Claude Desktop "Skills", or any agent that loads one folder).

Each skill is uploaded on its own there, so `../_shared/` would not resolve. This copies `_shared/` into every
skill as `shared/`, rewrites the references, and zips each skill into dist/skills/<name>.zip.

Run: python scripts/package_skills.py
"""

import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "skills", ROOT / "dist" / "skills"
shutil.rmtree(OUT, ignore_errors=True)
OUT.mkdir(parents=True)
shared = SRC / "_shared"
for skill in sorted(d for d in SRC.iterdir() if d.is_dir() and d.name.startswith("benji-")):
    stage = OUT / skill.name
    shutil.copytree(skill, stage)
    shutil.copytree(shared, stage / "shared")
    for md in stage.rglob("*.md"):
        md.write_text(md.read_text(encoding="utf-8").replace("../_shared/", "shared/"), encoding="utf-8")
    with zipfile.ZipFile(OUT / f"{skill.name}.zip", "w", zipfile.ZIP_DEFLATED) as z:
        for f in stage.rglob("*"):
            if f.is_file():
                z.write(f, Path(skill.name) / f.relative_to(stage))
    shutil.rmtree(stage)
print("\n".join(sorted(p.name for p in OUT.iterdir())))
