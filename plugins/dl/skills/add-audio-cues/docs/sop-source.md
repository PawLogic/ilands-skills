# SOP — 为任意视频/音频配 SFX、BGM、AMB

> **目标**：让 LLM agent 按这套 SOP，把一段任意输入视频或音频，自动配齐音效（SFX / Stinger）、背景音乐（BGM）、环境音（AMB），输出一条已混好的成片。
>
> **依赖**：pi-mono `dl` CLI（`dl transcribe` / `dl knowledge search` / `dl artifact`）+ **本机原生 `ffmpeg` / `ffprobe`**（不经 `dl ffmpeg` 沙箱）。本 SOP 不调用任何外部 HTTP 服务。

---

## 0. 前置依赖与工作目录

### 0.1 ffmpeg / ffprobe 安装

agent 跑这套 SOP 前，**本机环境必须**有可执行的 `ffmpeg` 和 `ffprobe`。强烈推荐用 BtbN 维护的静态 GPL 构建（每日自动更新，全部 codec / filter 齐全，含 `libmp3lame` / `loudnorm` / `sidechaincompress` / `alimiter` / `afade` / `aloop` / `adelay` / `apad` / `amix` / `asplit` 等本 SOP 用到的全部组件）。

**Linux 安装（推荐，与 dramaland-platform 线上一致）**：

```bash
# 系统依赖
apt-get update && apt-get install -y wget xz-utils

# 按架构下载静态构建
ARCH=$(dpkg --print-architecture)
if [ "$ARCH" = "arm64" ]; then
  wget https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linuxarm64-gpl.tar.xz
  tar xf ffmpeg-master-latest-linuxarm64-gpl.tar.xz
  mv ffmpeg-master-latest-linuxarm64-gpl/bin/ffmpeg /usr/local/bin/
  mv ffmpeg-master-latest-linuxarm64-gpl/bin/ffprobe /usr/local/bin/
elif [ "$ARCH" = "amd64" ]; then
  wget https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz
  tar xf ffmpeg-master-latest-linux64-gpl.tar.xz
  mv ffmpeg-master-latest-linux64-gpl/bin/ffmpeg /usr/local/bin/
  mv ffmpeg-master-latest-linux64-gpl/bin/ffprobe /usr/local/bin/
fi
chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe
rm -rf ffmpeg-*
```

**macOS 本地开发**：`brew install ffmpeg`（确保 brew 版 ≥ 5.0，覆盖本 SOP 用到的 filter）。

**校验**（开干前跑一次）：

```bash
ffmpeg -version | head -1                       # 期望：ffmpeg version N-… 或 5.x+
ffmpeg -filters 2>/dev/null | grep -E "loudnorm|sidechaincompress|alimiter|aloop|adelay" | wc -l
# 期望：5（每个 filter 都存在）
```

任一缺失就停下报错，让用户先装好。

### 0.2 工作目录

整套 SOP 跑下来会产生若干中间文件（prepared mp3、master、final video），统一放在一个临时工作目录里：

```bash
WORKDIR=$(mktemp -d /tmp/audio_sop_XXXXXX)
echo "$WORKDIR"   # 例：/tmp/audio_sop_abc123
```

后续 SOP 里所有 `${WORKDIR}/...` 都指这个目录。skill 结束时是否清理由编排层决定（debug 时保留，生产可删）。

### 0.3 输入 URL 与本地文件的处理

- ffmpeg 5.x+ 原生支持 `https://` / `http://` URL 作为 `-i` 输入，无需先下载。本 SOP 默认把远端 URL 直接喂给 ffmpeg。
- 网络抖动 / 大文件场景可先 `curl -L -o ${WORKDIR}/<name> <url>` 拉到本地再用，命令模板同样适用。
- 中间产物（prepared mp3）和最终产物（master.mp3 / final.mp4）都是**本地路径**。如需对外分发 CDN URL，agent 在 §7 落盘前用 `dl asset register --url=<上传后的 url>` 注册（具体上传方式超出本 SOP 范围，按编排层惯例）。

---

## 1. 输入约定

agent 开始前必须确认：

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `media_url` | ✅ | 公网可访问的 URL（视频或音频）。本地文件先上传 + `dl asset register` 拿到 URL |
| `media_kind` | ✅ | `video` 或 `audio` |
| `total_duration_sec` | ✅ | 整段时长（秒）。Phase 1 必先 `ffprobe` 确认 |
| `language_hint` | 可选 | `auto`、`zh`、`en` … 给 ASR 用 |
| `narrative_context` | 可选 | "剧情梗概 / 旁白文字 / 视频说明"。让 agent 在 Phase 2 脑补语境；没有就只用 ASR 转录 |

### 1.1 立即持久化输入到 artifact（必做，开干前第一步）

后续每个 Phase 都会回头用 `media_url` / `total_duration_sec` / `narrative_context`。整条 SOP 链路长，agent 的 working memory 经常被压缩 / 折叠 / 跨轮丢失，所以**开干前第一件事**：把 §1 表格里的字段写进 artifact slot `audio_design_input` 并 `finalize --mode=verify_and_promote`。`total_duration_sec` 在 §2.2 探出后用 `dl artifact patch-json` 回填。

> 规则：后续命令模板里所有 `<media_url>` 占位符，**真值都从 `dl artifact read --slot=audio_design_input` 取**。一旦发现 working memory 里的 media_url 与 artifact 里不一致，以 artifact 为准。

---

## 2. Phase 1 — 转录（先复用，再现做）

**目标**：拿到带时间戳的 transcript segments 数组和总时长。

> 整条 SOP 的时间单位都是 **float 秒**（与 `dl transcribe` 输出的 `segments[].start` 一致），不再产出/消费 SRT 字符串。

### 2.1 先看上下文 / artifact 里有没有现成的

按以下顺序检查，命中任一即跳到 §2.2 探时长：

1. **当前对话上下文**：用户消息或前置 agent 是否已经给了 transcript / segments 数组 / SRT 文本 / 时间戳列表？
   - 如果给的是 SRT 文本，反解析成 `[{start, end, text}, ...]` 数组形式（每条的 start/end 用 float 秒），与 `dl transcribe` 的输出对齐。
2. **artifact slot**：

   ```bash
   dl artifact list
   # 关注名字含 transcript / asr / caption / srt 的 slot
   dl artifact read --slot=<候选 slot>
   ```

   常见命名：`transcript`、`asr_result`、`caption_track`、`srt_text`。

如果命中，**校验时长**：把 segments 最后一条的 `end` 与 §2.2 探出来的 `total_duration_sec` 比较，差异 > 5s 视为不匹配，重做。

如果**完全没有**，**先告知用户**：

> "未发现现成转录。即将用 `dl transcribe` 重新转录 `<media_url>`（约 X 秒）。如果你已有 transcript / SRT，请贴在对话里，我会优先用你提供的那份。"

得到用户回复或默认继续后，再走 §2.3。

### 2.2 探时长（始终要做，不能省）

```bash
ffprobe -v quiet -print_format json -show_format -show_streams "<media_url>"
```

从输出 JSON 读 `format.duration`，记为 `total_duration_sec`。

### 2.3 转录

```bash
dl transcribe \
  --audio-url=<media_url> \
  --language=auto \
  --word-timestamps \
  --vad-filter \
  --max-segment-duration=5
```

`dl transcribe` 是 async：submit 立即返回 `{status:"pending", job_ref, data:{task_id}}`，必须**结束本轮**等 `[async-callback] job=<ref>` 注入下一轮。不要 `nohup` / `sleep` / `for` / `while` / `dl poll` 兜底。`--model-size` 已经下线（模型由 ASR 服务端决定）。

callback 到达后的 payload `result` 形态：

```json
{ "success": true, "language": "en",
  "duration": 12.408,
  "text": "...",
  "segments": [
    { "id": 0, "start": 3.2, "end": 5.8, "text": "First segment text." },
    { "id": 1, "start": 6.1, "end": 9.4, "text": "Second segment text." },
    ...
  ],
  "words": [ ... ],  // 仅在 --word-timestamps 时出现
  "srt_content": "...",
  "srt_url": "https://..."
}
```

**保留 `result.segments[]` 原样备用**（直接喂给 §3.2 的 prompt，无需任何格式转换）。`words[]` / `text` / `srt_*` 这一版 SOP 用不到，可以丢。

如果是新做的转录（不是 §2.1 复用别人的），把 `segments[]` 写到 artifact slot `transcript` 并 `finalize --mode=verify_and_promote`。这样符合 §2.1 设计的对称机制 —— 别的 skill（字幕渲染、旁白翻译等）也能复用同一份转录。

> **退化**：如果输入是音乐 / 噪声为主、ASR 全空（`segments == []`），跳过 Phase 2 走"无对话纯音效"路径 —— 选一条 BGM 全长铺底（不出 AMB），SFX/STINGER 由 `narrative_context` 或用户描述驱动。

---

## 3. Phase 2 — 情绪与位置标注（生成 audio cues）

**目标**：让 LLM 当 sound designer，把 segments + narrative_context 转成"什么时候该响什么音"的 JSON 清单。

### 3.1 cue 数据结构（Phase 3/4 都依赖的契约）

```json
{
  "audio_cues": [
    { "start": 3.2,   "type": "AMB",     "duration_sec": 30,  "description": "rainy city street at night with distant traffic" },
    { "start": 33.0,  "type": "BGMSTOP" },
    { "start": 33.5,  "type": "BGM",     "duration_sec": 45,  "description": "melancholic slow piano for flashback scene" },
    { "start": 12.1,  "type": "SFX",     "duration_sec": 1.2, "description": "glass breaking shatter on concrete floor" },
    { "start": 78.0,  "type": "STINGER", "duration_sec": 1.5, "description": "horror reveal dramatic hit with reverb" }
  ]
}
```

字段说明：
- `start`：**float 秒**，媒体起点 = 0。与 `dl transcribe` 的 `segments[].start` / `ffmpeg` 的 `adelay` 全程统一单位，零格式转换。
- `type` ∈ `AMB | BGM | SFX | STINGER | BGMSTOP`。
- `duration_sec`：**float 秒**（允许 0.1s 粒度，方便表达 < 1s 的 SFX/STINGER）；`BGMSTOP` 不需要 duration。
- `description`：5–15 词、检索友好（直接拿去喂 §4 的 `dl knowledge search --query`）。
- **AMB 与 BGM 共享同一条 "bed" 轨**：同一时刻只允许一种铺底音。两者切换时，前一条必须先结束（自身 `duration_sec` 走完，或在下一条开始前出现 `BGMSTOP`）。SFX 与 STINGER 不受此约束，可以自由叠加在 bed 之上。
- **没有 `scene_number`**。情绪 / 场景切换由 LLM 用 `BGMSTOP` 显式标记，AMB/BGM 的 duration 在同一情绪段内闭合即可。

### 3.2 Sound design 原则（agent 自驱）

> agent 在这一步充当 sound designer，自己读 segments + narrative_context，自己决策每条 cue 的位置 / 类型 / 时长 / 描述。下面的 INSTRUCTIONS 与 GUIDELINES 是必须遵守的产出规则。

#### 输入材料

- `segments_json`：来自 §2.3 `dl transcribe` 输出的 `segments[]`，每条 `{"start": <float秒>, "end": <float秒>, "text": <string>}`。Time origin = 媒体起点 (= 0)。
- `total_duration_sec`：来自 §2.2 ffprobe，整段时长（float 秒）。
- `narrative_context`（可选）：剧情梗概 / 旁白文字 / 视频说明，用来脑补语境。可能为空。

#### INSTRUCTIONS — 5 类 cue 的角色定位

- **AMB** (ambience) — Environmental sounds that establish atmosphere
- **BGM** (background music) — Musical scores that enhance mood
- **SFX** (sound effects) — Specific sounds tied to actions or events
- **STINGER** (stingers) — Short musical accents for dramatic moments
- **BGMSTOP** — Marker to stop the currently sounding bed (AMB or BGM)

#### GUIDELINES — 7 条产出规则（必须全部遵守）

1. Place AMB at scene transitions or location changes; AMB usually 10–60s.
2. AMB and BGM share a SINGLE "bed" track in this workflow — only ONE of them may be active at any given moment. Use AMB for environmental beds (rain, café murmur, wind) when the scene grounds in atmosphere; use BGM for emotional/musical beds when the scene needs scoring. Before switching from one to the other, the previous bed must end first — either by its own duration finishing exactly at the switch point, or by a BGMSTOP cue placed at that point. Do NOT emit two beds whose `[start, start + duration_sec]` intervals overlap.
3. SFX must be specific and tied to a visible/mentioned action; ≤ 2s. SFX may freely overlap with the bed and with each other.
4. STINGER for reveals, twists, or emotional peaks; ≤ 2s. STINGER may freely overlap with the bed.
5. BGMSTOP stops the active bed (AMB or BGM, whichever is currently sounding) — use it before dramatic pauses, tonal shifts, or when you need silence under dialogue. The "previous bed must end" rule from #2 can be satisfied either by exact duration OR by a BGMSTOP at the switch point.
6. Timestamps are floats in seconds (precision to 0.1s is sufficient). All cues must satisfy `start + duration_sec ≤ total_duration_sec`.
7. Descriptions must be specific enough for audio-library retrieval（5–15 词，描述声音本身，不是描述剧情。例：✅ `"glass breaking shatter on concrete floor"` / ❌ `"the moment she drops the cup"`）。

#### 产出

按 §3.1 schema 生成 `audio_cues` 数组，写入 `cues.json`。下一步 §3.3 会做 4 道自我校验。

### 3.3 自我校验（agent 写完 cues.json 后必跑）

agent 生成 `audio_cues` 数组后，**自己**对照下面 4 条做一遍校验，违规的就地修补，记到 `cue_corrections[]`：

1. **结构校验**：`audio_cues` 是数组；每条有 `start` (number) / `type` (string)；`type` ∈ 5 个枚举；`BGMSTOP` 之外的有 `duration_sec` (number)。结构错就重写这一条。
2. **时间线合法性**：`start + duration_sec ≤ total_duration_sec`；超出的截断到 `total_duration_sec - start`，记入 `cue_corrections[]`。
3. **bed 不并存校验**：把所有 AMB / BGM cue 按 `start` 排序，相邻两条若 `prev.start + prev.duration_sec > next.start` 且两者之间没有 BGMSTOP，则视为违规：把 `prev.duration_sec` 截短到 `next.start - prev.start`，记入 `cue_corrections[]`。
4. **description 检索友好度**：每条 cue（除 BGMSTOP 外）的 `description` 必须 5–15 词，描述"声音本身"而不是"剧情上下文"。不达标的就地重写。

保存为 `cues.json`。

> **退化**：如果 agent 自己产出严重不达标（结构混乱、cue 数量异常多/少、绝大多数 description 偏剧情而不是声音）→ 退化到"全长一条 BGM 铺底 + 0 条其它 cue"（`{"start": 0.0, "type": "BGM", "duration_sec": <total_duration_sec>}`），并把 `quality_tier` 标记为 `degraded`。

### 3.4 写入 audio_cues_plan + 用户 checkpoint（必做，强 checkpoint）⭐

§3.3 自校验通过后，把 cues 写到 artifact slot `audio_cues_plan`，**先以 `mode=verify` finalize（draft 状态，不 promote）**，然后**主动向用户展示**：

- cue 总数（按 type 分组），例如 `AMB×3, BGM×2, SFX×5, STINGER×1`
- 关键几条（agent 觉得最有戏剧效果的、用户最可能想审的，例如所有 BGM 与 STINGER 的 timestamp + description）
- 任何在 §3.3 自校验里被截断 / 修补 / 退化的项

**询问用户**："这个音效设计方案 OK 吗？要调整哪里？还是直接进检索？"

> 这是整个 SOP 唯一的强 checkpoint。**没有用户明确通过之前，绝对不要进 §4** —— §4 / §5 是烧素材库 + 烧 ffmpeg + 烧带宽的最贵环节，cue 错了全白干。

用户通过后，`dl artifact finalize --slot=audio_cues_plan --mode=verify_and_promote`，再进 §4。用户提修改意见时，agent 改完 cues 重写 artifact（`patch-json` 或重新 `write`），再次拿给用户确认 —— 反复直到通过。

---

## 4. Phase 3 — 素材检索（cue → asset URL + 真实时长）

**目标**：每条 cue 找一条最匹配的素材，得到 `{cue, asset_url, real_duration_sec, asset_id}` 列表。

### 4.1 按 cue type 映射 domain

| cue type | `--domain` | 推荐 filter |
| --- | --- | --- |
| AMB | `amb` | `{"loopable": true}` |
| BGM | `bgm` | （无） |
| SFX | `sfx` | `{"distance": "near"}` 贴动作；远景动作用 `"mid"` / `"far"` |
| STINGER | `stinger` | （无） |
| BGMSTOP | — | 不检索，§5.2 当作 bed 截断信号 |

### 4.2 命令

```bash
# AMB（场景循环型）
cat <<'EOF' | dl knowledge search --domain=amb --query="rainy city street at night with distant traffic" --filters-file=- --k=5
{"loopable": true}
EOF

# SFX（贴动作型）
cat <<'EOF' | dl knowledge search --domain=sfx --query="glass breaking shatter on concrete floor" --filters-file=- --k=5
{"distance": "near"}
EOF

# BGM / STINGER 不带 filter
dl knowledge search --domain=bgm --query="melancholic slow piano for flashback scene" --k=5
dl knowledge search --domain=stinger --query="horror reveal dramatic hit with reverb" --k=3
```

返回 `data[]`，每条带 `asset_id` / `filename` / CDN URL / metadata（含 `duration` 等）。
agent 选 top-1（或按 score + duration 适配度选）。

### 4.3 拿真实时长（必跑）

KB 里 metadata 的 duration 不一定准，§5 需要精确数。每条命中的素材再 `ffprobe` 一次：

```bash
ffprobe -v quiet -print_format json -show_format "<asset_url>"
```

读 `format.duration` 记为 `real_duration_sec`。

### 4.4 输出 manifest（暂留 working memory）

把每条 cue 的检索结果整理成 manifest（agent 在 working memory 里维护一份）。每条 entry 至少包含：
- 与 `audio_cues_plan` 对齐的 cue 索引、type、start_sec、description
- 检索结果：asset_url、asset_id、real_duration_sec
- 推荐：retrieval_score、retrieval_query（用户 debug 时有用）
- prepared_path：先留空，§5.3 跑完 4a 后填（本地路径，例 `${WORKDIR}/prepared_<idx>.mp3`）

> 这一步**不**写 artifact —— 是中间产物。`audio_retrieval_manifest` artifact 等到 §5.3 全部 4a 完成、prepared_path 填齐后再一次性写 + finalize（见 §5.3.1）。

> **退化**：某条 cue 召回为空时，**不要**用别的 type 替代。AMB 缺 → 留 silence；SFX/STINGER 缺 → 整条 cue drop；BGM 缺 → 用 `audio_any` 域再搜一次，仍空就 drop。每个被 drop 的 cue 都记到 `failed_cues[]`。

---

## 5. Phase 4 — 素材准备 + timeline 混音

整个 Phase 4 拆成两步：

- **§5.3 Phase 4a — 素材准备**：每条 cue 单独跑一次 `ffmpeg`，做 `download + trim + loop`，输出一段时长恰为 `target_sec` 的 prepared mp3（写到 `${WORKDIR}`）。
- **§5.4 Phase 4b — timeline 混音**：一次 `ffmpeg` 把所有 prepared mp3 + 原声做 `fade + LUFS + adelay + sidechain + amix + 最终 loudnorm + alimiter`，输出 `${WORKDIR}/master.mp3`。

为什么要拆：
- 4a 每条独立，可以并发（多进程或 `xargs -P`）；任一条失败不会拖垮整体。
- 4b 的 filter graph 不再含 `aloop` / `atrim`（已在 4a 完成），更短、更易调试。
- agent 在 4a 后能做 sanity check（每个 prepared mp3 时长是否 ≈ `target_sec`），出错可定位到具体 cue。

### 5.1 LUFS 目标 + fade 时长（按 type）

| 类型 | LUFS | fade-in (s) | fade-out (s) |
| --- | --- | --- | --- |
| dialogue / 原声 | -16 | 0 | 0 |
| AMB | -30 | 3.0 | 3.0 |
| BGM | -25 | 3.0 | 3.0 |
| SFX | -22 | 0.1 | 0.1 |
| STINGER | -20 | 0.05 | 1.0 |

> 数值参考 broadcast / streaming 的常用经验：dialogue 接近 EBU R128 -16 LUFS；bed（AMB/BGM）比 dialogue 低 ~10–15 LUFS，让对话自然居前；SFX/STINGER 与 dialogue 同档或略高，确保听感冲击。一组数值通用，不区分模式。

> §5.4 末尾还会对 master 整体过一道 `loudnorm=I=-16:TP=-1.5:LRA=11` 再加 `alimiter`，保证整片符合广播响度且不削顶。

### 5.2 BGMSTOP 折算（在 4a 之前）

每条 AMB / BGM cue 的实际播放时长 = `min(cue.duration_sec, 下一条 BGMSTOP.start - cue.start)`。先扫一遍 `cues.json`：
- 把折算后的 `target_sec` 写到 manifest 对应记录上（替换原 `duration_sec`）。
- 从 manifest 删掉 BGMSTOP 自身 —— 它不入 ffmpeg。

SFX / STINGER 的 `target_sec` 直接 = `cue.duration_sec`（不受 BGMSTOP 影响）。

### 5.3 Phase 4a — 素材准备（per-cue 一次 ffmpeg）

每条 cue 的输入是 §4 检索到的 `asset_url`，输出是一段时长恰为 `target_sec` 的 prepared mp3（写到 `${WORKDIR}/prepared_<cue_index>.mp3`）。

**AMB / BGM**（短素材循环、长素材截断）：

```bash
ffmpeg -y \
  -stream_loop -1 -i "<asset_url>" \
  -t <target_sec> \
  -c:a libmp3lame -q:a 2 -ar 48000 -ac 1 \
  "${WORKDIR}/prepared_<cue_index>.mp3"
```

`-stream_loop -1` 是 input option，在 demuxer 层无限循环，对 mp3 不需要重新解码全部素材；`-t <target_sec>` 在第一遍循环内就截断。素材已经 ≥ target 时，第一遍走完就结束 —— 同一条命令兼容两种情况。

**SFX / STINGER**（不循环；`real < target` 时按 real 截短）：

```bash
ffmpeg -y \
  -i "<asset_url>" \
  -t <min(real_duration_sec, target_sec)> \
  -c:a libmp3lame -q:a 2 -ar 48000 -ac 1 \
  "${WORKDIR}/prepared_<cue_index>.mp3"
```

参数说明：
- `-y`：覆盖已存在的输出文件
- `-c:a libmp3lame -q:a 2`：MP3 VBR ~190kbps，与 dramaland 线上音质一致
- `-ar 48000`：48 kHz 采样率（广播标准）
- `-ac 1`：单声道（dramaland 线上配置）

> 为什么 SFX / STINGER 不 loop？这两类是"贴动作 / 顶情绪"的瞬时音，循环会变成"咔哒咔哒咔哒"很可笑。Phase 3 选片时就该让 `real ≥ target`；选不到就接受比 target 短。

每条 prepared mp3 的本地路径写回 manifest 对应 entry 的 `prepared_path` 字段。

**并发提示**：N 条 cue 之间彼此独立，可以并发跑 ffmpeg（`xargs -P 4`、GNU parallel，或编排层并行调用）：

```bash
# 示例：并发度 4
cat cmds.sh | xargs -P 4 -I {} bash -c '{}'
```

每个进程跑一条 4a 命令，远端 URL 下载在并发时是天然并行的。

**4a sanity check**：所有 4a 完成后用 ffprobe 抽查每条 prepared mp3 的时长是否 ≈ `target_sec`（误差 < 0.1s）；不达标的 cue 重跑或 drop。

```bash
ffprobe -v quiet -print_format json -show_format "${WORKDIR}/prepared_<cue_index>.mp3"
# 读 format.duration 与 target_sec 比较
```

### 5.3.1 写入 audio_retrieval_manifest（必做）

§5.3 全部 4a 完成、prepared_path 填齐后，把 manifest 一次性写到 artifact slot `audio_retrieval_manifest` 并 `finalize --mode=verify_and_promote`。

这个 artifact 三个用处：
- **§6.1 用户提小改意见时**（删 1-2 条 cue / 调 duration / 换某条素材）：agent 从 manifest 读已有素材清单，**只重跑改动的那几条 cue**，复用其它的检索 + 4a 结果，然后只重跑 §5.4。避免无脑全链路重做。
- **跨 session 续跑**：§5.3 跑完关掉 session，第二天 §5.4 直接从 artifact 读 manifest 接着跑。
- **debug**：用户问"这首 BGM 怎么这么悲"时，agent 能精准答出选了哪个 asset_id / 检索打分多少。

### 5.4 Phase 4b — timeline 混音（一次 ffmpeg 出 master）

输入：原声 dialogue（取自 `<media_url>` 的音轨）+ 所有 prepared mp3（`${WORKDIR}/prepared_*.mp3`）。filter_complex 里每条只做 `loudnorm → afade × 2 → adelay`（不再有 aloop / atrim），最后整体过 `loudnorm + alimiter`。

#### filter graph 总结构

```
[0:a]asplit=3[dRaw][dSC_amb][dSC_bgm];   # 原声复制 3 路：直出、AMB sidechain key、BGM sidechain key
[dRaw]loudnorm=I=-16:TP=-1.5:LRA=7[d];

# 每条 AMB cue：LUFS → fade in/out → adelay
[1:a]loudnorm=I=-30:TP=-1.5:LRA=7,
     afade=t=in:st=0:d=3,afade=t=out:st=<target-3>:d=3,
     adelay=<ms>|<ms>[amb1];
… (其它 AMB)
[amb1][amb2]…amix=inputs=K_amb:duration=longest[ambMix];
[ambMix][dSC_amb]sidechaincompress=threshold=0.001:ratio=10:attack=5:release=800[ambD];

# 每条 BGM cue 同上但 LUFS 与 ducking 参数不同
[k:a]loudnorm=I=-25:…,afade=…,afade=…,adelay=<ms>|<ms>[bgm1];
…
[bgm1][bgm2]…amix=inputs=K_bgm:duration=longest[bgmMix];
[bgmMix][dSC_bgm]sidechaincompress=threshold=0.005:ratio=3:attack=10:release=800[bgmD];

# SFX / STINGER 不走 sidechain
[m:a]loudnorm=I=-22:…,afade=…,afade=…,adelay=<ms>|<ms>[sfx1];
[n:a]loudnorm=I=-20:…,afade=…,afade=…,adelay=<ms>|<ms>[stg1];

# 合轨 + 尾段补 silence + 整体响度归一化 + 限幅
[d][ambD][bgmD][sfx1][stg1]…amix=inputs=N:duration=longest:normalize=0[mixed];
[mixed]apad=whole_dur=<total_duration_sec>[padded];
[padded]loudnorm=I=-16:TP=-1.5:LRA=11[normalized];
[normalized]alimiter=level_in=1:level_out=0.95:limit=0.95:attack=5:release=50[out]
```

为什么这样组织：
- AMB 和 BGM 各自独立 sidechain（参数不同：AMB 压得更狠 ratio=10、BGM 较温和 ratio=3，对应两类 bed 的听感期望）。即便 LLM 没遵守"bed 不并存"规则，graph 也能跑出结果，AMB/BGM 同时存在时会各自被 ducking。
- dialogue 通过 `asplit=3` 复制 3 路：1 路直接进 master，2 路分别做 AMB / BGM 的 sidechain key。ffmpeg filter graph 里每个流只能被消费一次，所以必须 split。
- SFX / STINGER 不 ducking：它们本就是要顶在对话上的重音，压下去反而失去作用。
- `amix=...:normalize=0`：关掉 amix 的自动归一化（默认会按输入数分母平均，导致音量被压扁；关掉让每条 chain 在 §5.1 设定的 LUFS 上发挥）。
- `apad=whole_dur=<total>` 把 master 时长补齐到与原视频/音频一致。
- **最后两道 `loudnorm + alimiter`**：master 整体过一道 EBU R128 -16 LUFS 响度归一化，再加 alimiter（`level_out=0.95:limit=0.95`）防 peak 削顶。这是 dramaland 线上 mix_final_audio 的固定收尾步骤。
- `<ms>` = `round(cue.start * 1000)`，整数毫秒。

#### 完整命令模板

下面这版覆盖"原声 + 2 AMB + 1 BGM + 2 SFX + 1 STINGER" 的常规组合。多/少几条按同模式扩展：

```bash
ffmpeg -y \
  -i "<media_url>" \
  -i "${WORKDIR}/prepared_amb_1.mp3" \
  -i "${WORKDIR}/prepared_amb_2.mp3" \
  -i "${WORKDIR}/prepared_bgm_1.mp3" \
  -i "${WORKDIR}/prepared_sfx_1.mp3" \
  -i "${WORKDIR}/prepared_sfx_2.mp3" \
  -i "${WORKDIR}/prepared_stg_1.mp3" \
  -filter_complex "
    [0:a]asplit=3[dRaw][dSC_amb][dSC_bgm];
    [dRaw]loudnorm=I=-16:TP=-1.5:LRA=7[d];

    [1:a]loudnorm=I=-30:TP=-1.5:LRA=7,
         afade=t=in:st=0:d=3,afade=t=out:st=27:d=3,
         adelay=3200|3200[amb1];
    [2:a]loudnorm=I=-30:TP=-1.5:LRA=7,
         afade=t=in:st=0:d=3,afade=t=out:st=17:d=3,
         adelay=60000|60000[amb2];
    [amb1][amb2]amix=inputs=2:duration=longest:normalize=0[ambMix];
    [ambMix][dSC_amb]sidechaincompress=threshold=0.001:ratio=10:attack=5:release=800[ambD];

    [3:a]loudnorm=I=-25:TP=-1.5:LRA=7,
         afade=t=in:st=0:d=3,afade=t=out:st=42:d=3,
         adelay=8500|8500[bgm1];
    [bgm1][dSC_bgm]sidechaincompress=threshold=0.005:ratio=3:attack=10:release=800[bgmD];

    [4:a]loudnorm=I=-22:TP=-1.5:LRA=7,
         afade=t=in:st=0:d=0.1,afade=t=out:st=0.9:d=0.1,
         adelay=12100|12100[sfx1];
    [5:a]loudnorm=I=-22:TP=-1.5:LRA=7,
         afade=t=in:st=0:d=0.1,afade=t=out:st=0.9:d=0.1,
         adelay=24500|24500[sfx2];

    [6:a]loudnorm=I=-20:TP=-1.5:LRA=7,
         afade=t=in:st=0:d=0.05,afade=t=out:st=1:d=1,
         adelay=33000|33000[stg1];

    [d][ambD][bgmD][sfx1][sfx2][stg1]amix=inputs=6:duration=longest:normalize=0[mixed];
    [mixed]apad=whole_dur=120[padded];
    [padded]loudnorm=I=-16:TP=-1.5:LRA=11[normalized];
    [normalized]alimiter=level_in=1:level_out=0.95:limit=0.95:attack=5:release=50[out]
  " \
  -map "[out]" \
  -c:a libmp3lame -q:a 2 -ar 48000 -ac 1 \
  "${WORKDIR}/master.mp3"
```

替换说明：
- `-i "<media_url>"`：第 0 路输入是原始视频/音频的 URL，ffmpeg 自动取它的 `:a` 流当 dialogue。
- 每条 cue 的 `adelay` 值 = `round(start_sec * 1000)`，毫秒整数。
- `asplit=3` 的 "3" = 1 (dRaw) + 1 (如有任意 AMB) + 1 (如有任意 BGM)；如果某类一条都没有，相应 split 减 1，并删掉对应 sidechain 行。
- `apad=whole_dur=<total_duration_sec>` 把 master 时长补齐到与原视频/音频一致。

### 5.5 退化（按从轻到重）

1. **某条 cue 的 4a 失败**（ffmpeg 退出码 ≠ 0 / 输出文件不存在 / 时长不对）→ 从 manifest 删除，记 `failed_cues[]`，4b 继续。
2. **4b filter graph 报错**（chain 名拼错 / cue 数对不上 inputs / `Invalid argument`）→ 把可疑 chain 从命令删掉重跑；ffmpeg stderr 通常能定位到具体哪一行。
3. **4b 跑得慢 / 出 master 超时**（极端长 cue list，>15 条左右）→ 拆成两次 4b：
   - 第一次：dialogue + AMB + BGM → `${WORKDIR}/partial.mp3`（不做 final loudnorm/alimiter）
   - 第二次：`${WORKDIR}/partial.mp3` 当原声输入 + SFX/STINGER → `${WORKDIR}/master.mp3`（这次跑 final loudnorm/alimiter）
4. **sidechaincompress 让音色发抖** → 去掉它，AMB/BGM 各自 chain 末尾改成 `volume=0.4` / `volume=0.3`（其它不变）。
5. **某条 cue 整体失败（4a + 4b 都救不回来）** → 从 manifest 永久 drop。

---

## 6. Phase 5 — 合回视频（仅视频输入）

```bash
ffmpeg -y \
  -i "<media_url>" \
  -i "${WORKDIR}/master.mp3" \
  -map 0:v -map 1:a \
  -c:v copy -c:a aac -b:a 192k \
  -shortest \
  "${WORKDIR}/final.mp4"
```

`-c:v copy` 不重编码视频；`-c:a aac -b:a 192k` 把混好的 MP3 转 AAC 给 MP4 容器；`-shortest` 防止音频比视频长导致黑画面。

### 6.1 成片确认（必做）⭐

成片出来后**必须等用户 ack**：把 `${WORKDIR}/master.mp3` / `${WORKDIR}/final.mp4` 的可访问路径或 URL（必要时上传后注册为 CDN URL）发给用户，问"听一下，OK 我去 finalize；不 OK 你想从哪步重来 —— 改 cue（回 §3.4）/ 换素材（回 §4）/ 调音量（回 §5.5.4 的静态 volume 退化）？"

**用户拍板前不要进 §7 的 finalize**。

**用户提小改时**（删 1-2 条 cue / 调 duration / 换某条素材）：从 `audio_retrieval_manifest` 读已有素材清单，**只重跑改动的那几条 cue** 的 §4 + §5.3，复用其它 entry 的 prepared_path，然后只重跑 §5.4 + §6。不要无脑全链路重跑。

**用户提大改时**（"风格不对，全换" / 大量 cue 要重新设计）：回到 §3.4 重新设计 `audio_cues_plan`，走完整 §4 / §5 / §6。

---

## 7. Phase 6 — 落盘

§6.1 用户 ack 通过后，把整次跑的最终结果写到 artifact slot `audio_design_result` 并 `finalize --mode=verify_and_promote`。

最少应该包含的信息（agent 自己组织 JSON 字段，不强制 schema）：
- 输入溯源：`media_url`（取自 `audio_design_input`）、transcript 来源（artifact 复用 / 新做 / 用户贴）、`total_duration_sec`
- 设计与混音产物：`audio_cues_plan` slot 引用、`audio_retrieval_manifest` slot 引用、`master.mp3` 路径或 URL、`final.mp4` 路径或 URL（仅视频）
- 健康指标：`cue_counts` / `failed_cues` / `cue_corrections` / `quality_tier`（`ok` 或 `degraded`）
- `created_at`

写入 + finalize 后 skill 终止。如需对外分发，agent 在 finalize 前用 `dl asset register` 把 master/final 注册成 CDN URL，再把 URL 写进 artifact。

---

## 8. Fallback Ladder（按从轻到重）

1. 某条 cue 检索为空 → drop 这条，记 `failed_cues[]`，继续。
2. 某条 cue 4a 失败 → drop，4b 继续。
3. 4b filter graph 报错 → 删可疑 chain 重跑。
4. 4b 超时 / 太重 → 拆成两次 4b（见 §5.5.3）。
5. 侧链闪避音色异常 → 退化到静态 volume（见 §5.5.4）。
6. LLM cue 设计 JSON 解析连续失败 → 全长一条 BGM 铺底，`quality_tier="degraded"`。
7. 超过一半 cue 失败 → 仍出 master，但 `quality_tier="degraded"`。

---

## 9. Completion Rules

- terminal artifact = `audio_design_result`，写入并 `finalize` 后 skill 终止。
- `failed_cues[]` 可以非空，但 `master.mp3` 必须存在（本地路径或 URL）。
- 视频输入时 `final.mp4` 必填；音频输入时该字段缺省。
- 工作目录 `${WORKDIR}` 默认保留（debug 友好），由编排层决定清理时机。

---

## 10. 命令速查

| 步骤 | 工具 | 一行命令模板 |
| --- | --- | --- |
| 装 ffmpeg | system | 见 §0.1（BtbN 静态构建 → `/usr/local/bin`） |
| 准备工作目录 | shell | `WORKDIR=$(mktemp -d /tmp/audio_sop_XXXXXX)` |
| 探时长 | `ffprobe` | `ffprobe -v quiet -print_format json -show_format "<media_url>"` |
| 复用已有转录 | `dl artifact` | `dl artifact list && dl artifact read --slot=<name>` |
| 转录 | `dl transcribe` | `dl transcribe --audio-url=<url> --word-timestamps --vad-filter` |
| Cue 设计 | LLM (agent 自身) | 用 §3.2 prompt，喂 segments JSON + narrative_context |
| 检索 SFX | `dl knowledge search` | `--domain=sfx --query="..." --filters-file=- # {"distance":"near"}` |
| 检索 AMB | `dl knowledge search` | `--domain=amb --query="..." --filters-file=- # {"loopable":true}` |
| 检索 BGM | `dl knowledge search` | `--domain=bgm --query="..."` |
| 检索 STINGER | `dl knowledge search` | `--domain=stinger --query="..."` |
| 4a 准备（AMB/BGM） | `ffmpeg` | `ffmpeg -y -stream_loop -1 -i "<url>" -t <T> -c:a libmp3lame -q:a 2 -ar 48000 -ac 1 "${WORKDIR}/prepared_<i>.mp3"` |
| 4a 准备（SFX/STINGER） | `ffmpeg` | `ffmpeg -y -i "<url>" -t <min(real,target)> -c:a libmp3lame -q:a 2 -ar 48000 -ac 1 "${WORKDIR}/prepared_<i>.mp3"` |
| 4b 混音 | `ffmpeg` | 见 §5.4 完整模板（含 final loudnorm + alimiter） |
| 合回视频 | `ffmpeg` | `ffmpeg -y -i "<media_url>" -i "${WORKDIR}/master.mp3" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest "${WORKDIR}/final.mp4"` |
| 落盘 | `dl artifact` | `dl artifact write --slot=audio_design_result --content-file=- && dl artifact finalize --slot=... --mode=verify_and_promote` |
