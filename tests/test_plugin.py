"""The repo is also a Claude Code plugin + marketplace: manifests must stay valid and point at real parts."""

import json
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


def _json(rel):
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def test_plugin_and_marketplace_manifests():
    plugin = _json(".claude-plugin/plugin.json")
    market = _json(".claude-plugin/marketplace.json")
    assert plugin["name"] == "benji" and plugin["version"]
    entry = next(p for p in market["plugins"] if p["name"] == plugin["name"])
    assert entry["source"] == "./" and entry["version"] == plugin["version"]
    assert market["owner"]["name"]


def test_plugin_mcp_server_config():
    srv = _json(".mcp.json")["mcpServers"]["benji"]
    assert srv["args"] == ["-m", "benji.mcp_server"]
    assert srv["env"]["PYTHONPATH"] == "${CLAUDE_PLUGIN_ROOT}"
    assert "benji-memory" in srv["env"]["BENJI_MEMORY"]  # outside the plugin cache, survives updates
    assert "fastmcp" in (REPO / "requirements.txt").read_text(encoding="utf-8")


def test_plugin_skills_are_discoverable():
    dirs = [d for d in (REPO / "skills").iterdir() if d.is_dir() and not d.name.startswith("_")]
    assert len(dirs) == 13 and all((d / "SKILL.md").exists() for d in dirs)
