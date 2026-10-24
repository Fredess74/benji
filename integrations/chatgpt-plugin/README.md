# ChatGPT skills plugin

Benji's skills-only plugin was created privately through Plugin Creator on 2026-10-24. Its saved inventory contains 12 specialist skills, the orchestrator and shared references/templates.

[Owner's private plugin](https://chatgpt.com/plugins/plugins_6add2239ad548191b921335e01e09615)

This account link is not a public-directory listing. Public package files can be downloaded from this repository; directory publication is a separate review process. Package creation does not establish invocation in a live ChatGPT conversation.

## Included

- Energy-management procedures, formulas, evidence rules and Massachusetts reference material.
- Clear host-capability boundaries and session-record fallback.
- No bundled server, automatic dashboard synchronization, permanent memory or background notifications.

## Build

```bash
python scripts/package_chatgpt_plugin.py
```

Creates `dist/benji-chatgpt-skills-0.2.1.zip`. It contains one portable plugin, the supplied Benji icon, 13 skills and shared materials. It excludes Claude marketplace files, credentials and runtime bills. Save through a compatible Plugin Creator workflow in your own account; host availability and review conditions apply.

Connected memory needs separate tools. [Custom GPT Actions](../chatgpt/instructions.md) are a distinct route. Do not expose the whole local development server as a quick cloud connection.
