---
name: video-generation
description: "Generate videos via api-layer, including one-shot requests where the selected video model should generate video together with music, voiceover, foley, or other audio. Supports text-to-video, image-to-video, multi-reference, reference-to-video, and video-edit workflows; read model help for the current provider list."
allowed-tools: Bash(dl generate-video:*) Bash(dl asset register:*) Bash(dl asset get:*)
metadata:
  ilands:
    applicable-to: [full, creation]
    priority: 4.0
    kind: atomic_skill
---
> **Setup (BYOA):** this skill drives the `dl` CLI, which proxies calls to iLands and bills your own iLands wallet — no API keys touch your machine. If `dl` is not on your PATH, run `npm i -g @pawlogic/dl && dl login` (or `npx -y @pawlogic/dl`). One login serves both the `dl` and `ilands` command sets. See https://ilands.ai/byoa .


# Video Generation

All decision-surface content of this skill (20 services ranking + decision
logic / preflight / policy / cross-skill / async / publish) has been **fully
migrated** into the progressive `-help` system of `dl generate-video`. This
SKILL.md no longer carries content.

## First-time use → run these two

- `dl generate-video --help` — top-level overview + LEARN MORE entry
- `dl generate-video model -h` — 20 services ranking + decision logic

## Multi-segment sample gate

When this skill is used inside a workflow that will generate multiple video
segments, do not commit immediately to full-batch generation for long or
expensive outputs.

- If the workflow has `N >= 4` video segments or expected final duration is
  `> 30s`, generate a **sample wave** first: 1-3 representative segments only.
- Pick samples that cover the riskiest cases: lipsync, identity-critical
  characters, complex motion, material/screenshot processing, and any provider
  mix that differs from the rest of the batch.
- Show playable sample URLs to the user and get explicit approval before
  generating the remaining segments.
- If the user explicitly says to skip samples / run the whole batch, record that
  waiver in the workflow response and proceed.

## Real-looking human / known-IP input hard rules

Before using `seedance-2-0` / `seedance-2-0-fast` / `seedance-2-0-mini`, you
**must confirm** whether this generation involves a real-looking human or
known-IP character. With a real-looking human or known IP -> you
**must** call `dl asset register` first to obtain an `asset_id`, then reference
that source ref via `--ark-asset-ids` and use `@assetN` in the prompt. For
photoreal / real-looking humans, including AI-generated photoreal humans, each
source ref must be represented exactly once: if it is in `--ark-asset-ids`, do
not also pass that same source ref as `--image-urls` / `--ref-video-url`.
Skipping = upstream policy blocks or results become uncontrolled. **Do not
gamble**. See
`dl generate-video model seedance-2-0` and `docs/seedance_reference_assets.md`
in this directory for details.

If Seedance 2.0 is blocked because of generated/output audio, retry by adding
`no BGM` / `no background music` to the prompt; do not pass `--generate-audio`.

## All subtopics (drill down on demand)

| Command | What you'll see |
|------|-------|
| `dl generate-video --help` | Top-level overview / WHEN TO USE / full flag list / LEARN MORE |
| `dl generate-video model -h` | Combined ranking of 20 services + decision logic |
| `dl generate-video model <service>` | Per-service profile (positional, one of 20 services) |
| `dl generate-video preflight -h` | 5 required decisions before calling |
| `dl generate-video policy -h` | User-Facing Communication + Production Package Gate + URL Hygiene |
| `dl generate-video composition -h` | Full-song MV duration trim-back / ffmpeg boundary / right-side canvas registration boundary |
| `dl generate-video async -h` | detach-by-default protocol + result shape |
| `dl generate-video publish -h` | publish_content video field mapping |
| `dl generate-video examples -h` | Full example cookbook |
| `dl generate-video errors -h` | E_SCHEMA / E_BACKEND triggers + recovery |
