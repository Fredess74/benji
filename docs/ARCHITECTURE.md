# Architecture

The skills are the product; the host supplies the AI model. Benji supplies procedures, sources, memory conventions and optional tools.

| Mode | Skills only | Connected skills |
|---|---|---|
| State | Session record or exported files | Shared `BENJI_MEMORY` through file access, MCP or HTTP |
| Numbers | Explicit formulas and available host calculation tools; estimates | Optional deterministic cross-check and thermal tool |
| Dashboard | No automatic synchronization | Reads and manages the same saved record |
| Follow-up | On demand | External scheduler can invoke the skill |

The ChatGPT package is skills only. The Claude Code package declares local MCP tools. A valid package is not proof of a working external-client installation.

```mermaid
sequenceDiagram
    actor User
    participant Agent as Assistant + Benji
    participant Memory as Place memory
    participant Calc as Calculation tool
    participant UI as Dashboard
    User->>Agent: Bills, building facts, goals
    Agent->>Memory: Store extracted bills as pending
    UI->>Memory: Read pending bills
    User->>UI: Confirm or request correction
    UI->>Memory: Confirm; mark old results stale
    Agent->>Memory: Read confirmed inputs
    Agent->>Calc: Cross-check supported numbers
    Calc-->>Agent: Results and missing inputs
    Agent->>Memory: Findings, plan, tasks, log
    UI->>Memory: Poll current state
    User->>UI: Update a task
    UI->>Memory: Save decision
    Note over Agent,Memory: Later runs read assignments; assignment does not start a run
```

## The record

```text
benji-memory/<place>/
  profile.md          Facts, roles, equipment, source notes
  bills.csv           Pending / confirmed / corrected / excluded records
  findings.md         Evidence and uncertainty
  plan.md             Next step, options, task owners and status
  open-questions.md   Missing facts and answers
  log.md              Date, skill, channel and change
  documents/          Supporting text records
```

Nine MCP tools: `list_places`, `read_place`, `create_place`, `write_file`, `append_log`, `confirm_bills`, `update_task`, `cross_check`, `room_heating_scenario`. HTTP additionally supports question answers and dashboard metadata.

The calculator retains 13 implemented runtime functions in its historical 20-slot registry. This is different from 12 specialist Markdown skills plus the orchestrator.

## Computational boundaries

- Memory cross-checks translate supported profile fields and confirmed electricity/gas bills into a temporary calculator. Free-text contractor quotes and incentive approvals are not imported.
- Displaying an agent-written plan does not validate its contents. Check the source labels, missing inputs and supported numerical cross-check.
- Room scenarios are simplified single-zone heat balances, not professional sizing or humidity simulation.
- Compatible peers require suitable property type, energy coverage and sample size. Homes and small shops must not inherit large-building rankings.

## Persistence and access

The prototype is local and single-user. Bills and runtime memory are excluded from Git, but data submitted to an AI host remains subject to that host's privacy practices. The dashboard loads external Google Fonts.

The optional bearer key does not protect every legacy API route. A public service needs authentication, user isolation, secure storage and upload controls. File memory has no transactional multi-writer conflict resolution. Bill confirmation marks results stale automatically; other edits rely on the skill protocol. Channel labels are declared metadata, not verified identities.
