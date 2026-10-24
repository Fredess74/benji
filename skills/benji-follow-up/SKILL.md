---
name: benji-follow-up
description: Keep the plan moving and check results - monthly check-ins when a new bill arrives, budget vs actual, task nudges, rebate follow-ups, seasonal reminders, and after a measure is done, a measured before/after comparison of energy and cost kept separate from the original estimate. Use when the user wants reminders or monitoring, when Benji runs on a schedule (e.g. OpenClaw), or for "did it work?".
---

# Follow-up

## Set up
Agree channel (chat, email, calendar, the business agent's task list), frequency (default monthly + task due
dates) and quiet hours; save as `check_in` in `profile.md`. In a plain chat you can't message first - suggest a
calendar reminder a few days after the usual meter-read date.

## Each check-in (alert only when something is actionable)
1. New bill → `benji-bills-import`; compare per day with the same month last year and with the budget.
2. ≤ 3 tasks due or overdue, each with owner and next step.
3. Rebate applied > 8 weeks ago → suggest asking for status.
4. Seasonal: autumn - heating schedule, filters, weatherstripping; spring - AC service, cooling set-points.

## Output
Check-in: what happened (1 line) · what to do (1 line) · task id. Result: "Electricity −11% per day Apr-Jun vs last
year (measured on your bills); estimate was 14-16%; June was warmer."

## Did it work? (≥ 2 billing months after completion)
1. After = bills starting one cycle after completion; before = same months last year, same meter.
2. Δ per day per fuel; price at the **current** usage-based rate, separately from any rate change.
3. List confounders with direction: weather (not adjusted), hours/occupancy, other equipment, estimated reads,
   billing days.
4. Label `measured` with confidence (low 2-3 months · medium a season · higher a year). Keep the original estimate
   next to it; never overwrite. Far below the estimate → was it fully done, reverted, rebound, wrong input?

## Memory
Each check-in in `log.md`; task statuses in `plan.md`; results as findings ("Result: LED - measured"). Real-time
monitoring needs interval data; otherwise alerts are monthly and bill-based. Never act without approval.
