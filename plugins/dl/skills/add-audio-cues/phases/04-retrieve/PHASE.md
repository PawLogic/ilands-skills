# Phase 04: Retrieve Library Assets

## Goal

For every cue in `audio_cues_plan` (except BGMSTOP), find the best matching library asset via `dl knowledge search` and probe its real duration with ffprobe. Build an in-memory manifest that Phase 05 will consume and persist.

## Required Inputs

- `audio_cues_plan` (verified, post-user-approval, Phase 03)
- `audio_design_input` (for `total_duration_sec`)
- `ARTIFACT_CONTRACT_PATH`

## Required Slot / Schema Loads

No artifact write happens in this phase (manifest stays in working memory
until Phase 05.3.1). No new schema to load here.

## Steps

### 1. Read the verified cue plan

```bash
PLAN=$(dl artifact read --slot=audio_cues_plan)
```

Extract the cue list from `data.cues[]`. Each item has `cue_number`,
`category`, `title` (the retrieval query), `start_time`, and optional
`duration` / `description` / `scene` / `correction`.

### 2. Filter out BGMSTOP

BGMSTOP cues are timeline-control markers, not playable assets. Skip them
in retrieval; they will be re-applied in Phase 05.2 as "bed early-stop"
deadlines.

### 3. Map cue category → knowledge domain + filter

| cue.category | --domain | recommended filter |
| --- | --- | --- |
| AMB | `amb` | `{"loopable": true}` |
| BGM | `bgm` | (none) |
| SFX | `sfx` | `{"distance":"near"}` for hand-of-camera actions; `"mid"` / `"far"` for distant |
| STINGER | `stinger` | (none) |

### 4. Run `dl knowledge search` per cue

For each cue, send the cue's `title` as `--query` (it's the retrieval-friendly text). Examples:

```bash
# AMB with loopable filter
cat <<'EOF' | dl knowledge search \
  --domain=amb \
  --query="rainy city street at night with distant traffic" \
  --filters-file=- \
  --k=5
{"loopable": true}
EOF

# SFX with distance filter
cat <<'EOF' | dl knowledge search \
  --domain=sfx \
  --query="glass breaking shatter on concrete floor" \
  --filters-file=- \
  --k=5
{"distance": "near"}
EOF

# BGM / STINGER without filter
dl knowledge search --domain=bgm --query="melancholic slow piano for flashback scene" --k=5
dl knowledge search --domain=stinger --query="horror reveal dramatic hit with reverb" --k=3
```

The response returns `data[]` with `asset_id`, `filename`, CDN URL, and
`metadata.score` per hit.

### 5. Pick one asset per cue

Default: top-1 by score. Heuristic adjustments:

- For SFX / STINGER: if top-1's library `metadata.duration` < cue's
  `duration`, prefer the next hit that's ≥ cue duration (avoid the
  "real shorter than target" problem in Phase 05.3).
- For AMB / BGM: loopable assets ≥ 10s tolerate any length (loop in 5.3).
  Just pick top-1.
- Empty `data[]`: try the `audio_any` domain once as a fallback. Still
  empty → drop this cue (record in `failed_cues[]`); don't substitute
  another cue type. AMB missing → leave silence at that spot.
  SFX / STINGER missing → drop the cue entirely.

### 6. Probe real duration

`metadata.duration` from knowledge search is not always accurate; Phase 05.3
needs precise numbers. For each picked asset:

```bash
ffprobe -v quiet -print_format json -show_format "<asset_url>"
```

Read `format.duration`. Store as `real_duration_sec` (float).

### 7. Build the working-memory manifest

For each retained cue, build an entry (working memory shape — mirrors the
new `audio_retrieval_manifest` schema so Phase 05.3.1 can write it directly):

```json
{
  "cue_number": 1,
  "category": "AMB",
  "title": "rainy city street at night with distant traffic",
  "start_time": 3.2,
  "target_duration": 30,
  "actual_duration": 18.4,
  "audio_url": "https://cdn.example.com/amb/ad042_rain_city.mp3",
  "asset_id": "ad042",
  "retrieval_score": 0.82,
  "retrieval_status": null,
  "prepared_path": null
}
```

`retrieval_status` and `prepared_path` are filled by Phase 05.3 after
`-stream_loop` / `-t` prepares the per-cue mp3.

Also keep two side lists:

- `failed_cues[]` — cues that retrieved 0 results (after `audio_any` fallback) and were dropped. Each entry: `{cue_number, category, title, reason}`.
- `bgm_stops[]` — original `start_time` of every BGMSTOP cue from the plan. Phase 05.2 uses these to truncate bed durations.

### 8. Do NOT write any artifact yet

`audio_retrieval_manifest` is only written after Phase 05.3 fills
`prepared_path` for every retained cue. Keep all three structures
(`manifest`, `failed_cues`, `bgm_stops`) in working memory and hand them
to Phase 05.

## Output

- In-memory: `manifest` (array), `failed_cues` (array), `bgm_stops` (array of floats)
- No artifact change.

## Failure Handling

- A knowledge domain search returns malformed JSON: retry once; still bad →
  drop the cue.
- `ffprobe` fails on a CDN URL (404, codec): record `real_duration_sec`
  from `metadata.duration` as best-effort, mark `tags: [{"label":"unverified-duration"}]` in the manifest entry, continue.
- More than 50% of cues drop: continue but flag `quality_tier=degraded`
  for Phase 07 to record.

## Next Phase Entry

After the manifest is built, load:

    phases/05-prepare-and-mix/PHASE.md
