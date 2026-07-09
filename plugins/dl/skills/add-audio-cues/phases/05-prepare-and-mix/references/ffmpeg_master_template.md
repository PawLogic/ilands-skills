# FFmpeg Master Mix — Filter Graph & Command Template

> Reasoning reference only. Phase 05.4 produces this command at runtime; numbers come from `ffmpeg_loudness_targets.md` and per-cue timings come from the manifest.

## Filter graph design (general form)

```text
[0:a]asplit=3[dRaw][dSC_amb][dSC_bgm];   # dialogue split: 1 direct, 2 sidechain keys
[dRaw]loudnorm=I=-16:TP=-1.5:LRA=7[d];

# Per AMB cue (i=1..K_amb): loudnorm → fade → adelay
[1:a]loudnorm=I=-30:TP=-1.5:LRA=7,
     afade=t=in:st=0:d=3,afade=t=out:st=<target-3>:d=3,
     adelay=<ms>|<ms>[amb1];
... (other AMB cues)
[amb1][amb2]…amix=inputs=K_amb:duration=longest:normalize=0[ambMix];
[ambMix][dSC_amb]sidechaincompress=threshold=0.001:ratio=10:attack=5:release=800[ambD];

# Per BGM cue: same shape, different LUFS / ducking
[k:a]loudnorm=I=-25:...,afade=...,afade=...,adelay=...[bgm1];
...
[bgm1][bgm2]…amix=inputs=K_bgm:duration=longest:normalize=0[bgmMix];
[bgmMix][dSC_bgm]sidechaincompress=threshold=0.005:ratio=3:attack=10:release=800[bgmD];

# SFX / STINGER — no ducking
[m:a]loudnorm=I=-22:...,afade=...,afade=...,adelay=...[sfx1];
[n:a]loudnorm=I=-20:...,afade=t=in:st=0:d=0.05,afade=t=out:st=<target-1>:d=1,adelay=...[stg1];

# Combine + pad + final loudnorm + alimiter
[d][ambD][bgmD][sfx1][stg1]…amix=inputs=N:duration=longest:normalize=0[mixed];
[mixed]apad=whole_dur=<total_duration_sec>[padded];
[padded]loudnorm=I=-16:TP=-1.5:LRA=11[normalized];
[normalized]alimiter=level_in=1:level_out=0.95:limit=0.95:attack=5:release=50[out]
```

### Why this layout

- **`asplit=3` on dialogue** — ffmpeg filter graph consumes each stream once; dialogue is needed in 3 places (direct out + AMB sidechain key + BGM sidechain key). The 3rd output `dSC_bgm` is used only if BGM cues exist; if `K_bgm=0`, change to `asplit=2`. If both `K_amb=0` and `K_bgm=0`, drop the split entirely and use `[0:a]loudnorm=…[d]`.
- **`amix=...:normalize=0`** — default amix divides by input count, which crushes the LUFS targets set per chain. Explicit `normalize=0` keeps each chain at its intended LUFS.
- **AMB and BGM chains separated** — even though the cue plan rule (#2) says they don't overlap in time, keeping the sidechain compressors separate lets each domain keep its tuned ducking params (`ratio=10` for AMB, `ratio=3` for BGM).
- **SFX / STINGER go straight into final amix** — no sidechain. They're meant to punch through dialogue.
- **`apad=whole_dur=<total>`** — final master matches the source video's total duration exactly; even if all cues end before video end, the master gets silence padded so Phase 06's mux aligns cleanly.
- **Final `loudnorm` + `alimiter`** — the pre-mix per-chain `loudnorm` lines target individual chain levels; the final master pass lifts the entire program to broadcast spec (LRA=11 widens the dynamic range for cinematic feel) and `alimiter` is the brick-wall safety against inter-sample peaks. Matches dramaland-platform `mix_final_audio` line.

## Concrete command shape

Example: 2 AMB + 1 BGM + 2 SFX + 1 STINGER (input indices 0=dialogue, 1–6 are cues):

```bash
ffmpeg -y \
  -i "<media_url>" \
  -i "${WORKDIR}/prepared_0.mp3" \
  -i "${WORKDIR}/prepared_1.mp3" \
  -i "${WORKDIR}/prepared_2.mp3" \
  -i "${WORKDIR}/prepared_3.mp3" \
  -i "${WORKDIR}/prepared_4.mp3" \
  -i "${WORKDIR}/prepared_5.mp3" \
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

## Substitution rules at runtime

For every entry in the manifest:

- `start_ms = round(start_sec * 1000)` (integer milliseconds for adelay)
- `target_sec` = the bed's BGMSTOP-adjusted duration (Phase 05.2) for AMB / BGM; otherwise `cue.duration_sec`.
- fade-out start time = `target_sec - fade_out_seconds`
- adelay format: `adelay=<ms>|<ms>` (one value per channel; mono masters use `ms|ms` anyway to handle the input safely)

`asplit=N` count:

- N = 1 (`dRaw` only) — if both `K_amb=0` AND `K_bgm=0`. (Use `[0:a]loudnorm=…[d]` and skip the split entirely.)
- N = 2 — if only one of AMB / BGM exists.
- N = 3 — both exist.

`amix` final input count = 1 (d) + (1 if K_amb>0 else 0) + (1 if K_bgm>0 else 0) + K_sfx + K_stg. Drop the corresponding `[ambD]` / `[bgmD]` from the final mix when their chain is absent.

## Heavy-list fallback

If the master command becomes prohibitively large (> ~15 cues, filter
graph deep) and ffmpeg times out or crashes:

1. **First pass**: dialogue + AMB + BGM only → `${WORKDIR}/partial.mp3`. Do NOT run the final `loudnorm + alimiter` step in this pass.
2. **Second pass**: take `${WORKDIR}/partial.mp3` as input 0, add SFX + STINGER as additional inputs, run the final `amix + apad + loudnorm + alimiter` block. Output `${WORKDIR}/master.mp3`.

This keeps each invocation's filter graph manageable and reuses the same
master template structure.

## Sidechain artifact fallback (audible pumping)

If the user reports audible "breathing" / pumping in the bed:

- Replace each `[<bed>][dSC_*]sidechaincompress=…` line with a fixed
  volume scale: `[<bed>]volume=0.4[bedD]` for AMB or `[<bed>]volume=0.3[bedD]` for BGM.
- Drop the corresponding `asplit` output (`dSC_amb` / `dSC_bgm`).
- Mark `quality_tier=degraded` for Phase 07 to record.
