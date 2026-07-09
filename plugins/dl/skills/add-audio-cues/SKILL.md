---
name: add-audio-cues
description: >-
  Adds full sound design (SFX, Stingers, BGM, AMB ambience) to an existing
  video that already has dialogue or narration. Designs a cue timeline from
  the ASR transcript, retrieves library assets via knowledge search, prepares
  per-cue clips with native ffmpeg, mixes a master with EBU R128 loudness +
  sidechain ducking, then muxes the result back to a final mp4. Use when a
  video has clean speech but feels empty without atmosphere or score. Do NOT
  use for music videos (use music-generation), talking-head broadcasts (use
  host-broadcast), or audio-only pieces with no existing dialogue track.
allowed-tools: Bash(dl transcribe:*) Bash(dl knowledge search:*) Bash(dl artifact:*) Bash(dl asset:*) Bash(ffmpeg:*) Bash(ffprobe:*) Bash(mktemp:*) Bash(curl:*) Bash(wget:*)
compatibility: "Pi-safe; requires local ffmpeg / ffprobe in PATH (BtbN static GPL build recommended) — does NOT go through dl ffmpeg sandbox."
metadata:
  ilands:
    applicable-to: [creation]
    priority: 2.5
    kind: atomic_skill
artifact-contract: schemas/artifact_contract.json
---
> **Setup (BYOA):** this skill drives the `dl` CLI, which proxies calls to iLands and bills your own iLands wallet — no API keys touch your machine. If `dl` is not on your PATH, run `npm i -g @pawlogic/dl && dl login` (or `npx -y @pawlogic/dl`). One login serves both the `dl` and `ilands` command sets. See https://ilands.ai/byoa .


<!-- cli-audit: native-ffmpeg-direct -->

# Add Audio Cues

## What This Skill Owns

- audio cue design (AMB / BGM / SFX / STINGER timeline) from transcript
- library asset retrieval via `dl knowledge search` (sfx / bgm / amb / stinger domains)
- per-cue ffmpeg preparation (download + trim + loop to target duration)
- timeline mix with EBU R128 loudness + sidechain ducking + final limiter
- mux mixed audio back to final mp4
- terminal `audio_design_result` artifact

## What This Skill Does Not Own

- transcription pipeline correctness (delegated to `dl transcribe` / upstream `transcript` artifact)
- knowledge base curation (assets come from existing `sfx` / `bgm` / `amb` / `stinger` domains)
- video editing beyond audio mux (no shot trimming, no caption render — that's other skills)
- approval / publish / budget policy (runtime concerns)
- generic runtime pause / resume mechanics

## Overview

```text
input video (with dialogue)
  │
  ▼  Phase 01  Intake — persist inputs (media_url, total_duration, …)
[audio_design_input]            (internal, user_visible:false)
  │
  ▼  Phase 02  Transcribe — reuse upstream or run dl transcribe
[transcript]                    (internal, user_visible:false)
  │
  ▼  Phase 03  Design cues — agent acts as sound designer; user checkpoint
[audio_cues_plan]               ⭐ user reviews & approves
  │
  ▼  Phase 04  Retrieve — dl knowledge search per cue, ffprobe real durations
[ (manifest in working memory) ]
  │
  ▼  Phase 05  Prepare & Mix
  │       4a per-cue native ffmpeg → prepared mp3
  │       4b one ffmpeg invocation → master.mp3 (loudnorm + sidechain + limiter)
[audio_retrieval_manifest]      ⭐ written after 4a finishes
  │
  ▼  Phase 06  Attach to video — native ffmpeg mux master.mp3 onto media
[ (final.mp4 in WORKDIR) ]
  │
  ▼  Phase 07  Finalize — user acks the cut, write & promote terminal artifact
[audio_design_result]           ⭐ terminal, promoted
```

## Required Bootstrap

Before Phase 1 starts:

1. Resolve the artifact contract path:

   ```bash
   ARTIFACT_CONTRACT_PATH="$(realpath skills/add-audio-cues/schemas/artifact_contract.json)"
   ```

2. Verify ffmpeg / ffprobe are reachable and have the required filters:

   ```bash
   command -v ffmpeg && command -v ffprobe
   ffmpeg -filters 2>/dev/null | grep -E "loudnorm|sidechaincompress|alimiter|aloop|adelay" | wc -l
   # expect: 5 (one per filter)
   ```

   If anything is missing, follow `phases/05-prepare-and-mix/references/ffmpeg_install.md`
   to install the BtbN static GPL build, then re-check.

3. Create the working directory:

   ```bash
   WORKDIR=$(mktemp -d /tmp/audio_sop_XXXXXX)
   ```

4. Load `phases/01-intake/PHASE.md` to start.

## Artifact CLI Primer

This skill uses the artifact working set through `dl artifact ...`.

Common operations:

- `dl artifact write --slot=<name> --content-type=<mime> --content-file=- --contract='<ARTIFACT_CONTRACT_PATH>'` (stdin pipe)
- `dl artifact read --slot=<name>`
- `dl artifact patch-json --slot=<name> --operations-file=-` (stdin pipe; JSONPath-lite, no `--contract`)
- `dl artifact finalize --slot=<name> --mode=verify --contract='<ARTIFACT_CONTRACT_PATH>'`
- `dl artifact finalize --slot=<name> --mode=verify_and_promote --contract='<ARTIFACT_CONTRACT_PATH>'` (terminal only)

Rules:

- `--content` is always a string. Serialize JSON before passing it.
- Use `write` for first write or full replacement; `patch-json` only for incremental structured updates.
- `patch-json` is JSONPath-lite (paths look like `field`, `nested.field`, `items[0].field`); ops ∈ `set / merge / append / delete`. Do NOT pass `--contract` to `patch-json` — finalize afterwards with the contract.
- Write and finalize calls must use the same `ARTIFACT_CONTRACT_PATH`.
- After a successful `write`, the immediate next non-read action must be `finalize` for the same slot.
- Use `verify_and_promote` only for `audio_design_result` (terminal). Other slots use plain `verify`.

If exact syntax is unclear, consult `dl artifact --help`.

## Shared Schema Discipline

- Load the exact slot schema before the first write to that slot
  (e.g. `schemas/audio_cues_plan.schema.json`).
- Start from `templates/<slot>.minimum.json` when present.
- Treat minimum templates as validation floors, not richness ceilings.
- Keep cross-field semantics coherent: `start + duration_sec ≤ total_duration_sec`,
  AMB/BGM bed intervals never overlap, etc.
- Repair AJV errors literally; do not invent alternate field shapes.

## Shared Artifact Protocol Discipline

All five slots follow the new artifact protocol: `dl artifact` envelopes
`{ slot, status, version, data }`; `data` is **pure domain data**, no UI
fields (`component_type` / `variant` / `content_layout` are forbidden — the
frontend infers rendering from field names + array shape).

User-visible domain shapes per slot:

| Slot | data shape | rendering driven by |
| --- | --- | --- |
| `audio_cues_plan` | `{ cues: [{cue_number, category, title, start_time, duration?}] }` | `start_time + duration` → auto timeline view; `category` → badge chip |
| `audio_retrieval_manifest` | `{ cues: [{cue_number, category, title, audio_url, start_time, ...}] }` | `audio_url` (.mp3/.wav) → auto audio player; `retrieval_status` → badge chip |
| `audio_design_result` | `{ video_url, title, description, duration, quality_tier, cue_counts, ... }` | `video_url` (.mp4) → auto video player; `quality_tier` → badge chip |

The two internal slots (`audio_design_input`, `transcript`) are
`user_visible: false` — they exist as working memory across phases, never
rendered to the user.

## Artifact Flow

```text
audio_design_input  (Phase 01, opt-out)
        │
        ▼
transcript          (Phase 02, opt-out)
        │
        ▼
audio_cues_plan      ⭐ user checkpoint (Phase 03, user_visible)
        │
        ▼
audio_retrieval_manifest  (Phase 05.3.1, user_visible)
        │
        ▼
audio_design_result  ⭐ terminal, promoted (Phase 07, user_visible)
```

## Phase Entry Map

| Phase | Entry file | Primary output |
| --- | --- | --- |
| 01 | `phases/01-intake/PHASE.md` | `audio_design_input` (verified) |
| 02 | `phases/02-transcribe/PHASE.md` | `transcript` (verified) — or reused upstream |
| 03 | `phases/03-design-cues/PHASE.md` | `audio_cues_plan` (verified, after user checkpoint) |
| 04 | `phases/04-retrieve/PHASE.md` | manifest in working memory (not yet artifact) |
| 05 | `phases/05-prepare-and-mix/PHASE.md` | `audio_retrieval_manifest` (verified) + `master.mp3` in WORKDIR |
| 06 | `phases/06-attach-to-video/PHASE.md` | `final.mp4` in WORKDIR |
| 07 | `phases/07-finalize/PHASE.md` | `audio_design_result` (promoted) |

Follow the chain phase-by-phase. After each PHASE.md's "Next Phase Entry"
pointer, load the next file with the built-in `read` tool.

## Completion Definition

This workflow is complete when:

- `slot_verified(audio_design_input)`
- `slot_verified(transcript)`
- `slot_verified(audio_cues_plan)`
- `slot_verified(audio_retrieval_manifest)`
- `slot_promoted(audio_design_result)`

The skill ends after the terminal `audio_design_result` is promoted in
Phase 07. Publish, distribution, or further editing belongs to outer
orchestration.

## Failure and Partial Completion

Failure ladder (per `failure_policy`):

1. **Retry** — bounded same-step retry (e.g. one cue's 4a ffmpeg fails → retry once).
2. **Alternate** — switch params or asset (e.g. BGM retrieval empty → search `audio_any` domain; sidechain artifacts → static volume).
3. **Degrade** — emit a degraded plan (`quality_tier="degraded"`):
   - LLM cue design garbage → single BGM bed full duration.
   - >50% cues dropped → continue but mark degraded.
4. **Partial finalize** — `audio_retrieval_manifest` can carry `failed_cues[]` while still promoting `audio_design_result`, as long as a usable `master.mp3` / `final.mp4` exists.
5. **Emit failure metadata** — if even partial mix fails, do not promote `audio_design_result`; record the blocker for the outer runtime.

## Trigger Patterns

Route to this skill when:

- User has a video clip with clean dialogue / narration but flat audio.
- User says "add sound effects", "add BGM", "配音效", "加背景音乐", "make it cinematic", "add atmosphere".
- A prior skill produced a video + dialogue track and asks for sound design pass.

Do NOT route here when:

- The input is audio-only (no video) — that's not this skill's scope.
- The user wants to compose music from scratch — use `music-generation`.
- The user wants a talking-head one-shot piece — use `host-broadcast` (handles its own BGM).
- The user wants subtitles burned in — use `caption-render` after this skill.

## Runtime Boundaries

- Runtime activation / reload of this skill source is external.
- Approval density (how often to confirm with user) is runtime policy, not skill code. This SOP marks **two** mandatory user checkpoints: `audio_cues_plan` review (Phase 03) and final cut ack (Phase 07). Outer runtime decides whether additional confirmations are inserted.
- Budget governance (token / sandbox cost) is runtime concern.
- Long-running pause / resume across sessions is outer runtime mechanic; artifacts (especially `audio_retrieval_manifest`) make resume feasible, but the orchestration belongs outside.
