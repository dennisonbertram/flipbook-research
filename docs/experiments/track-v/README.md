# Track V: Hosted Video Model Benchmarks

Track V tests external image-to-video models as the "animate the generated page" branch.

This is intentionally separate from Track C:

- Track C asks whether the page itself can be rendered as neural-canvas pixels.
- Track V asks whether a hosted video model can animate one generated page state while preserving text and layout.

## Current Models

- Kling 2.5 Turbo Standard through fal: `fal-ai/kling-video/v2.5-turbo/standard/image-to-video`
- LTX 13B distilled through fal: `fal-ai/ltx-video-13b-distilled/image-to-video`

Kling has a minimum 5 second request shape, so its wall time is an API/product latency number rather than a clean 33-frame model-layer number. LTX exposes `num_frames` and `frame_rate`, so it can be tested closer to the repo's `33 frames at 24fps` target.

## Benchmark Command

```bash
python3 scripts/track_v/fal_video_benchmark.py \
  --model kling \
  --duration 5 \
  --prep-resolution 960x540 \
  --append-results
```

```bash
python3 scripts/track_v/fal_video_benchmark.py \
  --model ltx \
  --frames 33 \
  --fps 24 \
  --ltx-resolution 480p \
  --first-pass-steps 2 \
  --second-pass-steps 2 \
  --second-pass-skip-steps 1 \
  --prep-resolution 960x540 \
  --append-results
```

Outputs go to:

```text
outputs/track-v/<run-id>/
  input.png
  output.mp4
  frame-first.png
  frame-mid.png
  frame-last.png
  contact-sheet.jpg
  metrics.json
  quality.json
```

Compact results go to:

```text
docs/experiments/track-v/results.tsv
```

## First Pass Criteria

The script marks a hosted run as `pass` only when:

- OCR/layout proxy text score is at least `0.70`.
- Layout proxy is at least `0.80`.

That is deliberately softer than the pure neural-canvas gates. Hosted video models can be useful for a Flipbook-like two-stage bridge, but a pass here is not proof of the pure pixel-rendered page system. Manual review remains required, especially for:

- text hallucination or spelling drift;
- diagram-line drift;
- global page warping;
- whether motion is meaningful or just camera wobble.

## Current Snapshot

The first text-heavy smoke tests show the split clearly:

- fal-hosted LTX can return 33 frames, but dense text is badly degraded.
- Kling preserves text and layout better, especially with a low-CFG static prompt, but dense words still drift across a 5 second clip.

The first illustration fixture was generated with OpenAI `gpt-image-2`:

```text
fixtures/track-v/gpt-image-2-illustrated-canal-city.png
```

On that richer visual page, Kling is the better hosted bridge candidate so far. It keeps more detail and structure at 720p, while fal-hosted LTX is softer at 480p. Both hosted paths are tens of seconds per request, so these are quality/product-latency probes, not realtime model-layer wins.

## Sources

- Kling fal API: https://fal.ai/models/fal-ai/kling-video/v2.5-turbo/standard/image-to-video/api
- LTX fal API: https://fal.ai/models/fal-ai/ltx-video-13b-distilled/image-to-video/api
