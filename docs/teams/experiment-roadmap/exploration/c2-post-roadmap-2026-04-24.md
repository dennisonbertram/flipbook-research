# Neural Canvas Experiment Roadmap After C2.4

Date: 2026-04-24

## Baseline

C2.4 is the current post-C2 reference point:

| Stress | OCR token-F1 | 33 render wall | Note |
| --- | ---: | ---: | --- |
| Moderate element-frame-scale | 0.7321 | 441.822ms | OCR line anchors help modestly. |
| Strong element-frame-scale | 0.4124 | 401.190ms | Text remains below product quality. |

The next work should preserve the Track C rule: every visible content pixel is rendered by the model from the persistent canvas. No source text overlay, DOM text layer, or copied glyph safety pass in these experiments. Those are valid Track B/product controls, but they do not answer the neural-canvas question.

Common metrics for all runs:

- `render_33_wall_ms + encode_ms <= 1300`
- `ocr_similarity`, plus line/crop OCR where available
- `motion_delta >= 0.04` for resize/reflow stress, `>= 0.07` for dramatic motion
- `temporal_consistency >= 0.98` and low loop error
- resize/reflow visual review: text remains readable, anchors do not overlap, page identity is stable

## Highest Learning, Low Cost

### E1. C2.5 Anchor-Scale Sweep

Hypothesis: C2.4 gains come mainly from letting text-line patches scale less than the global frame. A lower `element_scale_ratio` may improve strong-stress OCR, but too low will cause overlap or detached text.

Run:

```bash
tmux new-session -d -s track-c-c25-anchor-ratio '
cd /Users/dennisonbertram/Develop/flipbook-research || exit 1
for ratio in 0.00 0.10 0.25 0.50; do
  modal run scripts/track_c/modal_canvas_c2_lite.py --steps 4500 --train-resolution 1280x736 --flow-scale 0 --motion-mode static --motion-strength 0 --video-layout-mode element-frame-scale --layout-transform-strength 0.18 --layout-transform-pan 0.035 --element-scale-ratio "$ratio" --element-anchor-padding 4 --edge-sample-ratio 0.1 --edge-loss-weight 1.0 --text-box-sample-ratio 0.55 --text-box-loss-weight 8.0 --text-box-padding 4 --text-box-min-conf 55 --min-ocr-similarity 0.35 > "docs/experiments/track-c/c25-anchor-ratio-${ratio}.log" 2>&1
done
'
```

Expected metrics: best strong OCR rises from `0.4124` toward `0.50+`; render time may stay `400-500ms` until batching exists.

Stop when: best ratio is identified, or all ratios stay within `0.03` OCR of C2.4 while adding visible overlap.

### E2. High-Resolution Text Supervision Sweep

Hypothesis: stronger local text supervision at `1536x864` can improve glyph fidelity without symbolic hacks, especially when rendering down to `960x544`.

Run:

```bash
tmux new-session -d -s track-c-c25-hires-text '
cd /Users/dennisonbertram/Develop/flipbook-research || exit 1
modal run scripts/track_c/modal_canvas_c2_lite.py --steps 5500 --train-resolution 1536x864 --batch-size 131072 --flow-scale 0 --motion-mode static --motion-strength 0 --video-layout-mode element-frame-scale --layout-transform-strength 0.18 --layout-transform-pan 0.035 --element-scale-ratio 0.10 --element-anchor-padding 4 --edge-sample-ratio 0.1 --edge-loss-weight 1.0 --text-box-sample-ratio 0.65 --text-box-loss-weight 12.0 --text-box-padding 5 --text-box-min-conf 55 --min-ocr-similarity 0.45 > docs/experiments/track-c/c25-hires-text-strong.log 2>&1
'
```

Expected metrics: strong OCR improves by `>= 0.08`; `crop-2x` OCR improves; compile time can rise, but render+encode must remain under budget.

Stop when: high-res training does not beat C2.4 by `0.05` OCR, or first-frame render becomes consistently `> 60ms`.

### E3. Dense Reflow Failure Boundary

Hypothesis: learned dense coordinate motion still fails under responsive/reflow-like movement, even with OCR-box weighting. Quantifying that boundary prevents over-investing in flow-only motion.

Run:

```bash
tmux new-session -d -s track-c-c25-responsive-squeeze '
cd /Users/dennisonbertram/Develop/flipbook-research || exit 1
modal run scripts/track_c/modal_canvas_c2_lite.py --steps 4500 --train-resolution 1280x736 --flow-scale 0.10 --motion-mode responsive-squeeze --motion-strength 0.10 --video-viewport-mode zoom-pulse --viewport-zoom 0.08 --viewport-pan 0.015 --edge-sample-ratio 0.1 --edge-loss-weight 1.0 --text-box-sample-ratio 0.55 --text-box-loss-weight 8.0 --text-box-padding 4 --text-box-min-conf 55 --min-ocr-similarity 0.25 > docs/experiments/track-c/c25-responsive-squeeze.log 2>&1
'
```

Expected metrics: motion is visible, but OCR likely falls below C2.3/C2.4 layout-transform runs. This gives a hard "do not use dense flow for reflow" result.

Stop when: OCR is below `0.35` at `motion_delta >= 0.04`, or if it unexpectedly beats `0.60`, run a stronger `motion_strength=0.16` repeat.

## Highest Learning, Moderate Cost

### E4. Batched OCR Line Anchors

Hypothesis: C2.4 quality can be preserved while recovering C2.3-like speed by batching all anchor patch coordinates into one renderer query per frame.

Required code: add an `--element-render-mode batched` path to `modal_canvas_c2_lite.py`.

Target run:

```bash
tmux new-session -d -s track-c-c26-batched-anchors '
cd /Users/dennisonbertram/Develop/flipbook-research || exit 1
modal run scripts/track_c/modal_canvas_c2_lite.py --steps 4500 --train-resolution 1280x736 --flow-scale 0 --motion-mode static --motion-strength 0 --video-layout-mode element-frame-scale --element-render-mode batched --layout-transform-strength 0.18 --layout-transform-pan 0.035 --element-scale-ratio 0.10 --element-anchor-padding 4 --edge-sample-ratio 0.1 --edge-loss-weight 1.0 --text-box-sample-ratio 0.55 --text-box-loss-weight 8.0 --text-box-padding 4 --text-box-min-conf 55 --min-ocr-similarity 0.45 > docs/experiments/track-c/c26-batched-anchors.log 2>&1
'
```

Expected metrics: strong OCR within `0.02` of the best E1 run; `render_33_wall_ms <= 330ms`.

Stop when: batching fails to cut render wall time by at least `25%`, or quality changes because batching no longer exactly matches sequential patch queries.

### E5. Model-Rendered Alpha Anchors

Hypothesis: rectangular patch replacement is too crude. A model-rendered alpha or text-importance mask can blend line patches without copying source pixels, reducing seams and overlap while keeping glyphs readable.

Required code: add `--element-mask-mode text-alpha` and a seam metric around anchor borders.

Target run:

```bash
tmux new-session -d -s track-c-c27-alpha-anchors '
cd /Users/dennisonbertram/Develop/flipbook-research || exit 1
modal run scripts/track_c/modal_canvas_c2_lite.py --steps 5000 --train-resolution 1280x736 --flow-scale 0 --motion-mode static --motion-strength 0 --video-layout-mode element-frame-scale --element-render-mode batched --element-mask-mode text-alpha --layout-transform-strength 0.18 --layout-transform-pan 0.035 --element-scale-ratio 0.10 --element-anchor-padding 6 --edge-sample-ratio 0.1 --edge-loss-weight 1.0 --text-box-sample-ratio 0.60 --text-box-loss-weight 10.0 --text-box-padding 5 --text-box-min-conf 55 --min-ocr-similarity 0.45 > docs/experiments/track-c/c27-alpha-anchors.log 2>&1
'
```

Expected metrics: OCR holds or improves; seam score improves; layout similarity does not drop. All pixels still come from neural-canvas queries.

Stop when: alpha reduces OCR by `> 0.03`, or seams remain visible after one padding/feather sweep.

### E6. Element Reflow Instead Of Global Frame Scale

Hypothesis: real resize/reflow requires per-element transforms, not one global scale plus text rescue. Grouped OCR lines, diagram blocks, and card-like regions should move as model-rendered elements.

Required code: add `--video-layout-mode element-reflow` with a deterministic two-column-to-stacked stress profile.

Target run:

```bash
tmux new-session -d -s track-c-c28-element-reflow '
cd /Users/dennisonbertram/Develop/flipbook-research || exit 1
modal run scripts/track_c/modal_canvas_c2_lite.py --steps 5000 --train-resolution 1280x736 --flow-scale 0 --motion-mode static --motion-strength 0 --video-layout-mode element-reflow --reflow-profile two-column-stack --reflow-strength 1.0 --element-render-mode batched --element-mask-mode text-alpha --edge-sample-ratio 0.1 --edge-loss-weight 1.0 --text-box-sample-ratio 0.60 --text-box-loss-weight 10.0 --text-box-padding 5 --text-box-min-conf 55 --min-ocr-similarity 0.50 > docs/experiments/track-c/c28-element-reflow.log 2>&1
'
```

Expected metrics: line OCR `>= 0.60` under moderate reflow, overlap/invalid-region metrics reported, and motion reads as responsive layout rather than page zoom.

Stop when: per-element motion cannot beat global C2.4 strong OCR by `0.10`, or readable text requires freezing/copying source pixels.

## Strategic, Higher Cost

### E7. Text Identity Tokens In The Canvas

Hypothesis: exact text preservation needs identity-bearing state, not only per-pixel MSE. The canvas can store OCR line text as latent/text tokens and render glyph pixels through a local neural decoder while still producing final pixels model-side.

Required code: new text-token renderer path, probably `scripts/track_c/modal_canvas_c29_text_tokens.py`.

Target run:

```bash
tmux new-session -d -s track-c-c29-text-tokens '
cd /Users/dennisonbertram/Develop/flipbook-research || exit 1
modal run scripts/track_c/modal_canvas_c29_text_tokens.py --steps 6000 --train-resolution 1280x736 --token-source ocr-lines --decoder local-glyph --video-layout-mode element-frame-scale --layout-transform-strength 0.18 --layout-transform-pan 0.035 --element-scale-ratio 0.10 --frames 33 --fps 24 --min-ocr-similarity 0.60 > docs/experiments/track-c/c29-text-tokens.log 2>&1
'
```

Expected metrics: strong OCR improves by `>= 0.15` over C2.4; per-line edit distance is reported; no original glyph pixels are composited.

Stop when: the one-page overfit cannot exceed `0.60` strong OCR, because a general compiler will not fix a renderer that cannot preserve known text.

### E8. Dramatic Non-Text Motion Head

Hypothesis: dramatic motion should be carried by material/parallax/background residuals and layout transforms, while text receives very small model-rendered deformation. This tests "lively, not melting" motion without text overlays.

Required code: add a factorized residual/material motion head with text-box motion penalties.

Target run:

```bash
tmux new-session -d -s track-c-c30-material-motion '
cd /Users/dennisonbertram/Develop/flipbook-research || exit 1
modal run scripts/track_c/modal_canvas_c30_material_motion.py --steps 6000 --train-resolution 1280x736 --motion-profile parallax-shimmer-scale --motion-strength 0.18 --text-motion-budget 0.02 --video-layout-mode element-frame-scale --layout-transform-strength 0.08 --layout-transform-pan 0.015 --frames 33 --fps 24 --min-motion-delta 0.07 --min-ocr-similarity 0.70 > docs/experiments/track-c/c30-material-motion.log 2>&1
'
```

Expected metrics: `motion_delta >= 0.07`, moderate OCR `>= 0.70`, strong visual motion in non-text regions, text jitter metric near zero.

Stop when: motion is only perceptible by damaging text, or motion remains below `0.05` after two profiles.

### E9. Multi-Fixture Neural Canvas Robustness

Hypothesis: the current result may be overfit to one page geometry. Before a real compiler, test whether the renderer recipe works across several text/diagram densities.

Required code/data: add 4-6 fixtures and a multi-fixture runner that appends per-fixture metrics.

Target run:

```bash
tmux new-session -d -s track-c-c31-multi-fixture '
cd /Users/dennisonbertram/Develop/flipbook-research || exit 1
modal run scripts/track_c/modal_canvas_c31_multi_fixture.py --fixture-set docs/experiments/track-c/fixture-set-v1.json --steps 5000 --train-resolution 1280x736 --renderer element-alpha-anchors --stress-set frame-scale,strong-reflow,crop-2x --frames 33 --fps 24 > docs/experiments/track-c/c31-multi-fixture.log 2>&1
'
```

Expected metrics: median and p10 OCR across fixtures, per-fixture render time, crop OCR, and failure thumbnails.

Stop when: p10 OCR under strong stress is below `0.45`, or failures cluster around small text/diagrams that need a new representation.

### E10. Compact Multiscale Canvas

Hypothesis: a full-resolution feature grid proves the interface but is not the final representation. A multiscale latent/hash-style canvas should preserve C2.4 quality with lower memory and better zoom behavior.

Required code: new multiscale canvas backend, e.g. `scripts/track_c/modal_canvas_c32_multiscale.py`.

Target run:

```bash
tmux new-session -d -s track-c-c32-multiscale '
cd /Users/dennisonbertram/Develop/flipbook-research || exit 1
modal run scripts/track_c/modal_canvas_c32_multiscale.py --steps 7000 --train-resolution 1280x736 --levels 4 --base-resolution 160x92 --features-per-level 8 --renderer element-alpha-anchors --layout-transform-strength 0.18 --layout-transform-pan 0.035 --frames 33 --fps 24 --min-ocr-similarity 0.45 > docs/experiments/track-c/c32-multiscale.log 2>&1
'
```

Expected metrics: memory/parameter count, render time, strong OCR within `0.05` of best full-grid C2.x, and better `crop-2x` OCR than C2.4.

Stop when: compactness costs more than `0.08` OCR without a clear zoom/latency gain.

## Parallelization Plan

Run E1, E2, and E3 immediately because they use the existing script and answer different questions. In parallel, split implementation work into independent branches/tasks:

- E4 owns performance of the current C2.4 idea.
- E5 owns text-preservation quality without source-pixel overlays.
- E6 owns resize/reflow stress beyond global scaling.
- E7 to E10 are strategic renderer-representation bets and should start only after E4/E5 identify the best anchor baseline.
