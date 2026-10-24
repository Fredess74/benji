# Data

- `processed/berdo_2026_peers.csv` (committed): anonymised extract of the City of Boston BERDO Data Disclosure 2026
  (calendar-year 2025 data): property type, floor area, energy and emissions totals, compliance status, ZIP prefix.
  No owner names, addresses, parcel or BERDO IDs.
- `raw/` (not committed): download `2026-berdo-data-disclosure-9.30.26.xlsx` from the City of Boston BERDO page
  (https://www.boston.gov/departments/environment/berdo) and place it here only if you want to rebuild the cache
  (`benji/berdo.py: build_cache`) or regenerate `skills/_shared/data/` (`python scripts/build_skill_references.py`).
  Check the City's terms before redistributing the workbook.
