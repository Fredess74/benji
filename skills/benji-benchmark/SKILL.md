---
name: benji-benchmark
description: Compare a building's energy use per square foot with Boston BERDO peers of the same type and size (reporting year 2025) only when the comparison is fair, explaining the peer group, sample size and limits - otherwise say "insufficient comparable data". Use for "do we use a lot compared with others?", BERDO questions, or prioritising an office or apartment building.
---

# Benchmark

Data: `../_shared/data/berdo-peers.md` (generated from the 2026 BERDO disclosure; EUI recomputed from totals).

## Fair only if ALL hold
1. Type in the table (office, apartment 5+, retail, grocery, food service, medical office). **Homes 1-4 units:
   stop** - BERDO is large Boston buildings; compare with their own history instead (`benji-usage-patterns`).
2. 12 confirmed months for **every** fuel used, same period; bills cover the **whole** building (ask if unknown).
3. Floor area known.
4. Peer row **n ≥ 30** (size band; else "all sizes" - say so). Still < 30 → **Insufficient comparable data**.

## Steps
1. Site EUI = (kWh × 3.412 + therms × 100 + other fuels in kBtu) ÷ sq ft.
2. Below Q1 = lower than most · Q1-Q3 = typical · above Q3 = higher than most. Give n, band, year.
3. Which fuel's intensity is furthest from the peer median → where to look first.
4. One-line "why this comparison" and limits: large Boston buildings only, not weather- or occupancy-adjusted,
   kitchens/server rooms/laundry distort it, annual totals can't name equipment. BERDO duties vary by building -
   point to https://www.boston.gov/departments/environment/berdo, don't judge compliance.

## Output
"74 kBtu/sq ft/yr - higher than most of 111 similar Boston offices (median 54, BERDO 2025). That's where to look,
not what you'd save."

## Memory
Finding with inputs, peer row and labels; `log.md`. Never turn the gap into savings or name a peer building.
