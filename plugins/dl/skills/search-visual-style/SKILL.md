---
name: search-visual-style
description: "Search the visual_style knowledge base during visual_config selection for cinematic or animation style references with prompts and thumbnails. Use the CLI form `dl knowledge search --domain=visual_style --query=\"...\" --k=5` and adjust `k` as needed."
allowed-tools: Bash(dl knowledge search:*)
metadata:
  ilands:
    applicable-to: [full, creation]
    priority: 1.5
    kind: atomic_skill
---
> **Setup (BYOA):** this skill drives the `dl` CLI, which proxies calls to iLands and bills your own iLands wallet — no API keys touch your machine. If `dl` is not on your PATH, run `npm i -g @pawlogic/dl && dl login` (or `npx -y @pawlogic/dl`). One login serves both the `dl` and `ilands` command sets. See https://ilands.ai/byoa .


<!-- cli-audit: 4118bdac3ca2af22 -->

# Search Visual Styles

## Commands

This skill involves:

- `dl knowledge search` — search the `visual_style` knowledge base for film /
  animation style references (prompt + thumbnail)

Before calling, you **must** run `dl knowledge search --help` once to confirm
current flags / filter-passing format / domain enums; do not write parameters
from memory or stale docs.

## Domain

| Domain | What it contains | When to use | Example query |
|--------|-----------------|-------------|---------------|
| `visual_style` | 116 cinematic/animation visual styles with prompts | Choosing a visual language for any video or image content | `"dark moody cinematic neo-noir"` |

## Methodology

1. Compose a descriptive query about the desired visual characteristics — mood, lighting, color palette, camera style, art direction.
2. **If you know the general style family, narrow with the `type` filter — not just the query text**. See Filters section for the 5 allowed values. The KB mixes families across rows, so filter-first is materially better than encoding `realistic` / `2D animation` etc. in the query alone.
3. If unsure of family, ask the user before searching ("realistic live-action vs stylized 2D/3D animation vs illustration vs experimental?"). Use the answer to set the `type` filter.
4. Results include `prompt` (general image-gen prompt), `prompt_gpt` (gpt-image-2 specific variant; other services use `prompt`), and `img_url` (reference thumbnail). Surface all three back to the caller — `img_url` is the per-candidate thumbnail to render in option-with-image dialogs.

## Filters (narrow by `type`)

When you already know the general style family **before** querying — or when
plain query results are off-target — narrow with the `type` filter. The
`visual_style` domain accepts exactly one filter key: `type` (no other keys
are honored — anything else in the JSON is silently dropped by the backend).
The exact way to pass the filter to `dl knowledge search` (`--filters-file`
etc.) is authoritative in `--help`.

**Known `type` values (5)**:

1. `Realistic/Live` — realistic film / live-action drama
2. `3D Render` — 3D rendering (clay, CGI, Unreal-style, etc.)
3. `Illustration` — flat / illustration / 2D stills
4. `Animation` — animation umbrella (2D animation / motion graphics / stop-motion etc.)
5. `Experimental` — experimental / abstract / glitch / non-conventional visuals

Filter values are **case-sensitive** (`Realistic/Live` is not equal to `realistic/live`).

## Constraints

- Keep queries concise but descriptive (5-15 words).
- Use `--k` to control result count (default 10, effective max 20 — `dl` silently clamps).
- Scores above 0.7 indicate strong matches; 0.5-0.7 are reasonable.
- Filter values are **case-sensitive** (`Realistic/Live` is not equal to `realistic/live`).
- If the first query hits but with low scores, prefer **rewording the query**
  rather than immediately reaching for the filter; the query itself better
  reflects user intent.
