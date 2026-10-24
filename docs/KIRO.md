# How we used Kiro

Built in the **Kiro IDE** (agent in autopilot) on 2026-10-24, in increments. Everything is in `.kiro/`.

- **Spec-driven development.** `.kiro/specs/benji-agent-skills` is the current spec: the 12 skills + orchestrator,
  the file memory and its API/MCP. Earlier specs (`benji-skills-engine`, `benji-channels-dashboard`) are kept as
  history: they produced the calculator and its safeguards, which now serve as the skills' cross-check. Requirements
  are SHALL statements mapped to tests (e.g. "applied is not approved" → `test_applied_rebate_is_not_confirmed`;
  "every skill reachable from the orchestrator" → `test_orchestrator_routes_only_to_existing_skills`).
- **Steering.** `product.md` (evidence rules, positioning), `tech.md` (architecture), `structure.md` (repo map).
  The rule with the biggest effect: "never invent tariffs, efficiencies or program amounts; unknown stays unknown".
- **Agent hook.** `.kiro/hooks/benji-tests-on-save.json` runs the test suite when an engine or catalog file is saved.
- **Property-based testing.** Hypothesis checks money invariants (net cost and cash-now bounds, loans never lower
  net cost, later rebates never lower cash now, no payback without savings); it caught a rounding edge case.
- **Audit → regression loop.** An external audit reproduced 8 calculator defects (e.g. benchmark with a missing
  fuel, applied = approved, stale plan revived); each became a regression test before the fix.
- **Agent dry-runs of the skills.** Kiro sub-agents acted as Benji using only the Markdown skills on two scenarios
  (a leased coffee shop; a renter with an estimated meter read and a prompt-injection line in a bill photo). The run
  showed correct arithmetic and guardrails but answers that were far too long and too many skills per turn, so we
  merged 20 skills into 12, added hard length/turn limits and fixed packaging for Claude.ai.
- **MCP.** Benji ships its own MCP server (`benji/mcp_server.py`) for memory and cross-checks. No third-party MCP
  servers were used inside Kiro. **Kiro powers:** none.
