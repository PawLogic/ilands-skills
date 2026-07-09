# Phase 06: Attach Mixed Audio to Video

## Goal

Mux `${WORKDIR}/master.mp3` onto the original video stream from `media_url`, producing `${WORKDIR}/final.mp4`. Keep the original video stream untouched (copy, no re-encode); the only re-encode is the audio track (mp3 → AAC for mp4 container).

## Required Inputs

- `${WORKDIR}/master.mp3` (from Phase 05)
- `media_url` (read from `audio_design_input`)
- `total_duration_sec` (from `audio_design_input`, for safety check)
- `ARTIFACT_CONTRACT_PATH`

## Required Slot / Schema Loads

No artifact write in this phase. `final.mp4` stays as a local file in
`${WORKDIR}` until Phase 07 wraps it into `audio_design_result`.

## Required Companion Resources

- `phases/05-prepare-and-mix/references/ffmpeg_loudness_targets.md` §"Output container for final mp4" — explains the `-c:v copy -c:a aac -b:a 192k -shortest` choice.

## Steps

### 1. Read inputs

```bash
MEDIA_URL=$(dl artifact read --slot=audio_design_input | jq -r '.media_url')
```

### 2. Mux

```bash
ffmpeg -y \
  -i "$MEDIA_URL" \
  -i "${WORKDIR}/master.mp3" \
  -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 192k \
  -shortest \
  "${WORKDIR}/final.mp4"
```

- `-map 0:v -map 1:a` — take video from input 0 (original media), audio from input 1 (mixed master). The original audio track on the source video is discarded; it's already incorporated into `master.mp3` via Phase 05.4's dialogue chain.
- `-c:v copy` — no video re-encode (lossless, near-instant).
- `-c:a aac -b:a 192k` — AAC re-encode of mp3 master (mp4 container can carry AAC reliably; mp3-in-mp4 is supported but has historic edge cases).
- `-shortest` — defensive: if `master.mp3` is slightly longer than the video (shouldn't happen given Phase 05.4's `apad`), truncate audio rather than padding video with black.

### 3. Sanity check

```bash
ffprobe -v quiet -print_format json -show_format -show_streams "${WORKDIR}/final.mp4"
```

Verify:

- A video stream and an audio stream exist.
- `format.duration` is within ±0.5s of `audio_design_input.total_duration_sec`.

If the audio stream is missing or duration is wildly off, the mux failed
— retry once. Still failing → emit failure metadata and stop (do NOT
promote `audio_design_result` without a valid `final.mp4`).

## Output

- `${WORKDIR}/final.mp4` exists and ffprobe reports both v + a streams.

## Failure Handling

- `media_url` fetch fails mid-mux: retry once (network blips). Still failing → `curl -L -o "${WORKDIR}/source.mp4" "$MEDIA_URL"` first, then swap the `-i "$MEDIA_URL"` for `-i "${WORKDIR}/source.mp4"` and retry.
- Audio codec rejection (rare; only certain mp4 muxers reject mp3 + aac transcode chain): retry with explicit `-strict experimental` after `-c:a aac`.

## Next Phase Entry

After `${WORKDIR}/final.mp4` is verified, load:

    phases/07-finalize/PHASE.md
