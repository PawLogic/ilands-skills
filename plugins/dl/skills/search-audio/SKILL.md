---
name: search-audio
description: "Search audio knowledge bases — sound effects (SFX), stingers, background music (BGM), ambient soundscapes, or all audio combined."
allowed-tools: Bash(dl knowledge search:*)
metadata:
  ilands:
    applicable-to: [full, creation]
    priority: 1.5
    kind: atomic_skill
---
> **Setup (BYOA):** this skill drives the `dl` CLI, which proxies calls to iLands and bills your own iLands wallet — no API keys touch your machine. If `dl` is not on your PATH, run `npm i -g @pawlogic/dl && dl login` (or `npx -y @pawlogic/dl`). One login serves both the `dl` and `ilands` command sets. See https://ilands.ai/byoa .


<!-- cli-audit: 2427e42d1980628c -->

# Search Audio Assets

Vector-search the SFX / Stinger / BGM / Ambient / audio_any knowledge bases by
domain and pull `asset_id` / `filename` for downstream asset assembly. This
skill covers "how to pick a domain / how to write the query / how to combine
filters" — **flag names / parameter ranges / output schema are authoritative
in `dl knowledge search --help`**.

## Commands

- `dl knowledge search` — synchronous search; the response carries `results[]`
  directly. **Do not** follow it with `dl poll`.

Before first use of any voice / audio domain, run `dl knowledge search --help`
to confirm current legal flags (`--domain` / `--query` / `--k` /
`--filters-file` etc.) and schema. Do not rely on memory.

## Domains

| Domain | What it contains | When to use | Example query |
|--------|-----------------|-------------|---------------|
| `sfx` | 262 sound effects with action, material, distance | Adding specific physical sounds to scenes | `"glass breaking shatter on concrete floor"` |
| `stinger` | 105 transition/accent sounds with emotion, mood | Punctuating scene transitions or dramatic moments | `"horror reveal dramatic hit with reverb"` |
| `bgm` | 99 background music tracks with emotion, instrument, tempo | Selecting music that matches the mood of a scene | `"melancholic slow piano for flashback scene"` |
| `amb` | 219 ambient soundscapes with space, atmosphere, elements | Building environmental audio for scenes | `"rainy city street at night with distant traffic"` |
| `audio_any` | All audio domains combined | Discovery when unsure which audio type is needed | `"suspenseful dark atmosphere"` |

## Filters

Filter keys supported per domain (the exact JSON shape is in `--help` or
`--print-schema`):

- `sfx`: `distance` (`"near"` / `"mid"` / `"far"`), `loopable` (`true` / `false`)
- `amb`: `loopable` (`true` / `false`)
- `stinger`, `bgm`, `audio_any`: no filters

When no filter is needed, just pass `--query`. To narrow by distance / loopable,
pass a JSON object via `--filters-file` (stdin `-` or absolute path both work).

## Decision Logic

**Pick a domain first, then write the query**:

- You know exactly which audio type (SFX / Stinger / BGM / AMB) → use the
  matching domain directly for highest recall quality
- Unsure of type / exploratory → use `audio_any` to recall across domains and
  see which type matches best
- **Need to land a selection into an artifact**: use a specific domain, not
  `audio_any` (which does not emit an artifact receipt)

**Query style**: 5–15 words with scene / mood / object / material / distance
sensory descriptors. A single "sad music" generally recalls worse than
"melancholic slow piano for flashback scene".

**`--k`**: default 10, effective max 20 (`dl` silently clamps beyond that).
Crank to 20 for scoring / bulk scan; 3–5 for high-confidence single pick.

## Constraints

- Keep queries concise but descriptive (5–15 words)
- `--k` controls returned count (default 10, max 20)
- `audio_any` does not emit an artifact receipt — switch to a specific domain
  when you need to commit a final selection
- The returned `asset_id` / `filename` are the keys downstream creation steps
  use to reference the asset
