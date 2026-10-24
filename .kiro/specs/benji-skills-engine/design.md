# Design: Benji skills engine

## Layers
```
Dashboard (later) ──┐
Integrations (later)├──> benji/api.py ──> benji/engine.py ──> skills registry ──> sNN_*.py
Tests ──────────────┘                         │                    │
                                              └── store.py (SQLite)└── billing / finance / units / berdo / catalog
```
Skills are pure functions over a `SkillContext` (building, bills, measure inputs, upstream results, settings).
The engine owns persistence and staleness; skills never write.

## Execution order and dependencies
`04 -> 01 -> 03 -> 02 -> 09 -> 06 -> 07 -> 13 -> 14 -> 10 -> 17 -> 20`
Hard dependencies: 02/03/06/09 need 01; 07 needs 04 + 09; 10 needs 09 (uses 14 if selected); 14 needs 13;
17 needs 04 (uses 03, 06, 07, 10, 14); 20 uses whatever completed.

## Staleness
The engine stores fingerprints of building, bills, measure inputs and settings with every analysis. On read, changed
fingerprints map to affected skills (`INVALIDATION`). Stale analyses cannot be exported; plans show `stale: true`.

## Key calculations
- Usage-based rate = usage-based line items / quantity (or user tariff input). Fixed and demand charges never fall.
- Heating split = gas minus baseload (mean daily use of the 3 lowest bills x days). Modelled estimate.
- LED kWh = fixtures x (W_old - W_new) x hours / 1000, capped by annual kWh check.
- Set-back = heating therms x fraction (assumption, 0-10%, default 5% citing DOE "up to 10%").
- Heat pump: delivered = therms x 100 x AFUE x coverage; kWh = delivered / (COP x 3.412). COP must come from a
  contractor/spec (no default).
- Emissions use factors derived from the BERDO 2026 disclosure (total emissions / total usage).
- Site EUI computed as total site kBtu / GFA. The disclosure's published EUI column is ~19x smaller than its own
  totals imply, so it is not used.

## Financial model
`finance.project_financials`: instant discounts reduce upfront and net; after-installation rebates and tax benefits
reduce net only; loans reduce upfront only; stacking groups keep the largest amount. Simple payback only when savings > 0.

## Ranking
Tier 0 data fixes, 1 low-cost investigation, 2 cost-reducing estimated measures (within budget first, then payback),
3 envelope assessment, 4 trade-off measures (cost increase / high disruption), 5 solar assessment. Reasons are text.

## Decisions
- API-first; dashboard deferred (user direction, 2026-10-24).
- Incentive amounts are never pre-filled; users enter amounts confirmed by the program or contractor.
- Catalog records are `unverified` until checked against the official page on a recorded date.
