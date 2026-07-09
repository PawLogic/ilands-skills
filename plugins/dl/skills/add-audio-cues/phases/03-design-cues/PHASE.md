# Phase 03: Design Cues — Agent Sound Designer + User Checkpoint

## Goal

Agent acts as sound designer: reads `transcript.segments[]` + `audio_design_input.narrative_context`, produces an ordered AMB / BGM / SFX / STINGER / BGMSTOP cue list, runs 4 self-checks, writes `audio_cues_plan` artifact, then **must wait for explicit user approval** before any downstream phase touches the cue list.

This is the only strong user checkpoint in the entire skill.

## Required Inputs

- `audio_design_input` (verified, Phase 01)
- `transcript` (verified, Phase 02)
- `ARTIFACT_CONTRACT_PATH`

## Required Slot / Schema Loads

Before writing the artifact, load:

- `schemas/audio_cues_plan.schema.json` — derived schema for this slot (list + card + landscape, is_segment=false)
- `templates/audio_cues_plan.minimum.json` — minimum payload skeleton

## Required Companion Resources

- `references/sound_design_principles.md` — the INSTRUCTIONS + 7 GUIDELINES + self-check rules. **Read this file explicitly before producing the cue list.** It is the agent's design rulebook.

## Steps

### 1. Read inputs

```bash
INPUT=$(dl artifact read --slot=audio_design_input)
TRANSCRIPT=$(dl artifact read --slot=transcript)
TOTAL_DURATION=$(echo "$INPUT" | jq -r '.total_duration_sec')
NARRATIVE=$(echo "$INPUT" | jq -r '.narrative_context // ""')
SEGMENTS=$(echo "$TRANSCRIPT" | jq '.segments')
```

### 2. Read the design rulebook

```text
read phases/03-design-cues/references/sound_design_principles.md
```

The agent treats this file as the active prompt for itself in this phase. The
file contains: 5 cue type definitions, 7 production guidelines (including
the bed non-overlap rule), density heuristics, output shape, and the 4-step
self-check.

### 3. Design the cue list

Using `SEGMENTS` and `NARRATIVE` and `TOTAL_DURATION`, the agent generates
the JSON object:

```json
{
  "audio_cues": [
    { "start": <float>, "type": "AMB|BGM|SFX|STINGER|BGMSTOP",
      "duration_sec": <float, omit for BGMSTOP>,
      "description": "<5-15 words sound description, omit for BGMSTOP>" }
  ]
}
```

Sorted by `start` ascending.

### 4. Run the 4 self-checks (see references/sound_design_principles.md §Self-check)

Track every auto-correction in a `cue_corrections[]` array (kept in working
memory for now, surfaced to the user in Step 6).

If self-check shows the design is severely flawed (>50% structurally bad
after one repair) → degrade to single full-duration BGM bed; record
`quality_tier=degraded` to surface in Step 6.

### 5. Map cues to the artifact schema shape

The artifact's `data` is pure domain — a `{ cues: [...] }` object. Each cue
carries the retrieval query (`title`), category badge, timing for the auto
timeline view, and any self-check marker. Mapping:

| Cue source field | data.cues[] field | Notes |
| --- | --- | --- |
| Sequential number | `cue_number` | 1, 2, 3, ... — drives auto sequence display |
| Cue type | `category` | One of AMB / BGM / SFX / STINGER / BGMSTOP — auto badge chip |
| `description` (or "BGMSTOP marker" for stops) | `title` | Retrieval query text — consumed verbatim by Phase 04 |
| Original `start` | `start_time` | Seconds — combined with `duration` enables timeline view |
| Original `duration_sec` | `duration` | Seconds — omit for one-shot STINGER/BGMSTOP |
| (optional) longer mix intent | `description` | Optional — body text |
| Scene grouping label | `scene` | Optional |
| Self-check correction marker | `correction` | e.g. "truncated", "bed-conflict-fixed" |

### 6. Write `audio_cues_plan` as DRAFT and ack to user

```bash
cat <<'EOF' | dl artifact write \
  --slot=audio_cues_plan \
  --content-type=application/json \
  --contract="$ARTIFACT_CONTRACT_PATH" \
  --content-file=-
{
  "cues": [
    {
      "cue_number": 1,
      "category": "AMB",
      "title": "rainy city street at night with distant traffic",
      "start_time": 3.2,
      "duration": 30
    }
  ]
}
EOF
```

**Do NOT finalize yet.** Surface to the user a structured summary so they
can decide:

- Total cue count by type: e.g. `AMB×3, BGM×2, SFX×5, STINGER×1, BGMSTOP×2`.
- All BGM and STINGER lines explicitly (timestamp + description) — these
  are the highest-impact cues and most likely to be revised.
- Any items from `cue_corrections[]` (truncated for bounds, bed-overlap
  fixed, description rewritten for sound-not-story).
- `quality_tier` if degraded.

Ask: "这个音效设计方案 OK 吗？要调整哪些 cue？还是直接进检索（Phase 04）？"

### 7. Iterate on user feedback (loop)

- User says "OK" → go to Step 8.
- User says "改第 N 条" / "删掉 AMB 的 X" / "BGM 换更悲伤的" → rewrite the
  cues internally, then re-`patch-json` the slot (or rewrite via `write`
  if the structure changes a lot), bump `version`, and re-finalize as
  draft. Loop back to Step 6 user ack.
- User says "全换" → start over from Step 3.

Patching example (single field edit — paths are JSONPath-lite, not JSON Pointer; do NOT pass `--contract` to `patch-json`):

```bash
cat <<'EOF' | dl artifact patch-json --slot=audio_cues_plan --operations-file=-
[
  {"op":"set","path":"cues[2].duration","value":20},
  {"op":"set","path":"cues[2].correction","value":"shortened on user request"}
]
EOF

dl artifact finalize \
  --slot=audio_cues_plan \
  --mode=verify \
  --contract="$ARTIFACT_CONTRACT_PATH"
```

### 8. User approved — finalize verified

```bash
dl artifact finalize \
  --slot=audio_cues_plan \
  --mode=verify \
  --contract="$ARTIFACT_CONTRACT_PATH"
```

(Verified only — this slot is not promoted. Only the terminal
`audio_design_result` gets promoted in Phase 07.)

## Output Slot

- `audio_cues_plan` (verified, status=verified, content reflects approved cues)

## Hard Rule

**The user MUST approve the plan before Phase 04 starts.** Phases 04 and 05
together are the most expensive (knowledge search calls + per-cue ffmpeg
prep + master mix); a bad cue list wastes all of that. There is no
shortcut around this checkpoint.

## Failure Handling

- LLM output not parseable JSON: retry the design once with stricter
  instruction "Return ONLY raw JSON, no markdown."; still failing → degrade
  to single BGM bed, mark `quality_tier=degraded`.
- User rejects 3+ revisions in a row: surface a degraded plan
  (`quality_tier=degraded`) with the agent's best single-BGM fallback;
  user can accept that or abort the run.

## Next Phase Entry

After `audio_cues_plan` is verified post-user-approval, load:

    phases/04-retrieve/PHASE.md
