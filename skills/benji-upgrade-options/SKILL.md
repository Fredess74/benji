---
name: benji-upgrade-options
description: Compare improvement options and planned changes for a place - free operating changes, thermostat set-back, lighting, refrigeration and hot-water fixes, air sealing/insulation, heat pumps, heat pump water heaters, solar assessment, and the impact of new equipment or longer hours - with energy, operating-cost and emissions effects, cash needed now, net cost and simple payback, without double counting and with an electrical-readiness check. Use for "what should I improve", quotes, or "what will this new equipment do to my bills".
---

# Upgrade options

Uses: profile, confirmed costs (usage-based rates, heating share), `../_shared/measures.md`,
`../_shared/formulas.md`, `../_shared/data/emission-factors.md`, quotes the user shares.

## Steps
1. **Shortlist 3-5** that fit the place, the role and the findings. Free steps first. Drop what's done or doesn't
   apply.
2. **Status per option:** `estimated` (all inputs known - compute) · `needs data` (list exactly what: fixture count,
   quote, seasonal COP…) · `assessment only` (air sealing, insulation, solar) · `check input` (physically
   implausible value - ask, never correct it yourself).
3. **Effects, kept separate:** Δ kWh / Δ therms · Δ operating cost at usage-based rates (fixed charges unchanged) ·
   Δ kgCO2e (factor named) · comfort/disruption in words. Electrification may **raise** cost while cutting emissions -
   say "+$X/yr".
4. **Money:** gross cost from a quote (else "get 2 quotes") → cash needed now, net cost with confirmed incentives,
   net "if leads pan out" (labelled), funding gap vs cash available now, simple payback only if saving > 0.
5. **Combined:** apply in order operations → set-back → envelope → heat pump on the remaining load; the total is
   less than the sum.
6. **New equipment / longer hours:** rated kW (spec sheet) × hours × duty factor (from vendor or plug meter, else a
   labelled range); gas Btu/h ÷ 100,000 = therms/h at full fire. Flag possible demand-charge increases (ask for the
   tariff). Offer the efficient alternative (ENERGY STAR, induction, heat pump water heater) - some programs need
   pre-approval **before** buying.
7. **Any new electric load:** run the electrical check in `measures.md`.

## Output
≤ 5-row table: option · status · Δ cost/yr · cash now · payback · who approves; then 1-2 sentences of trade-offs.

## Memory
Options as findings; assumptions (value, range, source) in `findings.md`; quotes in `documents/`; hand to
`benji-action-plan`; `log.md`. Generic "% savings" only with a labelled source and range.
