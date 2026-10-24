---
name: benji-usage-patterns
description: Find unusual or wasted energy in a place's own data - jumps versus the same period last year (per day, same meter), always-on baseload, and what runs at night or after closing using interval (15-min/hourly, Green Button) data or, with monthly bills only, a guided after-closing walk-through. Use for "is this normal for us?", unexplained increases, or small businesses checking what stays on.
---

# Usage patterns

## A. Year over year (needs 13+ months on the same meter)
1. Per bill: daily use vs the bill ±16 days around the same date last year. Flag ≥ ±25% (default; user may change).
2. Explain away first: estimated read / catch-up bill · recorded operating change (hours, tenant, equipment,
   people) · weather (say: "not weather-adjusted").
3. Remaining flags → specific questions for the place type: space heaters, new appliance, running hot water
   (homes); oven/fryer hours, walk-in door or gasket, refrigeration alarm (food); thermostat/BMS schedules,
   after-hours tenants, boiler running in summer (buildings).

## B. Night / after-hours
- **Interval data:** confirm the schedule, then average kW occupied vs unoccupied, minimum overnight kW, weekends.
  Unoccupied kWh/yr ≈ unoccupied kW × unoccupied hours; price at the usage-based rate; label estimate.
- **Monthly bills only:** say they can't show night use, then run a 10-minute walk-through at closing / bedtime:
  lights & signs, display-case lights, thermostat setting, ovens/fryers/hot-holding, espresso machines on standby,
  dishwasher booster, PCs/POS, space heaters, fans, refrigeration doors and covers. Record what's on, what could go
  off, who closes. Suggest a plug meter or the utility's smart-meter app for suspects.

## Output
0-5 flags ("+32% per day vs last March, from your bills") as questions, plus 1-3 free actions.

## Memory
Findings with bill ids; explanations as dated notes in `profile.md`; free actions for `benji-action-plan`; `log.md`.
Never call something waste before it is explained; never switch off refrigeration, required ventilation or safety
lighting.
