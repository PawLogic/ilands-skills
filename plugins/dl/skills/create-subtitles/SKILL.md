---
name: create-subtitles
version: 0.1.3
description: Create SRT subtitles from a public audio or video URL, optionally burn them into video, and persist a subtitle_result artifact. Supports standard line-based subtitles and word-by-word captions. Default rendering uses local ffprobe / ffmpeg; fall back to dl render-caption when local rendering is unavailable or hosted rendering is requested.
allowed-tools: Read(*) Bash(dl transcribe:*) Bash(dl render-caption:*) Bash(dl ffmpeg:*) Bash(dl script:*) Bash(dl artifact:*) Bash(ffprobe:*) Bash(ffmpeg:*) Bash(mktemp:*) Bash(printf:*) upload_file ask
metadata:
  ilands:
    applicable-to: [full, creation]
    priority: 2.8
    kind: atomic_skill
---
> **Setup (BYOA):** this skill drives the `dl` CLI, which proxies calls to iLands and bills your own iLands wallet — no API keys touch your machine. If `dl` is not on your PATH, run `npm i -g @pawlogic/dl && dl login` (or `npx -y @pawlogic/dl`). One login serves both the `dl` and `ilands` command sets. See https://ilands.ai/byoa .


# Create Subtitles

Create subtitles from a public audio or video URL. The workflow is: transcribe with ASR, generate or normalize SRT, choose a caption style that fits the video, optionally burn captions into the video, then write `subtitle_result`.

Use `dl transcribe` for ASR. Prefer local `ffprobe` / `ffmpeg` for burned captions. Fall back to `dl render-caption` when local ffmpeg is missing, resource-constrained, upload is unavailable, or hosted rendering is explicitly requested.

## Target Language

Use the user's input language as the target language for user-visible subtitle text decisions, artifact notes, warnings that are safe to show the user, and any natural-language delivery summary. Determine the primary language from the user's latest 2-3 messages.

- Do not translate source-media speech unless the user explicitly asks for translation. By default, preserve ASR/user-provided subtitle text in the spoken/source language.
- If the user asks for translated subtitles, record that choice in `notes` and keep timestamps unchanged unless validation requires overlap normalization.
- Artifact JSON keys, schema fields, CLI flags, SRT syntax, timestamps, URLs, and technical enum values remain exactly as specified.
- Caption style labels and natural-language notes should follow the target language when they are user-facing.

## Inputs

- `source_url`: required public audio or video URL. Pass it to ASR as `--audio-url`; the ASR service extracts audio from video.
- `delivery`: optional. Use `burned_video` by default for video inputs; use `srt_only` when only subtitle text is needed.
- `srt_content`: optional existing SRT. If provided, skip ASR but still validate, sort, normalize overlaps, and wrap lines.
- `language`: optional ASR hint. Default `auto`.
- `subtitle_mode`: optional, `standard` or `word_by_word`. If unspecified, infer from the content; English short-form videos, music, ads, and rhythmic spoken-word clips are good cases to ask whether to use word-by-word captions.
- `caption`: optional caption style JSON. Respect fields the user explicitly provides; fill missing fields with the adaptive style script.

## Caption Mode

Use `standard` for ordinary narration, education, interviews, and long-form videos.

Ask whether to use `word_by_word` when the video is English, music-driven, social-first, ad-like, or strongly rhythmic. Word-by-word requires ASR word timings. If no usable word timings are available, fall back to `standard` and record a warning.

## Caption Style

Do not hardcode `font_size_px: 36`. Probe video resolution first, then run `scripts/caption_style.py` to calculate defaults and wrapping limits.

Before rendering, consider the actual video content: visual style, scene brightness, framing, faces, products, UI, CTA areas, platform, and whether the lower third is important. If the right style is not obvious, ask one short style question.

Default style:

- White text, black outline, `noto_sans`, bold.
- Adaptive font size: vertical videos use about `height * 0.022`; landscape uses about `height * 0.026`; clamp to `18-34px`.
- Bottom center by default: vertical `position_value: 0.13`, landscape `position_value: 0.10`.
- If lower-third content, faces, products, UI, buttons, or CTAs would be covered, set `avoid_lower_third: true` or use `position: "top"`.
- Standard subtitles use at most 2 lines. Pass `max_chars_per_line` from `caption_style.py` into the SRT scripts.
- Word-by-word captions usually work best as a compact single-line layout with stronger outline / shadow.

Example style input:

```json
{"width":540,"height":960,"avoid_lower_third":false}
```

Example return:

```json
{
  "caption": {
    "fill_color": "#FFFFFF",
    "border_color": "#000000",
    "font_id": "noto_sans",
    "font_weight": "bold",
    "position": "bottom",
    "position_value": 0.13,
    "font_size_px": 21
  },
  "layout": {
    "width": 540,
    "height": 960,
    "orientation": "vertical",
    "max_chars_per_line": 38,
    "max_lines": 2
  }
}
```

## Workflow

### 1. Read the Artifact Contract

Read `schemas/artifact_contract.json` from this skill directory and keep its absolute path as `ARTIFACT_CONTRACT_PATH` for later `dl artifact` calls.

### 2. Probe Input Media

For `delivery=burned_video`, probe the video first:

```bash
ffprobe -v quiet -print_format json -show_format -show_streams "https://..."
```

If local `ffprobe` is unavailable, times out, or cannot access the URL, fall back to:

```bash
dl ffmpeg --input src=https://... --output-kind probe_json --command-file=- <<'EOF'
ffprobe -v quiet -print_format json -show_format -show_streams /input/src
EOF
```

Use the first video stream for `width` and `height`. If there is no video stream, downgrade `delivery` to `srt_only`.

Decide `subtitle_mode` before ASR. Use `standard` unless the user requested kinetic captions or the content is a good fit for word-by-word; in that case, ask whether to use `word_by_word`.

### 3. Generate or Accept SRT

If the user provides valid SRT, preserve the text and go to validation. Do not rewrite captions unless the user asks.

Otherwise call ASR:

```bash
dl transcribe \
  --audio-url="https://..." \
  --language=auto \
  --word-timestamps \
  --vad-filter \
  --max-segment-duration=4
```

After `dl transcribe` returns `{status:"pending", job_ref, data:{task_id}}`, end the turn. The result arrives later as an `[async-callback] job=<ref>` message. Do not wait with `sleep`, `nohup`, loops, or polling.

When the callback arrives, call `scripts/segments_to_srt.py` through `dl script exec`. Include callback `result.segments`, and include `result.words` or `segments[].words` when available:

```json
{
  "segments": [{"start": 0, "end": 2.5, "text": "Hello"}],
  "words": [{"start": 0, "end": 0.45, "word": "Hello"}],
  "subtitle_mode": "standard",
  "max_chars_per_line": 38,
  "max_lines": 2
}
```

For `subtitle_mode: "word_by_word"`, the script emits one SRT cue per word. For `standard`, it emits segment-level cues and wraps long text.

The script returns:

```json
{
  "srt_content": "1\n00:00:00,000 --> 00:00:02,500\nHello\n",
  "cue_count": 1,
  "subtitle_mode": "standard",
  "warnings": [],
  "srt_validation": {
    "valid": true,
    "cue_count": 1,
    "overlap_count": 0,
    "skipped_count": 0,
    "warnings": [],
    "strategy": "none"
  }
}
```

Do not hand-write SRT timestamps in the model response.

### 4. Validate and Normalize SRT

Before rendering or persisting, validate with `scripts/validate_srt.py`:

```json
{
  "srt_content": "1\n00:00:00,000 --> 00:00:02,500\nHello\n",
  "max_chars_per_line": 38,
  "max_lines": 2
}
```

Use the returned `srt_content` as canonical and write `srt_validation` into the artifact.

Rules:

- SRT passed to renderers must be strictly increasing and non-overlapping.
- ASR-generated and user-provided SRT both need normalized numbering, order, overlap handling, and line wrapping.
- Do not rewrite user or ASR text unless the user explicitly asks.
- If `valid:false`, do not render. Write a partial `subtitle_result` with `render.requested=false` and the validation errors.
- If ASR returns no usable segments, write a partial `subtitle_result` with `render.requested=false` and the ASR error / empty-output reason.

### 5. Compute Adaptive Style

Run `scripts/caption_style.py`. If the user provided `caption`, overlay only explicit user fields and let the script fill the rest.

```json
{
  "width": 540,
  "height": 960,
  "avoid_lower_third": false,
  "position": "bottom"
}
```

If the video has a CTA card, bottom text, buttons, diagnosis labels, UI, product details, or visible mouth area:

- If the obstruction is brief, keep bottom captions but increase `position_value` or shorten affected cues.
- If important lower-third content is present for most of the video, use `position: "top"`.
- Keep vertical social captions to 1-2 lines; avoid 3+ line blocks.

### 6. Optionally Burn Captions

Render only when `delivery=burned_video`, the source is a video URL, and canonical SRT is non-empty.

#### Default: local ffmpeg

When local `ffmpeg` is available and `upload_file` can upload the result:

1. Write canonical SRT to `/workspace/subtitles.srt`.
2. Use the style result:
   - `FONT_SIZE = caption.font_size_px`
   - `MARGIN_V = round(height * caption.position_value)`
   - `ALIGNMENT = 2` for bottom, `8` for top
3. Render:

```bash
ffmpeg -hide_banner -y \
  -i "https://..." \
  -vf "subtitles=filename=/workspace/subtitles.srt:original_size=WIDTHxHEIGHT:force_style='FontName=Noto Sans,FontSize=FONT_SIZE,PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BorderStyle=1,Outline=2,Shadow=0,Alignment=ALIGNMENT,MarginV=MARGIN_V'" \
  -c:v libx264 -preset veryfast -crf 20 \
  -c:a copy \
  -movflags +faststart \
  /workspace/captioned.mp4
```

4. Upload `/workspace/captioned.mp4` with `upload_file` and write the returned `publicUrl` to `render.video_url`.

Local failure signals include missing ffmpeg, missing `subtitles` / libass filter, download failure, disk pressure, killed process, timeout, or empty output. Fall back once; do not repeatedly rerun the same command.

#### Fallback: dl render-caption

Use hosted rendering when local rendering is unavailable, resources are insufficient, `upload_file` is unavailable, or the user asks for hosted caption rendering:

```bash
dl render-caption \
  --video-url="https://..." \
  --srt-content="1\n00:00:00,000 --> 00:00:02,500\nHello\n" \
  --caption='{"fill_color":"#FFFFFF","border_color":"#000000","font_id":"noto_sans","font_weight":"bold","position":"bottom","position_value":0.13,"font_size_px":21}'
```

`dl render-caption` is synchronous. Do not call `dl poll`.

If rendering fails, keep the SRT and write a partial artifact with `render.success=false`, `render.failure_step`, and `render.error`.

### 7. Write subtitle_result

Write a JSON artifact with `artifact_type: "subtitle_result"` matching `schemas/subtitle_result.schema.json`.

```bash
cat <<'EOF' | dl artifact write --slot=subtitle_result --content-type=application/json --contract='<ARTIFACT_CONTRACT_PATH>' --content-file=-
<serialized subtitle_result JSON>
EOF
```

Then finalize according to the artifact contract terminal mode.

## Output

The artifact must record:

- Source URL and requested delivery mode.
- `subtitle_mode` actually used (`standard` or `word_by_word`).
- ASR language, text, segments, and word timings when available.
- Generated or user-provided canonical SRT.
- SRT validation results, including overlap fixes, skipped cues, wrapping warnings, and errors.
- Caption style actually used.
- Render request status, captioned video URL on success, or failure metadata.

## Constraints

- Input media must be accessible to ASR and either local ffmpeg or hosted rendering.
- Default captions should be at most 2 lines; do not use one fixed large font across all resolutions.
- Default `--max-segment-duration` is `4` to keep standard cues short.
- Do not change timestamps just to fix text.
- Do not pass overlapping SRT to a renderer.
- Do not invent captioned video URLs. Local rendering must use `upload_file`; hosted rendering must use the URL returned by `dl render-caption`.
