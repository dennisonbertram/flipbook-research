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

Current human favorite:

```text
outputs/track-v/20260425T144658Z-fal-kling-fal-kling-naturalist-etching-960x540-960x540/output.mp4
```

This run uses the OpenAI-generated naturalist etching fixture:

```text
fixtures/track-v/gpt-image-2-naturalist-etching-plate.png
```

Kling preserves the historical plate composition, etched linework, and naturalist illustration style better than the earlier canal-city and dense-text smokes. It is the best hosted-video aesthetic reference so far, but it is still not a realtime model-layer proof: the Kling request took `47.176s` for a `5.042s` clip, about `9.5x` slower than realtime from finished image to MP4. Including the `gpt-image-2` source image generation (`36.6s`), the end-to-end path is about `16.8x` slower than realtime.

Follow-up:

```text
outputs/track-v/20260425T160020Z-fal-kling-fal-kling-naturalist-etching-living-v2-960x540-960x540/output.mp4
```

This used a slightly more "living illustration" prompt on the same naturalist plate. It stayed visually stable and preserved the plate well, but did not add much more obvious motion than the first favorite. API wall time was `49.403s` for the same `5.042s`/`121` frame output, about `9.8x` slower than realtime from finished image to MP4.

## Current Diagnostic Notes

- `track-v-camera-path-diagnostic-2026-04-27.md` checks whether first/mid/last frames are explainable as crops of the source page.
- The diagnostic supports the working distinction between deterministic plate drift, conservative model plate motion, and generated-pixel document collapse.
- The 6s first/last-frame anchored LTX 2.3 Fast dense-text run preserves the first and last page but invents a bad mid-frame page-fold artifact.
- The 2s first/last-frame anchored run with a strict locked-page prompt is the strongest hosted dense-text result so far: text `0.8099`, layout `0.9992`, API wall `14.762s`.
- Ablations show both the anchor and the strict prompt are required. A 2s anchored default-prompt run fails text (`0.6476`), and a 2s locked-prompt run without the last-frame anchor fails harder (`0.3196`).
- This is still a background enhancement path rather than realtime re-layout: the best hosted run takes about `15s` and is nearly static.
- Modal old-LTX condition probes are faster but still fail dense text: `768x448` took `6.492s` wall with text `0.4604`; `960x544` took `9.766s` wall with text `0.2184`. Both stayed in page coordinates but were nearly static and text-damaging.

## Sources

- Kling fal API: https://fal.ai/models/fal-ai/kling-video/v2.5-turbo/standard/image-to-video/api
- LTX fal API: https://fal.ai/models/fal-ai/ltx-video-13b-distilled/image-to-video/api
