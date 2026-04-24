# Flipbook Research

Research notes, experiments, and proof-of-concept code for realtime neural-canvas rendering inspired by Flipbook-style model-rendered interfaces.

See the tweet that got me excited: https://x.com/zan2434/status/2046982383430496444?s=20

The core investigation is whether we can render interactive visual pages as pixels from a learned canvas, without repainting the entire screen through a video model every frame.

Current progress examples: 

Rendered ~2.5x realtime by the model!

https://github.com/user-attachments/assets/6fcdb84c-d5e7-40e3-b885-a03fd29fcea6

https://github.com/user-attachments/assets/328edda6-f908-4b04-9333-1b11749a1f04


Initial results: 


## Current Direction

Track C is the most promising path:

```text
stable learned canvas
+ layout/query transform
+ small neural renderer
= realtime model-rendered pixels
```

The current proof of concept trains a tiny per-page neural renderer on a text-heavy fixture, then stress-tests resizing, cropping, and motion.

Key result:

```text
Dense learned frame-scale motion:
  moderate OCR: 0.1053
  strong OCR:   0.0000

Stable canvas + layout transform:
  moderate OCR: 0.7091
  strong OCR:   0.3610

Stable canvas + OCR line anchors:
  moderate OCR: 0.7321
  strong OCR:   0.4124
```

Raw frame rendering is faster than realtime in the current prototype: roughly `300-440ms` for `33` frames at `960x544`, where `33` frames at `24fps` represents `1.375s` of video.

## Repository Map

- `docs/architecture/` - observed Flipbook architecture notes.
- `docs/poc/` - proof-of-concept tracks and benchmark target.
- `docs/research/` - model, text, and neural-canvas research notes.
- `docs/planning/` - active research plans and parallel workstreams.
- `docs/evaluation/` - neural-canvas scorecards and eval schemas.
- `docs/benchmarks/` - summarized benchmark results.
- `docs/experiments/` - compact experiment logs and TSV result tables.
- `scripts/track_a/` - LTX/video-model benchmark helpers.
- `scripts/track_c/` - neural-canvas Modal experiments.
- `fixtures/` - small reproducible input fixtures.
- `outputs/` - lightweight showcase images only; large generated run dumps are ignored.

## Running Track C

The main experiment entrypoint is:

```bash
modal run scripts/track_c/modal_canvas_c2_lite.py --help
```

Long-running runs should be launched through `tmux`; see `scripts/track_c/README.md` for exact benchmark commands.
