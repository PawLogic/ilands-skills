---
name: tts
description: "Generate speech audio from text. Supports platform voice libraries, custom voice creation from a text description, and voice cloning from an audio URL; use `dl generate-tts model -h` to choose the provider."
allowed-tools: Bash(dl knowledge search:*) Bash(dl generate-tts:*)
metadata:
  ilands:
    applicable-to: [full, creation]
    priority: 3.0
    kind: atomic_skill
---
> **Setup (BYOA):** this skill drives the `dl` CLI, which proxies calls to iLands and bills your own iLands wallet — no API keys touch your machine. If `dl` is not on your PATH, run `npm i -g @pawlogic/dl && dl login` (or `npx -y @pawlogic/dl`). One login serves both the `dl` and `ilands` command sets. See https://ilands.ai/byoa .


<!-- cli-audit: 40f0adb3b6c81c3a -->

# Text-to-Speech (TTS)

All decision-surface content of this skill — provider routing / voice
identity / custom voice creation from description / audio URL voice
cloning / marker syntax / pronunciation discipline / fallback ladder /
package gate / publish mapping — lives in the progressive `-help` system
of `dl generate-tts`. This SKILL.md is just navigation.

## First-time use → run these

- `dl generate-tts --help` — top-level overview + LEARN MORE entry
- `dl generate-tts model -h` — provider choices + when to use a library voice, description-created voice, or audio-URL voice clone
- `dl generate-tts model <provider>` — per-provider call shape before choosing voice identity flags

## All subtopics (drill down on demand)

| Command | What you'll see |
|---|---|
| `dl generate-tts --help` | Top-level overview / WHEN TO USE / full flag list / LEARN MORE |
| `dl generate-tts model -h` | 4 provider routes + decision logic |
| `dl generate-tts model <provider>` | Per-provider profile; confirms whether voice identity comes from `voice_id`, a `--control` description, or `--audio-url` |
| `dl generate-tts preflight -h` | 4 required decisions (provider / voice identity / text preparation / audio format) |
| `dl generate-tts policy -h` | User-Facing + Package Gate + MiniMax marker / voxcpm input discipline / Pronounceability / Fallback ladder |
| `dl generate-tts composition -h` | search-voice / lipsync / publish_content coordination boundary |
| `dl generate-tts async -h` | detach protocol + result shape + no poll loop |
| `dl generate-tts publish -h` | presentation_family='text' + media_urls.audio field mapping |
| `dl generate-tts examples -h` | Example cookbook |
| `dl generate-tts errors -h` | E_SCHEMA / E_UNKNOWN_OPTION / E_BACKEND |
