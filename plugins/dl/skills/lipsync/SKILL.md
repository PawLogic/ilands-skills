---
name: lipsync
description: "Generate lip-sync talking-head video from image/images and driving audio. Supported services: dlai2v_pro, dlai2v_pro_multiframe, dlai2v, longcat-avatar. Preferred default: dlai2v_pro. LTX-family prompts must follow the three-part subject speaking + character action + camera move template; MV segment workflow must use segment-specific performance still + canonical driving audio (do not crop / pad / stretch)."
allowed-tools: Bash(dl lipsync:*)
metadata:
  ilands:
    applicable-to: [full, creation]
    priority: 3.5
    kind: atomic_skill
---
> **Setup (BYOA):** this skill drives the `dl` CLI, which proxies calls to iLands and bills your own iLands wallet — no API keys touch your machine. If `dl` is not on your PATH, run `npm i -g @pawlogic/dl && dl login` (or `npx -y @pawlogic/dl`). One login serves both the `dl` and `ilands` command sets. See https://ilands.ai/byoa .


<!-- cli-audit: fb245d9f29bc9016 -->

# Lip Sync

All decision-surface content of this skill (service ranking + decision logic /
preflight / policy / prompt templates / composition / async / publish) has been
**fully migrated** into the progressive `-help` system of `dl lipsync`. This
SKILL.md no longer carries content.

## First-time use → run these two

- `dl lipsync --help` — top-level overview + LEARN MORE entry
- `dl lipsync model -h` — supported-service decision + per-service profile

## ⚠ LTX 2 family prompt template hard rules

`dlai2v_pro` / `dlai2v_pro_multiframe` / `dlai2v` prompts **must** contain three parts:

1. **Subject speaking/singing** (explicitly state the character *speaking* or *singing* with perfect lip sync)
2. **Character action** (head nods/tilts / gaze / hands / shoulders / breathing)
3. **Camera movement** (Dolly in / slow push in / static medium close-up; even static must be stated explicitly)

You may append a `"high quality, natural lighting"` quality tail. For detailed
templates, see `dl lipsync model dlai2v_pro` and `dl lipsync policy -h`.

## Model boundary

Use only `dlai2v_pro`, `dlai2v_pro_multiframe`, `dlai2v`, or
`longcat-avatar` for lipsync.

## Duration hard rule

`dl lipsync` duration follows `--audio-url`. Do not pass `--duration`; split or
trim the driving audio upstream, then trim any padded output video afterward.

## All subtopics (drill down on demand)

| Command | What you'll see |
|------|-------|
| `dl lipsync --help` | Top-level overview / WHEN TO USE / full flag list / LEARN MORE |
| `dl lipsync model -h` | Combined ranking of supported services + decision logic |
| `dl lipsync model <service>` | Per-service profile |
| `dl lipsync preflight -h` | Required decisions (service / audio length / resolution / face plan) |
| `dl lipsync policy -h` | User-Facing + Package Gate + LTX template + URL Hygiene + MV duration & still + Fallback |
| `dl lipsync composition -h` | tts / image-gen / publish_content coordination boundary |
| `dl lipsync async -h` | detach protocol + result shape + no poll loop |
| `dl lipsync publish -h` | presentation_family='video' field mapping |
| `dl lipsync examples -h` | Example cookbook |
| `dl lipsync errors -h` | E_SCHEMA / E_UNKNOWN_OPTION / E_BACKEND |
