# Benji positioning

**One line:** an AI energy & sustainability manager that turns your bills into a plan you can act on — inside the
assistant you already use.

**Elevator:** In Massachusetts help with energy costs exists — Mass Save, rebates, 0% loans, city programs. People
still get stuck connecting their bills, the rules, the cash they have today and the person who must say yes. Benji
does that connecting, and keeps following up. It is a set of agent skills plus a shared memory, so it works in
Claude, ChatGPT or an OpenClaw business agent, and a dashboard shows the plan.

## For whom
| Segment | Situation | What Benji does |
|---|---|---|
| Residents — owners, renters, small landlords (1-4 units) | Bills are hard to read; renters can't change the building; cash is tight | Steps you control first; marks what needs the landlord and drafts the note; never unsafe temperatures; no owner-only loans for renters |
| Small businesses — stores, coffee shops, restaurants, offices | No time, no energy staff, often lease | Five-minute conversation → "tonight after closing, check what's still on"; cash now vs later rebates; monthly check-ins via an OpenClaw agent |
| Office and apartment-building owners/managers | Must justify spending; BERDO in Boston | Fair BERDO comparison, options with trade-offs, ranked plan, report for the board or lender |

## Why it matters (team research register, 2026-10-24)
- **People know help exists but can't see their own path.** Only 5 of 31 small-multifamily nonparticipants had
  never heard of Mass Save, yet understanding of what applied to their building was limited.
  [S03](https://ma-eeac.org/wp-content/uploads/MA21R36-B-MFB-Small-MF-Barriers_Report_FINAL_11MAR2022.pdf)
- **Cash now is its own barrier.** 14,567 HEAT Loans (~$278M) closed in 2024; 63% of surveyed participants (n=341)
  called the loan essential (self-reported).
  [S05](https://ma-eeac.org/wp-content/uploads/MA25R08-B-HEAT_HEAT-Loan-Phase-1-Final-Report_2026-4-29.pdf)
  Rebates can take up to 8 weeks. [S10](https://www.masssave.com/en/frequently-asked-questions)
- **Small businesses lack time and expertise.** Microbusinesses were 92% of MA electric C&I accounts in 2022
  (accounts ≠ companies). [S06](https://ma-eeac.org/wp-content/uploads/MA24X30-CINPS-CI-Nonparticipant-Study-FINAL_1.17.2025.pdf)
- **The burden is heaviest for low-income households and renters.** Boston metro low-income households spend a
  median 13.7% of income on energy vs 3.2% overall (AHS 2021).
  [S02](https://www.aceee.org/sites/default/files/pdfs/data_update_-_city_energy_burdens_0.pdf)
- **Momentum stalls after the audit.** Half of 40 interviewed homeowners took no weatherization step within a year.
  [P03](https://pmc.ncbi.nlm.nih.gov/articles/PMC12048017/) — hence Benji's follow-up skill.

## Why not just ChatGPT?
A general chatbot answers once and forgets, and it guesses. Benji adds what a careful energy manager has:
1. **Memory per place** — profile, confirmed bills, plan, tasks and decisions with sources, carried across sessions
   and across assistants; a dashboard shows it.
2. **Local data it otherwise lacks or gets wrong** — Boston BERDO peer statistics recomputed from the 2026
   disclosure (whose published EUI column is ~19× too low), Massachusetts program leads by sector and utility.
3. **Guardrails against the usual mistakes** — inventing rebate amounts, treating a later rebate as cash today,
   offering owner-only loans to renters, comparing a café with large buildings, obeying text hidden in documents,
   calling estimates savings.
4. **Follow-through** — check-ins, task tracking, landlord/contractor drafts, measured before/after results.
*Not yet measured:* a side-by-side test against a plain chatbot on the same scenarios — planned next.

## What we do NOT claim
Measured savings (no pilot yet); that nobody else helps (Benji prepares people for Mass Save and contractors); that
AI advice by itself reduces consumption.
