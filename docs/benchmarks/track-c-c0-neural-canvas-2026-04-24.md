# Track C Neural Canvas Benchmark

Date: 2026-04-24

## Purpose

Test the first neural canvas renderer contract:

```text
same learned canvas -> multiple resolutions, crops, and a 33-frame render
```

This is not yet a generative world compiler. It overfits one text-heavy fixture into a persistent learned canvas, then renders pixels from that canvas.

## Model

The first C0 implementation uses:

```text
trainable full-resolution latent feature grid
bilinear feature sampling by viewport coordinates
small MLP renderer
```

This is a renderer-interface test. The canvas is learned, not hand-rendered DOM/CSS.

## Runs

| Run | Compile | Render 960 | 33 Renders | Encode | OCR Token-F1 | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `20260424T141533Z-c0-canvas-960x544-s1500` | 2.943s | 4.043ms | 125.081ms | 238.990ms | 0.7397 | pass |
| `20260424T141858Z-c0-canvas-960x544-s5000` | 13.339s | 5.170ms | 162.389ms | 234.166ms | 0.7281 | pass |
| `20260424T142739Z-c2-lite-960x544-s3000` | 14.554s | 16.375ms | 300.104ms | 230.038ms | 0.8326 | pass |
| `20260424T145821Z-c2-lite-glyph-960x544-s4000` | 19.822s | 14.917ms | 300.210ms | 267.389ms | 0.8288 | pass |
| `20260424T151017Z-c2-lite-text-1280x736-s4500` | 29.608s | 43.783ms | 301.365ms | 633.911ms | 0.8545 | pass |
| `20260424T152249Z-c2-lite-text-frame-scale-1280x736-s4500` | 28.365s | 15.021ms | 298.354ms | 254.951ms | 0.0000 | quality fail |
| `20260424T152418Z-c2-lite-text-frame-scale-1280x736-s4500` | 29.208s | 14.328ms | 298.903ms | 259.238ms | 0.1053 | quality fail |
| `20260424T153539Z-c2-lite-text-static-layout-frame-scale-1280x736-s4500` | 29.503s | 16.067ms | 302.278ms | 239.698ms | 0.7091 | pass |
| `20260424T153736Z-c2-lite-text-static-layout-frame-scale-1280x736-s4500` | 29.184s | 14.815ms | 302.067ms | 256.981ms | 0.3610 | pass |
| `20260424T155703Z-c2-lite-text-static-layout-element-frame-scale-1280x736-s4500` | 29.231s | 14.513ms | 441.822ms | 244.547ms | 0.7321 | pass |
| `20260424T155913Z-c2-lite-text-static-layout-element-frame-scale-1280x736-s4500` | 29.455s | 15.504ms | 401.190ms | 546.285ms | 0.4124 | pass |

The stronger C0 run reduced pixel MSE but did not improve OCR. C2-lite improved the OCR proxy while adding visible motion. The first glyph-weighted C2-lite run stayed just as fast, but did not improve OCR over the unweighted C2 baseline. The C2.1 text-box run is the first text-specific improvement.

The C2-lite run adds a learned time-conditioned motion field that samples from the same persistent canvas. It produces visible motion, loops cleanly, and still stays well inside the live budget.

The glyph-weighted C2-lite run oversamples high-frequency/dark regions and weights loss on likely glyph pixels. It is useful as a negative result: simple edge attention is not enough to preserve exact text.

The C2.1 run uses OCR word boxes from the source fixture:

```text
train resolution:       1280x736
OCR boxes:              105
text mask coverage:     15.4%
text-box samples:       55% of each batch
text-box loss weight:   8x
edge samples/loss:      10% / 1x
```

This is the first sign that text-specific supervision helps the neural canvas. It improved OCR token-F1 from `0.8326` to `0.8545` while remaining under the chunk target.

## Dramatic Motion Stress Test

The first C2.2 stress test replaces the subtle jiggle with a looped frame-scale target and renders the video through an additional zoom-pulse viewport. This is closer to the resize/reposition pressure we actually care about.

```text
strong stress:
  motion_mode:          frame-scale
  motion_strength:      0.18
  viewport_zoom:        0.18
  motion_delta:         0.0707
  OCR token-F1:         0.0000

moderate stress:
  motion_mode:          frame-scale
  motion_strength:      0.06
  viewport_zoom:        0.08
  motion_delta:         0.0432
  OCR token-F1:         0.1053
```

This is a useful negative result. The renderer remains fast, but the text becomes horizontal streaks under frame-scale motion. The current learned flow head is enough for small stable motion and viewport queries, but not for layout-like repositioning.

## C2.3 Layout-Transform Result

C2.3 separates stable content from frame/layout motion:

```text
train:
  stable text-box-weighted canvas
  no learned motion target

render:
  every output pixel still queries the neural canvas
  frame-scale motion is an inverse coordinate transform at render time
  invalid outside-canvas pixels become page background
```

This directly tests the hypothesis from the C2.2 failure: text should move because the query/layout changes, not because a dense learned motion field repaints the text.

```text
moderate layout transform:
  layout_transform_strength: 0.08
  motion_delta:              0.0455
  OCR token-F1:              0.7091

strong layout transform:
  layout_transform_strength: 0.18
  motion_delta:              0.0600
  OCR token-F1:              0.3610
```

Compared with C2.2, this is a large improvement at the same stress levels:

```text
moderate: 0.1053 -> 0.7091
strong:   0.0000 -> 0.3610
```

The text is still not product-grade under strong resize, but the architecture is clearly better: stable content identity plus layout-time transforms beats learned dense motion for frame sizing.

## C2.4 Element-Anchor Result

C2.4 adds OCR-derived line anchors on top of C2.3. The page still renders from the stable neural canvas, but text-line regions get their own gentler scale during frame-size motion.

```text
global page:
  frame-scale layout transform

text lines:
  12 OCR-derived line anchors
  element_scale_ratio: 0.25
  each line patch is re-queried from the learned canvas
```

This is still neural rendering: the line patches are not DOM text. They are additional model-rendered pixel queries from the same stable canvas.

```text
moderate stress:
  C2.3 global layout OCR:   0.7091
  C2.4 line anchors OCR:    0.7321
  render_33_wall_ms:        302.278ms -> 441.822ms

strong stress:
  C2.3 global layout OCR:   0.3610
  C2.4 line anchors OCR:    0.4124
  render_33_wall_ms:        302.067ms -> 401.190ms
```

C2.4 is a positive but modest quality improvement. The tradeoff is latency: this first implementation renders anchor patches sequentially. It still beats realtime, but the next version should batch element queries.

## Artifacts

Showcase:

```text
outputs/track-c/showcase-c0-20260424.jpg
outputs/track-c/showcase-c2-lite-20260424.jpg
outputs/track-c/showcase-c2-glyph-20260424.jpg
outputs/track-c/showcase-c21-text-20260424.jpg
outputs/track-c/showcase-c22-frame-scale-20260424.jpg
outputs/track-c/showcase-c22-frame-scale-moderate-20260424.jpg
outputs/track-c/showcase-c23-layout-frame-scale-20260424.jpg
outputs/track-c/showcase-c23-layout-frame-scale-strong-20260424.jpg
outputs/track-c/showcase-c24-element-frame-scale-20260424.jpg
outputs/track-c/showcase-c24-element-frame-scale-strong-20260424.jpg
```

Best current run:

```text
outputs/track-c/20260424T141858Z-c0-canvas-960x544-s5000/
outputs/track-c/20260424T142739Z-c2-lite-960x544-s3000/
outputs/track-c/20260424T145821Z-c2-lite-glyph-960x544-s4000/
outputs/track-c/20260424T151017Z-c2-lite-text-1280x736-s4500/
outputs/track-c/20260424T152249Z-c2-lite-text-frame-scale-1280x736-s4500/
outputs/track-c/20260424T152418Z-c2-lite-text-frame-scale-1280x736-s4500/
outputs/track-c/20260424T153539Z-c2-lite-text-static-layout-frame-scale-1280x736-s4500/
outputs/track-c/20260424T153736Z-c2-lite-text-static-layout-frame-scale-1280x736-s4500/
outputs/track-c/20260424T155703Z-c2-lite-text-static-layout-element-frame-scale-1280x736-s4500/
outputs/track-c/20260424T155913Z-c2-lite-text-static-layout-element-frame-scale-1280x736-s4500/
```

Key files:

```text
render-512.png
render-960.png
crop-2x.png
crop-shifted.png
render-viewport-mid.png
render-layout-mid.png
render-element-mid.png
text-mask.png
text-boxes.json
output.mp4
metrics.json
quality.json
```

## Takeaways

- The persistent renderer abstraction works mechanically.
- Rendering is very fast: C0 `960x544` still renders in roughly `4-5ms`, and C2 motion renders in roughly `15-16ms` on Modal L40S.
- A 33-frame sequence renders far under the `1.3s` target before encoding.
- Crops and resize queries work from the same canvas.
- Text preservation is much better than fast full-frame LTX, but still not source-faithful enough.
- More MSE training alone does not solve glyph fidelity.
- Time-conditioned rendering works: C2-lite produced `33` moving frames in about `300ms`, with `~230ms` encode time.
- The C2-lite motion was trained from a synthetic smooth motion target. This proves the interface, not yet semantic motion.
- Simple glyph-biased sampling/loss did not beat the unweighted C2-lite OCR score: `0.8288` vs `0.8326`.
- The live budget remains comfortable: glyph C2 rendered and encoded `33` frames in about `568ms`.
- OCR-box-weighted training did improve text: `0.8545` vs the previous `0.8326`.
- The C2.1 text-box run trained at `1280x736` but still rendered `33` frames at `960x544` in about `301ms`.
- The first render measurement was slower at `43.8ms`, likely including warmup/cache effects; the 33-frame wall time is the better steady-state signal here.
- Encode time rose to `633.9ms` on this run, but render+encode still finished in about `935ms`.
- The jiggle test is not a strong enough stress test for the product vision.
- Frame-scale motion is the current failure boundary: even moderate scaling kept render latency near `299ms` for `33` frames but dropped OCR to `0.1053`.
- The current architecture can animate pixels, but it does not know how to re-layout or reposition text as symbolic content.
- C2.3 shows the better split: train a stable neural canvas, then apply frame sizing as a render/query transform.
- C2.3 keeps the 33-frame render near `302ms` while recovering text under resize stress.
- This is still neural rendering, not DOM/CSS: every visible content pixel is queried from the learned canvas.
- C2.4 line anchors improve resize-stress OCR modestly but increase render time to `~401-442ms` for `33` frames.
- Element anchoring looks like the right direction, but the implementation needs batched anchor queries and better masks.

## Next Step

Move from C2.4 to a batched element-aware neural canvas:

```text
same persistent neural canvas
separate stable content identity from motion/layout transforms
score OCR/token F1 under resize/reposition stress
keep render contract unchanged
```

Possible C2.5 interventions:

- batch all element anchor queries into one model call per frame
- use alpha/mask maps for text anchors instead of rectangular patch replacement
- split anchors into title/body/diagram/callout groups with different scale rules
- train at `1536x864`, then render down to `960x544`
- split OCR boxes into word/line masks and weight small text more than large headings
- add differentiable edge/Sobel loss only inside detected text boxes
- add perceptual/text recognition loss from a frozen OCR/text encoder
- supervise per-element boxes or anchors, not only per-pixel flow
- let the canvas store text/diagram identity and render from layout-time transforms
- replace the global frame-scale transform with per-element anchors and constraints
- evaluate against a target OCR crop for each transformed viewport, not only whole-page OCR
- try a sharper decoder with skip access to high-resolution canvas features

The strategic next proof remains C1: a more compact multiscale latent feature canvas that preserves the C0 render contract without storing full-resolution features.
