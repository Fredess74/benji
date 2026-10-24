"""Bundle the existing Benji workflows into one uploadable skill; Python stdlib only.

Run: python scripts/package_session_skill.py
Default output: downloads/benji.zip (safe to publish: instructions/references only).
"""
import argparse
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def build(output: Path) -> Path:
    skills = ROOT / "skills"
    specialist_dirs = sorted(p for p in skills.glob("benji-*") if p.name != "benji-orchestrator")
    text = (skills / "benji-orchestrator" / "SKILL.md").read_text(encoding="utf-8")
    text = text.replace("name: benji-orchestrator", "name: benji", 1).replace("../_shared/", "shared/")
    boundary = (ROOT / "integrations" / "chatgpt-plugin" / "host-capabilities.md").read_text(encoding="utf-8")
    boundary = boundary.replace("This plugin bundles", "This skill bundles")
    end = text.index("\n---", 3) + 4
    text = text[:end] + "\n\n" + boundary + text[end:]
    text = text.replace("## Routing", "## Routing\nRead the linked specialist workflow before applying it. These files are included in this upload.")
    for directory in specialist_dirs:
        text = text.replace(f"`{directory.name}`", f"[{directory.name}](specialists/{directory.name}.md)")
    files = {"benji/SKILL.md": text.encode("utf-8")}
    for directory in specialist_dirs:
        body = (directory / "SKILL.md").read_text(encoding="utf-8").replace("../_shared/", "../shared/")
        files[f"benji/specialists/{directory.name}.md"] = body.encode("utf-8")
    for path in sorted((skills / "_shared").rglob("*")):
        if path.is_file() and not path.is_symlink():
            files["benji/shared/" + path.relative_to(skills / "_shared").as_posix()] = path.read_text(encoding="utf-8").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(files.items()):
            # Stable timestamps keep repeated builds identical and easy to audit.
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 24, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, content)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "downloads" / "benji.zip")
    print(build(parser.parse_args().output))
