# Human Review Notes

Date: 2026-04-24

## Human-Positive / Metric-Negative Case

Run:

```text
outputs/track-c/20260424T174026078431Z-c2-lite-text-static-layout-element-frame-scale-c26-word-rect-r010-1280x736-s4500/output.mp4
```

User review:

```text
"this one looks very good"
```

Automated eval:

```text
scenario:          frame-scale-strong
anchor mode:       word
element ratio:     0.10
OCR token-F1:      0.1143
render_33_wall_ms: 3172.452
encode_ms:         526.506
segment_wall_ms:   3698.959
```

Interpretation:

- OCR is likely underrating this run because the visual output reads better than the token match suggests.
- Word-sized support regions preserve local visual context better than glyph-only alpha and may avoid dragging large unrelated illustration regions.
- The current implementation is too slow because `105` word patches are rendered sequentially for every frame.

Decision:

```text
Do not discard word anchors.
Prioritize batched word-anchor rendering.
Add human-review status to future eval summaries.
```

Next experiments:

```text
c28-word-batched-r010
c28-word-batched-moderate-r010
c28-line-batched-r005
```

## Positive Low-Aggression Motion Baseline

Run:

```text
outputs/track-c/20260424T151017Z-c2-lite-text-1280x736-s4500/output.mp4
```

User review:

```text
"less aggressive motion, but the animation did work well with the text"
```

Automated eval:

```text
scenario:          still-full-resize / gentle learned motion
flow_scale:        0.005
OCR token-F1:      0.8545
render_33_wall_ms: 301.365
encode_ms:         633.911
segment_wall_ms:   935.276
motion_delta:      0.0158
loop_error:        0.0008
```

Interpretation:

- Gentle learned motion can coexist with stable, readable text.
- The failure boundary is not animation itself; it is aggressive resize/reflow pressure and large coordinate deformation.
- The eval plan should keep separate "pleasant motion" scenarios from stress scenarios.

Decision:

```text
Keep C2.1 as the positive gentle-motion baseline.
Add a gentle-motion ladder so the pleasant-motion boundary is measured, not guessed.
```

Follow-up measurements:

```text
c29-gentle-flow-010: OCR 0.8402, segment 548.963ms, motion_delta 0.0297, pass
c29-gentle-flow-020: OCR 0.7123, segment 509.898ms, motion_delta 0.0489, quality_fail
c29-product-layout-r0025: OCR 0.7713, segment 627.449ms, motion_delta 0.0295, pass
c30-gentle-flow-0125: OCR 0.8545, segment 525.153ms, motion_delta 0.0353, pass
c30-gentle-flow-015: OCR 0.7615, segment 540.984ms, motion_delta 0.0411, quality_fail
c30-product-layout-r0025-s008: OCR 0.7580, segment 631.642ms, motion_delta 0.0455, pass
c30-line-batched-r0025-strong: OCR 0.4976, segment 627.692ms, motion_delta 0.0616, quality_fail
```

Interpretation:

- The text-friendly motion boundary appears between `flow_scale=0.0125` and `flow_scale=0.015` for learned jiggle motion.
- Low-strength layout motion with line anchors gives similar visible motion while preserving text better than raw learned flow.
- Moderate layout-anchor motion still passes, but `c30-gentle-flow-0125` is the cleanest pleasant-motion result so far because it preserves the original C2.1 OCR while adding more motion and lowering segment time.
- Batching the best strong-stress `r0.025` line-anchor setting preserves latency but loses too much text quality versus the earlier sequential result, so the next batching work should focus on exact pixel parity or overlap/order effects.

## Generalizable Neural-Canvas Direction

Run:

```text
outputs/track-c/20260424T183934556364Z-c2-lite-text-c30-gentle-flow-0125-1280x736-s4500/output.mp4
```

User review:

```text
"something tells me this is probably more of the correct direction ... the text masking works, but it's not really generalizable. Not all text will be clean squares."
```

Interpretation:

- The promising direction is learned-flow neural canvas rendering where every output pixel still comes from the model query path.
- OCR boxes, line anchors, word anchors, and rectangular replacement masks are useful probes, but they are too shape-specific to be the core product mechanism.
- The next experiments should test whether dense visual priors, especially edge/glyph weighting without OCR text boxes, can keep arbitrary high-frequency marks readable.

Next experiments:

```text
c31-general-flow-0125-edge1
c31-general-flow-0125-edge4
c31-general-flow-010-edge4
c31-general-flow-0125-edge8
c31-text-flow-0135-box8
c31-text-flow-014-box8
c31-text-flow-0125-box12
c31-alpha-layout-r0025-s004
```

Parallelism update:

```text
MAX_PARALLEL = 6
```

Decision:

- Pursue both tracks in parallel.
- Track C31-general tests the thesis: neural canvas pixels stay readable without text boxes.
- Track C31-text keeps OCR boxes only as a training signal, not a render-time mask.
- Track C31-alpha tests a shape-aware bridge for cases where a practical text-preserving mechanism is still useful.

Early C31 results:

```text
c31-general-flow-0125-edge1: OCR 0.8219, segment 521.440ms, motion_delta 0.0341, pass
c31-general-flow-010-edge4: OCR 0.8288, segment 894.055ms, motion_delta 0.0292, pass
c31-general-flow-0125-edge4: OCR 0.4679, segment 544.087ms, motion_delta 0.0348, quality_fail
c31-general-flow-0125-edge8: OCR 0.7037, segment 584.051ms, motion_delta 0.0347, quality_fail
c31-text-flow-0135-box8: OCR 0.8440, segment 546.841ms, motion_delta 0.0384, pass
```

Interpretation:

- Dense visual weighting can work without OCR boxes, but over-weighting edges hurts text more than it helps.
- The best no-OCR result so far is light edge weighting at the C30 flow sweet spot.
- The best bridge result so far is OCR-box training loss only at `flow_scale=0.0135`; there is still no render-time text mask.

Next experiments:

```text
c32-general-flow-0125-edge05
c32-general-flow-0135-edge1
c32-text-flow-0145-box8
c32-text-flow-0135-box12
```

## Modal Scale-Up

Decision:

- Raise the default autonomous loop cap to `10` concurrent Track C experiment sessions.
- Keep the cap configurable with `TRACK_C_MAX_PARALLEL`.
- Scale horizontally across independent Modal L40S runs before changing the renderer architecture.
- Run both pure no-OCR and text-aware bridge experiments in the same wave.

Completed C32 results:

```text
c32-general-flow-0125-edge05: OCR 0.8440, segment 575.076ms, motion_delta 0.0342, pass
c32-general-flow-0135-edge1: OCR 0.8519, segment 560.209ms, motion_delta 0.0358, pass
c32-text-flow-0145-box8: OCR 0.7421, segment 557.677ms, motion_delta 0.0393, quality_fail
c32-text-flow-0135-box12: OCR 0.8402, segment 573.293ms, motion_delta 0.0373, pass
```

Interpretation:

- The pure no-OCR path is now the strongest current direction: `c32-general-flow-0135-edge1` nearly matches the original C2.1 OCR while avoiding text boxes entirely.
- The bridge path still helps, but pushing box-weighted flow past `0.0135` is fragile.
- The next larger Modal wave should emphasize no-OCR flow/edge/capacity sweeps while keeping a smaller bridge bracket alive.

Next experiments:

```text
c33-general-flow-0135-edge075
c33-general-flow-0135-edge15
c33-general-flow-014-edge1
c33-general-flow-01425-edge1
c33-general-flow-0135-edge1-s6000
c33-general-flow-0135-edge1-cap24h128
c33-general-flow-014-edge05
c33-text-flow-01375-box8
c33-text-flow-0135-box6
c33-general-responsive-012-edge1
```

## Overfitting And Generalization

Status:

```text
Track C is overfit by design.
Track D is the generalization track.
```

Interpretation:

- The current Track C renderer fits one page and asks whether a persistent neural canvas can render it fast, resize it, animate it, and preserve high-frequency detail.
- This is the right first proof because a general model will not fix a renderer that cannot preserve a known page.
- The C32 no-OCR result reduces the risk that the approach only works through text boxes or rectangular masks, but it is still a single-page result.

Decision:

- Keep scaling Track C on Modal to characterize the renderer.
- Start Track D once the C33 no-OCR sweeps settle: build a multi-page fixture generator, train an amortized encoder/prior, and evaluate held-out pages.
- Do not claim generality until held-out pages pass without render-time text masks.

Reference:

```text
docs/research/track-d-general-neural-canvas.md
```

## C33 Result And C35 Stress Pivot

Completed C33 highlights:

```text
c33-general-flow-014-edge1: OCR 0.8767, segment 565.333ms, motion_delta 0.0371, pass
c33-general-responsive-012-edge1: OCR 0.8676, segment 570.907ms, motion_delta 0.0405, pass
c33-general-flow-014-edge05: OCR 0.8430, segment 559.672ms, motion_delta 0.0370, pass
c33-text-flow-0135-box6: OCR 0.8479, segment 545.589ms, motion_delta 0.0379, pass
```

Interpretation:

- The best pure no-OCR run now beats the earlier text-box-weighted C30 local-motion score.
- This is excellent renderer evidence, but the current best case is still mostly local wiggle.
- Local wiggle can hide failures that show up when the viewport moves, the frame scales, or text must be repositioned.

Decision:

- Treat local wiggle as a control, not the main proof.
- Make C35 primarily an aggressive movement suite:
  - viewport zoom/pan at multiple amplitudes
  - global frame-scale resize/reposition pressure
  - responsive squeeze plus viewport zoom
  - one local-motion control for comparison
- Keep all C35 primary tests on the pure no-OCR path: no text boxes, no masks, no anchors.
