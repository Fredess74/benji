# Benji downloads

## Claude

[Download benji.zip](https://github.com/Fredess74/benji/raw/refs/heads/main/downloads/benji.zip).

Upload this single archive through Claude's custom Skills interface. It contains the existing Benji orchestrator, twelve specialist workflows, formulas, source references and record templates. No local server, Python install, sensor or Raspberry Pi is needed for the session workflow.

The host supplies the AI and any browsing/file/calculation capabilities. Without a connected Benji server, records stay in the session or exported files; there is no automatic dashboard synchronization, guaranteed persistence or background monitoring. Program leads still need current verification.

The archive is generated from the repository's skill sources and contains no customer memory, bills or credentials. Rebuild with `python scripts/package_session_skill.py`. Automated checks verify archive contents, internal paths and reproducibility; actual Claude upload/invocation is a separate check.

## ChatGPT

[Download the ChatGPT skills package](https://github.com/Fredess74/benji/raw/refs/heads/main/downloads/benji-chatgpt-skills-0.2.1.zip). Use it as source material with Plugin Creator where your account/workspace permits plugin creation, following the [quick start](../README.md#2-chatgpt). It is a separate package from Claude's single-skill ZIP.

It includes the orchestrator, 12 specialist skills, shared references, host-capability rules and icons. It does not include a server, customer memory, bills or credentials. Public directory publication is still deferred; archive validation is not a live ChatGPT installation test. Build with `python scripts/package_chatgpt_plugin.py`, then copy the generated archive from `dist/` into this directory when releasing updated sources.
