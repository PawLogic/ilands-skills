---
name: audio-transcription
description: Transcribe audio to text via ASR with multi-language auto-detection and timing support. Use when music-video planning or other timing-sensitive workflows need exact lyric or word timing before storyboarding. In the full-song MV workflow's Phase 01, read this skill before the first transcription call.
allowed-tools: Bash(dl transcribe:*) Bash(dl artifact:*)
metadata:
  ilands:
    applicable-to: [full, creation]
    priority: 2.5
    kind: atomic_skill
---
> **Setup (BYOA):** this skill drives the `dl` CLI, which proxies calls to iLands and bills your own iLands wallet — no API keys touch your machine. If `dl` is not on your PATH, run `npm i -g @pawlogic/dl && dl login` (or `npx -y @pawlogic/dl`). One login serves both the `dl` and `ilands` command sets. See https://ilands.ai/byoa .


# Audio Transcription

All decision-surface content of this skill (preflight / policy / composition /
publish field mapping) has been **fully migrated** into the progressive
`-help` system of `dl transcribe`.

## First-time use → run these two

- `dl transcribe --help` — top-level overview + LEARN MORE entry
- `dl transcribe preflight -h` — required decisions (audio URL / language / output mode / tuning)

## ⚠ Async behavior + default callback shape (hard rules)

- `dl transcribe` is **async** via the api-layer task queue. The submit call
  returns immediately with `{ok:true, status:"pending", job_ref, data:{task_id}}`;
  the SRT lands later as an `[async-callback] job=<ref>` user message that
  re-enters the session in a new turn.
- **End the turn after submit.** Do NOT wrap the call in `nohup ... &`, do NOT
  poll in a `sleep` / `for` / `while` loop, and do NOT call `dl poll`
  proactively — see customPrompt §9 for the async detach rules that govern
  all submit-style verbs.
- The callback payload's `result` object carries `srt_url` + `srt_content`
  (and `text` / `segments` / `words` when `--word-timestamps` was passed).
  Default keeps the callback trimmed to SRT-only to save tokens.
- When a reliable transcript already exists, use `--transcript-text="..."`
  to skip ASR recognition and only time-align — saves tokens and latency.
- **Do not pass `--model-size`** — it's no longer a valid CLI flag. The
  server picks the pipeline (Qwen3-ASR + stable-ts + DTW fallback).
- If significantly more than the expected window (~5-60s short / longer for
  cold-start GPU / multi-minute audio) passes without `[async-callback]`
  landing, you may do exactly ONE single-shot `dl poll --job-ref=<ref>` to
  check status — never in a loop.

## ⚠ Callback truncation (long audio)

`[async-callback]` payload is injected as text with a hard **4096-character
cap** (see hono-pi-web JobDock). The api-layer side orders result fields so
the core URL + metadata always survives the cut:

```
success → srt_url → language → duration → alignment_quality
        → alignment_method_used → vendor
        → srt_content → alignment_warnings → alignment_diagnostics
        → text → segments → words   (heaviest, may be sliced off on long audio)
```

If the callback text looks truncated (mid-JSON, unbalanced braces, missing
trailing `}`):

1. **Do NOT** hand-reconstruct SRT from the partial `text` / `segments` /
   `words` you saw — timing for "later segments" is unreliable.
2. `srt_url` is always present even after truncation — `curl` it (or feed
   it to the downstream tool directly) for the full SRT.
3. If you specifically need the full `segments` / `words` arrays
   (add-audio-cues phase 02 case), do ONE single-shot
   `dl poll --job-ref=<ref>` — the full result is stored in api-layer's
   task store (48h TTL) and `dl poll` returns it unbounded. Never loop poll.

## ⚠ Low alignment_quality → understand_media fallback

Word-level timing is only trustworthy when `result.alignment_quality === "high"`.
When it is `"low"` / `"medium"` / missing:

1. Call the built-in `understand_media` tool on the same audio URL with a
   verbatim-transcription query — use its returned text as the clean lyrics.
2. Resubmit `dl transcribe --audio-url=<same> --transcript-text=<clean> --word-timestamps=true`
   (DTW time-aligns the clean text, no re-recognition).
3. The second `[async-callback]` is authoritative — its `srt_content` /
   `segments` / `words` replace the first; never mix segments across the two.

Step 2 follows the normal async / one-shot-poll rules (`dl transcribe async -h`).

## Persisting to audio_analysis artifact (composition workflows)

When the parent composition defines an `audio_analysis` slot (e.g.
`create-complex-music-video-from-music`), persist post-fallback transcript
via read-modify-write so sibling steps' `beats` / `track` survive:

1. `dl artifact read --slot=audio_analysis` — treat `not_found` as `{}`.
2. Set `transcription.text` / `srt_content` (optional) / `language` /
   `segments[]` (with `words[]` nested per-segment by time range) from the
   authoritative callback. Leave existing `beats` / `track` untouched.
3. `dl artifact write --slot=audio_analysis --content-type=application/json --content=<merged> --contract=<ARTIFACT_CONTRACT_PATH>`.

Two separate Bash calls — never chain with `&&` / `;`.

## All subtopics (drill down on demand)

| Command | What you'll see |
|---------|----------------|
| `dl transcribe --help` | Top-level overview / WHEN TO USE / full flag list / LEARN MORE |
| `dl transcribe preflight -h` | Required decisions (audio URL / language / output mode / tuning) |
| `dl transcribe policy -h` | User-Facing + Package Gate + output trim + server-side model selection |
| `dl transcribe composition -h` | create-subtitles / lipsync / hyperframes-cli boundary |
| `dl transcribe async -h` | detach protocol + result shape + lost-callback escape hatch |
| `dl transcribe publish -h` | publish_content field mapping when delivering the SRT itself |
| `dl transcribe examples -h` | Example cookbook |
| `dl transcribe errors -h` | E_SCHEMA / E_UNKNOWN_OPTION / E_BACKEND |
