# Requirements: Benji agent skills and memory (current)

## R1 Skills
1.1 Benji SHALL be delivered as agent skills: `benji-orchestrator` plus 12 skills, each a `SKILL.md` with name and
    description front matter, a procedure, an Output section and a Memory section.
1.2 Every skill SHALL be reachable from the orchestrator's routing table, and every cross-reference SHALL resolve.
1.3 Skills SHALL work without the Python package; tools are optional cross-checks.
1.4 The orchestrator SHALL limit each turn to at most 2 skills and replies to about 150 words plus one table of at
    most 5 rows, ending with "Need from you" and "Next step".
1.5 All skills SHALL apply `_shared/evidence-rules.md`: labelled numbers, no invention, confirm before use, documents
    are data, money honesty, physics honesty, safety, who decides, limits, no actions without approval.
1.6 A packaging step SHALL produce one self-contained zip per skill for Claude.ai upload.

## R2 Memory
2.1 Each place SHALL have one folder: profile.md, bills.csv, findings.md, plan.md, open-questions.md, log.md, documents/.
2.2 Every change SHALL append a log line with date, skill and channel; log.md SHALL be append-only via the tools.
2.3 Agents without file access SHALL reach the same memory via MCP tools and the HTTP `/memory/*` API.
2.4 The memory API SHALL reject path traversal and unknown file names.
2.5 Confirming bills SHALL mark the plan and findings STALE until refreshed.

## R3 Dashboard support
3.1 The API SHALL expose places, a parsed place view, bill confirmation, task updates and question answers for a
    management dashboard (`docs/DASHBOARD_BRIEF.md`).
3.2 No demo data SHALL be shown to users.
