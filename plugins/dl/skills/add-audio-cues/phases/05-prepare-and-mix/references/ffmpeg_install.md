# FFmpeg / FFprobe Installation Reference

The skill calls native `ffmpeg` and `ffprobe` directly (NOT the `dl ffmpeg` sandbox). Both binaries must be in PATH and must support the filters used in Phase 05.

## Required filters / features

The Phase 05 master command relies on:

- `libmp3lame` (mp3 encoder)
- `loudnorm` (EBU R128 loudness normalization)
- `sidechaincompress` (sidechain ducking)
- `alimiter` (final peak limiter)
- `aloop` (input-side: `-stream_loop -1`)
- `adelay` (timeline placement)
- `afade` (fade in / out)
- `apad` (pad to whole duration)
- `amix` (multi-input mixer)
- `asplit` (split stream for sidechain key reuse)

## Linux installation (matches dramaland-platform production)

Static GPL build from BtbN — has every filter above, auto-updates daily, no codec licensing issues.

```bash
# System deps (Debian / Ubuntu)
apt-get update && apt-get install -y wget xz-utils

# Architecture-aware download
ARCH=$(dpkg --print-architecture)
case "$ARCH" in
  arm64)
    URL=https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linuxarm64-gpl.tar.xz
    DIR=ffmpeg-master-latest-linuxarm64-gpl
    ;;
  amd64)
    URL=https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-linux64-gpl.tar.xz
    DIR=ffmpeg-master-latest-linux64-gpl
    ;;
  *)
    echo "Unsupported architecture: $ARCH" >&2
    exit 1
    ;;
esac

wget "$URL"
tar xf "$(basename "$URL")"
mv "$DIR/bin/ffmpeg" /usr/local/bin/
mv "$DIR/bin/ffprobe" /usr/local/bin/
chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe
rm -rf "$DIR" "$(basename "$URL")"
```

## macOS (local development)

```bash
brew install ffmpeg
# brew ffmpeg ≥ 5.0 ships every required filter
```

## Verification (run at the top of Phase 05, fail-fast)

```bash
command -v ffmpeg && command -v ffprobe || { echo "ffmpeg/ffprobe missing" >&2; exit 1; }

EXPECTED=5  # loudnorm + sidechaincompress + alimiter + aloop + adelay
GOT=$(ffmpeg -filters 2>/dev/null | grep -E "^\s+[A-Z\.]+\s+(loudnorm|sidechaincompress|alimiter|aloop|adelay)\b" | wc -l | tr -d ' ')
if [ "$GOT" -lt "$EXPECTED" ]; then
  echo "ffmpeg missing required filters (got $GOT/$EXPECTED). Reinstall using the BtbN GPL build." >&2
  exit 1
fi
```

If verification fails, stop the phase and surface the installation
instructions to the user. Do NOT attempt to install ffmpeg automatically
in the runtime — that's an out-of-band operator action.

## Why not `dl ffmpeg`?

`dl ffmpeg` is pi-mono's sandboxed wrapper. It auto-uploads outputs to GCS
and returns CDN URLs, which is convenient for short one-shot operations.
But this skill produces N+1 ffmpeg invocations (one per cue in 4a, one for
the master mix in 4b, one for the final mux in Phase 06). Going through
the sandbox for each would:

- Trigger N GCS uploads of intermediate `prepared_*.mp3` that no one needs
  to access externally.
- Add per-call sandbox boot overhead.
- Lose the ability to chain stdout / locally-managed paths.

Native ffmpeg in the agent's own environment is faster and cheaper here.
The only outputs that need outside-world URLs are the final `master.mp3`
(visible in `audio_retrieval_manifest` if you choose to upload it) and
the final `.mp4` (in `audio_design_result`). Those uploads happen
explicitly in Phase 05.3.1 / Phase 07.
