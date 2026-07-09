---
name: ffmpeg
description: "FFmpeg and ffprobe media processing. Probe / -c copy / simple trim locally; -c:v re-encode / filter_complex / inputs >2min via `dl ffmpeg` (sync). Long encodes (>5min) use `dl ffmpeg --async` for callback resume."
allowed-tools: Bash(ffmpeg:*) Bash(ffprobe:*) Bash(dl ffmpeg:*)
metadata:
  ilands:
    applicable-to: [full, creation]
    priority: 3.5
    kind: atomic_skill
---
> **Setup (BYOA):** this skill drives the `dl` CLI, which proxies calls to iLands and bills your own iLands wallet — no API keys touch your machine. If `dl` is not on your PATH, run `npm i -g @pawlogic/dl && dl login` (or `npx -y @pawlogic/dl`). One login serves both the `dl` and `ilands` command sets. See https://ilands.ai/byoa .


<!-- cli-audit: 0872e00cd130eafa -->

# FFmpeg Processing Guide

预判任务特征 → 选路由,**不要先试本地撞墙再 fallback**。重编码、filter_complex、长输入直接走 `dl ffmpeg`;长编码(>5min)开 `--async` 走 callback。

## Non-Negotiable Rules

- Do **not** run `apt-get install ffmpeg`.
- Do **not** call `dl poll` for ffmpeg jobs (sync 模式 dl ffmpeg 自身已等待;async 模式等 `[async-callback]` 注入)。
- For local work, use normal local paths or direct media URLs and write outputs under `/workspace/`.
- For `dl ffmpeg`, pass inputs with repeated `--input name=url` flags and reference them as `/input/{name}` inside the command.
- For `dl ffmpeg`, write exactly one output file under `/output/`. `ffprobe` is the only no-output exception.
- Do **not** use remote `--inputs`; that is a stale flag.
- **不要**在 sandbox bash 里 `sleep` / `while` / `for` 等任何 ffmpeg 完成 — sandbox 5min idle 会杀掉等待。详见 Async / Long Job Rules。

## Routing Decision

按任务特征选路由,不要"先本地撞墙再 fallback"。

| 任务特征 | 路由 | 原因 |
|---------|------|------|
| `ffprobe` / metadata 查询(本地文件或 URL) | **本地** `ffprobe` | 秒级,远程 overhead 不值 |
| `-c copy` stream copy / 简单 trim / mux | **本地** `ffmpeg` | 不重编码,毫秒到几秒 |
| 任何 `-c:v` 重编码,输入 ≤2min | **`dl ffmpeg`**(默认 sync) | 本地易撞 sandbox 5min cap |
| 输入 >2min 且需重编码 | **`dl ffmpeg`**(sync, 注意 timeout 预算) | 几乎必超本地预算 |
| 复杂 `filter_complex`(>3 filter / 多输入 mix) | **`dl ffmpeg`** | CPU/内存吃不消 |
| 预估编码 >5min | **`dl ffmpeg --async`** | 同步阻塞会浪费整个 turn |
| 预估编码 >25min(远程 1800s 上限) | **拆步** | 远程也救不了,走 concat 章节策略 |

`dl ffmpeg` 输入约束:**必须是公网 URL**。sandbox `/workspace/` 文件先 `upload_file` 拿 URL;上游 dl 命令输出本身已是 GCS URL,直接喂下游。

## Encoder Settings

**默认值**:`-preset medium -crf 20-23`(合理体积 vs 速度 trade-off)。

| 用途 | preset | CRF | 备注 |
|------|--------|-----|------|
| 试跑 / 一次性中间产物 | `ultrafast` | 23 | 体积爆炸 3-4x,**绝不用于最终输出** |
| 默认 / production | `medium` | 20-23 | 推荐起点 |
| 存档 / 最优体积 | `slow` | 18-20 | 慢 2-3x,体积更小 |

**⚠️ 实测**:同一 60s 720p 任务,`ultrafast` 输出 11.8Mbps / 418MB,`medium -crf 23` 输出 3.7Mbps / 130MB ——`ultrafast` 跳过几乎所有压缩优化,**只有快没有别的好处**。

音频默认 `-c:a aac -b:a 192k`(除非另有声学要求)。

## Async / Long Job Rules

**`dl ffmpeg` 默认是同步的**(命令返回时 job 已完成,直接拿 `data.url`)。对于**长编码 (>5min)**, 改用 `--async`:

- 命令立刻返回 `{ status: 'pending', job_ref: '...' }`,**你必须 end turn**
- 结果会作为 `[async-callback] job=<ref>` 在后续 turn 推回来
- **不要** `dl poll`、不要再 submit 同一个 job、不要 `sleep`/`while`/`for` 等待

**绝对不要**在 sandbox bash 里写等待循环(任何模式都不行):

- sandbox 5min idle 会杀掉整个等待
- 单 bash 默认 5min cap(可通过 `bash { timeout: N }` 拓到 15min,但仍属同步阻塞 turn,不推荐用于 ffmpeg)

**示例**:

```bash
# ❌ 错:自己写 ffmpeg + 后台等待 —— sandbox 会杀
ffmpeg -i big.mp4 -c:v libx264 -preset medium output.mp4 &
while kill -0 $! 2>/dev/null; do sleep 5; done

# ❌ 错:把 sleep 换成 pgrep 或缩短间隔不治本

# ✅ 对(同步,短任务默认):
dl ffmpeg --input src=$URL --command-file=- <<'EOF'
ffmpeg -i /input/src -c:v libx264 -preset medium -crf 23 /output/out.mp4
EOF

# ✅ 对(异步,长编码):
dl ffmpeg --async --input src=$URL --command-file=- <<'EOF'
ffmpeg -i /input/src -c:v libx264 -preset medium -crf 23 /output/out.mp4
EOF
# 命令立刻返回 { status: 'pending', job_ref } → end turn → 等 [async-callback]
```

## Local Shape

Basic probe:

```bash
ffprobe -v quiet -print_format json -show_format -show_streams <src>
```

Basic transform:

```bash
ffmpeg -i <src> ... /workspace/out.mp4
```

Multi-input transform:

```bash
ffmpeg -i <src1> -i <src2> ... /workspace/out.mp4
```

Use `<src>` as either a local `/workspace/...` path or a direct media URL.

## Remote Shape (`dl ffmpeg`)

Remote probe (sync,毫秒级):

```bash
dl ffmpeg --input src=<url> --output-kind probe_json --command-file=- <<'EOF'
ffprobe -v quiet -print_format json -show_format -show_streams /input/src
EOF
```

Remote transform (sync, 短编码 ≤5min):

```bash
dl ffmpeg --input src=<url> --output-kind transformed_video --timeout 300 --command-file=- <<'EOF'
ffmpeg -i /input/src -c:v libx264 -preset medium -crf 23 /output/out.mp4
EOF
```

Remote multi-input transform (sync):

```bash
dl ffmpeg --input a=<url1> --input b=<url2> --output-kind merged_video --command-file=- <<'EOF'
ffmpeg -i /input/a -i /input/b ... /output/out.mp4
EOF
```

Long encode (async, >5min):

```bash
dl ffmpeg --async --input src=<url> --output-kind final_mv --timeout 1500 --command-file=- <<'EOF'
ffmpeg -i /input/src -c:v libx264 -preset medium -crf 20 -c:a aac /output/final.mp4
EOF
# 命令返回 { status: 'pending', job_ref: '...' } → end turn → 等 [async-callback]
```

Remote inputs must be real, publicly reachable URLs. Sync 模式的响应在 job 完成后到达;async 模式立刻返回 pending,完整结果走 callback。对 `ffprobe`,`data` 是 parsed probe JSON;对 `ffmpeg`,`data` 是 `{ task_id, url, filename, size_bytes }`。

## Always Probe First

Probe first whenever duration, resolution, frame rate, or codec matters.

```bash
ffprobe -v quiet -print_format json -show_format -show_streams <src>
```

Use the probe result to choose crop math, fade timing, concat strategy, and whether stream copy is safe.

For multi-segment assembly, probe every segment and build a manifest before
concat. Record at least: source URL, duration, width, height, fps, SAR, video
codec, audio codec / layout when present, and whether normalization is needed.
Do not infer compatibility from requested model settings.

## Common Operations

### Trim (fast stream copy)

```bash
ffmpeg -i <src> -ss 10 -to 30 -c copy /workspace/trimmed.mp4
```

### Trim (precise re-encode)

```bash
ffmpeg -ss 10 -i <src> -t 20 -c:v libx264 -c:a aac /workspace/trimmed.mp4
```

### Concat with crossfade

```bash
ffmpeg -i <src1> -i <src2> -filter_complex '[0:v][1:v]xfade=transition=fade:duration=0.5:offset=4.5[v];[0:a][1:a]acrossfade=d=0.5[a]' -map '[v]' -map '[a]' /workspace/merged.mp4
```

### Simple concat

```bash
ffmpeg -i <src1> -i <src2> -filter_complex '[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[v][a]' -map '[v]' -map '[a]' /workspace/merged.mp4
```

### Long or mixed-provider concat

For more than 6 segments, or when probes show mixed width, height, fps, SAR,
codec, or audio layout, use a staged plan:

1. Normalize mismatching segments one at a time or in small batches.
2. Concat normalized video-only chunks, keeping each command small enough for
   the current timeout budget.
3. Concat the chunks.
4. Mux the final soundtrack in a separate final command.

Avoid one giant `filter_complex` that scales every input, concatenates all
segments, trims audio, and mixes audio in one command. It is slow, hard to
debug, and commonly hits local or remote timeouts.

For more than 32 segments, chunked concat is mandatory even when probes show
compatible specs. Prefer chunks of roughly 8-12 segments, then concat the
chunk outputs, then mux the final soundtrack in a separate command.

### Speed change

```bash
ffmpeg -i <src> -filter_complex '[0:v]setpts=0.5*PTS[v];[0:a]atempo=2.0[a]' -map '[v]' -map '[a]' /workspace/fast.mp4
```

`setpts=0.5*PTS` means 2x speed. For audio factors above 2x, chain multiple `atempo` filters.

### Crop to vertical

```bash
ffmpeg -i <src> -vf 'crop=ih*9/16:ih' /workspace/vertical.mp4
```

### Resize and pad to 1080p

```bash
ffmpeg -i <src> -vf 'scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2' /workspace/resized.mp4
```

### Extract audio

```bash
ffmpeg -i <src> -vn -c:a libmp3lame -q:a 2 /workspace/audio.mp3
```

### Remove audio

```bash
ffmpeg -i <src> -an -c:v copy /workspace/silent.mp4
```

### Mix voice and BGM

```bash
ffmpeg -i <voice> -i <bgm> -filter_complex '[0:a]volume=1.0[v];[1:a]volume=0.3[b];[v][b]amix=inputs=2:duration=first[a]' -map '[a]' /workspace/mixed.mp3
```

### Overlay watermark or logo

```bash
ffmpeg -i <base_video> -i <logo_image> -filter_complex '[1:v]format=rgba,colorchannelmixer=aa=0.7[wm];[0:v][wm]overlay=10:10[out]' -map '[out]' -map '0:a?' /workspace/watermarked.mp4
```

### Compose final video with mixed audio

```bash
ffmpeg -i <video> -i <voice> -i <bgm> -filter_complex '[1:a]volume=1.0[v];[2:a]volume=0.25[b];[v][b]amix=inputs=2:duration=first[a]' -map '0:v' -map '[a]' -c:v copy /workspace/final.mp4
```

### Fade in/out

```bash
ffmpeg -i <src> -vf 'fade=t=in:st=0:d=1,fade=t=out:st=9:d=1' -af 'afade=t=in:st=0:d=1,afade=t=out:st=9:d=1' /workspace/faded.mp4
```

### Drawtext caption

```bash
ffmpeg -i <src> -vf "drawtext=text='HELLO WORLD':fontsize=48:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=20" /workspace/captioned.png
```

### Meme text

```bash
ffmpeg -i <src> -vf "drawtext=text='TOP TEXT':fontsize=48:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=20,drawtext=text='BOTTOM TEXT':fontsize=48:fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h-th-20" /workspace/meme.png
```

### Convert to GIF

```bash
ffmpeg -i <src> -vf 'fps=15,scale=480:-1:flags=lanczos' -loop 0 /workspace/out.gif
```

## Workflow

1. Probe the input first(本地 `ffprobe` 首选)when timing or geometry matters。
2. 查 Routing Decision 表选路由 + 查 Encoder Settings 表选 preset/CRF。
3. 写命令:本地用 `/workspace/` 路径;`dl ffmpeg` 用 `/input/{name}` + `/output/{filename}`。
4. 长编码(>5min)加 `--async`;否则默认 sync。
5. Sync 模式直接读返回 `data`;async 模式等 `[async-callback]` 注入。
6. 把返回的 URL 喂给下游命令或 artifact。

## Constraints

- `--timeout` 上限 **1800s (30min)**,受 Cloud Run timeoutSeconds 制约。预估总耗时接近上限时必须拆步(参考 Long or mixed-provider concat 章节)。
- Remote inputs must be real, publicly reachable URLs.
- Remote commands may use `/input/{name}` and `/output/{filename}` only. No arbitrary absolute paths, no `http://` inside the command, no `pipe:`, no path traversal.
- Sync 模式 + 长编码会阻塞整个 turn,且受 sandbox 5min bash cap 制约(可 `bash { timeout: N }` 拓到 15min,但 >15min 必须 `--async`)。
- Async 模式提交后 turn 必须立刻结束,等 `[async-callback]`。**不要** `dl poll`、`sleep`、`while`、再 submit。
- 如果 `dl ffmpeg` 返回 `E_BACKEND` / timeout / 4xx / 5xx,先看路由表是否选错(短任务别走 async),再拆步,最后才考虑改 media 逻辑。

For exact flags, use `dl ffmpeg --help`.
