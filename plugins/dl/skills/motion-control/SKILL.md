---
name: motion-control
description: "Transfer motion/pose from a source video onto a target character. Supports DreamActor (BytePlus) and Kling 3.0 Motion."
allowed-tools: Bash(dl motion-control:*)
metadata:
  ilands:
    applicable-to: [creation]
    priority: 3.0
    kind: atomic_skill
---
> **Setup (BYOA):** this skill drives the `dl` CLI, which proxies calls to iLands and bills your own iLands wallet — no API keys touch your machine. If `dl` is not on your PATH, run `npm i -g @pawlogic/dl && dl login` (or `npx -y @pawlogic/dl`). One login serves both the `dl` and `ilands` command sets. See https://ilands.ai/byoa .


# Motion Control

All decision-surface content of this skill (2 services / decision logic /
preflight / async / publish) has been **fully migrated** into the progressive
`-help` system of `dl motion-control`. This SKILL.md no longer carries content.

## First-time use → run these

- `dl motion-control --help` — top-level overview
- `dl motion-control model -h` — 2-service decision

## All subtopics

| Command | What you'll see |
|------|-------|
| `dl motion-control --help` | Top level |
| `dl motion-control model -h` | dreamactor vs kling3.0-motion decision |
| `dl motion-control model <service>` | Per-service profile |
| `dl motion-control preflight -h` | 3 required decisions |
| `dl motion-control policy -h` | User-facing + package gate |
| `dl motion-control composition -h` | pi_media_log boundary |
| `dl motion-control async -h` | detach protocol + result |
| `dl motion-control publish -h` | publish_content video |
| `dl motion-control examples -h` | Example cookbook |
| `dl motion-control errors -h` | E_SCHEMA / E_BACKEND |
