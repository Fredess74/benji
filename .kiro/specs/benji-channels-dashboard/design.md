# Design: channels and dashboard

```
Dashboard /app (index.html, app.js, start.js)
   |-- detailed tabs  -> /api/*       --\
   '-- Start here     -> /assistant/* ---+--> benji/assistant.py --> engine.analyze --> skills registry
Claude  -> benji/mcp_server.py (FastMCP, stdio) --/
ChatGPT -> /assistant/* via /assistant/openapi.json (bearer key)
OpenClaw -> integrations/openclaw/benji/SKILL.md (curl to /assistant/*)
```

- `assistant.summarize()` builds "what we found / what to do first / programs / missing / limits" from skill outputs
  only. It does no new arithmetic.
- Role defaults (`s17_plan.ROLE_DEFAULTS`) map occupant_role to who pays and who authorizes.
  `LANDLORD_MEASURES` are moved to tier 4 for tenants.
- Categories: `BUSINESS_TO_BERDO` maps business types to BERDO property types. Homes return insufficient data.
- Plan skill 17 no longer requires a complete profile. An incomplete profile becomes the first recommendation, and
  "no bills" produces "collect information + no-cost assessment".
- Decision: no model call in any channel. The external assistant is the language layer, and Benji is the
  calculator. This keeps numbers reproducible and keeps API keys out of Benji.
