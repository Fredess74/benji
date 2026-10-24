# Design: Benji agent skills and memory

```
User <-> Assistant (Claude / ChatGPT / OpenClaw / Kiro)
              | reads skills/benji-orchestrator -> 12 skills -> _shared (rules, formulas, data)
              | reads/writes benji-memory/<place>/  (files, or MCP / HTTP /memory tools)
              | optional: cross_check (deterministic calculator in benji/)
Dashboard ----> HTTP /memory/*  (same files; confirm bills, update tasks, answer questions)
```
- Intelligence lives in the skills; the Python package is a tool server (memory I/O + calculator), never required.
- Memory is plain files so every agent and person can read and correct it; the API only parses and edits
  structured parts (front matter, bills.csv, task and question tables) and logs every change with its channel.
- Data references are generated from repo data (`scripts/build_skill_references.py`) so agents can use BERDO and
  program information without running code.
- Decision (2026-10-24): 20 skills -> 12 after dry-runs showed overlap and over-long answers; capabilities kept.
