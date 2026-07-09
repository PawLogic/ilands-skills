# FFmpeg Loudness & Fade Targets

> Reasoning reference only — Phase 05.4's master template uses these numbers verbatim.

## LUFS targets (per chain `loudnorm=I=…`)

Numbers follow broadcast / streaming convention: dialogue near EBU R128 -16 LUFS, beds (AMB / BGM) sit 10–15 LUFS below dialogue so speech reads naturally on top, SFX / STINGER at or slightly above dialogue for punch.

| Stream | LUFS (`I=`) | TP | LRA |
| --- | --- | --- | --- |
| Dialogue / source video audio | -16 | -1.5 | 7 |
| AMB (ambience bed) | -30 | -1.5 | 7 |
| BGM (music bed) | -25 | -1.5 | 7 |
| SFX | -22 | -1.5 | 7 |
| STINGER | -20 | -1.5 | 7 |

## Fade in / out durations

Per cue type:

| Type | fade-in (s) | fade-out (s) | Rationale |
| --- | --- | --- | --- |
| dialogue / source | 0 | 0 | Don't touch the original |
| AMB | 3.0 | 3.0 | Long ambience needs gentle entry / exit so the room "fills" naturally |
| BGM | 3.0 | 3.0 | Music beds need musical entry; avoid abrupt cuts |
| SFX | 0.1 | 0.1 | Hard hit on action — minimal fade only to avoid click |
| STINGER | 0.05 | 1.0 | Instant attack, decaying tail for resolution |

## Sidechain ducking parameters

When dialogue is sounding, the bed should automatically duck. Two flavors:

### AMB ducking (stronger)

```
sidechaincompress=threshold=0.001:ratio=10:attack=5:release=800
```

Rationale: AMB is meant to be subliminal background; aggressive ratio (10) and very low threshold (0.001) push it well below dialogue when speech starts. Attack 5ms catches dialogue onset, release 800ms keeps the duck through pauses without pumping.

### BGM ducking (gentler)

```
sidechaincompress=threshold=0.005:ratio=3:attack=10:release=800
```

Rationale: BGM has musical content that listeners actively perceive; ratio 3 is gentle enough to not destroy musical flow, threshold 0.005 only ducks when dialogue is meaningfully loud, attack 10ms allows musical transients to breathe.

### SFX / STINGER — no ducking

These exist to punch through; ducking would defeat the purpose.

## Final master pass

After all chains are mixed:

```
loudnorm=I=-16:TP=-1.5:LRA=11
alimiter=level_in=1:level_out=0.95:limit=0.95:attack=5:release=50
```

`loudnorm` (second pass) brings the entire master to broadcast-spec EBU R128
-16 LUFS with relaxed LRA=11 (wider dynamic range for cinematic feel).
`alimiter` (`level_out=0.95:limit=0.95`) is a brick-wall safety net against
inter-sample peaks; settings match dramaland-platform's
`mix_final_audio` line for predictable output.

## Audio output format

```
-c:a libmp3lame -q:a 2 -ar 48000 -ac 1
```

- `libmp3lame -q:a 2` — VBR ~190 kbps; high quality with reasonable file size.
- `-ar 48000` — broadcast standard sample rate.
- `-ac 1` — single channel (matches dramaland's mono dialogue pipeline). If
  the agent needs stereo output for a specific delivery context, swap to
  `-ac 2`; everything else stays the same.

## Output container for final mp4 (Phase 06)

```
-map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -shortest
```

- `-c:v copy` — no re-encode of the original video stream (lossless,
  instant).
- `-c:a aac -b:a 192k` — re-encode mixed mp3 to AAC for mp4 container
  compatibility; 192 kbps stereo-equivalent for a single mono master.
- `-shortest` — if the audio mix is slightly longer than the source video
  (shouldn't happen given Phase 05.4's `apad=whole_dur=<total>`), don't
  pad the video with black.
