# Proof Of Concept Tracks

The PoC should answer the model-layer question before the app question:

```text
Can we produce one browser-playable 33-frame segment in <= 1.3s?
```

Transport, WebSockets, Modal routing, and share UI are secondary until one of the model paths clears or nearly clears that gate.

## Track A: Full-Frame LTX

Track A uses LTX as the main video generator. The input is the static page image; the output is a complete short video segment.

This is the most direct clone of the public Flipbook claim, but it is likely the hardest path to get under the latency target.

See `track-a-full-ltx.md`.

## Track B: Codec-Style Animation

Track B treats the static image as the canonical I-frame and generates motion with masks, flow, depth, parallax, and optional masked video generation.

This is less pure but probably more product-correct for text-heavy visual pages: preserve the page, animate only safe regions, and composite the final frames.

See `track-b-codec-style-animation.md`.

## Track C: Neural Canvas Renderer

Track C is the purist model-rendered-pixels path. It compiles a page/world into a persistent neural canvas, then renders pixels from that canvas for a requested viewport, resolution, and time.

This is the closest path to the full Flipbook promise: no DOM, no CSS, no hand-composited page as the core abstraction. The model owns the rendered pixels, but it renders from stable world state instead of repainting from scratch.

See `track-c-neural-canvas-renderer.md`.

## Shared Output Contract

All tracks should emit the same core artifact shape so they can be compared in one viewer:

```text
outputs/<run-id>/
  input.png
  output.mp4
  metrics.json
  preview.jpg
```

`metrics.json` should include:

```json
{
  "track": "A, B, or C",
  "width": 960,
  "height": 544,
  "frames": 33,
  "fps": 24,
  "wall_time_ms": 0,
  "preprocess_ms": 0,
  "model_ms": 0,
  "decode_or_composite_ms": 0,
  "encode_ms": 0,
  "effective_generated_fps": 0,
  "notes": ""
}
```
