# Dashboard design and implementation notes

**Implemented:** `dashboard/index.html`, served at `/app`. Current views: Home, Agents, Memory and Activity. The requirements below record the design direction; they are not a claim that every proposed control is implemented. See [VERIFICATION.md](VERIFICATION.md).

**Role:** the management view of what the Benji agent knows and is doing for each place. The conversation happens
in the assistant; the dashboard is where the person **checks, confirms, decides and tracks**. Manual data entry is
deliberately minimal (upload a file, fix a value) — the agent collects data.

**Data source:** the file memory via the HTTP API (`python -m uvicorn benji.api:app --port 8000`, OpenAPI at
`/docs`). Every write is logged with channel `dashboard` (send header `x-benji-channel: dashboard`). Display only
what the API returns; the dashboard does no energy or money calculations.

| Endpoint | Use |
|---|---|
| `GET /memory/places` | Place cards: name, type, role, next step, bills to confirm, open tasks, open questions, stale flag, last activity |
| `GET /memory/places/{slug}` | Place page: `profile` (value + source note per field), `next_step`, `actions`, `tasks`, `not_now`, `findings` (titles), `bills`, `bills_pending`, `open_questions`, `log`, `documents`, `plan_stale`, `findings_stale`, `raw` files (Markdown) |
| `POST /memory/places/{slug}/bills/confirm` `{bill_ids?, confirmed_by}` | "These are correct" for bills the agent extracted |
| `PATCH /memory/places/{slug}/tasks/{id}` `{status?, owner?, due?}` | Task tracking (status: not_started, in_progress, blocked, done, skipped) |
| `POST /memory/places/{slug}/questions/{id}` `{answer}` | Answer what Benji asked |
| `GET /memory/places/{slug}/cross-check` | Optional "verify numbers" panel: costs per fuel, usage-based rates, peer comparison, applicable options, program leads |
| `PUT /memory/places/{slug}/files/{file}` | Edit a memory file (advanced) |

## Screens
1. **Places** — cards; badges for "to confirm", "needs refresh" (stale), open tasks. Empty state explains how to
   connect an assistant.
2. **Place** — top: **Next step** (big). Then **Waiting for you** (pending bills table with "Correct — use them" /
   "Something's wrong"; unanswered questions with inline answer). Then **Plan** (actions table + task list with
   status/owner/due controls). Side: profile facts with their source notes, findings list, programs, **Activity**
   timeline showing which channel (Claude / ChatGPT / OpenClaw / Dashboard) did what. Render `raw` Markdown for
   findings and reports.
3. When `plan_stale` is true: banner "Something changed — ask Benji to refresh the plan."

## Must keep
- Labels as written by Benji (estimate / from your bills / assumption / unverified lead); never restyle an estimate
  into a "saving".
- No demo data. Plain words, readable on a phone, keyboard accessible, text labels next to status colours.
- Poll `GET /memory/places/{slug}` (e.g. every 10 s) so changes made by the agent appear without reload.
