# Requirements: Benji skills engine (MVP)

Scope: the reusable skill layer and API behind the Benji Dashboard. The dashboard UI is a separate, later spec.

## R1 Skill registry
1.1 The system SHALL register 20 skills, each with ID, name, category (5 groups), purpose, inputs, outputs,
    data prerequisites, evidence/assumptions, failure behaviour and implementation status.
1.2 Skills 01, 02, 03, 04, 06, 07, 09, 10, 13, 14, 17, 20 SHALL be implemented; 05, 08, 11, 12, 15, 16, 18, 19 SHALL be
    reported as `coming_later` and SHALL NOT run or return results.
1.3 WHEN a skill is not selected THEN it SHALL NOT run, and skills that depend on it SHALL return
    `blocked_by_prerequisite` with the missing skill named.

## R2 Data and profiles
2.1 Imported bills (CSV, text PDF) SHALL be stored as `pending_confirmation` with the original file hash, and SHALL be
    excluded from analysis until confirmed.
2.2 WHEN a PDF has no extractable text THEN the system SHALL explain that OCR is unavailable and offer manual entry.
2.3 Data-quality checks SHALL detect gaps, overlaps, duplicates, unit mismatches, implausible values, missing totals,
    line-item mismatches and incomplete years, each with a specific correction action.
2.4 WHEN a bill is corrected THEN the correction SHALL be recorded and dependent results SHALL be marked stale;
    stale results SHALL NOT be exported.

## R3 Analysis and benchmarking
3.1 Costs SHALL separate fixed, usage-based, demand and other charges; savings SHALL be priced only at usage-based rates.
3.2 Incomplete data SHALL only be annualised (>=180 days) with a labelled assumption.
3.3 Unusual consumption SHALL compare daily-normalised use with the same period a year earlier and SHALL state it is
    not weather-normalised.
3.4 Benchmarking SHALL use BERDO peers of the same property type and compatible size, show reporting year, sample size,
    selection and limitations, and return "Insufficient comparable data" when peers < minimum, fuels are uncovered,
    or bills do not cover the whole building.

## R4 Improvements and incentives
4.1 Each measure SHALL state required inputs, method, assumptions, dependencies, exclusions and uncertainty; missing
    inputs SHALL yield `needs_data` with the exact items.
4.2 Scenarios SHALL apply measures sequentially so overlapping savings are not double-counted.
4.3 Operating cost, consumption and emissions SHALL be reported separately; cost increases SHALL be flagged.
4.4 Financials SHALL distinguish gross cost, net cost and upfront cash; post-installation rebates SHALL NOT reduce
    upfront cash; loans SHALL NOT reduce net cost; stacking groups SHALL prevent summing incompatible incentives;
    zero/negative savings SHALL NOT show payback.
4.5 Incentive matching SHALL respect sector, location and measure; eligibility SHALL return Potentially eligible /
    Known condition not met / More information needed.
4.6 The confirmed financial view SHALL include only incentives the user confirmed with the program; others appear only
    in a labelled hypothetical view.

## R5 Plan and reporting
5.1 The plan SHALL order recommendations by explicit rules and state the reason for each position.
5.2 Each recommendation SHALL include issue, evidence, unknowns, action, costs/benefits, assumptions, incentives,
    who pays / benefits / authorizes, and next step; tasks SHALL have owner, prerequisites, due date and status.
5.3 Plans and task edits SHALL persist across restarts.
5.4 Reports SHALL be exported as dated, immutable snapshots, label synthetic data, and separate estimates from
    measured results.

## R6 Resilience
6.1 WHEN the model service is unavailable THEN explanations SHALL fall back to deterministic text labelled as such and
    the workflow SHALL continue.
6.2 A demo mode SHALL create and reset clearly labelled synthetic commercial and residential cases without touching
    user data.
