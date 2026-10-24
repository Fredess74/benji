"""Build one skills-only Agent Plugins archive; never include user memory or secrets."""
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "integrations" / "chatgpt-plugin"


def build():
    manifest = json.loads((SOURCE / "plugin.json").read_text(encoding="utf-8"))
    interface = manifest["extensions"]["com.openai"]["interface"]
    assert len(interface["shortDescription"]) <= 30
    assert manifest["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    out = ROOT / "dist"
    out.mkdir(exist_ok=True)
    archive = out / f"benji-chatgpt-skills-{manifest['version']}.zip"
    boundary = (SOURCE / "host-capabilities.md").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory(prefix="benji-package-") as tmp:
        package = Path(tmp) / "benji"
        package.mkdir()
        shutil.copytree(ROOT / "skills", package / "skills")
        (package / "assets").mkdir()
        for icon in ("benji-app-icon.svg", "benji-mark.svg"):
            shutil.copy2(ROOT / "docs" / "brand" / icon, package / "assets" / icon)
        (package / "plugin.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        # Preserve older-host compatibility without adding an MCP/app declaration.
        compat = {k: manifest[k] for k in ("name", "version", "description", "author", "homepage", "repository", "keywords")}
        compat.update({"interface": interface, "skills": "./skills"})
        (package / ".codex-plugin").mkdir()
        (package / ".codex-plugin" / "plugin.json").write_text(json.dumps(compat, indent=2) + "\n", encoding="utf-8")
        skills = sorted((package / "skills").glob("benji-*/SKILL.md"))
        assert len(skills) == 13
        for skill in skills:
            content = skill.read_text(encoding="utf-8")
            end = content.find("\n---", 3)
            assert content.startswith("---\n") and end > 0
            skill.write_text(content[:end + 4] + "\n\n" + boundary + content[end + 4:], encoding="utf-8")
        for asset in (interface["logo"], interface["composerIcon"]):
            assert (package / asset).is_file()
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
            for p in sorted(package.rglob("*")):
                if p.is_file():
                    assert not p.is_symlink()
                    z.write(p, Path("benji") / p.relative_to(package))
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert len([p for p in z.namelist() if p.endswith("/SKILL.md")]) == 13
        assert not any(p.endswith(".app.json") or "marketplace.json" in p for p in z.namelist())
    print(archive)


if __name__ == "__main__":
    build()
