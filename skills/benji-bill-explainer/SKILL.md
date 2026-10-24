---
name: benji-bill-explainer
description: Explain energy bills and spending - what a bill's charges mean, why one bill differs from another (more usage vs higher rate vs more days vs fixed charges), yearly cost per fuel, the fixed share that won't drop, the usage-based rates used to price any saving, the heating share of gas, and a simple 12-month budget. Use for "why is my bill so high", "what am I spending", or "what will this winter cost".
---

# Bill explainer and costs

Uses confirmed bills only (`benji-bills-import`) and `../_shared/formulas.md` (Bills, Heating vs baseload).

## Steps
1. **One bill:** fixed charge · supply vs delivery (MA: basic service, competitive supplier or municipal
   aggregation - read it, don't assume) · usage-based charges · demand charges (businesses: $/kW of the peak, not
   the total) · taxes · credits.
2. **Two bills, same meter:** compare **per day** first, then split the $ change exactly into usage effect, rate
   effect, fixed change; mention extra billing days and estimated reads (a catch-up bill often follows an "E").
   No charge detail → say rate and usage can't be separated and ask for the charge page.
3. **Yearly costs** (≥ 360 days on every meter): usage and cost per fuel, fixed share, **usage-based rate**
   (= usage-based charges ÷ usage; the only rate used for savings), gas heating share (needs summer + winter
   bills). 180-359 days → scaled figure labelled assumption; < 180 → recorded totals only. Missing amounts stay
   unknown (show the known subtotal), never $0.
4. **Budget** (on request): each month = last year's daily use × days × current rate; range from year-to-year
   variation; a rate change only if the user or an official utility/DPU notice gives one. Not weather-adjusted.
5. Possible causes are **questions**, not conclusions: season, more days, estimated read, supplier change, new
   equipment, longer hours, space heaters. If affordability is a worry, point to the utility's discount rates and
   payment plans (eligibility decided by the utility).

## Output
Three lines first: "Your bill rose $X: about $A from more use, $B from a higher rate, $C from 4 extra days." Details
only when asked.

## Memory
Finding with bill ids and numbers; usage-based rates in `profile.md`; `log.md` line.
