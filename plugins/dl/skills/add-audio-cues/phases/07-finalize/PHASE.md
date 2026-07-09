# Phase 07: Finalize — User Ack + Terminal Promotion

## Goal

Wait for the user to ack the final cut (`${WORKDIR}/final.mp4` and / or `${WORKDIR}/master.mp3`). If approved, register the local outputs as CDN URLs (so the artifact can carry user-reachable links), then write & promote `audio_design_result` — the only promoted artifact in this skill, marking workflow completion.

## Required Inputs

- `${WORKDIR}/final.mp4` (from Phase 06)
- `${WORKDIR}/master.mp3` (from Phase 05)
- All prior artifacts verified: `audio_design_input`, `transcript`, `audio_cues_plan`, `audio_retrieval_manifest`
- `ARTIFACT_CONTRACT_PATH`

## Required Slot / Schema Loads

- `schemas/audio_design_result.schema.json` — terminal artifact schema (single + video + is_segment:false)
- `templates/audio_design_result.minimum.json` — payload skeleton

## Steps

### 1. Present the final cut to the user

Surface `${WORKDIR}/final.mp4` (and `${WORKDIR}/master.mp3` for
audio-only listen if useful) for review. If the runtime environment can
serve local files directly to the user (e.g. agent-on-host setup),
that's enough. If the runtime is remote-sandboxed, upload first:

```bash
# Upload via gsutil (or whatever the runtime's upload tool is), then register
FINAL_URL=$(gsutil cp "${WORKDIR}/final.mp4" "gs://<staging-bucket>/$(uuidgen).mp4" \
            && echo "https://storage.googleapis.com/<staging-bucket>/<uploaded-name>.mp4")
MASTER_URL=$(gsutil cp "${WORKDIR}/master.mp3" "gs://<staging-bucket>/$(uuidgen).mp3" \
             && echo "https://storage.googleapis.com/<staging-bucket>/<uploaded-name>.mp3")

dl asset register \
  --group-id="audio-design-$(date +%Y%m%d-%H%M%S)" \
  --name="final-cut" --asset-type="Video" --url="$FINAL_URL"
```

(Upload mechanics vary by deployment. The skill is agnostic; just ensure
`final.mp4` is reachable by the user before asking for ack.)

Ask the user:

> "Here's the final cut: `<URL or path>`. Listen / watch and let me know — OK to ship, or do you want to revise?"

### 2. Branch on user response

- **OK** → go to Step 3 (write + promote terminal).
- **Small revision** (delete 1-2 cues / change a cue's duration / swap one
  asset): the user says e.g. "remove cue 5, swap cue 3's BGM for something
  sadder."
  - Re-enter Phase 03 to update `audio_cues_plan` (patch-json only the
    affected items; bump version; verify).
  - In Phase 04, re-search ONLY for cues whose `description` changed. For
    untouched cues, **reuse** the existing manifest entry's `asset_url`
    and `real_duration_sec` (read from `audio_retrieval_manifest`).
  - In Phase 05, re-prepare ONLY the changed cues' mp3 (Phase 4a). Then
    re-run the master mix (Phase 05.4) using the updated set of
    `prepared_path` values; produce a new `master.mp3` overwriting the
    previous one.
  - Phase 06 re-mux → new `final.mp4`.
  - Return to Step 1 of this phase with the revised output. Loop until
    user OKs.
- **Large revision** ("wrong vibe, redesign everything"): go all the way
  back to Phase 03 Step 3 and design a fresh cue list; rerun 04 / 05 / 06.

### 3. Write & promote `audio_design_result`

The artifact's `data` is a flat domain object per
`schemas/audio_design_result.schema.json`. The frontend renders `video_url`
(.mp4) as the auto video player, `quality_tier` as a badge chip, and the
other fields as metadata. Mapping:

| Source field | data field |
| --- | --- |
| `FINAL_URL` | `video_url` |
| `MASTER_URL` | `master_audio_url` |
| `total_duration_sec` from `audio_design_input` | `duration` |
| "Sound-designed cut" (or user-given title) | `title` |
| `"<cue counts> · <quality_tier>"` | `description` |
| ok / degraded | `quality_tier` |
| `{AMB: N, BGM: N, SFX: N, STINGER: N}` | `cue_counts` |
| dropped cue ids | `failed_cues` |
| per-cue mix corrections | `cue_corrections` |
| `dl_transcribe` or upstream artifact ref | `transcript_source` |

```bash
cat <<'EOF' | dl artifact write \
  --slot=audio_design_result \
  --content-type=application/json \
  --contract="$ARTIFACT_CONTRACT_PATH" \
  --content-file=-
{
  "title": "Sound-designed cut",
  "description": "AMB×3 BGM×2 SFX×5 STINGER×1 · ok",
  "video_url": "<FINAL_URL>",
  "master_audio_url": "<MASTER_URL>",
  "duration": <total_duration_sec>,
  "quality_tier": "ok",
  "cue_counts": { "AMB": 3, "BGM": 2, "SFX": 5, "STINGER": 1 },
  "failed_cues": [],
  "cue_corrections": [],
  "transcript_source": "dl_transcribe"
}
EOF

dl artifact finalize \
  --slot=audio_design_result \
  --mode=verify_and_promote \
  --contract="$ARTIFACT_CONTRACT_PATH"
```

`verify_and_promote` is the only canonical promotion in this skill —
matches the artifact contract's `verification.mode` for this slot and
satisfies the completion predicate `slot_promoted(audio_design_result)`.

### 4. Handoff

The skill is complete. Subsequent steps (publish, transcode to other
codecs, distribute) belong to outer orchestration. The agent reports the
terminal artifact URL / slot reference back to the user.

## Output Slot

- `audio_design_result` (promoted, terminal)

## Hard Rules

- **Do NOT promote `audio_design_result` unless the user has explicitly OK'd the final cut.** The promotion gate is human approval, not automatic verification.
- **Do NOT promote if `${WORKDIR}/final.mp4` does not exist.** That means Phase 06 failed — emit failure metadata and stop instead.
- **Do NOT clean up `${WORKDIR}` from this skill.** The outer runtime decides when to garbage-collect; preserving the workdir keeps debugging tractable if the user reports an issue post-promotion.

## Failure Handling

- User keeps rejecting revisions (5+ rounds): surface a degraded resolution path — offer the current cut with `quality_tier=degraded`. If still rejected, emit `failure_metadata` and stop without promoting.
- Upload to staging bucket fails: retry once. Still failing → keep the artifact with local-path `video_url` (e.g. `file:///${WORKDIR}/final.mp4`); flag the outer runtime that distribution-ready URL is missing.

## End of Skill

After `audio_design_result` is promoted, the workflow is complete. No
further phase to load.
