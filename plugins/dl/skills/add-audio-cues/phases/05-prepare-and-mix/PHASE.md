# Phase 05: Prepare & Mix

## Goal

Convert the in-memory manifest from Phase 04 into a fully mixed `master.mp3` in two ffmpeg-native steps:

- **5a Per-cue prepare** — one `ffmpeg` invocation per retained cue: download the CDN asset, loop / trim to the target duration, write `${WORKDIR}/prepared_<i>.mp3`.
- **5b Master mix** — one `ffmpeg` invocation: take dialogue + all prepared mp3s, apply per-chain `loudnorm + afade + adelay`, ducking via `sidechaincompress`, final `loudnorm + alimiter`, write `${WORKDIR}/master.mp3`.

Then write the `audio_retrieval_manifest` artifact (5.3.1) with `prepared_path` filled and asset metadata exposed so the user can audition any cue's chosen asset.

## Required Inputs

- In-memory `manifest`, `failed_cues`, `bgm_stops` from Phase 04
- `audio_design_input` (for `total_duration_sec`)
- `audio_cues_plan` (verified)
- `WORKDIR` (created in SKILL.md bootstrap)
- `ARTIFACT_CONTRACT_PATH`

## Required Slot / Schema Loads

- `schemas/audio_retrieval_manifest.schema.json` — for the 5.3.1 write
- `templates/audio_retrieval_manifest.minimum.json` — payload skeleton

## Required Companion Resources (read explicitly)

- `references/ffmpeg_install.md` — install verification + why native (not `dl ffmpeg`)
- `references/ffmpeg_loudness_targets.md` — LUFS / fade / ducking numbers used in 5b
- `references/ffmpeg_master_template.md` — full 5b filter graph + command template

---

## 5.1 Verify ffmpeg toolchain (run once at phase entry)

```bash
command -v ffmpeg && command -v ffprobe || { echo "ffmpeg/ffprobe missing" >&2; exit 1; }
EXPECTED=5
GOT=$(ffmpeg -filters 2>/dev/null | grep -E "^\s+[A-Z\.]+\s+(loudnorm|sidechaincompress|alimiter|aloop|adelay)\b" | wc -l | tr -d ' ')
[ "$GOT" -ge "$EXPECTED" ] || { echo "ffmpeg missing required filters ($GOT/$EXPECTED)" >&2; exit 1; }
```

If this fails, stop and surface `references/ffmpeg_install.md` to the
user. Do NOT proceed.

## 5.2 BGMSTOP folding (before 5a)

For every AMB / BGM cue in the manifest, compute:

```
target_duration = min(cue.target_duration, next_bgmstop_after_cue.start_time - cue.start_time)
```

If no BGMSTOP exists after the cue, `target_duration = cue.target_duration`.

Write the resulting `target_duration` onto each manifest entry. SFX /
STINGER keep `target_duration` unchanged. The `bgm_stops[]` list itself is
discarded after this — BGMSTOP cues never enter ffmpeg.

## 5.3 Per-cue ffmpeg prepare (Phase 4a) — N invocations

For each retained cue, run one ffmpeg command. Use the appropriate template
based on category.

### AMB / BGM — short asset loops, long asset trims

```bash
ffmpeg -y \
  -stream_loop -1 -i "<audio_url>" \
  -t <target_duration> \
  -c:a libmp3lame -q:a 2 -ar 48000 -ac 1 \
  "${WORKDIR}/prepared_<cue_number>.mp3"
```

`-stream_loop -1` is an input-side option (demuxer-level loop, doesn't decode the whole asset repeatedly). `-t <target_duration>` truncates inside the first loop iteration. If the asset is already ≥ target, the first pass just truncates — same command handles both cases.

### SFX / STINGER — no loop, optionally truncated

```bash
ffmpeg -y \
  -i "<audio_url>" \
  -t <min(actual_duration, target_duration)> \
  -c:a libmp3lame -q:a 2 -ar 48000 -ac 1 \
  "${WORKDIR}/prepared_<cue_number>.mp3"
```

Don't loop these — looped SFX become "click-click-click" comically. Phase 04
should have picked an asset with `actual_duration ≥ target_duration`; if it
couldn't, accept the shorter output and continue.

### Concurrency

Per-cue invocations are independent. If the runtime supports parallel tool
calls, fan out (e.g. via `xargs -P 4 -I {} bash -c '{}'`). Each command
opens its own HTTPS download for the asset URL.

### Sanity check (after each cue completes)

```bash
ACTUAL=$(ffprobe -v quiet -print_format json -show_format "${WORKDIR}/prepared_<cue_number>.mp3" | jq -r '.format.duration')
DELTA=$(awk "BEGIN{print ($ACTUAL - $TARGET)}")
# |delta| < 0.1s is fine; otherwise retry once, then drop the cue.
```

Update the in-memory manifest: set `prepared_path` to
`${WORKDIR}/prepared_<cue_number>.mp3`. If sanity check fails twice, push
the cue into `failed_cues[]` and remove it from the manifest.

## 5.3.1 Write `audio_retrieval_manifest` (after all 5a finishes)

The artifact's `data` is `{ cues: [...] }` per
`schemas/audio_retrieval_manifest.schema.json`. The frontend renders the
array as an auto audio-cue list (`audio_url` triggers the auto player,
`retrieval_status` is auto-recognized as a badge chip). Mapping:

| manifest source | data.cues[] field |
| --- | --- |
| cue sequence number (aligns with plan) | `cue_number` |
| cue type | `category` |
| description / retrieval query | `title` |
| asset CDN URL | `audio_url` |
| original start | `start_time` |
| target / actual duration | `target_duration` / `actual_duration` |
| asset id / retrieval score | `asset_id` / `retrieval_score` |
| Phase 5a outcome | `retrieval_status` (`prepared` / `fallback` / `failed`) |
| local prepared file | `prepared_path` |

```bash
cat <<'EOF' | dl artifact write \
  --slot=audio_retrieval_manifest \
  --content-type=application/json \
  --contract="$ARTIFACT_CONTRACT_PATH" \
  --content-file=-
{
  "cues": [
    {
      "cue_number": 1,
      "category": "AMB",
      "title": "rainy city street at night with distant traffic",
      "audio_url": "https://cdn.example.com/amb/ad042_rain_city.mp3",
      "start_time": 3.2,
      "target_duration": 30,
      "actual_duration": 18.4,
      "asset_id": "ad042",
      "retrieval_score": 0.82,
      "retrieval_status": "prepared",
      "prepared_path": "${WORKDIR}/prepared_0.mp3"
    }
  ]
}
EOF

dl artifact finalize \
  --slot=audio_retrieval_manifest \
  --mode=verify \
  --contract="$ARTIFACT_CONTRACT_PATH"
```

Note: dropped cues from `failed_cues[]` do NOT appear in `cues[]` of this
artifact (the manifest lists only what was successfully prepared). They are
recorded in Phase 07's `audio_design_result.failed_cues[]` for audit.

## 5.4 Master mix (Phase 4b) — single ffmpeg invocation

Read `references/ffmpeg_master_template.md` for the full filter graph and
command template. The agent constructs the final command at runtime by:

1. Counting `K_amb`, `K_bgm`, `K_sfx`, `K_stg` from the manifest.
2. Deciding `asplit` size (1 / 2 / 3 depending on K_amb / K_bgm).
3. Emitting one chain per cue with substituted LUFS / fade / `adelay=<ms>|<ms>` values (where `ms = round(start_time * 1000)`).
4. Wiring the per-chain outputs through `amix → apad → loudnorm → alimiter → out`.
5. Mapping `[out]` to the libmp3lame encoder pointing at `${WORKDIR}/master.mp3`.

LUFS / fade / sidechain numbers are fixed (see
`references/ffmpeg_loudness_targets.md`). Per-cue start times come from
the manifest. `total_duration_sec` for `apad=whole_dur=...` comes from
`audio_design_input`.

Run the command. On success, `${WORKDIR}/master.mp3` exists.

### Heavy-list fallback (>15 cues, or ffmpeg timeout)

Split into two passes per `references/ffmpeg_master_template.md`
§"Heavy-list fallback":

1. dialogue + AMB + BGM → `${WORKDIR}/partial.mp3` (no final loudnorm/alimiter)
2. `partial.mp3` + SFX + STINGER → `${WORKDIR}/master.mp3` (with final pass)

### Sidechain artifact fallback (audible pumping)

Per `references/ffmpeg_master_template.md` §"Sidechain artifact fallback":
replace each sidechain line with a static volume scale (`volume=0.4` for
AMB, `volume=0.3` for BGM), drop the `asplit` outputs, mark
`quality_tier=degraded`.

## Output

- `audio_retrieval_manifest` (verified)
- `${WORKDIR}/master.mp3` exists and `ffprobe` reports duration ≈ `total_duration_sec`

## Failure Handling

- Single 4a cue retries 1×; on second fail, drop to `failed_cues[]` and continue.
- 4b filter graph error: read ffmpeg stderr's referenced label, remove that chain from the command, retry.
- 4b timeout: split into two passes per fallback above.
- Bed produces audible pumping in user audition: switch to static volume fallback per `ffmpeg_master_template.md`.

## Next Phase Entry

After both `audio_retrieval_manifest` is verified and `${WORKDIR}/master.mp3` exists, load:

    phases/06-attach-to-video/PHASE.md
