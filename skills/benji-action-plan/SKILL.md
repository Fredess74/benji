---
name: benji-action-plan
description: Turn findings, options and money limits into one ordered, explainable action plan with a single next step, tasks with owner, due date and status, and ready-to-send drafts (landlord request, contractor quote request, assessment booking) - and keep it current as tasks move or data changes. Use after analysis, for "what should I do first?", or to review progress.
---

# Action plan

## Order (state the reason for each position - no hidden score)
1. Fix blocking data problems.
2. Too little data → "collect the missing facts" + book a **no-cost assessment** (a valid first step).
3. Free steps the user controls (schedules, closing routine, set-back, obvious waste).
4. Low-cost steps with estimated savings - within cash available now first, then by payback.
5. Envelope assessment before heat-pump sizing.
6. Steps with trade-offs (cost increase, disruption, funding gap) - show the trade-off.
7. Steps needing someone else (tenants: landlord work, with a ready note).
8. Longer-term (solar, full electrification).

## Each action
Why now · cash now · estimated effect/yr (labelled) · programs + status · who pays / saves / approves · owner · due
date · status · **next concrete step** ("Tonight at closing set the thermostat to 60 °F"; "Call Mass Save to book
the business assessment").

## Drafts (user sends them)
- **Landlord request:** what was found (labelled numbers), the proposed step, who pays and who saves, relevant
  owner programs, ask for a decision or a visit by a date.
- **Contractor quote request:** scope, required specs (e.g. heat pump capacity and COP at 5 °F and 17 °F, a load
  calculation; LED wattage and count), permits, electrical work, warranty, timeline, incentives they expect and when
  paid - so quotes are comparable.

## Steps
Build/refresh `plan.md` from `../_shared/templates/plan.md`, **keeping the user's task status, owner and date
edits**. Add "Not now, and why". Remove the STALE line when refreshed.

## Output
The next step + the top 3 actions in one short table. Offer reminders (`benji-follow-up`) and a shareable summary
(`benji-report`).

## Memory
`plan.md`, drafts in `documents/`, `log.md`.
