# Benji for a regular Claude session

[Download benji.zip](https://github.com/Fredess74/benji/raw/refs/heads/main/downloads/benji.zip).

Upload this single archive through Claude's custom Skills interface. It contains the existing Benji orchestrator, twelve specialist workflows, formulas, source references and record templates. No local server, Python install, sensor or Raspberry Pi is needed for the session workflow.

The host supplies the AI and any browsing/file/calculation capabilities. Without a connected Benji server, records stay in the session or exported files; there is no automatic dashboard synchronization, guaranteed persistence or background monitoring. Program leads still need current verification.

The archive is generated from the repository's skill sources and contains no customer memory, bills or credentials. Rebuild with `python scripts/package_session_skill.py`. Automated checks verify archive contents, internal paths and reproducibility; actual Claude upload/invocation is a separate check.
