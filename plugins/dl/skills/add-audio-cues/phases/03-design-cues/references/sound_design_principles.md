# Sound Design Principles — Agent Self-Driven Methodology

> Reasoning methodology only. The PHASE.md owns command authority.

This is the rulebook the agent follows when acting as sound designer in Phase 03. The agent reads `transcript.segments[]` + `audio_design_input.narrative_context` and produces an `audio_cues` array. The rules below are non-negotiable and validated by §3.3 self-check.

---

## INSTRUCTIONS — The 5 cue types

- **AMB** (ambience) — Environmental sounds that establish atmosphere (rain, café murmur, wind, traffic, room tone).
- **BGM** (background music) — Musical scores that enhance mood (piano, orchestral, electronic).
- **SFX** (sound effects) — Specific sounds tied to actions or events (glass breaking, footsteps, door slam, keystroke).
- **STINGER** (stingers) — Short musical accents for dramatic moments (reveal hit, twist, emotional peak).
- **BGMSTOP** — Marker to stop the currently sounding bed (AMB or BGM). No duration needed.

---

## GUIDELINES — 7 production rules (all must hold)

1. **AMB placement**: Place AMB at scene transitions or location changes; AMB usually 10–60s. Use it whenever the scene needs ground-truth atmosphere (you can hear where you are).

2. **AMB and BGM share a SINGLE "bed" track** — only ONE of them may be active at any given moment. Use AMB for environmental beds (rain, café, wind); use BGM for emotional / musical beds (scoring). Before switching from one to the other, the previous bed must end first — either by its own `duration_sec` finishing exactly at the switch point, or by emitting a BGMSTOP cue at that point. **Do NOT emit two beds whose `[start, start + duration_sec]` intervals overlap.**

3. **SFX scope**: SFX must be specific and tied to a visible / mentioned action; ≤ 2s. SFX may freely overlap with the bed and with each other.

4. **STINGER scope**: STINGER for reveals, twists, or emotional peaks; ≤ 2s. STINGER may freely overlap with the bed. Use sparingly — typically 0–3 per minute of content.

5. **BGMSTOP semantics**: BGMSTOP stops the active bed (AMB or BGM, whichever is currently sounding) — use it before dramatic pauses, tonal shifts, or when you need silence under dialogue. The "previous bed must end" rule from #2 can be satisfied either by exact duration OR by a BGMSTOP at the switch point.

6. **Timing precision**: Timestamps are floats in seconds, precision to 0.1s is sufficient. All cues must satisfy `start + duration_sec ≤ total_duration_sec`.

7. **Description style**: Descriptions must be 5–15 words and describe **the sound itself**, not the dramatic context. The description is fed verbatim to `dl knowledge search --query=` in Phase 04, so retrieval-friendly diction matters:

   - ✅ `"glass breaking shatter on concrete floor"`
   - ✅ `"melancholic slow piano for flashback scene"`
   - ✅ `"rainy city street at night with distant traffic"`
   - ❌ `"the moment she drops the cup"` (describes story, not sound)
   - ❌ `"BGM here"` (too generic)
   - ❌ `"sound of glass"` (too vague — what kind? what surface? what distance?)

---

## Density heuristics (not strict, just a sanity floor)

For typical short-form video (1–3 minutes):

- AMB: 1–3 beds total (one per location / mood block)
- BGM: 1–2 beds total (cover the most emotionally charged segments)
- SFX: 3–10 (vary with action density)
- STINGER: 0–3 (only when a real twist / reveal warrants it)
- BGMSTOP: as many as needed by rule #2 (typically 0–2)

If your cue count for a 90-second clip exceeds 20, you're probably over-designing. Re-read the transcript and prune.

---

## Input fence

The agent only consumes:

- `transcript.segments[]` — array of `{start: float, end: float, text: string}`
- `audio_design_input.total_duration_sec` — float seconds
- `audio_design_input.narrative_context` — optional string (may be empty)

The agent must NOT browse outside these. No web search, no extra LLM calls. The design is fully a function of the transcript + narrative + 7 rules above.

---

## Output shape (what to produce)

A JSON object with one key `audio_cues` whose value is an array of cue objects:

```json
{
  "audio_cues": [
    { "start": 3.2,   "type": "AMB",     "duration_sec": 30,   "description": "..." },
    { "start": 33.0,  "type": "BGMSTOP" },
    { "start": 33.5,  "type": "BGM",     "duration_sec": 45,   "description": "..." },
    { "start": 12.1,  "type": "SFX",     "duration_sec": 1.2,  "description": "..." },
    { "start": 78.0,  "type": "STINGER", "duration_sec": 1.5,  "description": "..." }
  ]
}
```

Order by `start` ascending. Floats in seconds. `BGMSTOP` omits `duration_sec` and `description`.

---

## Self-check (run before writing the artifact)

After producing the array, the agent runs 4 internal checks:

1. **Structure**: array shape, every cue has required fields, type enum legal.
2. **Bounds**: `start + duration_sec ≤ total_duration_sec` for every non-BGMSTOP cue. Truncate offenders to fit, record in `cue_corrections[]`.
3. **Bed non-overlap** (Rule #2): sort AMB ∪ BGM by `start`; for adjacent pairs with `prev_end > next_start` and no BGMSTOP between them, truncate `prev.duration_sec` to `next.start - prev.start`. Record in `cue_corrections[]`.
4. **Description sound-vs-story**: every non-BGMSTOP cue's `description` must read like a retrieval query, not story narration. Rewrite offenders in place.

Failed self-check (>50% cues struct-invalid after one repair attempt, or >50% descriptions story-style) → degrade to `{"start": 0.0, "type": "BGM", "duration_sec": <total_duration_sec>, "description": "ambient cinematic underscore"}` and mark `quality_tier=degraded` for handoff to PHASE.md to record.

---

## Empty-transcript degenerate path

If `transcript.segments == []` (music / noise input from Phase 02):

- Skip per-segment cue derivation.
- Lay one BGM full-length: `{"start": 0.0, "type": "BGM", "duration_sec": <total>, "description": "<derive from narrative_context, or 'ambient cinematic underscore' as last resort>"}`.
- No AMB, no SFX, no STINGER unless `narrative_context` explicitly hints at action sounds.
- Mark `quality_tier=degraded` to signal limited design.
