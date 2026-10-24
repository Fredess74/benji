# Formulas and conversions (show your work)

Show inputs (with labels) and arithmetic in memory; in chat give only the result unless asked. If the Benji
`cross_check` tool is connected, use it for multi-step money results; if it disagrees with you, find the differing
input before answering.

## Units
| From | To | Factor |
|---|---|---|
| kWh | kBtu | × 3.412 |
| therm | kBtu | × 100 |
| ccf (gas) | therm | × the bill's therm factor (often about 1.03-1.04; use the bill's value; if it is missing say it is assumed) |
| MMBtu | kBtu | × 1,000 |
| tons of cooling | kW (thermal) | × 3.517 |
| Btu/h | kW | ÷ 3,412 |
| MBH (1,000 Btu/h) | kW | × 0.2931 |
| °F difference | K difference | × 5/9 |
| sq ft | m² | × 0.0929 |

Fuel oil, propane and steam: use the energy content printed on the delivery ticket or bill. Do not guess it.

## Bills
- Days in period = end date − start date.
- Average daily use = quantity ÷ days. **Always compare periods per day**, never raw monthly totals.
- Usage-based rate = (energy + usage-based delivery charges) ÷ quantity. It excludes the customer/fixed charge,
  demand charges, taxes and credits.
- All-in average rate = total ÷ quantity. Use it only for describing a bill, never for pricing savings.
- Bill-to-bill change for the same meter, when both bills have a reconciled breakdown:
  - consumption effect = (q₂ − q₁) × rate₁
  - price effect = (rate₂ − rate₁) × q₂
  - fixed change = fixed₂ − fixed₁
  - demand change = demand₂ − demand₁
  - tax/other change = other₂ − other₁
  - credit change = credits₂ − credits₁ (credits are signed, normally negative)
  - unexplained remainder = total₂ − total₁ − sum of all effects above
  Report any nonzero remainder; never assign it to consumption automatically. Consumption effect includes
  different billing-period lengths. Compare daily quantities to discuss intensity, but do not add a separate
  days effect to this decomposition. Missing components stay unknown; only a reconciled split is exact.
- Annual totals need about 12 months (≥ 360 covered days on every meter). With 180-359 days you may scale ×(365 ÷
  days) only as a labelled assumption. Below 180 days give recorded totals only.

## Heating vs. baseload (gas)
Requires about a year of bills including summer (Jun-Aug) and winter (Dec-Feb):
- baseload per day = average daily gas in summer bills
- heating gas = total − Σ min(bill, baseload/day × days)
Label: estimate, not weather-normalised.

## Intensity (for benchmarking)
Site EUI (kBtu/sq ft/yr) = (annual kWh × 3.412 + annual therms × 100 + other fuels in kBtu) ÷ floor area.
Every fuel the building uses must be in it.

## Money
- variable cost = quantity × usage-based rate
- annual operating saving = −(Δ kWh × electricity usage rate + Δ therms × gas usage rate). It can be negative.
- net cost = gross cost − rebates − instant discounts − tax benefits (confirmed ones only for the "confirmed" view)
- cash needed now = gross cost − instant discounts/at-purchase incentives − loan principal
- funding gap = max(0, cash needed now − cash available now)
- simple payback (years) = net cost ÷ annual saving, **only if the annual saving > 0**. Call it simplified: it
  ignores financing, maintenance, inflation and equipment life.

Fixtures for checking yourself (synthetic): 10,000 kWh × $0.20 = $2,000. $10,000 net ÷ $2,000/yr = 5.0 years.
$20,000 project with a $10,000 rebate paid after completion = $20,000 cash needed now.

## Measures (methods, not promises)
- **Lighting:** kWh saved = fixtures × (old W − new W) × hours/yr ÷ 1000. All four numbers come from the user,
  the quote or a fixture count. If the result exceeds annual electricity use, an input is wrong.
- **Thermostat set-back:** heating gas × fraction. The only sourced value Benji uses: DOE Energy Saver says "up to
  about 10%/yr" for a 7-10 °F set-back for 8 h/day (https://www.energy.gov/energysaver/programmable-thermostats,
  not re-verified, residential guidance). Use 0-10% as a range, about 5% as a planning midpoint, and label it an
  assumption.
- **Heat pump replacing gas heat:** delivered heat (kBtu) = heating therms × 100 × existing efficiency (as a
  fraction, e.g. 0.80). New kWh = delivered ÷ (seasonal COP × 3.412). Seasonal COP comes from the contractor or
  spec sheet. Never put HSPF or SEER in place of COP.
- **Emissions:** Δ kgCO2e = Δ kWh × electricity factor + Δ therms × gas factor (`data/emission-factors.md`).
- **Combining measures:** apply them in sequence on what remains (a set-back first, then the heat pump on the
  smaller heating load). Never add stand-alone savings together.

## Room warm-up / cool-down (single zone)
C · dT/dt = Q − H · (T − T_out) + gains
- C = effective thermal capacity [kWh/K]. It includes furniture and structure, not just air.
- H = heat-loss coefficient [kW/K] = Σ U·A + ventilation (0.335 W/(m³·K) × air changes per hour × volume m³).
- Q = the system's **thermal** output at these conditions [kW]. Heating is +, cooling is −.
- Equilibrium T_eq = T_out + (Q + gains) ÷ H.
- Time to target t = (C ÷ H) × ln((T_eq − T₀) ÷ (T_eq − T_target)). This works only if the target lies between T₀
  and T_eq; otherwise the target is **not reachable**.
- Heat delivered = Q × t. Purchased energy = heat ÷ COP (electric) or ÷ efficiency (fuel; then kWh × 3.412 ÷ 100 =
  therms).
- Check value (synthetic): C = 2, H = 0.2, T_out = 0, T₀ = 10, target 20, Q = 6 → t = 6.93 h, heat delivered
  41.6 kWh, 13.9 kWh at COP 3.
Cooling here is sensible only (no humidity).
