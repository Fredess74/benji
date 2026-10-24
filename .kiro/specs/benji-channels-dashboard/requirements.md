# Requirements: Benji channels and dashboard

## R1 Audiences
1.1 The system SHALL support property types home (1-4 units), small_business (store, grocery, food service, small
    office), commercial_office and multifamily (5+). Each SHALL have its own required profile fields.
1.2 WHEN the user is a renter or business tenant THEN the plan SHALL say that building work needs the landlord, rank
    occupant-controlled steps first, and exclude owner-only financing (HEAT Loan).
1.3 Homes SHALL NOT be benchmarked against BERDO. Small businesses SHALL be benchmarked only against BERDO rows of
    their business type, and only with a sufficient sample.

## R2 One pipeline, many channels
2.1 A single assistant facade SHALL provide create property, update property, add bills, confirm bills, analyze,
    summary, plan, skills, room scenario and electrification checklist.
2.2 The dashboard wizard, the HTTP /assistant API (ChatGPT Actions, OpenClaw) and the MCP server (Claude) SHALL call
    that facade. No channel SHALL contain calculation logic.
2.3 Bills entered through any channel SHALL stay pending until the user confirms them.
2.4 The summary SHALL be deterministic. It SHALL label estimates and synthetic data, and list missing information.
2.5 WHEN BENJI_API_KEY is set THEN /assistant endpoints SHALL require a bearer token.

## R3 Dashboard
3.1 A "Start here" wizard SHALL take a new user through: who you are, basics, 12-month bills, confirm, plain-language plan.
3.2 Example numbers SHALL mark the property as synthetic.
3.3 The Overview SHALL show the plain-language summary above the detailed cards.
3.4 The dashboard SHALL pass a real-browser end-to-end test, including on a mobile viewport.
