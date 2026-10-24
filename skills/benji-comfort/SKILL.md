---
name: benji-comfort
description: Solve comfort and heat-loss problems - cold or overheated rooms, drafts, slow warm-up after a set-back, whether a heating or cooling system can hold the target temperature, how long warm-up takes and what it costs, and whether air sealing/insulation or a different system would help. Guided diagnosis first; numbers only with real heat-loss, capacity and output inputs. Use for comfort complaints and heat-pump sizing questions.
---

# Comfort and heat loss

## 1. Diagnose (always; ≤ 3 questions at a time)
Which rooms, when (mornings, windy days)? Does heat come out - whole radiator/vent or only part? Thermostat in a
different room? Drafts at windows/doors/outlets? Condensation or musty smell (cooling/humidity)? Heat pump: only
below some outdoor temperature? Backup heat running?
Map to the likely cause with a cheap check:
- **Thermostat location / controls** → test: raise it 2-3° for 30 min and feel the cold room's emitter.
- **Distribution** (air in radiator, closed valve, blocked vent) → owner/landlord fixes; no DIY on boilers.
- **Envelope** (drafts) → curtains at night, removable draft kits (renter-safe), no-cost assessment with blower door.
- **Capacity** → contractor check (load calculation, airflow, charge).
Meanwhile: share heat (open doors), keep emitters clear. Space heaters: straight into the wall, away from bedding.
With gas appliances: working CO alarm. Don't recommend a night set-back if it makes a cold room worse.

## 2. Numbers (only if all inputs have a source)
H heat loss (W/K, from an assessment or U×A + air changes), C effective capacity (kWh/K, from an assessor - or
the explicit **air-only lower bound**, which makes warm-up look faster than reality), Q **thermal** output at that
outdoor temperature plus COP or combustion %, temperatures. Compute with `../_shared/formulas.md` (Room warm-up):
time to target or **not reachable**, heat delivered, energy bought and cost, load to hold target, headroom. Compare
alternatives only with an assessor's new H or a system's own Q/COP - never an assumed %.

## Output
Likely cause + one check this week. With numbers: ≤ 4-row table (option, time to target, cost per warm-up,
headroom). Preheat timing is advice, not control. Cooling here is sensible only.

## Memory
Findings with inputs and sources; questions for landlord/contractor in `open-questions.md`; `log.md`.
