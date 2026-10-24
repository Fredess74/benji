# Verification record

**2026-10-24.** Calculator/server baseline: `45d56cf`; branding then updated from `4c1f0fe`.

## Automated checks

An isolated clone of the public repository was used:

```text
python -B -m pytest -q tests -p no:cacheprovider --tb=short
176 passed, 2 warnings in 36.71s
```

The preceding restricted run could not write temporary databases/uploads. The successful run used normal local filesystem access; earlier environment errors were not counted as passes.

Warnings remain: Starlette's `httpx` test-client deprecation and a duplicate `confirmBills` operation ID in the combined OpenAPI document. HTTP tests passing does not resolve client-generation ambiguity.

Coverage includes skill routing, manifests, memory/API/MCP, calculation invariants, acceptance cases, previous regressions, thermal scenarios and property-based checks. It is not a security certification, usability study, external-client installation test or savings measurement.

## Interface and package

- `/app` serves the current `dashboard/index.html`.
- A separate server was opened with explicitly synthetic cafe records. Bill totals, missing upgrade inputs and insufficient-peer messaging were visible.
- The browser inspection used only that fixture, not customer data or proof of a live agent session.
- The ChatGPT private package was saved and its inventory re-read: all 13 skills and supporting files were present. Live conversation invocation is not claimed.
- The team reports a successful Claude Code-style MCP subprocess check. Actual Claude Code client installation remains unverified.

## Repeat before a release

Install dependencies, run tests, start agent and dashboard with the same memory path, confirm bills, create a plan, update a task and verify the next agent run reads it. Change an input and check staleness. Check each external client independently; channel labels are not identity evidence.
