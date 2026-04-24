# Track C Neural Canvas Scripts

Track C tests the persistent neural canvas idea:

```text
compiled canvas + viewport + resolution + time -> pixels
```

## C0 Modal Run

The first runnable experiment overfits the existing text-heavy fixture into a learned latent feature canvas and renders it at multiple resolutions/crops.

```bash
tmux new-session -d -s track-c-c0 \
  "cd /Users/dennisonbertram/Develop/flipbook-research && modal run scripts/track_c/modal_canvas_c0.py --steps 1500 --train-resolution 960x544 > docs/experiments/track-c/c0-modal.log 2>&1"
```

Outputs:

```text
outputs/track-c/<run-id>/
  input.png
  render-512.png
  render-960.png
  crop-2x.png
  crop-shifted.png
  output.mp4
  metrics.json
  quality.json
```

This is a renderer-interface test, not a general model. Compile/training time is allowed to be slow at C0; the important measurements are render speed, resize/crop consistency, and text identity.

## C2-Lite Motion Run

C2-lite keeps a persistent latent canvas and learns a small time-conditioned motion field before decoding pixels:

```text
canvas + x/y + t -> learned flow -> sampled canvas features -> rgb
```

```bash
tmux new-session -d -s track-c-c2 \
  "cd /Users/dennisonbertram/Develop/flipbook-research && modal run scripts/track_c/modal_canvas_c2_lite.py --steps 3000 --train-resolution 960x544 --flow-scale 0.006 > docs/experiments/track-c/c2-modal.log 2>&1"
```

The glyph-weighted variant oversamples likely text/edge pixels and weights loss there:

```bash
tmux new-session -d -s track-c-c2-glyph \
  "cd /Users/dennisonbertram/Develop/flipbook-research && modal run scripts/track_c/modal_canvas_c2_lite.py --steps 4000 --train-resolution 960x544 --flow-scale 0.006 --edge-sample-ratio 0.7 --edge-loss-weight 4.0 > docs/experiments/track-c/c2-glyph-modal.log 2>&1"
```

Current result: the glyph-weighted run preserves the realtime render budget but does not improve OCR over the unweighted C2-lite baseline. Treat it as a useful negative result and move next toward OCR-box/text-aware supervision.

## C2.1 OCR-Box Text Run

C2.1 computes OCR word boxes locally with Tesseract, passes them into the Modal job, builds a text mask on the GPU, and uses that mask for sampling and loss weighting.

```bash
tmux new-session -d -s track-c-c21-text \
  "cd /Users/dennisonbertram/Develop/flipbook-research && modal run scripts/track_c/modal_canvas_c2_lite.py --steps 4500 --train-resolution 1280x736 --flow-scale 0.005 --edge-sample-ratio 0.1 --edge-loss-weight 1.0 --text-box-sample-ratio 0.55 --text-box-loss-weight 8.0 --text-box-padding 4 --text-box-min-conf 55 > docs/experiments/track-c/c21-text-modal.log 2>&1"
```

Current result: OCR-box weighting improved OCR token-F1 from `0.8326` to `0.8545` while keeping `33` renders at about `301ms` and render+encode under `1.0s`.

## C2.2 Frame-Scale Stress Run

C2.2 adds dramatic motion controls:

```text
--motion-mode frame-scale
--motion-strength <amount>
--video-viewport-mode zoom-pulse
--viewport-zoom <amount>
```

Strong stress:

```bash
tmux new-session -d -s track-c-c22-frame-scale \
  "cd /Users/dennisonbertram/Develop/flipbook-research && modal run scripts/track_c/modal_canvas_c2_lite.py --steps 4500 --train-resolution 1280x736 --flow-scale 0.16 --motion-mode frame-scale --motion-strength 0.18 --video-viewport-mode zoom-pulse --viewport-zoom 0.18 --viewport-pan 0.035 --edge-sample-ratio 0.1 --edge-loss-weight 1.0 --text-box-sample-ratio 0.55 --text-box-loss-weight 8.0 --text-box-padding 4 --text-box-min-conf 55 > docs/experiments/track-c/c22-frame-scale-modal.log 2>&1"
```

Moderate stress:

```bash
tmux new-session -d -s track-c-c22-frame-scale-moderate \
  "cd /Users/dennisonbertram/Develop/flipbook-research && modal run scripts/track_c/modal_canvas_c2_lite.py --steps 4500 --train-resolution 1280x736 --flow-scale 0.06 --motion-mode frame-scale --motion-strength 0.06 --video-viewport-mode zoom-pulse --viewport-zoom 0.08 --viewport-pan 0.015 --edge-sample-ratio 0.1 --edge-loss-weight 1.0 --text-box-sample-ratio 0.55 --text-box-loss-weight 8.0 --text-box-padding 4 --text-box-min-conf 55 > docs/experiments/track-c/c22-frame-scale-moderate-modal.log 2>&1"
```

Current result: both stress runs keep `33` renders near `299ms`, but text quality fails. Strong stress hits OCR token-F1 `0.0000`; moderate stress reaches only `0.1053`. Use this as the first hard boundary for the current flow-based renderer.

## C2.3 Layout-Transform Stress Run

C2.3 trains stable content and applies frame sizing as a render-time layout transform over the learned canvas.

Moderate layout transform:

```bash
tmux new-session -d -s track-c-c23-layout-frame-scale \
  "cd /Users/dennisonbertram/Develop/flipbook-research && modal run scripts/track_c/modal_canvas_c2_lite.py --steps 4500 --train-resolution 1280x736 --flow-scale 0 --motion-mode static --motion-strength 0 --video-layout-mode frame-scale --layout-transform-strength 0.08 --layout-transform-pan 0.015 --edge-sample-ratio 0.1 --edge-loss-weight 1.0 --text-box-sample-ratio 0.55 --text-box-loss-weight 8.0 --text-box-padding 4 --text-box-min-conf 55 --min-ocr-similarity 0.5 > docs/experiments/track-c/c23-layout-frame-scale-modal.log 2>&1"
```

Strong layout transform:

```bash
tmux new-session -d -s track-c-c23-layout-frame-scale-strong \
  "cd /Users/dennisonbertram/Develop/flipbook-research && modal run scripts/track_c/modal_canvas_c2_lite.py --steps 4500 --train-resolution 1280x736 --flow-scale 0 --motion-mode static --motion-strength 0 --video-layout-mode frame-scale --layout-transform-strength 0.18 --layout-transform-pan 0.035 --edge-sample-ratio 0.1 --edge-loss-weight 1.0 --text-box-sample-ratio 0.55 --text-box-loss-weight 8.0 --text-box-padding 4 --text-box-min-conf 55 --min-ocr-similarity 0.35 > docs/experiments/track-c/c23-layout-frame-scale-strong-modal.log 2>&1"
```

Current result: C2.3 keeps render speed near `302ms` for `33` frames and improves resize-stress OCR from `0.1053` to `0.7091` on moderate motion, and from `0.0000` to `0.3610` on strong motion.

## C2.4 OCR Line Anchor Stress Run

C2.4 adds OCR-derived text-line anchors. The global page uses a layout transform, while each line anchor is re-rendered from the stable canvas with a gentler scale.

Moderate element-anchor transform:

```bash
tmux new-session -d -s track-c-c24-element-frame-scale \
  "cd /Users/dennisonbertram/Develop/flipbook-research && modal run scripts/track_c/modal_canvas_c2_lite.py --steps 4500 --train-resolution 1280x736 --flow-scale 0 --motion-mode static --motion-strength 0 --video-layout-mode element-frame-scale --layout-transform-strength 0.08 --layout-transform-pan 0.015 --element-scale-ratio 0.25 --element-anchor-padding 4 --edge-sample-ratio 0.1 --edge-loss-weight 1.0 --text-box-sample-ratio 0.55 --text-box-loss-weight 8.0 --text-box-padding 4 --text-box-min-conf 55 --min-ocr-similarity 0.5 > docs/experiments/track-c/c24-element-frame-scale-modal.log 2>&1"
```

Strong element-anchor transform:

```bash
tmux new-session -d -s track-c-c24-element-frame-scale-strong \
  "cd /Users/dennisonbertram/Develop/flipbook-research && modal run scripts/track_c/modal_canvas_c2_lite.py --steps 4500 --train-resolution 1280x736 --flow-scale 0 --motion-mode static --motion-strength 0 --video-layout-mode element-frame-scale --layout-transform-strength 0.18 --layout-transform-pan 0.035 --element-scale-ratio 0.25 --element-anchor-padding 4 --edge-sample-ratio 0.1 --edge-loss-weight 1.0 --text-box-sample-ratio 0.55 --text-box-loss-weight 8.0 --text-box-padding 4 --text-box-min-conf 55 --min-ocr-similarity 0.35 > docs/experiments/track-c/c24-element-frame-scale-strong-modal.log 2>&1"
```

Current result: OCR line anchors improve resize-stress OCR from `0.7091` to `0.7321` on moderate motion and from `0.3610` to `0.4124` on strong motion. Render time rises to about `401-442ms` for `33` frames because anchor patches are rendered sequentially.
