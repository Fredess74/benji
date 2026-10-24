# Benji memory — one record per place

Memory is the product's backbone: the agent, the person and the dashboard all read and write the same files.

```
benji-memory/
  <place-slug>/          e.g. corner-bean-cambridge
    profile.md           facts (front matter), each with source + date
    bills.csv            one row per bill: pending | confirmed | corrected | excluded
    findings.md          dated findings F-001…, each with evidence
    plan.md              next step + actions + task table (owner, due, status)
    open-questions.md    what Benji still needs and who can answer
    log.md               append-only: date | skill | channel | what changed
    documents/           bills, quotes, reports, drafts (optional)
```
Create a new place from `templates/`. Slug = short lowercase name + town.

**How to access it**
- Agent with files (Claude Code, OpenClaw, Kiro): read/write the folder directly. Default location:
  `./benji-memory/` in the workspace.
- Agent without files (Claude Desktop, ChatGPT): use the Benji memory tools — `list_places`, `read_place`,
  `write_file`, `append_log` (MCP server `benji`, or HTTP `/memory/...`).
- No memory access at all: keep the same structure in the chat and offer the files at the end.

**Rules**
1. Read `profile.md`, `open-questions.md`, `plan.md` and the last lines of `log.md` before acting. Don't re-ask what
   memory knows — confirm it.
2. Every fact: `value  # source, YYYY-MM-DD`.
3. Never silently overwrite. Conflicts → ask, then record the answer in the log.
4. When bills or facts change, put `STALE since <date>: <reason>` at the top of `findings.md` and `plan.md` until
   the affected skill is re-run.
5. Append one `log.md` line for every change: `2026-10-24 | benji-bills-import | claude | 12 bills added (pending)`.
6. Mask account numbers to the last 4 digits. One folder per place; never copy data between places.

**Status words:** tasks `not_started | in_progress | blocked | done | skipped`; programs `lead | potentially_eligible |
condition_not_met | more_info_needed | applied | approved | disbursed | rejected`.
