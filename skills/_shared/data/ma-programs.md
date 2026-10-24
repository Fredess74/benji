# Massachusetts program leads (generated from benji/catalog/incentives.json)

Catalog version 2026-10-24.2. Curated starter catalog. Program amounts change and depend on utility and equipment; no amount is pre-filled. Every record is 'unverified' until a team member confirms it against the official page on a stated date. Final eligibility and amounts are decided by the program operator.

Every record is a **lead**. Before relying on one, open the official page, then record the URL, the date checked and what it says in memory (`decisions.md`). Use the sector column strictly: residential programs never go to businesses, and the other way round.

Mass Save sponsors (electric): Eversource, National Grid, Unitil, Cape Light Compact. Gas: Eversource, National Grid, Unitil, Berkshire Gas, Liberty. Municipal-utility customers have separate programs.

## Mass Save business energy assessment  (`ms_business_assessment`)

- Sector: commercial_office, small_business. Type: no_cost_service. Paid: before installation. Pre-approval: None.
- Measures: energy_assessment, weatherization, solar_assessment.
- Known conditions: Building is in Massachusetts; Electric service from a Mass Save sponsor (municipal utilities run separate programs).
- Amount: Assessment offered to eligible business customers of sponsoring utilities; confirm current terms.
- Cannot be combined with other records in group: none.
- Source: https://www.masssave.com/ (unverified).
- Notes: Confirm availability and scheduling with Mass Save or the utility.

## Mass Save business lighting incentives  (`ms_business_lighting`)

- Sector: commercial_office, small_business. Type: instant_discount. Paid: at purchase. Pre-approval: None.
- Measures: led_lighting.
- Known conditions: Building is in Massachusetts; Electric service from a Mass Save sponsor; Products must be on the program's qualified list.
- Amount: Amount varies by product and utility; enter the amount confirmed by the distributor or program.
- Cannot be combined with other records in group: commercial_lighting.
- Source: https://www.masssave.com/ (unverified).
- Notes: Discount may be applied at the distributor; if instead paid as a rebate after installation, it does not reduce upfront cash.

## Mass Save business HVAC controls / thermostat incentives  (`ms_business_controls`)

- Sector: commercial_office, small_business. Type: rebate. Paid: after installation. Pre-approval: None.
- Measures: thermostat_controls.
- Known conditions: Building is in Massachusetts; Customer of a Mass Save sponsor.
- Amount: Amount varies; confirm with the program.
- Cannot be combined with other records in group: commercial_controls.
- Source: https://www.masssave.com/ (unverified).
- Notes: Rebate is paid after installation: it lowers net cost, not the cash needed upfront.

## Mass Save business heat pump incentives  (`ms_business_heat_pump`)

- Sector: commercial_office, small_business. Type: rebate. Paid: after installation. Pre-approval: None.
- Measures: heat_pump_heating.
- Known conditions: Building is in Massachusetts; Electric service from a Mass Save sponsor; Equipment must meet program efficiency requirements.
- Amount: Amount depends on equipment type, capacity and utility; confirm with the program.
- Cannot be combined with other records in group: commercial_heat_pump.
- Source: https://www.masssave.com/ (unverified).
- Notes: Paid after installation.

## Mass Save business custom incentives  (`ms_business_custom`)

- Sector: commercial_office, small_business. Type: rebate. Paid: after installation. Pre-approval: True.
- Measures: heat_pump_heating, thermostat_controls, weatherization.
- Known conditions: Building is in Massachusetts; Customer of a Mass Save sponsor.
- Amount: Project-specific amount determined by the program after technical review.
- Cannot be combined with other records in group: commercial_heat_pump.
- Source: https://www.masssave.com/ (unverified).
- Notes: Custom projects are reviewed before equipment is purchased; do not order equipment before written approval. Cannot be counted together with a prescriptive rebate for the same equipment.

## Mass Save multifamily energy assessment  (`ms_multifamily_assessment`)

- Sector: multifamily. Type: no_cost_service. Paid: before installation. Pre-approval: None.
- Measures: energy_assessment, weatherization, solar_assessment.
- Known conditions: Building is in Massachusetts; Multifamily program: 5 or more units; Electric service from a Mass Save sponsor.
- Amount: Assessment for multifamily properties of five or more units; confirm current terms.
- Cannot be combined with other records in group: none.
- Source: https://www.masssave.com/ (unverified).
- Notes: Buildings of 1-4 units use the residential Home Energy Assessment instead.

## Mass Save multifamily insulation and air sealing incentives  (`ms_multifamily_weatherization`)

- Sector: multifamily. Type: rebate. Paid: at purchase. Pre-approval: True.
- Measures: weatherization.
- Known conditions: Building is in Massachusetts; Multifamily program: 5 or more units; Work performed through the program's participating contractors.
- Amount: Amount set by the program after assessment; confirm with the program.
- Cannot be combined with other records in group: mf_weatherization.
- Source: https://www.masssave.com/ (unverified).
- Notes: Typically follows the program assessment.

## Mass Save multifamily heat pump incentives  (`ms_multifamily_heat_pump`)

- Sector: multifamily. Type: rebate. Paid: after installation. Pre-approval: None.
- Measures: heat_pump_heating.
- Known conditions: Building is in Massachusetts; Multifamily program: 5 or more units; Electric service from a Mass Save sponsor; Equipment must meet program requirements.
- Amount: Amount depends on equipment and project; confirm with the program.
- Cannot be combined with other records in group: mf_heat_pump.
- Source: https://www.masssave.com/ (unverified).
- Notes: Paid after installation.

## Mass Save multifamily thermostat / controls offers  (`ms_multifamily_thermostats`)

- Sector: multifamily. Type: rebate. Paid: after installation. Pre-approval: None.
- Measures: thermostat_controls, led_lighting.
- Known conditions: Building is in Massachusetts; Multifamily program: 5 or more units; Customer of a Mass Save sponsor.
- Amount: Offers vary; confirm with the program.
- Cannot be combined with other records in group: mf_controls.
- Source: https://www.masssave.com/ (unverified).
- Notes: Some measures may be installed at no cost through the assessment.

## Mass Save HEAT Loan (residential 0% financing)  (`ms_heat_loan`)

- Sector: home, multifamily. Type: loan. Paid: financing. Pre-approval: True.
- Measures: heat_pump_heating, weatherization, thermostat_controls.
- Known conditions: Building is in Massachusetts; Residential 1-4 unit buildings; Customer of a Mass Save sponsor; Borrower owns the property (renters cannot take this loan for the building).
- Amount: Interest-free financing for qualifying residential measures; loan limits and terms must be confirmed.
- Cannot be combined with other records in group: financing.
- Source: https://www.masssave.com/ (unverified).
- Notes: A loan reduces cash needed upfront but must be repaid; it is not a rebate.

## Mass Save Home Energy Assessment (1-4 unit homes)  (`ms_home_energy_assessment`)

- Sector: home. Type: no_cost_service. Paid: before installation. Pre-approval: None.
- Measures: energy_assessment, weatherization, thermostat_controls, solar_assessment.
- Known conditions: Home is in Massachusetts; Residential program: 1-4 units; Electric service from a Mass Save sponsor (municipal utilities run separate programs).
- Amount: Home assessment for customers of sponsoring utilities; confirm current terms and scheduling.
- Cannot be combined with other records in group: none.
- Source: https://www.masssave.com/ (unverified).
- Notes: Renters may need the property owner's permission for some work; confirm with the program.

## Mass Save residential insulation and air sealing incentives  (`ms_home_weatherization`)

- Sector: home. Type: instant_discount. Paid: at purchase. Pre-approval: True.
- Measures: weatherization.
- Known conditions: Home is in Massachusetts; Residential program: 1-4 units; Work done through a participating contractor.
- Amount: Incentive level set by the program, typically after an assessment; confirm.
- Cannot be combined with other records in group: home_weatherization.
- Source: https://www.masssave.com/ (unverified).
- Notes: Usually follows the Home Energy Assessment.

## Mass Save residential heat pump rebates  (`ms_home_heat_pump`)

- Sector: home. Type: rebate. Paid: after installation. Pre-approval: None.
- Measures: heat_pump_heating, heat_pump_water_heater.
- Known conditions: Home is in Massachusetts; Residential program: 1-4 units; Customer of a Mass Save sponsor; Equipment must meet program requirements.
- Amount: Amount depends on equipment and program rules; confirm before buying.
- Cannot be combined with other records in group: home_heat_pump.
- Source: https://www.masssave.com/ (unverified).
- Notes: Paid after installation: it does not reduce the cash needed upfront. Mass Save FAQ (checked by the research team 2026-10-24) says rebate processing can take up to 8 weeks.
