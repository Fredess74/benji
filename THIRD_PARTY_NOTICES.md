# Third-party notices

## Runtime dependencies (installed from PyPI, pinned in requirements.txt)
| Package | Version | License | Use |
|---|---|---|---|
| FastAPI | 0.137.2 | MIT | HTTP API |
| Uvicorn | 0.49.0 | BSD-3-Clause | ASGI server |
| Pydantic | 2.13.4 | MIT | Validation |
| python-multipart | 0.0.32 | Apache-2.0 | File uploads |
| httpx | 0.28.1 | BSD-3-Clause | Optional AI call |
| fastmcp | 3.1.0 | Apache-2.0 | MCP server (Claude plugin / Desktop) |
| pdfplumber | 0.11.9 | MIT | Text-PDF bills and drawing text candidates (words with bounding boxes) |
| pandas | 2.3.3 | BSD-3-Clause | One-time BERDO cache build |
| openpyxl | 3.1.5 | MIT | Reading the BERDO workbook |
| pytest, hypothesis, reportlab | 9.1.1, 6.155.7, 5.0.1 | MIT, MPL-2.0, BSD | Tests only |

No third-party source code is copied into this repository.

## Reference projects (consulted for method, not vendored)
| Project | License (as described by the project) | How Benji used it |
|---|---|---|
| dm4bem (github.com/cghiaus/dm4bem) | MIT | Reference for the lumped thermal-circuit method. Benji implements its own single-zone RC solver and validates it against an analytical case. |
| PsychroLib | MIT | Not used yet. Planned for latent/humidity cooling. Until then, cooling is labelled sensible-only. |
| PDF.js | Apache-2.0 | Not used yet. The dashboard links to the stored file instead. Planned for in-browser plan annotation. |
| OpenDSM (formerly OpenEEmeter) | Apache-2.0 | Not used. Roadmap for weather-adjusted baselines (skill 19). |
| OpenStudio-HPXML | BSD-3-like (check LICENSE.md before reuse) | Not used. Design reference for residential load and panel inputs. |
| pvlib-python | BSD-3-Clause | Not used. Roadmap for PV production scenarios. |

## Data
- City of Boston BERDO Data Disclosure 2026 (2025 data), local file `data/raw/2026-berdo-data-disclosure-9.30.26.xlsx`.
  Check the City's terms before republishing. Benji keeps only anonymous numeric and category columns in its cache.
