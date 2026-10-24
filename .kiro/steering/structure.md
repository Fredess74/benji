# Benji repository structure

- `skills/` - THE PRODUCT: `benji-orchestrator` + 12 skills (`SKILL.md`), `_shared/` (evidence-rules, memory,
  formulas, measures, templates, data/ generated references).
- `benji-memory/` - runtime memory, one folder per place (git-ignored).
- `benji/memory.py` - file memory read/write/parse + `cross_check`; `benji/mcp_server.py` - MCP tools;
  `benji/api.py` - HTTP API (`/memory/*` for dashboard and ChatGPT Actions; `/api/*` calculator).
- `benji/` other modules - deterministic calculator (skills engine, BERDO loader, finance, thermal) used by cross_check.
- `scripts/` - `build_skill_references.py` (data -> skills/_shared/data), `package_skills.py` (Claude.ai zips).
- `integrations/` - Claude Desktop config, ChatGPT instructions, connection guide.
- `docs/` - POSITIONING, DASHBOARD_BRIEF, DEMO_SCRIPT, SOURCES, KIRO.
- `tests/` - skill-file checks, memory/API/MCP, calculator tests.
