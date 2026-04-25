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

Completed C35 results:

```text
c35-viewport-014-edge1-z006: OCR 0.8727, segment 550.121ms, motion_delta 0.0488, pass
c35-viewport-014-edge1-z010: OCR 0.8624, segment 561.603ms, motion_delta 0.0549, pass
c35-viewport-014-edge1-z014: OCR 0.8664, segment 521.386ms, motion_delta 0.0608, pass
c35-responsive-014-edge1-z006: OCR 0.8597, segment 572.338ms, motion_delta 0.0411, pass
c35-responsive-016-edge1-z008: OCR 0.8636, segment 562.553ms, motion_delta 0.0501, pass
c35-frame-scale-008-edge1: OCR 0.7558, segment 555.382ms, motion_delta 0.0470, pass
c35-frame-scale-012-edge09: OCR 0.6636, segment 558.614ms, motion_delta 0.0567, pass
c35-frame-scale-012-edge1: OCR 0.5806, segment 596.264ms, motion_delta 0.0563, pass
c35-frame-scale-016-edge1: OCR 0.4039, segment 548.567ms, motion_delta 0.0599, near_miss
c35-control-wiggle-014-edge1: OCR 0.7854, segment 571.064ms, motion_delta 0.0373, near_miss
```

Interpretation:

- Viewport zoom/pan is not the weak point; it preserves text better than expected even at the highest C35 zoom.
- Responsive squeeze plus zoom is also strong on the pure no-OCR path.
- Global frame-scale resize is the real cliff: 0.08 is comfortable, 0.12 degrades but passes, 0.16 is near the failure boundary.
- The seeded wiggle control dropped far below the earlier unseeded C33 best, so optimization variance matters and single-seed wins should not be over-trusted.

Next experiments:

```text
c36-frame-scale-014-edge075
c36-frame-scale-014-edge09
c36-frame-scale-014-edge1
c36-frame-scale-016-edge075
c36-frame-scale-016-edge09
c36-frame-scale-016-edge09-s6000
c36-frame-scale-018-edge075
c36-frame-scale-018-edge05
c36-learned-frame-scale-006-flow04
c36-learned-frame-scale-008-flow05
```

Decision:

- Focus C36 on the resize/reposition cliff.
- Keep the main path no-OCR and mask-free.
- Add two learned frame-scale runs to test whether the renderer can learn nonlocal resize motion directly, rather than only using a canonical canvas query transform.

## C36 Resize Cliff Results

Completed C36 results:

```text
c36-frame-scale-014-edge09: OCR 0.5634, segment 547.378ms, motion_delta 0.0592, pass
c36-frame-scale-014-edge075: OCR 0.5505, segment 556.587ms, motion_delta 0.0593, pass
c36-frame-scale-014-edge1: OCR 0.5278, segment 543.993ms, motion_delta 0.0599, pass
c36-frame-scale-016-edge075: OCR 0.4327, segment 553.084ms, motion_delta 0.0597, pass
c36-frame-scale-016-edge09: OCR 0.2657, segment 544.929ms, motion_delta 0.0615, quality_fail
c36-frame-scale-016-edge09-s6000: OCR 0.4607, segment 554.590ms, motion_delta 0.0588, pass
c36-frame-scale-018-edge075: OCR 0.3689, segment 552.580ms, motion_delta 0.0607, pass
c36-frame-scale-018-edge05: OCR 0.3925, segment 555.626ms, motion_delta 0.0611, pass
c36-learned-frame-scale-006-flow04: OCR 0.1215, segment 553.610ms, motion_delta 0.0446, quality_fail
c36-learned-frame-scale-008-flow05: OCR 0.0513, segment 547.657ms, motion_delta 0.0513, quality_fail
```

Interpretation:

- The user's concern is right: local text wiggle is not a strong enough proof.
- Viewport zoom/pan survives, responsive squeeze survives, but frame-scale resize/reposition is the active boundary.
- Query-space/global frame scaling is much healthier than learned frame-scale motion. The learned nonlocal resize motion collapses text under the current architecture and training setup.
- More optimization steps help some strong-resize settings, but they do not erase the resize cliff.

Decision:

- Treat wiggle as a control only.
- Keep the main path pure neural-canvas: no OCR boxes, masks, or anchors at render time.
- Run C37 as a resize-focused bracket around strengths `0.12-0.14`, with no-pan and reduced-pan variants to separate scale damage from reposition damage.

Next experiments:

```text
c37-frame-scale-012-edge09-s6000
c37-frame-scale-0125-edge09
c37-frame-scale-013-edge09
c37-frame-scale-0135-edge09
c37-frame-scale-014-edge09-s6000
c37-frame-scale-014-edge075-s6000
c37-frame-scale-016-edge075-s6000
c37-frame-scale-014-edge09-pan000
c37-frame-scale-014-edge09-pan018
c37-frame-scale-014-edge075-pan000
```

## C37 Resize Bracket Results

Completed C37 results:

```text
c37-frame-scale-0125-edge09: OCR 0.6573, segment 560.983ms, motion_delta 0.0574, pass
c37-frame-scale-012-edge09-s6000: OCR 0.6204, segment 541.334ms, motion_delta 0.0563, pass
c37-frame-scale-014-edge075-pan000: OCR 0.5833, segment 577.247ms, motion_delta 0.0593, pass
c37-frame-scale-014-edge09-s6000: OCR 0.5860, segment 553.948ms, motion_delta 0.0588, pass
c37-frame-scale-0135-edge09: OCR 0.4766, segment 594.438ms, motion_delta 0.0581, quality_fail
c37-frame-scale-014-edge075-s6000: OCR 0.5634, segment 533.535ms, motion_delta 0.0590, pass
c37-frame-scale-016-edge075-s6000: OCR 0.4828, segment 554.838ms, motion_delta 0.0597, pass
c37-frame-scale-014-edge09-pan018: OCR 0.2937, segment 521.267ms, motion_delta 0.0601, quality_fail
c37-frame-scale-013-edge09: OCR 0.5110, segment 525.197ms, motion_delta 0.0577, quality_fail
c37-frame-scale-014-edge09-pan000: OCR 0.5024, segment 554.766ms, motion_delta 0.0594, quality_fail
```

Interpretation:

- The strongest resize bracket so far is `0.125/edge09`, not the old local-motion winner.
- The results are non-monotonic, which points to optimization basin sensitivity or aliasing rather than a clean single-parameter cliff.
- Removing pan does not automatically fix text. Some no-pan and reduced-pan variants are worse, so pan is not the only culprit.
- More steps help some stronger-resize cases, especially around `0.14-0.16`, but they do not restore the local-motion OCR range.

Decision:

- Stop spending the next batch on local wiggle.
- Diagnose the resize failure source directly: aliasing, model capacity, coordinate frequency, and seed variance.
- Keep the tests pure neural-canvas. No OCR boxes, render-time text masks, line anchors, or word anchors.

Next experiments:

```text
c38-frame-scale-0125-edge09-aa15
c38-frame-scale-014-edge09-aa15
c38-frame-scale-014-edge09-aa2
c38-frame-scale-016-edge075-aa15
c38-frame-scale-0125-edge09-cap24h128
c38-frame-scale-014-edge09-cap24h128
c38-frame-scale-0125-edge09-freq10
c38-frame-scale-014-edge09-freq10
c38-frame-scale-0125-edge09-seed1
c38-frame-scale-014-edge09-seed1
```

## C38 Resize Diagnosis Results

Completed C38 results:

```text
c38-frame-scale-0125-edge09-freq10: OCR 0.6912, segment 562.129ms, motion_delta 0.0562, pass
c38-frame-scale-0125-edge09-cap24h128: OCR 0.6852, segment 627.711ms, motion_delta 0.0570, pass
c38-frame-scale-014-edge09-aa2: OCR 0.6820, segment 1456.618ms, motion_delta 0.0594, latency_fail
c38-frame-scale-0125-edge09-seed1: OCR 0.6083, segment 547.376ms, motion_delta 0.0570, pass
c38-frame-scale-014-edge09-seed1: OCR 0.5674, segment 528.082ms, motion_delta 0.0591, pass
c38-frame-scale-0125-edge09-aa15: OCR 0.5741, segment 1012.228ms, motion_delta 0.0561, quality_fail
c38-frame-scale-014-edge09-aa15: OCR 0.5143, segment 927.921ms, motion_delta 0.0579, quality_fail
c38-frame-scale-014-edge09-freq10: OCR 0.4977, segment 568.591ms, motion_delta 0.0588, quality_fail
c38-frame-scale-014-edge09-cap24h128: OCR 0.4645, segment 601.116ms, motion_delta 0.0589, quality_fail
c38-frame-scale-016-edge075-aa15: OCR 0.3758, segment 1101.684ms, motion_delta 0.0595, quality_fail
```

Interpretation:

- Higher coordinate frequency is the best fast model-layer improvement so far: `freq_bands=10` at `0.125` beats the C37 resize winner while staying around `562ms` for 33 frames plus encode.
- Larger capacity helps nearly as much but costs more render time.
- Supersampling proves aliasing is part of the failure: `2x` at `0.14` jumps to OCR `0.6820`, but it misses the realtime budget.
- `1.5x` supersampling is not enough, so the useful sampling threshold appears somewhere between `1.5x` and `2x`.
- The `0.14` bracket is still unstable; high frequency alone does not rescue it.

Decision:

- Treat coordinate-frequency/representation as the leading model-layer path.
- Keep supersampling as a diagnostic and search for a latency-feasible midpoint, not as the final answer.
- Queue C39 to combine high frequency, capacity, denser latent resolution, more steps, and `1.75x` supersampling.

Next experiments:

```text
c39-frame-scale-0125-edge09-freq10-cap24h128
c39-frame-scale-014-edge09-freq10-cap24h128
c39-frame-scale-0125-edge09-freq10-s6000
c39-frame-scale-014-edge09-freq10-s6000
c39-frame-scale-014-edge09-aa175
c39-frame-scale-014-edge09-aa175-freq10
c39-frame-scale-014-edge09-aa175-cap24h128
c39-frame-scale-0125-edge09-freq10-aa15
c39-frame-scale-0125-edge09-freq10-train1536
c39-frame-scale-014-edge09-freq10-train1536
```

## C39 Combination Results

Completed C39 results:

```text
c39-frame-scale-0125-edge09-freq10-train1536: OCR 0.7000, segment 571.260ms, motion_delta 0.0578, pass
c39-frame-scale-014-edge09-freq10-train1536: OCR 0.6667, segment 560.830ms, motion_delta 0.0597, pass
c39-frame-scale-014-edge09-aa175: OCR 0.6635, segment 1191.003ms, motion_delta 0.0592, pass
c39-frame-scale-014-edge09-freq10-cap24h128: OCR 0.5556, segment 646.077ms, motion_delta 0.0594, pass
c39-frame-scale-0125-edge09-freq10-aa15: OCR 0.6574, segment 920.248ms, motion_delta 0.0573, quality_fail
c39-frame-scale-0125-edge09-freq10-s6000: OCR 0.6452, segment 561.935ms, motion_delta 0.0570, quality_fail
c39-frame-scale-0125-edge09-freq10-cap24h128: OCR 0.6204, segment 650.691ms, motion_delta 0.0572, quality_fail
c39-frame-scale-014-edge09-aa175-freq10: OCR 0.5488, segment 1199.287ms, motion_delta 0.0590, quality_fail
c39-frame-scale-014-edge09-aa175-cap24h128: OCR 0.5049, segment 1356.635ms, motion_delta 0.0588, quality_fail
c39-frame-scale-014-edge09-freq10-s6000: OCR 0.4025, segment 549.495ms, motion_delta 0.0598, quality_fail
```

Interpretation:

- Denser latent training is the cleanest improvement. `1536x864 + freq10` beats supersampling at similar quality while staying much faster.
- The harder `0.14` resize bracket is now strong enough to pass without render-time text tricks.
- Extra steps and bigger capacity do not reliably help; they may push optimization into worse basins.
- Supersampling remains useful as proof that sampling quality matters, but the model-layer answer is currently denser coordinates/latent resolution, not brute-force render samples.

Decision:

- Promote `train_resolution=1536x864, freq_bands=10` to the new resize baseline.
- Queue C40 around robustness and scaling of that baseline: seed repeat, freq12, edge weighting, `1920x1088` latent resolution, and stronger resize.

Next experiments:

```text
c40-frame-scale-0125-edge09-freq10-train1536-seed1
c40-frame-scale-014-edge09-freq10-train1536-seed1
c40-frame-scale-0125-edge09-freq12-train1536
c40-frame-scale-014-edge09-freq12-train1536
c40-frame-scale-0125-edge075-freq10-train1536
c40-frame-scale-014-edge075-freq10-train1536
c40-frame-scale-0125-edge09-freq10-train1920
c40-frame-scale-014-edge09-freq10-train1920
c40-frame-scale-0145-edge09-freq10-train1536
c40-frame-scale-016-edge09-freq10-train1536
```

## C40 Denser-Canvas Results

Completed C40 results:

```text
c40-frame-scale-0125-edge09-freq10-train1536-seed1: OCR 0.7222, segment 559.324ms, motion_delta 0.0574, pass
c40-frame-scale-0125-edge09-freq12-train1536: OCR 0.7032, segment 581.957ms, motion_delta 0.0572, pass
c40-frame-scale-0125-edge075-freq10-train1536: OCR 0.6972, segment 562.657ms, motion_delta 0.0579, pass
c40-frame-scale-016-edge09-freq10-train1536: OCR 0.5660, segment 575.939ms, motion_delta 0.0606, pass
c40-frame-scale-014-edge09-freq12-train1536: OCR 0.5981, segment 676.950ms, motion_delta 0.0595, quality_fail
c40-frame-scale-014-edge09-freq10-train1920: OCR 0.5860, segment 558.166ms, motion_delta 0.0594, quality_fail
c40-frame-scale-014-edge075-freq10-train1536: OCR 0.5803, segment 580.870ms, motion_delta 0.0603, quality_fail
c40-frame-scale-0145-edge09-freq10-train1536: OCR 0.5566, segment 574.298ms, motion_delta 0.0600, quality_fail
c40-frame-scale-0125-edge09-freq10-train1920: OCR 0.6606, segment 572.907ms, motion_delta 0.0579, quality_fail
c40-frame-scale-014-edge09-freq10-train1536-seed1: OCR 0.3143, segment 545.267ms, motion_delta 0.0600, quality_fail
```

Interpretation:

- The pure neural-canvas resize result now reaches OCR `0.7222` at `559.324ms`, which is close to the earlier masked/anchor strong-stress quality while staying general and fast.
- `1536x864 + freq10` remains the best baseline; `1920x1088` regresses, so more latent pixels are not automatically better.
- `freq12` helps the `0.125` bracket but not the harder `0.14` bracket.
- The main unsolved problem is optimizer stability. The same `0.14` family can pass in one seed and collapse in another.

Decision:

- Promote `1536x864 + freq10` as the current model-layer baseline.
- Stop chasing bigger latent canvas resolution for now.
- Queue C41 around lower learning rates and seed repeats for the fragile `0.14` bracket.

Next experiments:

```text
c41-frame-scale-014-edge09-freq10-train1536-lr007
c41-frame-scale-014-edge09-freq10-train1536-lr007-seed1
c41-frame-scale-014-edge09-freq10-train1536-lr005
c41-frame-scale-014-edge09-freq10-train1536-lr005-seed1
c41-frame-scale-014-edge09-freq12-train1536-seed1
c41-frame-scale-0125-edge09-freq10-train1536-seed2
c41-frame-scale-0125-edge09-freq10-train1536-seed3
c41-frame-scale-014-edge09-freq10-train1536-seed2
c41-frame-scale-014-edge09-freq10-train1536-seed3
c41-frame-scale-016-edge09-freq10-train1536-lr007
```

## C41 Optimizer Stability Results

Completed C41 results:

```text
c41-frame-scale-0125-edge09-freq10-train1536-seed2: OCR 0.7097, segment 561.222ms, motion_delta 0.0579, pass
c41-frame-scale-014-edge09-freq10-train1536-lr007-seed1: OCR 0.6849, segment 561.626ms, motion_delta 0.0597, pass
c41-frame-scale-014-edge09-freq12-train1536-seed1: OCR 0.6452, segment 564.720ms, motion_delta 0.0586, pass
c41-frame-scale-014-edge09-freq10-train1536-lr005-seed1: OCR 0.6419, segment 575.406ms, motion_delta 0.0604, pass
c41-frame-scale-014-edge09-freq10-train1536-seed3: OCR 0.6267, segment 585.656ms, motion_delta 0.0593, pass
c41-frame-scale-014-edge09-freq10-train1536-seed2: OCR 0.6083, segment 516.502ms, motion_delta 0.0594, quality_fail
c41-frame-scale-014-edge09-freq10-train1536-lr007: OCR 0.5769, segment 575.461ms, motion_delta 0.0594, quality_fail
c41-frame-scale-016-edge09-freq10-train1536-lr007: OCR 0.5673, segment 563.275ms, motion_delta 0.0604, pass
c41-frame-scale-014-edge09-freq10-train1536-lr005: OCR 0.4571, segment 564.228ms, motion_delta 0.0602, quality_fail
c41-frame-scale-0125-edge09-freq10-train1536-seed3: OCR 0.6636, segment 563.232ms, motion_delta 0.0578, quality_fail
```

Interpretation:

- The `0.125` denser-canvas family is meaningfully robust, but not perfectly stable: seeds land between OCR `0.6636` and `0.7222`.
- The `0.14` family is recoverable but unstable. Lower LR rescues seed `1`, while hurting seed `0`.
- Constant LR is probably the wrong control knob; the next test should try schedules and gradient clipping.
- The current model can handle `0.16` resize at pass-level OCR, but not yet with the quality we want.

Decision:

- Keep the `1536x864 + freq10` baseline.
- Test optimizer schedules before changing architecture again.
- C42 should try cosine LR decay, lower-LR cosine, and gradient clipping across the fragile `0.14` bracket and the weak `0.125` seed.

Next experiments:

```text
c42-frame-scale-014-edge09-freq10-train1536-cosine
c42-frame-scale-014-edge09-freq10-train1536-cosine-seed1
c42-frame-scale-014-edge09-freq10-train1536-lr007-cosine
c42-frame-scale-014-edge09-freq10-train1536-lr007-cosine-seed1
c42-frame-scale-014-edge09-freq10-train1536-clip1
c42-frame-scale-014-edge09-freq10-train1536-clip1-seed1
c42-frame-scale-014-edge09-freq12-train1536-lr007-cosine
c42-frame-scale-014-edge09-freq12-train1536-lr007-cosine-seed1
c42-frame-scale-0125-edge09-freq10-train1536-seed3-cosine
c42-frame-scale-016-edge09-freq10-train1536-lr007-cosine
```

## C42 Optimizer Schedule Results

Completed C42 results:

```text
c42-frame-scale-014-edge09-freq10-train1536-clip1-seed1: OCR 0.6944, segment 565.820ms, motion_delta 0.0601, pass
c42-frame-scale-0125-edge09-freq10-train1536-seed3-cosine: OCR 0.7064, segment 557.783ms, motion_delta 0.0583, pass
c42-frame-scale-014-edge09-freq12-train1536-lr007-cosine-seed1: OCR 0.6091, segment 583.468ms, motion_delta 0.0604, pass
c42-frame-scale-014-edge09-freq10-train1536-lr007-cosine-seed1: OCR 0.6019, segment 554.481ms, motion_delta 0.0604, quality_fail
c42-frame-scale-014-edge09-freq10-train1536-cosine: OCR 0.5833, segment 731.012ms, motion_delta 0.0605, quality_fail
c42-frame-scale-014-edge09-freq10-train1536-clip1: OCR 0.5650, segment 564.015ms, motion_delta 0.0600, quality_fail
c42-frame-scale-014-edge09-freq12-train1536-lr007-cosine: OCR 0.5495, segment 589.680ms, motion_delta 0.0602, quality_fail
c42-frame-scale-016-edge09-freq10-train1536-lr007-cosine: OCR 0.5395, segment 550.171ms, motion_delta 0.0610, quality_fail
c42-frame-scale-014-edge09-freq10-train1536-lr007-cosine: OCR 0.5273, segment 869.496ms, motion_delta 0.0593, quality_fail
c42-frame-scale-014-edge09-freq10-train1536-cosine-seed1: OCR 0.3834, segment 562.706ms, motion_delta 0.0603, quality_fail
```

Interpretation:

- Gradient clipping is the strongest new stability lead for `0.14`: clip `1.0` on seed `1` reaches OCR `0.6944`.
- Cosine LR is useful for one weak `0.125` seed but does not solve the harder `0.14` bracket.
- The next test should not broaden architecture again; it should characterize clipping strength and seed behavior.

Decision:

- Queue C43 as a gradient-clipping robustness sweep across clip `0.5`, `1.0`, `2.0`, seeds, and `lr007 + clip1`.

Next experiments:

```text
c43-frame-scale-014-edge09-freq10-train1536-clip05
c43-frame-scale-014-edge09-freq10-train1536-clip05-seed1
c43-frame-scale-014-edge09-freq10-train1536-clip05-seed2
c43-frame-scale-014-edge09-freq10-train1536-clip05-seed3
c43-frame-scale-014-edge09-freq10-train1536-clip1-seed2
c43-frame-scale-014-edge09-freq10-train1536-clip1-seed3
c43-frame-scale-014-edge09-freq10-train1536-clip2
c43-frame-scale-014-edge09-freq10-train1536-clip2-seed1
c43-frame-scale-014-edge09-freq10-train1536-lr007-clip1
c43-frame-scale-014-edge09-freq10-train1536-lr007-clip1-seed1
```

## C43 Clipping Robustness Results

Completed C43 results:

```text
c43-frame-scale-014-edge09-freq10-train1536-clip05: OCR 0.7281, segment 566.234ms, pass
c43-frame-scale-014-edge09-freq10-train1536-clip1-seed2: OCR 0.7281, segment 570.829ms, pass
c43-frame-scale-014-edge09-freq10-train1536-lr007-clip1: OCR 0.7230, segment 566.807ms, pass
c43-frame-scale-014-edge09-freq10-train1536-clip05-seed3: OCR 0.7156, segment 553.468ms, pass
c43-frame-scale-014-edge09-freq10-train1536-clip2: OCR 0.6977, segment 559.196ms, pass
c43-frame-scale-014-edge09-freq10-train1536-clip05-seed1: OCR 0.6912, segment 846.244ms, pass
c43-frame-scale-014-edge09-freq10-train1536-clip2-seed1: OCR 0.6759, segment 556.768ms, pass
c43-frame-scale-014-edge09-freq10-train1536-lr007-clip1-seed1: OCR 0.5755, segment 497.728ms, quality_fail
c43-frame-scale-014-edge09-freq10-train1536-clip05-seed2: OCR 0.5213, segment 545.259ms, quality_fail
c43-frame-scale-014-edge09-freq10-train1536-clip1-seed3: OCR 0.3553, segment 563.334ms, quality_fail
```

Interpretation:

- Gradient clipping is now the strongest model-layer stability result for global resize/reposition. It moves the hard `0.14` bracket to OCR `0.7281` while staying under the `1.3s` segment budget.
- Clip `0.5` and clip `1.0` both hit the same top OCR on different seeds, so the effect is not a one-off artifact.
- Seed variance remains large. Clipping improves the ceiling and pass rate, but it does not yet make the renderer robust.
- This is still one global transform. It is a useful boundary result, but it is not enough to prove independent page-level motion.

Decision:

- Keep `1536x864 + freq10 + edge09 + grad clipping` as the baseline.
- Stop optimizing only for global frame-scale.
- C44 should stress independent page items: separate coarse regions should move, pan, and resize on different timelines. The renderer should remain pure neural-canvas query rendering, with no OCR boxes, text masks, or render-time text overlays.

Next experiments:

```text
c44-regions-006-pan018-clip05
c44-regions-010-pan024-clip05
c44-regions-014-pan030-clip05
c44-regions-010-pan024-clip1
c44-regions-014-pan030-clip1
c44-regions-010-pan024-freq12-clip05
c44-regions-014-pan030-freq12-clip05
c44-regions-010-pan024-clip05-seed1
c44-regions-010-pan024-clip05-seed2
c44-regions-016-pan036-clip05
```

## C44 Independent Region Results

Completed C44 results:

```text
c44-regions-010-pan024-clip05-seed1: OCR 0.5055, segment 634.991ms, motion_delta 0.0330, quality_fail
c44-regions-014-pan030-clip05: OCR 0.5000, segment 624.006ms, motion_delta 0.0365, quality_fail
c44-regions-010-pan024-clip05-seed2: OCR 0.4792, segment 637.818ms, motion_delta 0.0332, quality_fail
c44-regions-010-pan024-clip1: OCR 0.4607, segment 684.891ms, motion_delta 0.0331, quality_fail
c44-regions-006-pan018-clip05: OCR 0.4469, segment 605.705ms, motion_delta 0.0280, quality_fail
c44-regions-010-pan024-freq12-clip05: OCR 0.4260, segment 664.665ms, motion_delta 0.0325, quality_fail
c44-regions-010-pan024-clip05: OCR 0.4061, segment 610.633ms, motion_delta 0.0334, quality_fail
c44-regions-016-pan036-clip05: OCR 0.4025, segment 840.143ms, motion_delta 0.0382, quality_fail
c44-regions-014-pan030-clip1: OCR 0.3492, segment 1047.912ms, motion_delta 0.0366, quality_fail
c44-regions-014-pan030-freq12-clip05: OCR 0.3085, segment 647.597ms, motion_delta 0.0367, quality_fail
```

Interpretation:

- Independent region motion is substantially harder than global resize. C43 reached OCR `0.7281` at the hard global `0.14` bracket; C44 drops to a best OCR of `0.5055`.
- Latency is not the bottleneck. Every C44 run is under the `1.3s` segment budget, and most are around `0.61-0.68s`.
- The human-visible failure is hard region tearing: broad rectangular regions move independently, but the compositor leaves obvious white seams and duplicated/blanked source areas.
- This means C44 is a useful stress signal, but the hard-rectangle generator is too artificial. It tests independence, but it also injects a failure mode that is not the pure neural-canvas end state.

Decision:

- Keep independent item motion as the main challenge.
- Replace hard region cutouts with a smooth blended independent-region query field so local transforms overlap continuously.
- Also test the more ambitious path: train the renderer on an `independent-field` target and render without any layout-time transform, forcing the model to synthesize multi-region motion directly from `x,y,t`.

Next experiments:

```text
c45-field-006-pan018-clip05
c45-field-010-pan024-clip05
c45-field-014-pan030-clip05
c45-field-014-pan036-clip05
c45-field-010-pan024-clip05-seed1
c45-learned-field-004-flow04
c45-learned-field-006-flow06
c45-learned-field-008-flow08
c45-learned-field-006-flow06-clip05
c45-learned-field-006-flow06-freq12-clip05
```

## C45 Smooth Field Results

Completed C45 query-time smooth independent-field results:

```text
c45-field-010-pan024-clip05-seed1: OCR 0.8165, segment 601.358ms, motion_delta 0.0164, quality_fail
c45-field-010-pan024-clip05: OCR 0.7818, segment 584.763ms, motion_delta 0.0163, quality_fail
c45-field-006-pan018-clip05: OCR 0.7892, segment 581.335ms, motion_delta 0.0128, quality_fail
c45-field-014-pan030-clip05: OCR 0.6912, segment 593.162ms, motion_delta 0.0197, quality_fail
c45-field-014-pan036-clip05: OCR 0.6912, segment 588.279ms, motion_delta 0.0224, quality_fail
```

Completed C45 learned independent-field results:

```text
c45-learned-field-004-flow04: OCR 0.6393, segment 548.702ms, motion_delta 0.0091, quality_fail
c45-learned-field-006-flow06: OCR 0.6161, segment 562.516ms, motion_delta 0.0138, quality_fail
c45-learned-field-006-flow06-freq12-clip05: OCR 0.6036, segment 512.876ms, motion_delta 0.0134, quality_fail
c45-learned-field-006-flow06-clip05: OCR 0.5688, segment 548.541ms, motion_delta 0.0141, quality_fail
c45-learned-field-008-flow08: OCR 0.2289, segment 565.164ms, motion_delta 0.0170, quality_fail
```

Interpretation:

- Smooth query-time fields solve the hard-rectangle artifact from C44. Text quality rebounds to `0.8165` OCR on the best run, and human inspection shows no broad white seams.
- This is still not enough. The motion is too subtle, and much of the apparent liveliness is elastic field deformation rather than object-like translation.
- The learned branch is the more important model-layer test, but the current small renderer does not yet learn strong independent motion. Mild fields keep some OCR; stronger flow collapses text before producing convincing translation.
- C46 should explicitly separate translation from stretch: local scale disabled, larger independent pans, and a learned translation-only mode.

Next experiments:

```text
c46-translate-pan030-clip05
c46-translate-pan045-clip05
c46-translate-pan060-clip05
c46-translate-pan075-clip05
c46-translate-pan090-clip05
c46-translate-pan060-freq12-clip05
c46-translate-pan075-clip05-seed1
c46-learned-translate-004-s7000
c46-learned-translate-006-s7000
c46-learned-translate-008-s7000
```

## C46 Translation-Only Results

Completed C46 translation-only results:

```text
c46-translate-pan030-clip05: OCR 0.6948, segment 572.905ms, motion_delta 0.0184, quality_fail
c46-translate-pan045-clip05: OCR 0.6606, segment 575.381ms, motion_delta 0.0241, quality_fail
c46-translate-pan060-freq12-clip05: OCR 0.4977, segment 608.441ms, motion_delta 0.0274, quality_fail
c46-translate-pan060-clip05: OCR 0.4700, segment 603.130ms, motion_delta 0.0272, quality_fail
c46-translate-pan075-clip05: OCR 0.4375, segment 905.745ms, motion_delta 0.0302, quality_fail
c46-translate-pan075-clip05-seed1: OCR 0.3385, segment 580.437ms, motion_delta 0.0302, quality_fail
c46-translate-pan090-clip05: OCR 0.2347, segment 586.274ms, motion_delta 0.0327, quality_fail
c46-learned-translate-004-s7000: OCR 0.3892, segment 627.167ms, motion_delta 0.0257, quality_fail
c46-learned-translate-006-s7000: OCR 0.3140, segment 516.280ms, motion_delta 0.0302, quality_fail
c46-learned-translate-008-s7000: OCR 0.1707, segment 558.853ms, motion_delta 0.0352, quality_fail
```

Interpretation:

- C46 is a better test than wiggle, but it is still not the end goal.
- The query-time translation controls prove that pan-only motion is harder than deformation: OCR stays good at pan `0.030-0.045`, but measured motion is still just under the gate.
- The learned translation branch is the most encouraging near-miss: flow `0.04` clears the motion gate (`0.0257`) and misses OCR by only about one point (`0.3892` vs `0.4000`).
- This does not yet prove Flipbook-style viability, because moving regions is not the same as creating a new layout. The next proof must resize/reposition the illustration and move text/content blocks into different page locations while still rendering every pixel directly from the model.

Next experiments:

```text
c47-layout-reflow-070-s9000
c47-layout-reflow-085-s9000
c47-layout-reflow-100-s9000
c47-layout-reflow-100-freq12-s9000
c47-layout-reflow-100-c24h128-s9000
c47-layout-reflow-100-c32h160-s10000
c47-layout-reflow-100-textw-s9000
c47-layout-reflow-100-textw-c24h128-s10000
c47-layout-reflow-100-lr007-s10000
c47-layout-reflow-100-cosine-s10000
```

## C47 Learned Layout-Reflow Results

Completed C47 layout-reflow results:

```text
c47-layout-reflow-100-c32h160-s10000: OCR 0.5193, segment 620.732ms, motion_delta 0.0520, pass
c47-layout-reflow-085-s9000: OCR 0.4663, segment 559.702ms, motion_delta 0.0473, pass
c47-layout-reflow-100-lr007-s10000: OCR 0.4422, segment 570.260ms, motion_delta 0.0515, pass
c47-layout-reflow-100-freq12-s9000: OCR 0.4403, segment 586.481ms, motion_delta 0.0545, pass
c47-layout-reflow-100-textw-s9000: OCR 0.4025, segment 573.198ms, motion_delta 0.0462, pass
c47-layout-reflow-100-cosine-s10000: OCR 0.4025, segment 563.481ms, motion_delta 0.0502, pass
c47-layout-reflow-100-textw-c24h128-s10000: OCR 0.3867, segment 622.839ms, motion_delta 0.0497, quality_fail
c47-layout-reflow-100-c24h128-s9000: OCR 0.3709, segment 639.189ms, motion_delta 0.0511, pass
c47-layout-reflow-100-s9000: OCR 0.3660, segment 550.950ms, motion_delta 0.0536, pass
c47-layout-reflow-070-s9000: OCR 0.3043, segment 583.513ms, motion_delta 0.0464, quality_fail
```

Interpretation:

- This is the first credible proof signal for neural-canvas layout change. The best run actually renders a changed page layout, not a global wiggle: the diagram is repositioned/resized and content bands move.
- Latency is not a blocker. The best layout-reflow run is `620.732ms` for 33 generated frames plus encode, still faster than realtime for the 24fps segment target.
- OCR still understates and overstates different things. The visual pass is meaningful, but text remains soft; target-vs-output inspection is now necessary.
- Higher capacity helps: `c32h160` is clearly better than the smaller baseline.
- C48 should keep the layout-reflow proof, add a saved target midpoint artifact, and test larger/text-weighted/high-resolution variants.

Next experiments:

```text
c48-layout-reflow-100-c32h160-s12000
c48-layout-reflow-100-c32h160-freq12-s12000
c48-layout-reflow-100-c40h192-s12000
c48-layout-reflow-100-c32h160-textw-s12000
c48-layout-reflow-100-textw-strong-s11000
c48-layout-reflow-100-train1920-c24h128-s10000
c48-layout-reflow-100-train1920-c32h160-s10000
c48-layout-reflow-100-c32h160-lr007-s12000
c48-layout-reflow-100-c32h160-cosine-s12000
c48-layout-reflow-100-c32h160-edge16-s12000
```

## C48 Capacity/Reflow Follow-Up Results

Completed C48 layout-reflow results:

```text
c48-layout-reflow-100-train1920-c24h128-s10000: OCR 0.4739, segment 634.374ms, motion_delta 0.0488, quality_fail
c48-layout-reflow-100-train1920-c32h160-s10000: OCR 0.4706, segment 706.145ms, motion_delta 0.0514, quality_fail
c48-layout-reflow-100-c32h160-lr007-s12000: OCR 0.4557, segment 623.097ms, motion_delta 0.0514, quality_fail
c48-layout-reflow-100-c32h160-s12000: OCR 0.4528, segment 708.337ms, motion_delta 0.0487, quality_fail
c48-layout-reflow-100-c32h160-edge16-s12000: OCR 0.4455, segment 700.160ms, motion_delta 0.0499, quality_fail
c48-layout-reflow-100-textw-strong-s11000: OCR 0.4444, segment 581.194ms, motion_delta 0.0510, quality_fail
c48-layout-reflow-100-c32h160-textw-s12000: OCR 0.4277, segment 751.085ms, motion_delta 0.0491, quality_fail
c48-layout-reflow-100-c32h160-cosine-s12000: OCR 0.4151, segment 717.772ms, motion_delta 0.0503, quality_fail
c48-layout-reflow-100-c32h160-freq12-s12000: OCR 0.4079, segment 727.767ms, motion_delta 0.0502, quality_fail
c48-layout-reflow-100-c40h192-s12000: OCR 0.4025, segment 818.575ms, motion_delta 0.0507, quality_fail
```

Interpretation:

- C48 did not beat the C47 layout-reflow peak (`0.5193` OCR), despite more steps, larger capacity, and higher train resolution.
- Latency remains excellent. Even the largest C48 branch is comfortably under the `1.3s` segment budget.
- The `target-mid.png` artifact is now saved and included in contact sheets. Human inspection shows the synthetic target is crisp and correctly reflowed, while model output follows the layout but blurs text.
- This points away from simple capacity scaling and toward the sampling/loss distribution. Source-side glyph/text sampling is likely spending too much budget where text used to be, not where the reflowed text lands.

Next experiments:

```text
c49-reflow-target-mid60-c32h160-s12000
c49-reflow-target-mid80-c32h160-s12000
c49-reflow-target-mid60-c32h160-s14000
c49-reflow-target-lr007-c32h160-s12000
c49-reflow-target-time6-c32h160-s12000
c49-reflow-target-edge18-c32h160-s12000
c49-reflow-target-textw-c32h160-s12000
c49-reflow-target-b196-c32h160-s10000
c49-reflow-target-train1920-c24h128-s11000
c49-reflow-target-train1920-c32h160-s11000
```

Queued behind C49:

```text
c50-reflow-ablate-target-sample-only
c50-reflow-ablate-target-weight-only
c50-reflow-ablate-midtime-only
c50-reflow-target-mid40-c32h160-s11000
c50-reflow-target-mid90n-c32h160-s11000
c50-reflow-target-freq12-c32h160-s11000
c50-reflow-target-c40h192-s11000
c50-reflow-target-cosine-c32h160-s11000
c50-reflow-target-clip1-c32h160-s11000
c50-reflow-target-train1920-textw-c24h128-s11000
```

## C49 Target-Side Reflow Results

Completed C49 results:

```text
c49-reflow-target-b196-c32h160-s10000: OCR 0.5761, segment 867.931ms, motion_delta 0.0517, pass
c49-reflow-target-mid60-c32h160-s14000: OCR 0.5714, segment 724.892ms, motion_delta 0.0498, pass
c49-reflow-target-train1920-c32h160-s11000: OCR 0.5497, segment 631.621ms, motion_delta 0.0489, pass
c49-reflow-target-mid60-c32h160-s12000: OCR 0.4875, segment 709.629ms, motion_delta 0.0501, quality_fail
c49-reflow-target-edge18-c32h160-s12000: OCR 0.4780, segment 706.553ms, motion_delta 0.0491, quality_fail
c49-reflow-target-textw-c32h160-s12000: OCR 0.4625, segment 705.667ms, motion_delta 0.0500, quality_fail
c49-reflow-target-train1920-c24h128-s11000: OCR 0.4568, segment 694.017ms, motion_delta 0.0533, quality_fail
c49-reflow-target-mid80-c32h160-s12000: OCR 0.4500, segment 638.482ms, motion_delta 0.0497, quality_fail
c49-reflow-target-time6-c32h160-s12000: OCR 0.4267, segment 728.181ms, motion_delta 0.0518, quality_fail
c49-reflow-target-lr007-c32h160-s12000: OCR 0.4198, segment 619.204ms, motion_delta 0.0516, quality_fail
```

Interpretation:

- Target-side reflow sampling is the first change since C47 that clearly improves learned layout reflow. The best C49 result beats the C47 OCR peak (`0.5193`) by about `0.0568`.
- Larger batch helped: `196608` samples per step at `10000` steps produced the best OCR, even though it is slower than the other C49 passes.
- More steps helped at the normal batch: `14000` steps beat `12000` steps by a wide margin (`0.5714` vs `0.4875`).
- `1920x1088` with `c32h160` is the fastest strong pass at `631.621ms`, but the `c24h128` high-res variant underperformed.
- Text-box weighting still did not help in this setup, which supports the pure neural-canvas direction rather than returning to box-specific tricks.
- Human contact-sheet review shows the target layout is being followed and the title/text are noticeably more stable, though text still has blur/ghosting at the reflow midpoint.

## C50 Ablation Results

Completed C50 results:

```text
c50-reflow-ablate-target-weight-only: OCR 0.5000, segment 620.067ms, motion_delta 0.0488, pass
c50-reflow-target-cosine-c32h160-s11000: OCR 0.4906, segment 720.773ms, motion_delta 0.0505, quality_fail
c50-reflow-ablate-midtime-only: OCR 0.4767, segment 735.640ms, motion_delta 0.0508, quality_fail
c50-reflow-target-train1920-textw-c24h128-s11000: OCR 0.4750, segment 631.337ms, motion_delta 0.0526, quality_fail
c50-reflow-target-mid90n-c32h160-s11000: OCR 0.4654, segment 727.581ms, motion_delta 0.0492, quality_fail
c50-reflow-target-mid40-c32h160-s11000: OCR 0.4500, segment 701.006ms, motion_delta 0.0468, quality_fail
c50-reflow-target-c40h192-s11000: OCR 0.4431, segment 722.699ms, motion_delta 0.0521, quality_fail
c50-reflow-ablate-target-sample-only: OCR 0.4277, segment 723.896ms, motion_delta 0.0511, quality_fail
c50-reflow-target-clip1-c32h160-s11000: OCR 0.4267, segment 708.023ms, motion_delta 0.0504, quality_fail
c50-reflow-target-freq12-c32h160-s11000: OCR 0.3553, segment 733.943ms, motion_delta 0.0477, quality_fail
```

Interpretation:

- Target-side weighting matters more than target-side coordinate sampling when isolated.
- Midpoint time pressure helps but is not sufficient alone.
- The best C49 outcomes likely came from target weighting plus either larger batch (`196608`) or more steps (`14000`), not from capacity/frequency changes.
- `freq12`, `c40h192`, and clip `1.0` all regress here, so C51 should not spend more budget on those axes yet.

Next experiments:

```text
c51-reflow-target-b196-c32h160-s12000
c51-reflow-target-b196-c32h160-s14000
c51-reflow-target-b229-c32h160-s10000
c51-reflow-target-mid60-c32h160-s16000
c51-reflow-target-mid60-c32h160-s18000
c51-reflow-weightonly-b196-c32h160-s10000
c51-reflow-weightonly-c32h160-s14000
c51-reflow-target-train1920-c32h160-s13000
c51-reflow-target-train1920-c32h160-s15000
c51-reflow-target-b196-c32h160-s10000-seed1
c51-reflow-target-mid60-c32h160-s14000-seed1
```

Partial C51 read while the last seed was still running:

```text
c51-reflow-weightonly-c32h160-s14000: OCR 0.5614, segment pending eval, motion_delta 0.0459, pass
c51-reflow-target-b196-c32h160-s14000: OCR 0.5238, motion_delta 0.0517, quality_fail
c51-reflow-weightonly-b196-c32h160-s10000: OCR 0.5023, motion_delta 0.0483, quality_fail
c51-reflow-target-b196-c32h160-s12000: OCR 0.4860, motion_delta 0.0504, quality_fail
c51-reflow-target-mid60-c32h160-s16000: OCR 0.4845, motion_delta 0.0529, quality_fail
c51-reflow-target-mid60-c32h160-s18000: OCR 0.4845, motion_delta 0.0488, quality_fail
c51-reflow-target-train1920-c32h160-s15000: OCR 0.4875, motion_delta 0.0509, quality_fail
c51-reflow-target-train1920-c32h160-s13000: OCR 0.4673, motion_delta 0.0505, quality_fail
c51-reflow-target-b229-c32h160-s10000: OCR 0.4596, motion_delta 0.0513, quality_fail
c51-reflow-target-b196-c32h160-s10000-seed1: OCR 0.4500, motion_delta 0.0476, quality_fail
```

Next experiments:

```text
c52-reflow-target-s025-c32h160-s14000
c52-reflow-target-s050-c32h160-s14000
c52-reflow-target-s075-c32h160-s14000
c52-reflow-weightonly-c32h160-s16000
c52-reflow-weightonly-c32h160-s18000
c52-reflow-weightonly-b196-c32h160-s12000
c52-reflow-weightonly-b196-c32h160-s14000
c52-reflow-weightonly-train1920-c32h160-s13000
c52-reflow-weightonly-c32h160-s14000-seed1
c52-reflow-weightonly-c32h160-s14000-seed2
c52-reflow-target-b196-c32h160-s10000-seed2
```

Partial C52 read:

```text
c52-reflow-target-s050-c32h160-s14000: OCR 0.5742, motion_delta 0.0502, pass
c52-reflow-weightonly-b196-c32h160-s14000: OCR 0.5729, motion_delta 0.0522, pass
c52-reflow-weightonly-train1920-c32h160-s13000: OCR 0.5524, motion_delta 0.0485, pass
c52-reflow-target-b196-c32h160-s10000-seed2: OCR 0.5490, motion_delta 0.0436, quality_fail
c52-reflow-target-s025-c32h160-s14000: OCR 0.5349, motion_delta 0.0513, quality_fail
c52-reflow-weightonly-c32h160-s18000: OCR 0.5029, motion_delta 0.0507, quality_fail
c52-reflow-weightonly-c32h160-s14000-seed1: OCR 0.4945, motion_delta 0.0482, quality_fail
c52-reflow-weightonly-c32h160-s14000-seed2: OCR 0.4875, motion_delta 0.0477, quality_fail
c52-reflow-target-s075-c32h160-s14000: OCR 0.4834, motion_delta 0.0475, quality_fail
c52-reflow-weightonly-c32h160-s16000: OCR 0.4505, motion_delta 0.0566, quality_fail
c52-reflow-weightonly-b196-c32h160-s12000: OCR 0.4375, motion_delta 0.0499, quality_fail
```

Interpretation:

- Partial target sampling helps, with `0.50` near the C49 best, but still does not pass `0.5761`.
- Bigger batch and more steps remain non-monotonic.
- The visible weak point is still blur/ghosting, so C53 tests whether adding L1 to weighted MSE sharpens the reflowed page.

Next experiments:

```text
c53-reflow-weightonly-l1-025-c32h160-s14000
c53-reflow-weightonly-l1-050-c32h160-s14000
c53-reflow-weightonly-l1-100-c32h160-s14000
c53-reflow-target-s050-l1-025-c32h160-s14000
c53-reflow-target-s050-l1-050-c32h160-s14000
c53-reflow-target-full-l1-025-b196-s10000
c53-reflow-target-full-l1-050-b196-s10000
c53-reflow-target-full-l1-025-c32h160-s14000
c53-reflow-target-full-l1-050-c32h160-s14000
c53-reflow-weightonly-l1-025-train1920-s13000
```

Completed C53 results:

```text
c53-reflow-target-full-l1-025-c32h160-s14000: OCR 0.5604, segment 848.440ms, motion_delta 0.0473, pass
c53-reflow-target-full-l1-025-b196-s10000: OCR 0.5455, segment 706.919ms, motion_delta 0.0491, quality_fail
c53-reflow-weightonly-l1-025-train1920-s13000: OCR 0.5426, segment 704.286ms, motion_delta 0.0489, pass
c53-reflow-target-full-l1-050-c32h160-s14000: OCR 0.4970, segment 697.198ms, motion_delta 0.0494, quality_fail
c53-reflow-weightonly-l1-050-c32h160-s14000: OCR 0.4938, segment 688.344ms, motion_delta 0.0481, quality_fail
c53-reflow-target-s050-l1-025-c32h160-s14000: OCR 0.4845, segment 894.384ms, motion_delta 0.0484, quality_fail
c53-reflow-target-s050-l1-050-c32h160-s14000: OCR 0.4780, segment 697.795ms, motion_delta 0.0517, quality_fail
c53-reflow-weightonly-l1-025-c32h160-s14000: OCR 0.4654, segment 704.924ms, motion_delta 0.0527, quality_fail
c53-reflow-target-full-l1-050-b196-s10000: OCR 0.4500, segment 648.116ms, motion_delta 0.0494, quality_fail
c53-reflow-weightonly-l1-100-c32h160-s14000: OCR 0.0000, segment 683.418ms, motion_delta 0.0000, quality_fail
```

Interpretation:

- L1 is not the right sharpening tool for this reflow target. The best C53 pass (`0.5604`) trails C49 (`0.5761`) and C52 (`0.5742`).
- Stronger L1 reduces motion/texture error numerically in some places but hurts OCR, which suggests it biases toward overly smooth or collapsed local averages instead of crisp glyph strokes.
- C54 should test local gradient consistency instead: compare the model and target one-pixel x/y differences at reflowed output coordinates. That is a sharper hypothesis for doubled strokes and blurred text edges.

Next experiments:

```text
c54-reflow-grad025-r00625-target-s050-c32h160-s14000
c54-reflow-grad050-r00625-target-s050-c32h160-s14000
c54-reflow-grad025-r0125-target-s050-c32h160-s14000
c54-reflow-grad050-r0125-target-s050-c32h160-s14000
c54-reflow-grad025-r00625-weightonly-c32h160-s14000
c54-reflow-grad050-r00625-weightonly-c32h160-s14000
c54-reflow-grad025-r0125-weightonly-c32h160-s14000
c54-reflow-grad025-r00625-target-full-b196-s10000
c54-reflow-grad050-r00625-target-full-b196-s10000
c54-reflow-grad025-r00625-train1920-weightonly-s13000
```

Completed C54 results:

```text
c54-reflow-grad050-r00625-weightonly-c32h160-s14000: OCR 0.5614, segment 720.876ms, motion_delta 0.0496, pass
c54-reflow-grad050-r00625-target-full-b196-s10000: OCR 0.5349, segment 700.093ms, motion_delta 0.0487, quality_fail
c54-reflow-grad025-r0125-weightonly-c32h160-s14000: OCR 0.5294, segment 626.469ms, motion_delta 0.0520, quality_fail
c54-reflow-grad025-r0125-target-s050-c32h160-s14000: OCR 0.5169, segment 704.844ms, motion_delta 0.0526, quality_fail
c54-reflow-grad025-r00625-target-full-b196-s10000: OCR 0.4875, segment 705.197ms, motion_delta 0.0484, quality_fail
c54-reflow-grad025-r00625-weightonly-c32h160-s14000: OCR 0.4625, segment 717.731ms, motion_delta 0.0481, quality_fail
c54-reflow-grad025-r00625-train1920-weightonly-s13000: OCR 0.4528, segment 711.352ms, motion_delta 0.0506, quality_fail
c54-reflow-grad025-r00625-target-s050-c32h160-s14000: OCR 0.4524, segment 645.104ms, motion_delta 0.0495, quality_fail
c54-reflow-grad050-r00625-target-s050-c32h160-s14000: OCR 0.4472, segment 870.696ms, motion_delta 0.0504, quality_fail
c54-reflow-grad050-r0125-target-s050-c32h160-s14000: OCR 0.3976, segment 637.243ms, motion_delta 0.0522, quality_fail
```

Interpretation:

- Gradient consistency did not beat the frontier. The best C54 result only matched the older C51 weight-only result (`0.5614`).
- Partial target sampling plus gradient loss is actively harmful in this target, especially at gradient weight `0.50`.
- Render latency remains fine because the loss only affects compile/training, but compile time rose materially, so this branch should not receive more broad budget.
- C55 should preserve source-side coverage and add target-side pressure as an auxiliary paired loss instead of replacing source-focused samples with target samples.

Next experiments:

```text
c55-reflow-pair0025-w050-weightonly-c32h160-s14000
c55-reflow-pair005-w050-weightonly-c32h160-s14000
c55-reflow-pair009-w050-weightonly-c32h160-s14000
c55-reflow-pair005-w025-weightonly-c32h160-s14000
c55-reflow-pair005-w100-weightonly-c32h160-s14000
c55-reflow-pair005-w050-target-s025-c32h160-s14000
c55-reflow-pair005-w050-target-s050-c32h160-s14000
c55-reflow-pair005-w050-b196-s10000
c55-reflow-pair009-w050-b196-s10000
c55-reflow-pair005-w050-train1920-s13000
```

Completed C55 results:

```text
c55-reflow-pair009-w050-b196-s10000: OCR 0.5495, segment 697.042ms, motion_delta 0.0485, pass
c55-reflow-pair005-w050-target-s025-c32h160-s14000: OCR 0.5161, segment 631.980ms, motion_delta 0.0520, quality_fail
c55-reflow-pair005-w050-train1920-s13000: OCR 0.5078, segment 698.812ms, motion_delta 0.0516, quality_fail
c55-reflow-pair009-w050-weightonly-c32h160-s14000: OCR 0.5055, segment 692.653ms, motion_delta 0.0535, quality_fail
c55-reflow-pair005-w050-weightonly-c32h160-s14000: OCR 0.4691, segment 724.121ms, motion_delta 0.0510, quality_fail
c55-reflow-pair005-w050-target-s050-c32h160-s14000: OCR 0.4641, segment 880.660ms, motion_delta 0.0536, quality_fail
c55-reflow-pair005-w025-weightonly-c32h160-s14000: OCR 0.4625, segment 706.683ms, motion_delta 0.0500, quality_fail
c55-reflow-pair0025-w050-weightonly-c32h160-s14000: OCR 0.4375, segment 719.565ms, motion_delta 0.0483, quality_fail
c55-reflow-pair005-w100-weightonly-c32h160-s14000: OCR 0.4250, segment 703.645ms, motion_delta 0.0506, quality_fail
c55-reflow-pair005-w050-b196-s10000: OCR 0.4000, segment 630.015ms, motion_delta 0.0503, quality_fail
```

Interpretation:

- Paired target loss does not beat the current C49/C52 learned layout-reflow frontier.
- The best result is a pass, but it sits below `c49-reflow-target-b196-c32h160-s10000` (`0.5761`) and `c52-reflow-target-s050-c32h160-s14000` (`0.5742`).
- The failures cluster around text reconstruction, not speed: all C55 runs remain safely under the `1.3s` 33-frame plus encode budget.
- This makes more loss pressure less promising than changing the model shape.

Next experiments:

```text
c56-detail8-025-target50-c32h160-s14000
c56-detail8-050-target50-c32h160-s14000
c56-detail16-025-target50-c32h160-s14000
c56-detail16h128-025-target50-s14000
c56-detail8-025-weightonly-c32h160-s14000
c56-detail16-025-weightonly-c32h160-s14000
c56-detail8-0125-weightonly-c32h160-s14000
c56-detail8-025-target-b196-s10000
c56-detail16-025-target-b196-s10000
c56-detail8-025-weightonly-train1920-s13000
```

C56 hypothesis:

- Coarse layout transport and high-frequency glyph/detail reconstruction may be fighting for the same latent channels and MLP capacity.
- A residual detail canvas/head keeps the base pure neural-canvas renderer but gives strokes a bounded high-frequency correction path.
- The branch should be judged against the C49/C52 frontier, not just against a pass gate.

Completed C56 results:

```text
c56-detail16h128-025-target50-s14000: OCR 0.5514, segment 875.921ms, motion_delta 0.0491, pass
c56-detail16-025-target-b196-s10000: OCR 0.5346, segment 1116.450ms, motion_delta 0.0495, quality_fail
c56-detail8-025-target50-c32h160-s14000: OCR 0.5119, segment 965.856ms, motion_delta 0.0505, quality_fail
c56-detail8-025-weightonly-c32h160-s14000: OCR 0.5029, segment 832.354ms, motion_delta 0.0493, quality_fail
c56-detail8-050-target50-c32h160-s14000: OCR 0.4906, segment 859.333ms, motion_delta 0.0515, quality_fail
c56-detail8-0125-weightonly-c32h160-s14000: OCR 0.4855, segment 857.504ms, motion_delta 0.0490, quality_fail
c56-detail16-025-weightonly-c32h160-s14000: OCR 0.4845, segment 824.906ms, motion_delta 0.0459, quality_fail
c56-detail8-025-target-b196-s10000: OCR 0.4815, segment 846.429ms, motion_delta 0.0491, quality_fail
c56-detail8-025-weightonly-train1920-s13000: OCR 0.4654, segment 1046.671ms, motion_delta 0.0514, quality_fail
c56-detail16-025-target50-c32h160-s14000: OCR 0.4277, segment 1021.801ms, motion_delta 0.0498, quality_fail
```

Interpretation:

- The residual-detail branch does not beat the learned layout-reflow frontier.
- It is also slower: even successful runs move from the old `~700ms` segment family toward `~825-1116ms`.
- The strongest result uses the larger detail head (`16` channels, hidden `128`) but still trails C49/C52.
- The next architecture branch should avoid a second sampled canvas and instead expose better coordinates to the existing MLP.

Next experiments:

```text
c57-sourcecoord-target50-c32h160-s14000
c57-sourcecoord-target75-c32h160-s14000
c57-sourcecoord-weightonly-c32h160-s14000
c57-sourcecoord-target-b196-s10000
c57-sourcecoord-weight-b196-s14000
c57-sourcecoord-target50-freq12-s12000
c57-sourcecoord-target50-c24h128-s12000
c57-sourcecoord-target50-flow08-s14000
c57-sourcecoord-target50-seed1-s14000
c57-sourcecoord-weightonly-train1920-s13000
```

C57 hypothesis:

- The current MLP sees output coordinates and a latent sample from warped coordinates, but it does not explicitly see the warped/source coordinate.
- Text strokes may need source-space phase information after layout motion; output-space coordinates alone are not enough.
- Adding source-coordinate features should be much cheaper than C56 because it changes conditioning width, not canvas sampling count.

Completed C57 results:

```text
c57-sourcecoord-target75-c32h160-s14000: OCR 0.6264, segment 817.800ms, motion_delta 0.0494, pass
c57-sourcecoord-target50-c24h128-s12000: OCR 0.6000, segment 761.756ms, motion_delta 0.0519, pass
c57-sourcecoord-target-b196-s10000: OCR 0.5981, segment 808.501ms, motion_delta 0.0505, pass
c57-sourcecoord-weightonly-train1920-s13000: OCR 0.5498, segment 804.615ms, motion_delta 0.0502, pass
c57-sourcecoord-weightonly-c32h160-s14000: OCR 0.5444, segment 685.778ms, motion_delta 0.0480, pass
c57-sourcecoord-target50-c32h160-s14000: OCR 0.5238, segment 791.286ms, motion_delta 0.0487, quality_fail
c57-sourcecoord-target50-flow08-s14000: OCR 0.5000, segment 806.558ms, motion_delta 0.0503, quality_fail
c57-sourcecoord-target50-freq12-s12000: OCR 0.4654, segment 746.490ms, motion_delta 0.0510, quality_fail
c57-sourcecoord-weight-b196-s14000: OCR 0.4528, segment 800.270ms, motion_delta 0.0503, quality_fail
c57-sourcecoord-target50-seed1-s14000: OCR 0.4497, segment 806.916ms, motion_delta 0.0500, quality_fail
```

Interpretation:

- Source-coordinate conditioning is the first architecture branch to beat the C49/C52 layout-reflow frontier.
- The best C57 run improves the learned reflow OCR peak from `0.5761` to `0.6264`, while segment latency stays below `1.3s`.
- The `target75` setting is the strongest, which suggests target-side coverage still matters when the MLP can see source-space phase.
- Seed variance remains real: the seed `1` target50 run regressed, so the next branch should test a structural transport hypothesis rather than only retrying the same configuration.

Next experiments:

```text
c58-flow020-target50-c32h160-s12000
c58-flow028-target50-c32h160-s12000
c58-flow035-target50-c32h160-s12000
c58-flow035-weightonly-c32h160-s12000
c58-flow045-target50-c32h160-s12000
c58-flowsup025-w0025-target50-c32h160-s12000
c58-flowsup035-w0025-target50-c32h160-s12000
c58-flowsup035-w005-target50-c32h160-s12000
c58-flowsup035-w0025-weightonly-c32h160-s12000
c58-flowsup045-w0025-target50-c32h160-s12000
```

C58 hypothesis:

- The learned-flow cap has been too small for full layout reflow. Some layout bands move around `0.45` in normalized page coordinates, while prior runs used `flow_scale=0.10`, internally capped around `0.14`.
- Larger flow range should let the latent canvas transport source detail instead of forcing the MLP to repaint text from local output coordinates.
- A light inverse-flow supervision term may make that transport learnable without adding masks, overlays, or a second sampled canvas.

Completed C58 results:

```text
c58-flow028-target50-c32h160-s12000: OCR 0.4286, segment 822.649ms, motion_delta 0.0528, quality_fail
c58-flowsup035-w0025-target50-c32h160-s12000: OCR 0.3727, segment 790.149ms, motion_delta 0.0520, quality_fail
c58-flowsup025-w0025-target50-c32h160-s12000: OCR 0.3086, segment 805.795ms, motion_delta 0.0543, quality_fail
c58-flow020-target50-c32h160-s12000: OCR 0.3077, segment 813.563ms, motion_delta 0.0512, quality_fail
c58-flow045-target50-c32h160-s12000: OCR 0.1896, segment 660.757ms, motion_delta 0.0565, quality_fail
c58-flow035-target50-c32h160-s12000: OCR 0.1744, segment 701.913ms, motion_delta 0.0528, quality_fail
c58-flowsup035-w005-target50-c32h160-s12000: OCR 0.1734, segment 818.933ms, motion_delta 0.0514, quality_fail
c58-flow035-weightonly-c32h160-s12000: OCR 0.1707, segment 867.212ms, motion_delta 0.0495, quality_fail
c58-flowsup035-w0025-weightonly-c32h160-s12000: OCR 0.1677, segment 679.363ms, motion_delta 0.0519, quality_fail
c58-flowsup045-w0025-target50-c32h160-s12000: OCR 0.1235, segment 670.777ms, motion_delta 0.0527, quality_fail
```

Interpretation:

- Wider learned-flow range is not enough; it actively hurts text quality.
- Light inverse-flow supervision also fails at these weights/ranges, so the flow network may be too unconstrained or the photometric objective may fight the transport objective.
- C58 remains fast, but speed is not the bottleneck. The model needs a cleaner way to separate layout transport from pixel/detail reconstruction.

Next experiments:

```text
c59-oracleflow-target75-c32h160-s12000
c59-oracleflow-target50-c32h160-s12000
c59-oracleflow-weightonly-c32h160-s12000
c59-oracleflow-target75-c24h128-s10000
c59-oracleflow-target75-nosrc-c32h160-s12000
c59-oracleflow-target75-freq12-s10000
```

C59 hypothesis:

- Use the known inverse layout-reflow map as an oracle transport control while still rendering all pixels through the neural canvas.
- If oracle flow beats C57, learned transport is the next model target.
- If oracle flow still fails, the bottleneck is in high-frequency reconstruction under reflow, not in motion-field learning.

Completed C59 results:

```text
c59-oracleflow-target75-c24h128-s10000: OCR 0.5207, segment 671.665ms, motion_delta 0.0500, quality_fail
c59-oracleflow-target50-c32h160-s12000: OCR 0.5060, segment 698.560ms, motion_delta 0.0510, quality_fail
c59-oracleflow-target75-nosrc-c32h160-s12000: OCR 0.5059, segment 595.257ms, motion_delta 0.0495, quality_fail
c59-oracleflow-weightonly-c32h160-s12000: OCR 0.4881, segment 675.039ms, motion_delta 0.0494, quality_fail
c59-oracleflow-target75-c32h160-s12000: OCR 0.4751, segment 683.105ms, motion_delta 0.0505, quality_fail
c59-oracleflow-target75-freq12-s10000: OCR 0.4238, segment 729.458ms, motion_delta 0.0493, quality_fail
```

Interpretation:

- Oracle flow does not beat the C57 source-coordinate frontier.
- The best C59 run reaches OCR `0.5207`, well below C57's OCR `0.6264`, even though C59 uses the known inverse layout map.
- Correct rigid transport alone is not enough. The current useful recipe is source-coordinate conditioning, target-side sampling, and a small learned flexible warp.
- C58 showed that larger unconstrained learned flow collapses text; C59 shows that rigid oracle box flow is also insufficient. The next model target is a more robust version of the C57 family, not a stronger box-flow diagnostic.

Next experiments:

```text
c60-sourcecoord-target60-c32h160-s14000
c60-sourcecoord-target70-c32h160-s14000
c60-sourcecoord-target80-c32h160-s14000
c60-sourcecoord-target90-c32h160-s14000
c60-sourcecoord-target100-c32h160-s14000
c60-sourcecoord-target75-seed1-c32h160-s14000
c60-sourcecoord-target75-seed2-c32h160-s14000
c60-sourcecoord-target75-b196-s10000
c60-sourcecoord-target75-c24h128-s12000
c60-sourcecoord-target75-c40h192-s12000
```

C60 hypothesis:

- The C57 gain is best understood as source-coordinate conditioning plus a flexible learned warp, not stronger/oracle transport.
- Sweep target-side sampling around `0.75` to check whether the winner is a narrow accident or a stable ratio.
- Repeat seeds and test C24/H128, B196, and C40/H192 to map the speed/quality frontier before adding new architecture.
