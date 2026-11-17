---
name: image-generation
description: "Generate or edit images via api-layer. Use `dl generate-image-prompt` for prompt-only images and `dl generate-image-ref` for any image grounded in source/reference URLs. Services: banana-pro (general / text, up to 2K), seedream (Asian aesthetic / portraits), seedream-5-lte (next-gen), gpt-image-2 (OpenAI GPT-Image-2, highest text-in-image fidelity and multi-image edit). Use during reference-pack creation or any image-driven workflow when upstream artifacts must preserve the returned URLs in structures such as `reference_list.ref_img_urls` and `selected_url`."
allowed-tools: Bash(dl generate-image-prompt:*) Bash(dl generate-image-ref:*)
metadata:
  ilands:
    applicable-to: [full, creation]
    priority: 3.0
    kind: atomic_skill
---
> **Setup (BYOA):** this skill drives the `dl` CLI, which proxies calls to iLands and bills your own iLands wallet — no API keys touch your machine. If `dl` is not on your PATH, run `npm i -g @pawlogic/dl && dl login` (or `npx -y @pawlogic/dl`). One login serves both the `dl` and `ilands` command sets. See https://ilands.ai/byoa .


# Image Generation

All decision-surface content of this skill (model selection / preflight / policy /
cross-skill composition / async semantics / publish rules) has been **fully
migrated** into the progressive `--help` system of `dl generate-image-prompt`
and `dl generate-image-ref`. This
SKILL.md no longer carries content.

## First-time use → run these two

- `dl generate-image-prompt --help` — prompt-only overview + LEARN MORE entry
- `dl generate-image-ref --help` — reference-required overview + LEARN MORE entry
- `dl generate-image-prompt model -h` — service ranking + decision logic

## All subtopics (drill down on demand)

| Command | What you'll see |
|------|-------|
| `dl generate-image-prompt --help` | Prompt-only top-level overview / WHEN TO USE / full flag list / LEARN MORE entry |
| `dl generate-image-ref --help` | Reference-required top-level overview / WHEN TO USE / full flag list / LEARN MORE entry |
| `dl generate-image-prompt model -h` | Combined ranking of the 5 services + decision logic |
| `dl generate-image-ref model <service>` | Per-service detailed profile including reference-image flags. Use `<service>` as a positional, not `-h <service>` |
| `dl generate-image-prompt preflight -h` / `dl generate-image-ref preflight -h` | Required decisions before calling |
| `dl generate-image-prompt policy -h` / `dl generate-image-ref policy -h` | User-Facing Communication Rule + Production Package Gate |
| `dl generate-image-ref composition -h` | music-video reference-pack / MV segment keyframe / right-side canvas registration boundary |
| `dl generate-image-prompt async -h` / `dl generate-image-ref async -h` | detach-by-default protocol + result shape |
| `dl generate-image-prompt publish -h` / `dl generate-image-ref publish -h` | publish_content text_image field mapping |
| `dl generate-image-prompt examples -h` / `dl generate-image-ref examples -h` | Full example cookbook |
| `dl generate-image-prompt errors -h` / `dl generate-image-ref errors -h` | E_SCHEMA / E_BACKEND triggers + recovery |
