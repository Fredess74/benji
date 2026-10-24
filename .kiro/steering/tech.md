# Benji technical steering

- Python 3.11, FastAPI, pydantic v2, SQLite (stdlib `sqlite3`), pandas/openpyxl only for the one-time BERDO cache,
  pdfplumber for text PDFs. No microservices, no second database, no agent framework.
- Skills are plain functions `run(ctx: SkillContext) -> SkillResult` registered in `benji/skills/registry.py`.
  The API, tests and any future integration call the same registry; never duplicate calculation logic in routes or UI.
- Skills never write to storage. `benji/engine.py` runs selected skills in `EXECUTION_ORDER`, records input
  fingerprints, and marks results stale when building, bills, measure inputs or settings change.
- A skill that is not selected must not run; dependents return `blocked_by_prerequisite`.
- Exceptions inside a skill become a `failed` result; the rest of the analysis continues.
- Tests: `python -m pytest -q tests` (unit fixtures, API acceptance checks, Hypothesis property tests).
  Add a test for every acceptance rule you touch.
- Secrets (ANTHROPIC_API_KEY) are read on the server only and never logged or returned.
- The API has no authentication yet; bind to 127.0.0.1.
