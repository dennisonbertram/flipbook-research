# Benchmark Target

## Primary Gate

```text
33 frames generated + decoded/composited + encoded in <= 1.3s
```

At `24fps`, `33` frames is `1.375s` of video. A system that can produce the next segment in about the duration of the current segment can plausibly feel live with only a small buffer.

## What Counts

The wall-clock target includes:

- image preprocessing
- model inference or procedural/mask computation
- VAE decode if Track A uses latent diffusion
- frame compositing if Track B uses layered motion
- browser-playable MP4/fMP4 encoding
- packet preparation

The target excludes:

- initial model/container cold start
- WebSocket transit
- browser `MediaSource` append/playback
- static page image generation

## First Benchmark Matrix

Use one representative text-heavy generated page image.

```text
frames:      33
fps:         24
resolutions: 768x432, 960x544, 1280x736
tracks:      A full-frame LTX, B codec-style animation
```

Track A should additionally test:

```text
steps:       4, 6, 8
guidance:    off / guidance_scale=1
weights:     distilled FP8 first
```

Track B should additionally test:

```text
masks:       text-freeze mask, saliency mask, depth layers
motion:      parallax only, parallax + local warps, masked generation
```

## Acceptance Criteria

Minimum viable pass:

```text
wall_time_ms <= 1300
effective_generated_fps >= 25.4
text remains readable
page layout remains stable
motion reads as intentional, not melting
```

Useful near miss:

```text
wall_time_ms <= 3000
output looks good enough to hide with buffering
clear path exists to cut latency by at least 2x
```

Hard fail:

```text
wall_time_ms > 3000
text or diagrams visibly mutate
latency is dominated by an irreducible model stage
```
