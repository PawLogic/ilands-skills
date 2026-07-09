# Phase 02: Transcribe

## Goal

Obtain the dialogue / narration segments (`{start, end, text}` array, float seconds) and persist them as the `transcript` artifact so Phase 03 can use them directly without any SRT format dance.

## Required Inputs

- `audio_design_input` (verified, from Phase 01)
- `ARTIFACT_CONTRACT_PATH`

## Required Slot / Schema Loads

`transcript` is `user_visible: false`. Contract floor:

- `segments` (array, required — may be empty for music/noise input)
- `source` (string, required — one of `"artifact_reuse"` / `"dl_transcribe"` / `"user_provided"`)

## Steps

### 1. Look for an existing transcript first (reuse before recompute)

Two places, in order:

1. **Current conversation context**: Did the user message or prior agent
   already provide a transcript / segments array / SRT text? If a raw SRT
   text was given, parse it into `[{start, end, text}, ...]` floats (do NOT
   keep the `HH:MM:SS,mmm` format — convert to float seconds).

2. **Artifact slots**:

   ```bash
   dl artifact list
   # scan for slot names containing transcript / asr / caption / srt
   dl artifact read --slot=<candidate_slot>
   ```

   Common names: `transcript`, `asr_result`, `caption_track`, `srt_text`.

If anything was found, **validate duration consistency**: compare the last
segment's `end` against `audio_design_input.total_duration_sec`. If the
delta is > 5s, treat the reuse as invalid and fall through to Step 2.

If found and valid, jump to Step 3 with `source: "artifact_reuse"` or
`"user_provided"`.

### 2. Submit dl transcribe (only if Step 1 found nothing usable)

`dl transcribe` is async. The submit call below returns
`{status:"pending", job_ref, data:{task_id}}` immediately; the ASR result
arrives in a later turn as `[async-callback] job=<ref>`. **End the turn after
submit.** Do not poll, do not wait — see customPrompt §9.

Tell the user briefly first:

> "No existing transcript was found. I'll run ASR on `<media_url>` now (this
> takes ~X seconds depending on length, result arrives via callback). If you
> already have an SRT / VTT, paste it in chat and I'll use yours instead."

After ack (or default-continue per outer runtime policy):

```bash
MEDIA_URL=$(dl artifact read --slot=audio_design_input | jq -r '.media_url')
LANG=$(dl artifact read --slot=audio_design_input | jq -r '.language_hint // "auto"')

dl transcribe \
  --audio-url="$MEDIA_URL" \
  --language="$LANG" \
  --word-timestamps \
  --vad-filter \
  --max-segment-duration=5
```

Submit response shape (no segments yet — they arrive in the callback):

```json
{ "ok": true, "status": "pending", "job_ref": "<dl-uuid>",
  "data": { "task_id": "ag:asr:qwen3-asr:<id>", "status": "pending" } }
```

End the turn. Continue with Step 3 only after `[async-callback]` lands.

### 3. Write & finalize `transcript` (after callback lands)

When `[async-callback] job=<ref>` arrives in the next turn, the payload's
`result` carries the full ASR output:

```json
{ "success": true, "language": "en",
  "duration": 12.408,
  "text": "...",
  "segments": [
    { "id": 0, "start": 3.2, "end": 5.8, "text": "First segment." },
    ...
  ],
  "words": [ ... ],
  "srt_content": "...",
  "srt_url": "https://..."
}
```

Keep `segments[]` exactly as returned (units are already float seconds, no
conversion). Discard `words[]` / `text` / `srt_*` — this skill doesn't use them.

If `segments == []` (input is music / noise without speech), still write
the artifact with an empty segments array. Phase 03 has a degenerate path
that handles that by laying down a full-duration BGM bed only.

**Callback truncation on long audio**: `[async-callback]` text is capped at
4096 chars (see audio-transcription skill). `segments` ranks after the core
URL/metadata in the field order, so on long videos it may arrive truncated
mid-array. If the JSON looks unbalanced or `segments` ends abruptly, do ONE
single-shot `dl poll --job-ref=<ref>` to retrieve the full result from the
task store (48h TTL) — never loop poll. Do NOT hand-reconstruct timing from
the partial segments you saw.

```bash
cat <<'EOF' | dl artifact write \
  --slot=transcript \
  --content-type=application/json \
  --contract="$ARTIFACT_CONTRACT_PATH" \
  --content-file=-
{
  "segments": [
    { "id": 0, "start": 3.2, "end": 5.8, "text": "First segment." },
    ...
  ],
  "language": "en",
  "source": "dl_transcribe"
}
EOF

dl artifact finalize \
  --slot=transcript \
  --mode=verify \
  --contract="$ARTIFACT_CONTRACT_PATH"
```

`source` must be one of `"artifact_reuse"`, `"dl_transcribe"`, or
`"user_provided"`. If reusing a different existing slot, also include a
`source_slot` field on the JSON so Phase 07 can record the lineage.

## Output Slot

- `transcript` (verified)

## Failure Handling

- ASR returns empty for a video that clearly has speech → retry once with
  `--denoise-audio` toggled (model selection is server-side; `--model-size`
  is no longer a valid flag); if still empty, write the empty-segments
  artifact and continue (Phase 03 degenerate path).
- ASR endpoint unreachable / callback never lands within the expected window
  → do ONE single-shot `dl poll --job-ref=<ref>` to check status (NOT in a
  loop, see customPrompt §9). If still failed, ask the user to paste a
  transcript, then write with `source: "user_provided"`.

## Next Phase Entry

After `transcript` is verified, load:

    phases/03-design-cues/PHASE.md
