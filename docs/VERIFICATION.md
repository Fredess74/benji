# Verification record

**2026-10-24.** Audit of `Fredess74/benji`, starting from `d792b728a1d9d91c60693d3d13b67f49b4e97a90`, in an isolated clone. No customer bills were used.

## Automated checks

An isolated clone of the public repository was used:

```text
python -B -m pytest -q tests -p no:cacheprovider --tb=short
200 passed, 1 warning in 43.22s
```

The baseline had 177 passing tests. This audit added 23 regression/package cases. Substantive defect cases were observed failing before their fixes. The successful full run used Python 3.11 on Windows with normal local temporary-file/socket access; sandbox environment failures were not counted as passes.

One warning remains: Starlette's `httpx` test-client deprecation. The duplicate `confirmBills` operation ID was fixed and all 59 generated operation IDs are unique. GitHub Actions is configured to repeat the suite on Ubuntu and check that the downloadable skill matches its sources; the local result above does not claim a completed remote run.

## Reproduced defects and repairs

| Failure | Repair and check |
|---|---|
| Changed bills, profile or answers could leave old advice looking current | Mark findings/plan stale on changes; identical input writes do not invalidate |
| Malformed confirmed bills could be omitted from a partial result | Validate rows and block the cross-check with specific missing/invalid evidence |
| Partial charge breakdowns could dilute the rate or become a false known total | Preserve missing values and explicit breakdown completeness |
| Demand charges and credits could be treated as usage-related money | Preserve categories; distinguish consumption, price, fixed, demand, other and credit effects |
| Rate rounding created a false unexplained amount | Calculate from unrounded inputs; a large-bill regression reconciles the actual $4 difference |
| Confirming a short CSV could fail when metadata columns were absent | Add confirmation columns for every row; normalize status whitespace |
| Electric/gas provider roles could be conflated | Parse each provider by its utility role |
| Configuring an API key did not cover every data-route family | Apply key checks to `/api`, `/memory` and `/assistant` data routes |
| An annualized partial year appeared to be an observed annual total | Preserve the estimate flag and show “scaled estimate” in the dashboard |
| Business renters could follow residential program instructions | Keep business/residential routing based on the property and account type |
| Bill-explanation instructions omitted non-usage charges | Align the skill formula and numerical output, including an unexplained remainder |

Local Markdown links and JSON manifests were checked. `git diff --check` passed. The review is bounded to these behaviors and the current product workflow, not an exhaustive security audit.

Coverage includes skill routing, manifests, memory/API/MCP, calculation invariants, acceptance cases, previous regressions, thermal scenarios and property-based checks. It is not a security certification, usability study, external-client installation test or savings measurement.

## Interface and package

- `/app` serves the current `dashboard/index.html`.
- A separate localhost server was opened with explicitly synthetic cafe records. Bill totals, missing upgrade inputs and insufficient-peer messaging were visible.
- In the browser, a question was answered and a task created/marked done. After reload, the answer and task status remained saved; the plan showed a stale warning and an updated next-step message.
- The Agents view correctly showed no recorded agent activity; assignments alone were not labelled as live connections.
- `downloads/benji.zip` packages one entry skill, all 12 specialist workflows and shared references. Tests check internal links, absence of customer/runtime data and reproducible output.
- A separate agent reviewed the archive as a consumer using a fictional leased cafe, incomplete bills and unsupported automation requests. It identified routing/formula defects, then rechecked their repairs. This is an instruction-consumption test, not an actual Claude client installation.
- Actual upload/invocation in Claude, Claude Code client installation, OpenClaw scheduling and a live multi-agent deployment remain unverified. ChatGPT catalog publication was not part of this audit.

## Repeat before a release

Install dependencies, run tests, start agent and dashboard with the same memory path, confirm bills, create a plan, update a task and verify the next agent run reads it. Change an input and check staleness. Check each external client independently; channel labels are not identity evidence.
