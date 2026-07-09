# ilands-skills

Public skill marketplace for **iLands BYOA** (Bring Your Own Agent) — install iLands creation & platform skills into your own coding agent (Claude Code, Codex, Cursor, pi, OpenClaw, Hermes) and create with **your own iLands wallet**. Vendor API keys never touch your machine: every call is proxied through the `dl` CLI to iLands and billed to your account.

Landing page & usage: **https://ilands.ai/byoa** · See your spend at **https://ilands.ai/usage**

## Two plugins

| Plugin | What | Access |
|--------|------|--------|
| **`dl`** | Creation skills — image / video / music / TTS / lipsync / audio / research / stock media | Any logged-in iLands user |
| **`ilands`** | Platform skills — publish content, bounties, social interaction, service listings, audience analysis | Installable by anyone; **use** gated server-side by your iLands account role |

## Install

**1. Install the CLI** (or let a skill do it): `npm i -g @pawlogic/dl`
**2. Log in** to your iLands account (one login serves both `dl` and `ilands`): `dl login`
**3. Add the marketplace + a plugin:**

| Agent | Commands |
|-------|----------|
| Claude Code | `/plugin marketplace add PawLogic/ilands-skills` → `/plugin install dl@ilands-skills` |
| Codex | `codex plugin marketplace add PawLogic/ilands-skills` → `codex plugin install dl@ilands-skills` |
| Cursor / any | `npx skills add PawLogic/ilands-skills` |
| pi | `pi install npm:@pawlogic/dl` |
| Hermes | `hermes skills install github:PawLogic/ilands-skills` |

Then in your agent: `dl generate-image-prompt --prompt "a quiet archipelago at dawn"`.

## Supply-chain transparency

- This repo is a **public, auditable one-way mirror**, generated from PawLogic's private skill sources by a sync script with a hardcoded-secret gate (no vendor keys, internal endpoints, or tokens are published).
- Skills only call the open-source `dl` CLI (`@pawlogic/dl`, npm provenance). No `curl | bash`, no obfuscation.
- All billing goes to your iLands wallet after you `dl login`; nothing is charged without your login.

_Sources are private (creation skills mirror `pi-mono/skills`; platform skills mirror `ilands/skills`); edit skills there, not here — this repo is regenerated._
