# Phase 01: Intake

## Goal

Capture the user's inputs (source video URL, narrative context, language hint) and persist them into the `audio_design_input` artifact so every later phase can resolve them deterministically — even after working memory is compressed across long sessions.

## Required Inputs

- `media_url` — public URL of the input video (must already have a dialogue / narration track)
- `media_kind` — `"video"` (this skill scope; audio-only inputs are not supported, see SKILL.md trigger patterns)
- `language_hint` — optional, e.g. `"auto"`, `"zh"`, `"en"` (passed to Phase 02 `dl transcribe`)
- `narrative_context` — optional one-paragraph synopsis / setup that helps the sound designer in Phase 03 understand intent when transcript alone is thin
- `ARTIFACT_CONTRACT_PATH` (resolved in root SKILL.md bootstrap)

## Required Slot / Schema Loads

`audio_design_input` is `user_visible: false`, so no separate slot schema —
the artifact contract's `verification.required_fields` are the only floor:

- `media_url` (string, required)
- `media_kind` (string, required)

## Required Companion Resources

None for this phase. Inputs come from the user / outer skill.

## Steps

### 1. Confirm inputs with user

Echo back what was captured (media URL, narrative context if provided). If
critical fields are missing (`media_url` absent, or `media_kind` is not
`"video"`), stop and ask the user — do not fabricate defaults.

### 2. Probe the source video's total duration

Native ffprobe (ffmpeg installation check must already be passing per
SKILL.md bootstrap step 2):

```bash
ffprobe -v quiet -print_format json -show_format -show_streams "<media_url>"
```

Read `format.duration` from the output JSON. Cast to float seconds and keep
as `total_duration_sec` for later patch-in.

If ffprobe fails (network, codec) → retry once; still failing → emit
failure_metadata and stop. No artifact written yet, so the run can be
restarted clean.

### 3. Write `audio_design_input` and finalize

```bash
cat <<'EOF' | dl artifact write \
  --slot=audio_design_input \
  --content-type=application/json \
  --contract="$ARTIFACT_CONTRACT_PATH" \
  --content-file=-
{
  "media_url": "<media_url>",
  "media_kind": "video",
  "language_hint": "auto",
  "narrative_context": "",
  "total_duration_sec": null
}
EOF

dl artifact finalize \
  --slot=audio_design_input \
  --mode=verify \
  --contract="$ARTIFACT_CONTRACT_PATH"
```

`total_duration_sec` is left `null` if probing happened before write. Patch
it in now:

```bash
cat <<'EOF' | dl artifact patch-json --slot=audio_design_input --operations-file=-
[{"op":"set","path":"total_duration_sec","value":<probed_duration>}]
EOF

dl artifact finalize \
  --slot=audio_design_input \
  --mode=verify \
  --contract="$ARTIFACT_CONTRACT_PATH"
```

(`patch-json` makes the slot draft again — re-finalize before downstream
use, per the Artifact CLI Primer rule.)

## Output Slot

- `audio_design_input` (verified)

## Resolution Rule for Downstream Phases

Every later command template that has `<media_url>` or `<total_duration_sec>`
takes its real value from:

```bash
dl artifact read --slot=audio_design_input
```

If working memory disagrees with the artifact, the artifact wins.

## Failure Handling

- ffprobe fails: retry 1×; if still fails, stop and let the user provide
  duration manually (then write the artifact with the manual value).
- User-provided narrative_context is empty: that's fine, leave the field
  empty; Phase 03 will rely on transcript alone.

## Next Phase Entry

After `audio_design_input` is verified, load:

    phases/02-transcribe/PHASE.md
