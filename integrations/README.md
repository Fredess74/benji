# Connecting Benji

| Agent | Skills | Memory |
|---|---|---|
| Claude Code, OpenClaw, Kiro | copy `skills/` into the agent's skills folder | files in `./benji-memory/` (direct) |
| Claude with custom Skills | Upload [one Benji ZIP](../downloads/benji.zip); individual skill ZIPs remain available through `python scripts/package_skills.py` | Session record by default; persistent tools need a separate compatible connection |
| Claude Desktop with local MCP | Add the skills separately | Example server config: `claude/claude_desktop_config.json`; replace local paths |
| ChatGPT with Plugin Creator available | Use the [prepared skills package and setup steps](../README.md#2-chatgpt) to create a private plugin | Session record or exported handoff; no automatic dashboard connection |
| ChatGPT custom GPT | `chatgpt/instructions.md` + skill files as knowledge | Actions from a separately secured HTTPS service's `/assistant/openapi.json`, bearer `BENJI_API_KEY` |

Connected channels share the same memory folder. With that connection configured, a place can be continued by another agent or managed on the dashboard. A skills-only session does not synchronize automatically. Each tool write is logged with its declared channel.

**OpenClaw as a small-business orchestrator:** add the skills and schedule `benji-follow-up` monthly (new bill
check) and on plan due dates. The orchestrator forbids sending, applying, booking or buying without the owner's
explicit approval for that action.

**Security:** the HTTP server has no user accounts. Keep it on 127.0.0.1. For a separately secured ChatGPT integration, `/memory/*` can require `Authorization: Bearer <key>` when `BENJI_API_KEY` is set; protect the complete exposed surface as described below. Memory holds addresses and bills —
keep it on the user's machine.

## Current status and access boundaries

The dashboard is implemented at `/app`. Point it and the agent to the same `BENJI_MEMORY` folder. The [ChatGPT skills-only package](chatgpt-plugin/README.md) is distinct from Custom GPT Actions and does not automatically connect local files. Claude Code plugin installation uses the root marketplace; Claude Desktop/web support different installation paths.

The optional bearer key now protects all data route families, including legacy calculator endpoints. It is a single-user shared secret. Do not treat the development server as a hosted multi-user service; public hosting needs user authorization, isolation and deployment hardening.
