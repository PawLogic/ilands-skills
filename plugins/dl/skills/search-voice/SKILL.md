---
name: search-voice
description: "Search TTS voice profiles — MiniMax (Chinese + English) and ElevenLabs (high-quality English) voice profiles for narration, dialogue, or character TTS."
allowed-tools: Bash(dl knowledge search:*)
metadata:
  ilands:
    applicable-to: [full, creation]
    priority: 1.5
    kind: atomic_skill
---
> **Setup (BYOA):** this skill drives the `dl` CLI, which proxies calls to iLands and bills your own iLands wallet — no API keys touch your machine. If `dl` is not on your PATH, run `npm i -g @pawlogic/dl && dl login` (or `npx -y @pawlogic/dl`). One login serves both the `dl` and `ilands` command sets. See https://ilands.ai/byoa .


<!-- cli-audit: 18322c490dd6e16e -->

# Search Voice Profiles

Vector-search MiniMax + ElevenLabs voice profiles via the `voice` domain
to get `voice_id` for downstream TTS generation. This skill covers
**domain knowledge** (provider differences / language codes / filter shape);
**flag names / value ranges / output schema** are authoritative in
`dl knowledge search --help` and `dl knowledge search --print-schema --domain=voice`
— do not work from memory.

## Commands

- `dl knowledge search` — synchronous search, response carries `results[]` directly,
  **do not** follow with `dl poll`

Run `dl knowledge search --help` before first use to see the current legal
flags (`--domain` / `--query` / `--k` / `--filters-file` / `--provider`).

## Domain

| Domain | What it contains | When to use | Example query |
|--------|-----------------|-------------|---------------|
| `voice` | 197 TTS voice profiles: MiniMax (CN+EN) + ElevenLabs (EN, high-quality) | Selecting a voice for narration, dialogue, or character TTS | `"warm deep male narrator for documentary"` |

## Filters

- `language`: Prefix `"CN"` for all Chinese or exact `"CN_Standard"` | `"CN_Canton"` | `"CN_Taiwan"` | `"CN_Special"`. Prefix `"EN"` for all English or exact `"EN_American"` | `"EN_British"` | `"EN_Australia"` | `"EN_Latin"` | `"EN_Special"`.
- `gender`: `"Male"` | `"Female"`
- `vendor`: `"elevenlabs"` | `"minimax"`. You can also use the voice-domain-only
  top-level `--provider` flag; the CLI maps it to `filters.vendor`. Inside
  `--filters-file` write `{"vendor":"..."}`, not `provider`.

## Providers

### MiniMax Voices (101 profiles)

| Language prefix | Accents | Count |
|----------------|---------|-------|
| `CN` | `CN_Standard` (普通话), `CN_Canton` (粤普), `CN_Taiwan` (台普), `CN_Special` | 40 |
| `EN` | `EN_American`, `EN_British`, `EN_Australia`, `EN_Latin`, `EN_Special` | 61 |

Use MiniMax voice IDs with `dl generate-tts` (always detached — result arrives
as `[async-callback]` pushed back to the session; if the next step needs the
audio immediately, use `dl poll --job-ref=<ref>` to fetch).

### ElevenLabs Voices (96 profiles — English only)

| Language | Accents | Count |
|----------|---------|-------|
| `EN` | `EN_American`, `EN_British`, `EN_Canadian` | 96 (42 Male, 54 Female) |

ElevenLabs voices offer higher-quality English TTS with audio tag support
(`[laughing]`, `[whispering]`, `[sad]`, `[excited]`, `[sighing]`) and
multi-voice dialogue synthesis. Use ElevenLabs voice IDs with:

- Single voice: `dl generate-tts --provider=elevenlabs`
- Multi-voice dialogue: `dl generate-tts --provider=elevenlabs-dialogue`

### How to tell providers apart in results

ElevenLabs voice IDs are alphanumeric strings (e.g., `alFofuDn3cOwyoz1i44T`),
while MiniMax voice IDs use descriptive names (e.g., `English_expressive_narrator`).

## Usage Examples

> Pass `language` / `gender` / `vendor` via `--filters-file=<path|->` as a
> JSON object. One-shot filtering can be piped through stdin
> (`--filters-file=-`), or point at a sandbox path. Run
> `dl knowledge search --print-schema --domain=voice` for the full schema.

```bash
# English young cheerful female character
cat <<'EOF' | dl knowledge search --domain=voice \
  --query="sweet cheerful energetic young girl voice" \
  --filters-file=-
{"language":"EN_American","gender":"Female"}
EOF
```

```bash
# ElevenLabs-only via --provider (CLI maps it to filters.vendor)
dl knowledge search --domain=voice \
  --provider=elevenlabs \
  --query="warm deep male narrator for documentary"
```

```bash
# MiniMax Chinese male narrator — --provider + --filters-file combined
cat <<'EOF' | dl knowledge search --domain=voice \
  --provider=minimax \
  --query="温润儒雅的男性旁白" \
  --filters-file=-
{"language":"CN_Standard","gender":"Male"}
EOF
```

## Constraints

- Keep queries concise but descriptive (5-15 words).
- Voice results include `voice_id`, `name`, `gender`, `description`, `age`,
  `language`, `sample_url`, and `similarity` — use `voice_id` in subsequent
  `dl generate-tts` calls.
- `--provider` is only valid with `--domain=voice`; passing it with another
  domain raises a structured CLI error.
