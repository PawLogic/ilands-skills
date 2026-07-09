---
name: external-research
description: "External web research and source discovery with `dl search`: find articles, docs, official pages, and candidate URLs, not downloadable media assets. Use `stock-media` first for image/video asset search and download; use `browser-use` only when selected URLs need page reading, JavaScript rendering, login/cookie state, screenshots, DOM extraction, or when search/stock-media cannot resolve the task."
allowed-tools: Bash(dl search:*)
metadata:
  ilands:
    applicable-to: [full, creation]
    priority: 1.2
    kind: atomic_skill
---
> **Setup (BYOA):** this skill drives the `dl` CLI, which proxies calls to iLands and bills your own iLands wallet — no API keys touch your machine. If `dl` is not on your PATH, run `npm i -g @pawlogic/dl && dl login` (or `npx -y @pawlogic/dl`). One login serves both the `dl` and `ilands` command sets. See https://ilands.ai/byoa .


<!-- cli-audit: d7a7888a4f5f2b03 -->

# External Research

This skill only handles web search and candidate source discovery. It does not open pages, read page bodies, click, log in, handle cookies, wait for JavaScript rendering, take screenshots, or download media assets. Use `stock-media` first for image/video asset search and download. After selecting URLs, use the `browser-use` skill to read a small number of high-value pages when search results alone are not enough.

> **Pi runtime surface:** Search goes through `dl search`. `--provider` is required, and only `baidu` / `baidu-image` / `serper` / `tavily` / `brave` are supported. There is no `auto` provider. Page reading belongs to `browser-use`; do not rely on a web-fetch vendor route that may not be configured.
> Legacy iLands knowledge-graph verbs (`knowledge web`, `knowledge web-read`, `knowledge context-find`, `knowledge context-write`) are not available in Pi and return `NOT_IMPL`. Social / trend data providers (`ensemble_data`, `twitter`) have no Pi equivalent; do not simulate them. **Pexels / Pixabay / Openverse stock media and Baidu image/video asset discovery belong to the `stock-media` skill (`dl stock search` / `dl stock download` / Baidu `dl search`)**, not this skill.

## Provider Selection

| Provider | Best for | Notes |
|----------|----------|------|
| `baidu` | Default broad web search, especially Chinese and fresh web results | Supports `--freshness=pw|pm|py`; advanced filters go through `--params-file=<path>` |
| `baidu-image` | Similar-image / reverse-image source discovery | Requires `--image-file=<jpg|png>` or base64 `image` in `--params-file`; `--query` is not required |
| `serper` | Google-style result quality or country hints | Supports `--country` |
| `brave` | Recency filters for the past day / week / month / year | Supports `--freshness=pd|pw|pm|py` |
| `tavily` | Time windows, domain constraints, research-oriented summaries | Adapter extras go through `--params-file=<path>` |

Pass adapter-specific extras, such as `days` or `include_domains`, only through `--params-file=<path>`. Do not wrap `dl` calls with heredocs or `cat` pipelines. When extras are needed, prepare the JSON file in a separate non-`dl` step, then run one direct `dl search ... --params-file=<path>` command.

### Examples

Default broad search with `baidu`:

```bash
dl search --query="latest llm benchmarks 2026" --provider=baidu --k=10
```

Baidu similar-image search:

```bash
dl search --provider=baidu-image --image-file=/tmp/reference.png --k=10
```

Serper search with a country hint:

```bash
dl search --query="comfyui custom nodes" --provider=serper --country=us --k=8
```

Brave search with a recency filter:

```bash
dl search --query="llama 4 release" --provider=brave --freshness=pw --k=5
```

Tavily domain / time-window search, assuming `/tmp/tavily-params.json` was prepared by an earlier step:

```bash
dl search --query="ai video generation" --provider=tavily --params-file=/tmp/tavily-params.json --k=8
```

## URL Deep Read

This skill does not read page bodies. When deep reading is needed, select at most **3 URLs** per round and hand them to `browser-use` to avoid latency and context bloat.

Prefer filtering out social URLs (`x.com`, `tiktok.com`, `instagram.com`, `threads.net`) and login-walled pages. They often return JavaScript shells, anti-bot pages, or interstitials unless the task explicitly needs those pages themselves.

## Method

1. Start broad by default with `dl search --query=... --provider=baidu --k=...`.
2. If the task starts from an image and needs source discovery, use `dl search --provider=baidu-image --image-file=... --k=...`.
3. If the topic is strongly time-sensitive, use `--provider=brave --freshness=pw` instead, or `pd` / `pm` / `py` as appropriate.
4. If domain or time-window constraints are required, use `--provider=tavily` and pass adapter extras with `--params-file`.
5. Select the most useful results and hand at most 3 URLs to `browser-use` for deep reading only when the selected pages need content extraction, JavaScript rendering, login/cookie state, screenshots, or source/provenance verification.
6. Cite sources in the final answer. If an artifact needs to be written, the parent workflow / composition skill owns that step.

## Output Format

```json
{
  "research_summary": "string -- concise summary of findings",
  "key_findings": ["string -- each major finding"],
  "sources": [
    {"url": "string", "title": "string", "relevance": "string"}
  ],
  "gaps": ["string -- topics that need further research"]
}
```

## Constraints

- `dl search` must explicitly pass `--provider=baidu|baidu-image|serper|tavily|brave`; do not use `auto`.
- Do not assume every adapter accepts the same parameters. Use this document for normal calls, and only use `dl search --print-schema` or `--help` when a real failure is not covered here.
- Adapter-specific extras must go through `--params-file`.
- Select at most 3 URLs per round for follow-up deep reading.
- Do not start a browser for ordinary search and source discovery. Use `browser-use` only for selected URL content reading, DOM extraction, login state, JavaScript rendering, screenshots, and source/provenance verification after `dl search` or `stock-media` is insufficient.
- Output must cite sources.

For real failures not covered by this document, use `dl search --help` for troubleshooting.
