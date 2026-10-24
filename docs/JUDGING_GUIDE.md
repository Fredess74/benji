# Judge's guide

**Hackachusetts 2026 · TRACK 3 — CLIMATE TECH**
**Cleaner, more affordable buildings**

## Potential Value

The problem is connecting bills, building conditions, available cash, support rules and approval authority. Benji offers reusable energy-management skills in an existing assistant, with a persistent record and a human management view.

The workflow accounts for tenants and owners, starts with low-cost steps where appropriate, and protects comfort. Bill-based guidance requires no special hardware. Host subscriptions and setup remain costs. The UI is English; replying in the user's language is a skill instruction, not validated multilingual service delivery.

Scalability is a hypothesis supported by reusable skills and local reference adapters, not proven capacity for a hosted multi-user service. [Evidence](EVIDENCE.md) · [Impact](IMPACT.md)

## Implementation

Inspect `.kiro/specs/`, `.kiro/steering/` and `.kiro/hooks/`. Kiro supported requirements, implementation, tests and iterative simplification. The reusable record joins conversational work with confirmation, task management and calculation cross-checks.

Claude Code packaging declares skills and local MCP tools. ChatGPT packaging supplies skills only. Nine MCP tools expose memory and calculations. The 176 passing checks cover computational and integration components, not every external client. [Kiro](KIRO.md) · [Architecture](ARCHITECTURE.md) · [Verification](VERIFICATION.md)

## Quality and Design

- The next action is visually prominent.
- Extracted bills wait for confirmation.
- Cash and approval responsibility are visible.
- Incomplete calculations remain incomplete.
- Home, Agents, Memory and Activity make the record inspectable.
- Short responses reduce information overload; detailed evidence stays in the record.

These are design choices, not proven usability gains or an accessibility certification. The originality is their combination around building decisions; comparative advantage still needs evaluation.

## Three-minute demonstration

To try the dashboard without a connected client: `python scripts/load_demo.py`, then start the server and open
`/app`. The example place is invented demo data, labelled as such in every file and on screen.

1. Introduce a business tenant with bills and a limited budget.
2. Show Benji reading back values and asking necessary questions.
3. Confirm bills, inspect the calculation and explain missing inputs.
4. Assign a task; show its saved state and a later agent read if connected.
5. Show one honest limitation, such as insufficient BERDO peers. Close with the impact measurement plan.

Use actual connected-client footage to claim an integration. Label fixtures and scripted steps. Do not claim autonomous delivery, device control, program approval or achieved emissions reduction.
