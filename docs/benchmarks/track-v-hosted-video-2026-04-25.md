# Track V Hosted Video Benchmark

Date: 2026-04-25

## Purpose

Run a parallel hosted-video track against the same core question Flipbook hints at: can a fast image-to-video model animate a static generated page while preserving text, layout, and diagram structure?

This is a bridge path, not the final pure neural-canvas proof. Flipbook's public copy says live video currently combines a custom optimized video model with an image generation system, while the longer-term direction is a single generated visual surface. Track V maps that bridge.

## Models

Initial endpoints through fal:

```text
fal-ai/kling-video/v2.5-turbo/standard/image-to-video
fal-ai/ltx-video-13b-distilled/image-to-video
```

The installed credential is `FAL_KEY`; the benchmark never writes the key into artifacts.

## Harness

The runnable harness is:

```text
scripts/track_v/fal_video_benchmark.py
```

It prepares a fixed page image, uploads it through fal, launches the requested image-to-video model, downloads the MP4, extracts first/middle/last frames, computes OCR/layout proxies, and writes artifacts under:

```text
outputs/track-v/<run-id>/
```

Compact rows append to:

```text
docs/experiments/track-v/results.tsv
```

## Measurement Caveat

Kling is a product API with a minimum 5 second duration, so the measured wall time includes queueing and service overhead. It is useful as a quality and product-latency probe, but not as a direct model-layer answer to the `33 frames <= 1.3s` question.

fal-hosted LTX exposes `num_frames` and `frame_rate`, so it can be tested closer to the 33-frame budget. It is still hosted API wall time, not low-level CUDA kernel timing.

## First Experiments

Run in tmux:

```text
tmux new-session -d -s track-v-kling-smoke \
  "cd /Users/dennisonbertram/Develop/flipbook-research && python3 scripts/track_v/fal_video_benchmark.py --model kling --duration 5 --prep-resolution 960x540 --append-results > docs/experiments/track-v/kling-smoke.log 2>&1"
```

```text
tmux new-session -d -s track-v-ltx-fal-smoke \
  "cd /Users/dennisonbertram/Develop/flipbook-research && python3 scripts/track_v/fal_video_benchmark.py --model ltx --frames 33 --fps 24 --ltx-resolution 480p --first-pass-steps 2 --second-pass-steps 2 --second-pass-skip-steps 1 --prep-resolution 960x540 --append-results > docs/experiments/track-v/ltx-fal-smoke.log 2>&1"
```

## Decision Rule

If Kling preserves text better than LTX, Track V should probe prompt and CFG around Kling while accepting that it is not the final latency shape.

If LTX is much faster but damages text, Track A should continue model-layer optimization and text-preservation work.

If both drift text badly, the two-stage video bridge is useful for rich imagery but not enough for model-rendered pages with dense text.

## 09:50 ET Update

Generated a richer visual fixture with OpenAI `gpt-image-2`:

```text
fixtures/track-v/gpt-image-2-illustrated-canal-city.png
```

Prompt summary: a detailed canal city inside a giant glass terrarium, with water channels, bridges, gardens, boats, sunlight, and no readable text.

Initial hosted-video results:

| Run | Model | Shape | API Wall | Proxy Result | Notes |
| --- | --- | --- | ---: | --- | --- |
| `20260425T134237Z-fal-ltx-text-fixture-smoke-960x540` | fal LTX 13B distilled | 33 frames, 832x480 | `48.835s` | quality fail | Preserves broad layout but destroys dense page text. |
| `20260425T134237Z-fal-kling-text-fixture-smoke-960x540` | Kling 2.5 Turbo | 121 frames, 1280x720 | `48.237s` | quality fail | Better text than LTX, but mid/last frames hallucinate or mutate dense copy. |
| `20260425T134448Z-fal-kling-static-text-cfg01-960x540` | Kling 2.5 Turbo | 121 frames, 1280x720 | `49.075s` | pass by soft OCR gate | Static prompt/low CFG improves text, but later frames still drift. |
| `20260425T135104Z-fal-kling-canal-city-illustration-960x540` | Kling 2.5 Turbo | 121 frames, 1280x720 | `59.151s` | pass with text gate skipped | Stronger visual fidelity than LTX on illustration; useful bridge-model candidate. |
| `20260425T135104Z-fal-ltx-canal-city-illustration-960x540` | fal LTX 13B distilled | 33 frames, 832x480 | `78.475s` | pass with text gate skipped | Lower resolution and visibly softer than Kling. |
| `20260425T144658Z-fal-kling-fal-kling-naturalist-etching-960x540-960x540` | Kling 2.5 Turbo | 121 frames, 1280x720 | `47.176s` | pass with text gate skipped | Best human-picked hosted result so far; preserves the 1800s naturalist-plate style and linework. |

Interpretation:

Kling looks useful for rich imagery where exact text is not the target. It is not close to realtime through the hosted API, and dense text still drifts. fal-hosted LTX is a poor latency proxy for the optimized LTX/Modal story and is weaker visually in these smoke tests. Track V should continue as a bridge-model quality track, while Track C remains the main realtime neural-canvas proof.

## 11:05 ET Naturalist Update

The naturalist etching fixture was generated with OpenAI `gpt-image-2` in `36.6s`, then animated with Kling in `47.176s` plus `0.914s` download time. The MP4 is `5.041667s`, so the hosted animation request is about `9.5x` slower than realtime, or about `16.8x` slower end-to-end including source image generation.

This is the strongest Track V quality reference so far, not a realtime proof. It suggests a useful bridge path for beautiful generated imagery, while Track C remains the path for "every pixel is rendered live by the model."
