"""A single-upload skill must contain every routed workflow and reference."""
import re
import subprocess
import sys
import zipfile
from pathlib import Path, PurePosixPath


def test_session_archive_is_self_contained_and_reproducible(tmp_path):
    root = Path(__file__).resolve().parent.parent
    out = tmp_path / "benji.zip"
    command = [sys.executable, str(root / "scripts" / "package_session_skill.py"), "--output", str(out)]
    subprocess.run(command, check=True, capture_output=True, text=True)
    first = out.read_bytes()
    subprocess.run(command, check=True, capture_output=True, text=True)
    assert out.read_bytes() == first
    with zipfile.ZipFile(out) as z:
        files = set(z.namelist())
        assert "benji/SKILL.md" in files
        assert len([f for f in files if f.startswith("benji/specialists/")]) == 12
        assert all(PurePosixPath(f).parts[0] == "benji" and ".." not in PurePosixPath(f).parts for f in files)
        assert not any(f.endswith((".db", ".env", ".py")) or "/benji-memory/" in f for f in files)
        # Resolve the navigation presented to the consuming assistant inside the archive.
        text = z.read("benji/SKILL.md").decode()
        paths = re.findall(r"\]\((specialists/[^)]+)\)", text)
        assert len(set(paths)) == 12
        for path in paths:
            assert "benji/" + path in files
        for file in files:
            if file.endswith(".md"):
                content = z.read(file).decode()
                for ref in re.findall(r"`((?:\.\./)?shared/[\w./-]+\.(?:md|csv))`", content):
                    full = PurePosixPath(file).parent / ref
                    parts = []
                    for p in full.parts:
                        if p == "..":
                            parts.pop()
                        else:
                            parts.append(p)
                    assert "/".join(parts) in files, (file, ref)
