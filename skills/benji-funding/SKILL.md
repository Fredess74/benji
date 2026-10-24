---
name: benji-funding
description: Work out whether and how a person can pay for an improvement - cash needed now vs net cost vs total budget, instant discounts, rebates paid after installation (and how long they take), 0% or other loans, landlord cost-sharing, tax benefits - comparing loan payments with estimated monthly savings and showing the funding gap and phasing options. Use when a step looks worthwhile and the user asks "can I afford it?".
---

# Funding

| Source | Lowers cash now? | Lowers net cost? | Note |
|---|---|---|---|
| Instant discount / at-purchase incentive | yes | yes | applied at sale |
| Rebate after installation | **no** | yes | you front the money; Mass Save says processing can take up to 8 weeks |
| 0% / low-interest loan | yes | no - it's repaid | use the lender's term and payment only |
| Tax credit / deduction | no | yes, at tax time | depends on their taxes → tax professional |
| Landlord cost-share | yes | yes (for the tenant) | needs agreement in writing |

## Steps
1. Two columns: **confirmed** (approved with reference) and **if leads pan out** (labelled).
2. Compute cash needed now, net cost, **funding gap** = max(0, cash now − cash available now), and the bridge time
   until a rebate arrives.
3. Loan: monthly payment from the lender's terms (0%: principal ÷ months) vs estimated monthly saving - say plainly
   if the payment is larger.
4. Gap → options: phase it (free steps first) · no-cost assessment path · ask about instant discounts or 0% loans ·
   ask the landlord to share · wait for equipment end-of-life.

## Output
"Do now / do after X / not now" per option, with cash now, gap and monthly payment vs saving.

## Memory
Funding decision with sources in `findings.md`, update `plan.md`, `log.md`.
