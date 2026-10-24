# Sources and assumptions register

## Public data
| ID | What | Value | Label | Source / note |
|---|---|---|---|---|
| berdo_2026 | Peer data | 5,591 rows. Office: 410 rows, 373 usable. Multifamily Housing: 1,475 rows, 1,296 usable | public_historical | City of Boston BERDO Data Disclosure 2026 (reporting year 2025), `data/raw/2026-berdo-data-disclosure-9.30.26.xlsx`, SHA-256 `c9ca76cb01f0814571ac9d7c760649aa62d5e23a51cfd3a08fad489e5576a185` |
| berdo_eui | Site EUI used by Benji | Total Site Energy (kBtu) / Gross Floor Area | public_historical (calculated, labelled) | The published "Site EUI" column is about 19.0x smaller than the row totals imply (median ratio over 2,655 usable rows). The cause is not established. Benji does not rescale the column; it recomputes EUI from row totals. Rows are excluded if EUI is missing, outside 1-1000, or floor area is missing. Peers using district steam are excluded when the building does not use steam. |
| ef_elec | Electricity emission factor | 0.1755 kgCO2e/kWh | public_historical | Sum of Electricity Emissions / sum of Electricity Usage in the same file. A historical BERDO accounting estimate, not a marginal-grid factor or a future guarantee. |
| ef_gas | Natural gas emission factor | 5.311 kgCO2e/therm | public_historical | Derived the same way. |

## Conversions and physics
| ID | Value | Note |
|---|---|---|
| kWh to kBtu | 3.412 | Standard site-energy conversion |
| therm to kBtu | 100 | Standard |
| ccf to therms | 1.037 | Fallback only when the bill gives no multiplier |
| Air volumetric heat capacity | 1.2 kg/m3 x 1.005 kJ/(kg K) | Used only for ventilation loss and the explicit air-only lower bound in skill 08 |
| U from R (IP) | U [W/m2K] = 5.678 / R [ft2 F h/Btu] | Standard conversion |

## Assumptions (editable, always labelled)
| ID | Value | Basis | Status |
|---|---|---|---|
| thermostat_setback_fraction | 5% of heating gas (allowed range 0-10%) | DOE Energy Saver says "up to" about 10% for a 7-10 F set-back over 8 h. Residential guidance. | Source page not re-fetched: **unverified** |
| anomaly threshold | 25% year over year | Design choice | n/a |
| minimum peer sample | 30 | Design choice | n/a |
| heating split | Summer (Jun-Aug) daily gas use = baseload | Needs 330+ days including summer and winter bills | modelled_estimate |

No default heat-loss coefficient, thermal capacity, COP, equipment output, tariff, quote or incentive amount exists
anywhere in the code. Missing values are reported as missing.

## Incentives
There are 10 Mass Save records in `benji/catalog/incentives.json`. All are **unverified** leads that link only to
masssave.com and have no pre-filled amounts. The confirmed financial view counts an incentive only when the user
records an approval (status approved or disbursed) together with reported_by, reported_on and a reference.
Benji does not verify approvals.

## Synthetic demo values
Everything in `benji/demo.py` is synthetic: tariffs, bills, quotes, COP, heat-loss coefficient, thermal capacity and
approval references. These are test values, not Massachusetts market data.
