---
name: stock-media
description: "Search for, evaluate, and obtain/download existing image or video media assets for b-roll, cutaways, illustrations, references, and image-to-video inputs. Use `dl stock search/download` for licensed stock providers, Baidu `dl search` for Chinese image/video discovery and similar-image source finding, and `browser-use` only as a fallback for selected source pages that need page reading, JavaScript, login state, screenshots, or provenance checks."
allowed-tools: Bash(dl stock search:*), Bash(dl stock download:*), Bash(dl search:*)
metadata:
  ilands:
    applicable-to: [full, creation]
    priority: 1.3
    kind: atomic_skill
---
> **Setup (BYOA):** this skill drives the `dl` CLI, which proxies calls to iLands and bills your own iLands wallet — no API keys touch your machine. If `dl` is not on your PATH, run `npm i -g @pawlogic/dl && dl login` (or `npx -y @pawlogic/dl`). One login serves both the `dl` and `ilands` command sets. See https://ilands.ai/byoa .


# Stock Media

Use this skill to search for and obtain existing image/video assets for b-roll, cutaways, article illustrations, slide visuals, mood references, and image-to-video inputs. The default download path is `/workspace/.stock-media/`.

## Source Strategy

| Source | Best for | Download / license posture |
|---|---|---|
| `dl stock search` | Default path for downloadable stock assets from Pexels, Pixabay, and Openverse | Results include `download_url`, license fields, and attribution metadata; use `dl stock download` directly |
| `dl search --provider=baidu --resource-type=image|video` | **Fallback discovery** for Chinese / China-local / culturally specific material when stock has no recall. ⚠ Baidu hits skew toward **finished content** (bilibili / social-media talking-head explainers, news clips, edited videos; posters / memes / press photos for image) — usable as moodboard reference but rarely as clean B-roll | Treat as candidate discovery, not pre-cleared stock. Gate every candidate through `browser-use` when the hit resolves to a source page (open page → confirm a usable raw asset → extract direct URL); verify rights before download |
| `dl search --provider=baidu-image` | Similar-image / reverse-image source discovery from a reference image | Use for finding visually similar candidates or likely source pages; verify rights and direct media URLs before use |

**Default to `dl stock search` for B-roll, regardless of language** — stock libraries return raw, clean assets (no talking heads, no edited-work overlays). Exhaust stock recall first (translate the query to English, try `--mode=fanout`, vary keywords) before escalating to Baidu, even for Chinese / culturally specific briefs. Baidu video hits skew toward finished content (bilibili / social-media talking-head explainers, news clips, edited works) — even with a direct `videoUrl`, confirm the clip is raw footage, not an edited work, before downloading. When a Baidu hit resolves to a source page rather than a direct media URL, gate through `browser-use` (open page → locate raw asset → extract direct URL) before `dl stock download`. Baidu finished content is fine as **mood reference**, not as B-roll.

## Do Not Use

- AI image or video generation: use `image-generation` or `video-generation`.
- Social-media URL downloading: use `media-download`.
- Arbitrary web page scraping or login-gated extraction: use `external-research` plus `browser-use`.
- Paid stock sources such as Getty, Adobe Stock, or Storyblocks.

## Primary Workflow

1. Search.
2. Inspect the result JSON and pick a candidate by relevance, dimensions, duration, preview URL, license, and attribution fields.
3. Download only direct media URLs with `dl stock download`.
4. Preserve the selected result object in `--metadata-json` so downstream steps can write credits.

```bash
RESULT=$(dl stock search --query="sunset beach warm color" --type=image --limit=5 | jq '.results[0]')
dl stock download \
  --asset-id="$(jq -r .asset_id <<<"$RESULT")" \
  --url="$(jq -r .download_url <<<"$RESULT")" \
  --metadata-json="$RESULT"
```

## Search Modes

| Mode | Behavior | When to use |
|---|---|---|
| `fallback` (default) | Query providers sequentially in provider order until `limit` results are collected | Most cases. Saves API budget and falls through if a provider fails |
| `fanout` | Query all enabled providers and merge results round-robin for diversity | Rare, specific, or low-recall briefs where one provider is not enough |

```bash
dl stock search --query="rare landscape" --type=image --mode=fanout
dl stock search --query="city traffic" --type=video --duration-min=5 --duration-max=15
dl stock search --query="..." --type=image --providers=pixabay,pexels
```

## Baidu Image / Video Discovery

Baidu discovery is routed through `dl search`, not `dl stock search`.

```bash
dl search --query="上海弄堂 清晨 空镜" --provider=baidu --resource-type=image --k=10
dl search --query="春节街市 人群 空镜 视频" --provider=baidu --resource-type=video --k=10
```

Use Baidu results as candidate source discovery:

- For image results, prefer `imageUrl` as the candidate direct media URL when present.
- For video results, prefer `videoUrl` only if it is a direct playable/downloadable media URL; otherwise treat `url` as a source page and hand off to the appropriate page-reading or media-download workflow.
- Preserve source fields such as `url`, `source`, `publishedAt`, `width`, `height`, `duration`, and `thumbnailUrl` in metadata.
- Do not imply Pexels/Pixabay/Openverse-style license safety for Baidu results.

If you decide a Baidu image URL is usable and direct, download it with a synthetic asset id and full metadata:

```bash
BAIDU=$(dl search --query="北京胡同 雪天 空镜" --provider=baidu --resource-type=image --k=5 | jq '.hits[0]')
dl stock download \
  --asset-id="baidu:hutong-snow-001" \
  --url="$(jq -r '.imageUrl // .url' <<<"$BAIDU")" \
  --metadata-json="$BAIDU"
```

## Similar-Image Search

Use similar-image search when the user provides a reference image, when you need more material with the same subject/composition, or when you need to locate likely source pages.

```bash
dl search --provider=baidu-image --image-file=/workspace/reference.png --k=10
```

For `baidu-image` results:

- Use `imageUrl` for visual inspection or direct download only when it is an actual image URL.
- Use `resultPage`, `url`, and `source` to trace provenance.
- Cross-check with `dl stock search` if the output needs a clearly reusable stock asset.

## `dl stock search`

| Flag | Required | Default | Notes |
|---|---|---|---|
| `--query <q>` | yes | - | Natural-language keywords. English usually works best for Pexels/Pixabay/Openverse |
| `--type <t>` | yes | - | `image` or `video` |
| `--orientation <o>` | no | any | `landscape`, `portrait`, or `square` |
| `--min-width <n>` | no | - | Minimum pixel width |
| `--duration-min <s>` | no | - | Video only |
| `--duration-max <s>` | no | - | Video only |
| `--limit <n>` | no | 10 | 1..30 |
| `--mode <m>` | no | `fallback` | `fallback` or `fanout` |
| `--providers <list>` | no | `pexels,pixabay,openverse` | CSV; order matters in fallback mode |

## `dl stock download`

| Flag | Required | Notes |
|---|---|---|
| `--asset-id <id>` | yes | `<provider>:<native_id>` from stock results, or a stable synthetic id such as `baidu:<slug>` for verified Baidu media |
| `--url <url>` | yes | Direct image/video URL only; not a normal article or search result page |
| `--to <path>` | no | Absolute path under `/workspace/`; defaults to `/workspace/.stock-media/<provider>-<id>.<ext>` |
| `--metadata-json <json>` | no | Pass the selected result object through for credits and auditability |

Files over 200 MB fail. Downloads default to a 60 second timeout.

## Licensing

Every `dl stock search` result includes license and attribution fields. Before rendering final output:

1. Check `attribution_required`.
2. If true, include `attribution_text` or equivalent author + license attribution.
3. For Pexels/Pixabay/CC0 assets, attribution may not be required but credits are still useful.

Baidu search results do not provide stock-style license guarantees. Use them only when rights are acceptable for the project, or when they are merely references rather than final shipped assets.

## Failure Handling

| Signal | Meaning | Action |
|---|---|---|
| `providers_failed` contains 429/503 | A stock provider hit quota or all keys are cooling down | Retry later, change provider order, or use Baidu as a discovery fallback |
| Stock results are generic or off-brief | Low recall in stock APIs | Try `--mode=fanout`, translate/expand the query, then try Baidu for Chinese/context-specific recall |
| Baidu result lacks a direct media URL | Result is a page/source rather than a downloadable asset | Do not pass page URLs to `dl stock download`; use `browser-use` on selected source pages for page reading / JS / screenshot / provenance checks, or choose another result |
| License is unclear | Asset may not be reusable | Prefer Pexels/Pixabay/Openverse or ask the user for acceptable rights constraints |
