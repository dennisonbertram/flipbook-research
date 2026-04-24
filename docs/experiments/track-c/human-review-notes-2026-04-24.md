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
