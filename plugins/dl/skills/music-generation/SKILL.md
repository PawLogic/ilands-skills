---
name: music-generation
description: "Generate standalone music/audio tracks via api-layer. Supports suno-v5_5 (default / strongest / 2 tracks), suno-v5 (next-best / 2 tracks), minimax (temporary fallback / 1 track / single-track fast). Do not use for one-shot video requests where the selected video model can generate video and audio together; use video-generation directly, or ask whether the user wants a separate song/score track first. Before calling you must explicitly decide the generation brief (generation mode / instrumental / custom / lyrics strategy / target duration / style package / service); after results return, they must be normalized into the music_candidate slot, and finalize happens only after the user picks among multi-track candidates."
allowed-tools: Bash(dl artifact:*) Bash(dl generate-music:*)
metadata:
  ilands:
    applicable-to: [full, creation]
    priority: 3.0
    kind: atomic_skill
artifact-contract: schemas/artifact_contract.json
---
> **Setup (BYOA):** this skill drives the `dl` CLI, which proxies calls to iLands and bills your own iLands wallet — no API keys touch your machine. If `dl` is not on your PATH, run `npm i -g @pawlogic/dl && dl login` (or `npx -y @pawlogic/dl`). One login serves both the `dl` and `ilands` command sets. See https://ilands.ai/byoa .


<!-- cli-audit: b66cded8b94df1ea -->

# Music Generation

All decision-surface content of this skill (3 services ranking + decision
logic / preflight / policy / prompt triangle contract / composition / async /
publish / fallback) has been **fully migrated** into the progressive `-help`
system of `dl generate-music`. This SKILL.md no longer carries content.

## First-time use → run these two

- `dl generate-music --help` — top-level overview + LEARN MORE entry
- `dl generate-music model -h` — 3-service decision + per-service profile

## ⚠ Prompt / Custom / Instrumental triangle-contract hard rules

`--prompt` is **always required**; `--custom` / `--instrumental` determine
prompt semantics:

| Goal | Params | prompt meaning |
|-----|-----|-------------|
| Instrumental BGM only | `--instrumental`, usually **not** `--custom` | **Musical direction** (style / mood / arrangement / tempo / structure / scene). **Do not write lyrics** |
| Suno writes lyrics | **No** `--custom`, **no** `--instrumental` | **Musical direction**; Suno generates lyrics from the brief |
| Custom lyrics | Pass `--custom` | **Actual lyrics**; structural markers like `[Verse]` / `[Chorus]` / `[Bridge]` / `[Outro]` are recommended |

**Need lyrics but the user did not provide any?** Try `dl generate-lyrics --prompt="<short brief, ≤200 chars>"` first — it returns 2-3 KIE-Suno candidates with [Verse]/[Chorus] markers; pick one and feed it as `dl generate-music --custom --prompt=<lyrics>`. Only hand-write lyrics yourself when `dl generate-lyrics` fails (E_BACKEND / sensitive-word block / timeout). A pure instrumental track must not call `generate-lyrics`.

For the detailed decision surface, see `dl generate-music policy -h` (rule 3).

## ⚠ Artifact-Finalize Gate hard rules

This skill mandates normalizing generation results into the `music_candidate`
slot (new artifact protocol — pure domain `data`; no UI fields):

- Multi-track providers (`suno-v5_5` / `suno-v5`) → `data.candidates[]` keeps
  all candidates, `data.selected_candidate_index` / `data.selected_audio_url`
  = null. The user **must** pick before you patch-json + re-finalize.
- Single-track provider (`minimax`) → one entry; `selected_candidate_index`
  is set to 0 and `selected_audio_url` is copied from
  `candidates[0].audio_url` on first write.

For the detailed landing flow, see `dl generate-music policy -h` (rule 4) plus
`schemas/` + `templates/` in this directory.

## All subtopics (drill down on demand)

| Command | What you'll see |
|------|-------|
| `dl generate-music --help` | Top-level overview / WHEN TO USE / full flag list / LEARN MORE |
| `dl generate-music model -h` | 3-service ranking + decision logic |
| `dl generate-music model <service>` | Per-service profile (positional, one of 3 services) |
| `dl generate-music preflight -h` | 7 required decisions (generation mode / instrumental / custom / lyrics / duration / style / service) |
| `dl generate-music policy -h` | User-Facing + Package Gate + Prompt triangle contract + Artifact-Finalize Gate + Fallback |
| `dl generate-music composition -h` | artifact slot / lipsync / analyze-beats / publish_content coordination boundary |
| `dl generate-music async -h` | detach protocol + result shape (2-track vs 1-track) + no poll loop |
| `dl generate-music publish -h` | presentation_family='text' + media_urls.audio field mapping |
| `dl generate-music examples -h` | Example cookbook |
| `dl generate-music errors -h` | E_SCHEMA / E_FILE_PARSE / E_UNKNOWN_OPTION |
