# Track C: Neural Canvas Renderer

## Goal

Build toward the real Flipbook promise:

```text
world state -> learned renderer -> pixels
```

No DOM, no CSS layout, no hand-composited text layer as the core abstraction. The page/world is compiled into a persistent latent canvas, and a fast renderer produces pixels for any viewport, resolution, and time.

## Why This Is Different From Track A

Track A asks a video model to repaint a full image into a clip:

```text
input image -> image-to-video model -> 33-frame video
```

That can be fast, but our first results show the model does not preserve the world. It preserves broad layout while repainting text as texture.

Track C instead makes the stable world representation explicit:

```text
prompt / query / facts
        ↓
world compiler
        ↓
persistent neural canvas
        ↓
viewport-time renderer
        ↓
pixels
```

The renderer can still be fully learned. The difference is that each frame is a view of the same latent world, not an independent repaint.

## Core Claim To Test

Can a compiled latent canvas be rendered repeatedly, resized, cropped, animated, and updated without losing identity?

For this project, identity means:

- text remains the same text
- labels stay attached to the same objects
- diagram structure stays consistent
- resizing does not create a new page
- time adds motion without rewriting content

## First POC: Overfit Neural Canvas

Start with the smallest experiment that tests the renderer abstraction rather than the full generative problem.

```text
input:      one text-heavy page image
compile:    train/fit a compact neural canvas to reconstruct it
render:     query pixels at multiple viewports, crops, resolutions, and times
measure:    latency, OCR, resize consistency, temporal consistency
```

This is intentionally not a product model. It answers whether the representation can support the interaction contract:

```text
same canvas -> 512px render
same canvas -> 960px render
same canvas -> cropped/zoomed render
same canvas -> 33-frame animated render
```

Compile time is excluded at first, just like cold model startup is excluded from Track A.

## Renderer Contract

The renderer should accept:

```json
{
  "canvas_id": "page-001",
  "viewport": {
    "x": 0.0,
    "y": 0.0,
    "width": 1.0,
    "height": 0.5667
  },
  "output": {
    "width": 960,
    "height": 544
  },
  "time": 0.0,
  "interaction_state": {}
}
```

and return:

```text
RGB frame
```

For video:

```text
same canvas_id + time[0..32] -> 33 frames
```

## First Benchmark Matrix

Use the existing text-heavy fixture.

```text
resolutions: 512x288, 768x448, 960x544, 1280x736
frames:      1 still render, then 33-frame sequence
fps:         24
views:       full page, 2x zoom crop, shifted crop
```

Measure:

```text
compile_ms
render_ms_per_frame
render_wall_time_ms_33_frames
encode_ms
ocr_similarity
layout_similarity
resize_consistency
temporal_consistency
```

## POC Ladder

### C0: Coordinate Neural Field

Fit a small coordinate network or hash-grid-style neural image representation to one page.

```text
(x, y, scale, time) -> rgb
```

This tests whether a learned renderer can preserve page identity across resize/crop queries.

### C1: Latent Feature Canvas

Replace direct pixel fitting with a multiscale latent feature grid.

```text
latent feature pyramid + viewport query -> rgb
```

This is closer to a practical renderer because it can cache a page/world representation and render many frames cheaply.

### C2: Motion Head

Add time conditioning:

```text
latent canvas + x/y + t -> rgb
```

The first motion can be subtle: lighting drift, tiny parallax, small material shimmer. The key is that time changes pixels without changing identity.

### C3: Generative World Compiler

Replace the input image with a compiler:

```text
prompt / facts / search result -> latent canvas
```

This is where a slower, stronger model can operate. It may use text-specialized image models, language models, or diffusion teachers. The fast renderer remains separate.

### C4: Distilled Real-Time Renderer

Distill the renderer so it can produce 33 frames at target resolutions within the live budget.

The likely techniques are:

- few-step consistency / rectified-flow distillation
- feed-forward latent decoding
- cached prompt/world embeddings
- multi-resolution tile rendering
- recurrent state updates for interaction

## Acceptance Criteria

Minimum still-render pass:

```text
single 960x544 render <= 40ms
OCR score close to source fixture
resize consistency passes manual review
```

Minimum video-render pass:

```text
33 frames rendered + encoded <= 1.3s
OCR score stays close to still render
motion is visible but identity is stable
```

Strategic pass:

```text
same canvas renders credible views at 512px, 960px, and cropped zoom without regenerating the page
```

## Why This Might Work

- The expensive generative step can be separated from the fast render step.
- A persistent canvas gives the model memory of exact content.
- Resize and crop become queries, not fresh generations.
- Text can be part of the learned world representation instead of transient diffusion texture.
- The render step can be optimized like graphics inference, not open-ended generation.

## Why This Might Fail

- Overfit neural fields can preserve one image but fail to generalize.
- Text may still require explicit symbolic conditioning to remain exact.
- Training/compiling a canvas per page may be too slow unless amortized.
- Feed-forward renderers may blur small glyphs unless resolution-aware.
- True generative canvas compilation is a much harder problem than animation.

## Next Step

Build C0:

```text
scripts/track_c/
  train_canvas.py
  render_canvas.py
  benchmark_canvas.py
```

The first version should overfit the existing fixture on Modal GPU, export a compact checkpoint, render the same canvas at several resolutions/crops, and score OCR/consistency.

This gives us a real artifact to compare against Track A:

```text
outputs/track-c/<run-id>/
  input.png
  render-512.png
  render-960.png
  crop-2x.png
  output.mp4
  metrics.json
  quality.json
```

## First C0 Result

The first C0 implementation exists at:

```text
scripts/track_c/modal_canvas_c0.py
```

It overfits the existing fixture into a full-resolution learned feature canvas plus a small MLP renderer.

Initial result:

```text
render_960_ms:       ~4-5ms
render_33_wall_ms:   ~125-162ms
encode_ms:           ~234-239ms
OCR token-F1:        ~0.73-0.74
```

This proves the renderer contract is plausible, but not the final text/readability quality. The next iteration should add glyph-aware training instead of only minimizing pixel MSE.

The first time-conditioned C2-lite run also exists:

```text
scripts/track_c/modal_canvas_c2_lite.py
```

It trains a learned motion field that samples from the same persistent canvas:

```text
canvas + x/y + t -> learned flow -> sampled canvas features -> rgb
```

Initial C2-lite result:

```text
render_960_ms:       ~16ms
render_33_wall_ms:   ~300ms
encode_ms:           ~230ms
OCR token-F1:        ~0.83
motion_delta:        ~0.019
loop_error:          ~0.0013
```

This proves that time can change pixels while the same canvas keeps the page identity mostly stable. The motion target is still synthetic, so the next real research step is semantic motion and glyph-aware preservation.

## First Glyph-Aware C2 Result

The first glyph-aware variant keeps the same C2-lite renderer but changes training:

```text
70% of samples from edge/dark likely-glyph pixels
4x extra loss weight on likely-glyph pixels
```

Result:

```text
render_960_ms:       ~15ms
render_33_wall_ms:   ~300ms
encode_ms:           ~267ms
OCR token-F1:        ~0.829
motion_delta:        ~0.019
loop_error:          ~0.0013
```

This stayed well under the `1.3s` chunk target, but did not improve OCR over the unweighted C2-lite run. Generic edge weighting is too blunt; the next renderer should use explicit text-region supervision, train at higher resolution before downsampling, or add a frozen OCR/text-recognition loss.

## First OCR-Box C2.1 Result

C2.1 keeps the same neural-canvas renderer but sends explicit OCR word boxes from the local source fixture into the Modal training job. The remote trainer builds a text mask and uses it for both sampling and loss weighting.

```text
train resolution:       1280x736
OCR boxes:              105
text mask coverage:     15.4%
text-box samples:       55% of each batch
text-box loss weight:   8x
edge samples/loss:      10% / 1x
```

Result:

```text
render_960_ms:       ~44ms first render
render_33_wall_ms:   ~301ms
encode_ms:           ~634ms
OCR token-F1:        ~0.855
motion_delta:        ~0.016
loop_error:          ~0.0008
```

This is the first positive text-specific result: OCR token-F1 improved from `0.8326` to `0.8545` while keeping the 33-frame render+encode chunk under `1.0s`. Text is still not source-faithful enough, but explicit text supervision is now clearly the right direction.

## C2.2 Dramatic Motion Stress

The next stress test asks whether the same renderer survives frame resizing/repositioning pressure, not just a small jiggle. It adds:

```text
motion_mode:          frame-scale
video_viewport_mode:  zoom-pulse
```

Two runs were tested:

```text
strong stress:
  motion_strength:    0.18
  viewport_zoom:      0.18
  render_33_wall_ms:  ~298ms
  encode_ms:          ~255ms
  motion_delta:       ~0.071
  OCR token-F1:       0.000

moderate stress:
  motion_strength:    0.06
  viewport_zoom:      0.08
  render_33_wall_ms:  ~299ms
  encode_ms:          ~259ms
  motion_delta:       ~0.043
  OCR token-F1:       0.105
```

This answers the stress-test question: jiggle is not enough. The current C2 flow head can keep latency under budget, but frame-scale motion turns text into streaks. A credible neural browser needs a layout-aware canvas where text identity is anchored separately from the motion field, rather than asking a dense coordinate warp to preserve glyphs during resize/reposition.

## C2.3 Stable Canvas + Layout Transform

C2.3 tests the architectural fix. Instead of training a time-conditioned flow to repaint frame-scale motion, it trains a stable text-box-weighted canvas and applies frame sizing as a render-time coordinate transform.

```text
stable canvas + layout transform + x/y/t query -> pixels
```

The renderer still produces pixels from the learned canvas. The difference is that frame sizing is no longer encoded as a dense learned deformation of text.

Results:

```text
moderate frame-scale:
  C2.2 learned flow OCR:       0.105
  C2.3 layout-transform OCR:   0.709
  render_33_wall_ms:           ~302ms

strong frame-scale:
  C2.2 learned flow OCR:       0.000
  C2.3 layout-transform OCR:   0.361
  render_33_wall_ms:           ~302ms
```

This is the strongest signal so far. A neural canvas can handle frame sizing better when content identity is stable and motion is represented as layout/query state. The next version should make those layout transforms local and element-aware rather than one global page transform.

## C2.4 OCR Line Anchors

C2.4 makes the C2.3 layout transform local for text. It groups OCR words into line anchors, renders the globally transformed page from the stable neural canvas, then re-queries those text-line regions from the same canvas with a gentler element scale.

```text
stable canvas + global layout transform -> background pixels
stable canvas + OCR line anchors -> text-line pixels
```

This is still model-rendered output. The anchors do not draw DOM text; they define additional coordinate queries into the learned canvas.

Results:

```text
moderate frame-scale:
  C2.3 global layout OCR:      0.709
  C2.4 OCR line anchor OCR:    0.732
  render_33_wall_ms:           ~442ms

strong frame-scale:
  C2.3 global layout OCR:      0.361
  C2.4 OCR line anchor OCR:    0.412
  render_33_wall_ms:           ~401ms
```

This is a modest but real improvement. It also exposes the next bottleneck: anchor patches are currently rendered sequentially, so quality improves at a measurable latency cost. C2.5 should batch all anchor queries per frame and use smoother alpha masks instead of rectangular patch replacement.
