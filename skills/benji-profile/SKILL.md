---
name: benji-profile
description: Build or update the profile of a home, small business or building - place type, the user's role, who pays and who approves, ZIP and utilities, heating and key equipment, opening hours, cash available now. Use for every new place, when the user mentions a fact about the place, or when another skill reports a missing fact.
---

# Profile

## Steps
1. Ask the two facts everything depends on: **what the place is** (home 1-4 units, small business, office,
   apartment building 5+) and **the user's role** (own & live, rent, landlord, business leases / owns space,
   manager).
2. State the defaults the role implies and confirm them: "You lease, so your landlord approves equipment work and
   you pay the bills - right?"
3. Then, ≤ 3 at a time, in this order: ZIP + electric and gas company (municipal utility?) · heating fuel and
   system (+ opening hours for businesses) · **cash available now** and openness to a 0% loan · floor area and
   whether bills cover the whole place (only needed for benchmarking) · main equipment (thermostat: who controls,
   programmable? lighting; kitchen/refrigeration) · goals and constraints (lease, no work during hours).
4. Photos of nameplates or the panel label become facts after the user confirms them. Efficiencies keep their
   unit (AFUE %, COP, HSPF2, SEER2, UEF) - never convert one into another.
5. Flag contradictions (a "home" with 6 units → apartment building; heat pump + gas bills → what uses the gas?).

## Output
"Here's what I know" (≤ 5 lines) + the most useful missing fact.

## Memory
`profile.md` (each value with source + date), unknowns in `open-questions.md`, one `log.md` line.
Never guess floor area, efficiency or age - "unknown" is a valid value.
