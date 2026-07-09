# Seedance 2.0 — Reference Asset Registration Guide

## When Asset Registration Is Required

You **MUST** register reference assets before using any Seedance 2.0 family service (`seedance-2-0`, `seedance-2-0-fast`, `seedance-2-0-mini`) when:

1. **Real-looking human reference** (`_reference_subject_type: "real_person"`): Any photoreal / photographed-looking human face or body, including AI-generated photoreal humans
2. **Known IP reference** (`_reference_subject_type: "known_ip"`): Any recognizable intellectual property character
3. **Video reference / sequel with a real-looking human**: Any video reference / continuation input that contains a real-looking human

You do **NOT** need asset registration for:
- `realistic_animal`: Realistic non-human animals
- Realistic aliens / non-human creatures
- `illustrated_human`: Clearly 3D, animated, cartoon, or illustrated humans
- Text-only prompts with no reference media

## Registration Flow

### Step 1: Register Each Required Asset with the Current CLI

```bash
dl asset register \
  --group-id "Character Name - refs" \
  --name "front portrait" \
  --url "https://cdn.example.com/face_front.jpg" \
  --asset-type Image \
  --project-name default
```

Returns:
```json
{
  "ok": true,
  "group": {
    "group_id": "grp_xxx",
    "name": "Character Name - refs"
  },
  "asset": {
    "...": "provider payload containing the created asset id"
  }
}
```

Repeat the command once per asset you need. Keep the returned asset ids and
pass them verbatim as `ark_asset_ids` in the generation call.

### Step 2: Use `ark_asset_ids` in `dl generate-video`

```bash
dl generate-video \
  --service=seedance-2-0 \
  --prompt="A person walking through a garden, @asset1 as the main character" \
  --ark-asset-ids=asset_a \
  --ark-asset-ids=asset_b \
  --duration=8 \
  --aspect-ratio=adaptive \
  --resolution=720p \
  --reference-subject-type=real_person
```

### Step 3 (Optional): Verify Asset Status

```bash
dl asset get --id asset_a
```

Returns asset status and metadata for confirmation before use.

## Key Rules

1. **Keep related assets together**: Use a consistent human-readable
   `--group-id` label for the same character and keep the returned asset ids
   together for reuse
2. **Video assets**: Video references must also be registered as assets (asset_type: "Video")
3. **Reuse**: Once registered, `ark_asset_ids` can be reused across multiple
   `dl generate-video` calls
4. **Prompt placeholders**: Use `@assetN` (1-indexed) in prompt to reference registered assets
5. **Asset-only for real-looking humans**: After registering a real-looking human image/video, submit only `ark_asset_ids` + `@assetN`; do not also pass that same media as `image_urls` / `ref_video_url` / raw video URL.

## Prompt Placeholder Reference

| Placeholder | Maps To | Example |
|-------------|---------|---------|
| `@imageN` | `image_urls[N-1]` | `@image1` = first reference image |
| `@audioN` | `reference_audio_url` (N=1 only) | `@audio1` = driving audio |
| `@videoN` | `ref_video_url` | `@video1` = reference video |
| `@assetN` | `ark_asset_ids[N-1]` | `@asset1` = first registered asset |

## Common Mistakes

- **Fabricating URLs**: NEVER invent storage URLs (e.g. `storage.dramaland.xyz/...`). Only use URLs returned by tools (generate_image, generate_music, TTS, upload) or provided by the user. If you need a reference image, generate one first.
- **Audio too long**: `reference_audio_url` must be ≤ 15 seconds. The API rejects longer audio. Trim via ffmpeg or generate a shorter clip before passing to submit_job.
- **Forgetting `@audio1` in lipsync prompt**: Seedance 2.0 lipsync will be blocked if prompt doesn't contain `@audio1`
- **Passing raw URLs for real-looking humans**: Photoreal human photos/videos, including AI-generated photoreal humans, MUST go through asset registration; raw image/video URLs will be blocked
- **Using unsupported 1080p resolution**: Seedance 2.0 Fast / Mini only support 480p and 720p; check `dl generate-video model seedance-2-0` before using Pro 1080p.
- **Wrong duration range**: Seedance 2.0 Pro / Fast support 4-15s; Seedance 2.0 Mini supports 5-12s. If the final clip needs to be shorter than the provider minimum, request the minimum and trim with ffmpeg.
- **Wrong field names**: Use `ref_video_url` (NOT `video_url`) and `reference_audio_url` (NOT `audio_url`) for Seedance 2.0 generate_video. Wrong field names silently drop the reference.
- **Mixing registered and raw human inputs**: Do not send the same real-looking human both as `ark_asset_ids` and as a raw URL
- **Audio moderation block**: If Seedance 2.0 is blocked because of generated/output audio, retry with prompt text such as `no BGM` / `no background music`; do not pass `--generate-audio`

## Fallback Guidance

If asset registration fails or is not applicable:
- For lipsync without a real-looking human: use `dlai2v` or `longcat-avatar` instead
- For video generation without a real-looking human: use `kling-o3-ref2v` for multi-reference
- For non-human realistic subjects or clearly 3D/animated/illustrated humans: use the normal image/video URL path directly
