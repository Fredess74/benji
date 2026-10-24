# Connecting Benji

| Agent | Skills | Memory |
|---|---|---|
| Claude Code, OpenClaw, Kiro | copy `skills/` into the agent's skills folder | files in `./benji-memory/` (direct) |
| Claude Desktop / Claude.ai | `python scripts/package_skills.py`, upload `dist/skills/*.zip` | MCP server: `claude/claude_desktop_config.json` |
| ChatGPT custom GPT | `chatgpt/instructions.md` + skill files as knowledge | Actions from `https://<tunnel>/assistant/openapi.json` (the `/memory/*` API), bearer `BENJI_API_KEY` |

All channels share the same memory folder, so a place started in Claude can be continued in ChatGPT, by an OpenClaw
agent, or managed on the dashboard. Each write is logged with its channel.

**OpenClaw as a small-business orchestrator:** add the skills and schedule `benji-follow-up` monthly (new bill
check) and on plan due dates. The orchestrator forbids sending, applying, booking or buying without the owner's
explicit approval for that action.

**Security:** the HTTP server has no user accounts. Keep it on 127.0.0.1. For a ChatGPT demo through a tunnel, set
`BENJI_API_KEY` first; `/memory/*` then requires `Authorization: Bearer <key>`. Memory holds addresses and bills —
keep it on the user's machine.
