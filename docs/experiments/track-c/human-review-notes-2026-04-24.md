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

Completed C60 results:

```text
c60-sourcecoord-target60-c32h160-s14000: OCR 0.5933, segment 1061.855ms, motion_delta 0.0450, pass
c60-sourcecoord-target75-c24h128-s12000: OCR 0.5837, segment 1013.454ms, motion_delta 0.0492, pass
c60-sourcecoord-target75-seed2-c32h160-s14000: OCR 0.5233, segment 789.126ms, motion_delta 0.0499, quality_fail
c60-sourcecoord-target80-c32h160-s14000: OCR 0.5176, segment 816.972ms, motion_delta 0.0514, quality_fail
c60-sourcecoord-target75-b196-s10000: OCR 0.4837, segment 807.725ms, motion_delta 0.0502, quality_fail
c60-sourcecoord-target75-seed1-c32h160-s14000: OCR 0.4750, segment 917.512ms, motion_delta 0.0509, quality_fail
c60-sourcecoord-target75-c40h192-s12000: OCR 0.4750, segment 899.818ms, motion_delta 0.0514, quality_fail
c60-sourcecoord-target100-c32h160-s14000: OCR 0.4684, segment 814.285ms, motion_delta 0.0502, quality_fail
c60-sourcecoord-target70-c32h160-s14000: OCR 0.4400, segment 812.567ms, motion_delta 0.0489, quality_fail
c60-sourcecoord-target90-c32h160-s14000: OCR 0.4238, segment 676.815ms, motion_delta 0.0506, quality_fail
```

Interpretation:

- C60 confirms source-coordinate conditioning is still the right family, but does not create a new frontier.
- The C57 `target75` result was not robust across seeds: seed `1` and seed `2` fall to OCR `0.4750` and `0.5233`.
- The best C60 signal moves lower, to target-side sampling ratio `0.60`.
- C24/H128 remains surprisingly competitive and worth probing because both C57 and C60 produced pass-quality small-model runs.
- Larger capacity and larger batch do not fix text; C40/H192 and B196 both regress.

Next experiments:

```text
c61-sourcecoord-target55-c32h160-s14000
c61-sourcecoord-target65-c32h160-s14000
c61-sourcecoord-target60-seed1-c32h160-s14000
c61-sourcecoord-target60-seed2-c32h160-s14000
c61-sourcecoord-target60-flow08-c32h160-s14000
c61-sourcecoord-target60-b196-s10000
c61-sourcecoord-target55-c24h128-s12000
c61-sourcecoord-target60-c24h128-s12000
c61-sourcecoord-target60-cosine-c32h160-s16000
c61-sourcecoord-target60-lr007-c32h160-s16000
```

C61 hypothesis:

- If target ratio `0.60` is real and not another seed accident, nearby ratios and seed repeats should cluster near or above OCR `0.59`.
- Lower learned-flow cap may preserve text without losing the required reflow motion.
- C24/H128 may be a better speed/regularization point than larger capacity for this overfit renderer.
- Optimizer variants test whether the C60 winner is optimization-limited before adding a new architecture branch.

Completed C61 results:

```text
c61-sourcecoord-target60-b196-s10000: OCR 0.6077, segment 712.728ms, motion_delta 0.0509, pass
c61-sourcecoord-target60-c24h128-s12000: OCR 0.5972, segment 669.808ms, motion_delta 0.0492, pass
c61-sourcecoord-target60-flow08-c32h160-s14000: OCR 0.5465, segment 1049.906ms, motion_delta 0.0503, quality_fail
c61-sourcecoord-target60-seed2-c32h160-s14000: OCR 0.5429, segment 817.617ms, motion_delta 0.0486, quality_fail
c61-sourcecoord-target60-cosine-c32h160-s16000: OCR 0.5029, segment 858.282ms, motion_delta 0.0501, quality_fail
c61-sourcecoord-target55-c24h128-s12000: OCR 0.4780, segment 893.704ms, motion_delta 0.0504, quality_fail
c61-sourcecoord-target55-c32h160-s14000: OCR 0.4750, segment 824.051ms, motion_delta 0.0465, quality_fail
c61-sourcecoord-target60-seed1-c32h160-s14000: OCR 0.4561, segment 805.678ms, motion_delta 0.0498, quality_fail
c61-sourcecoord-target65-c32h160-s14000: OCR 0.4528, segment 946.467ms, motion_delta 0.0480, quality_fail
c61-sourcecoord-target60-lr007-c32h160-s16000: OCR 0.4500, segment 817.397ms, motion_delta 0.0507, quality_fail
```

Interpretation:

- C61 does not beat the C57 peak, but it finds the best faster candidate: B196 with target ratio `0.60`.
- The B196 run reaches OCR `0.6077` at `712.728ms`, much closer to the C57 peak than C60 while staying faster.
- The C24/H128 run is also strong at OCR `0.5972` and `669.808ms`, supporting the idea that smaller capacity can regularize this overfit renderer.
- Plain C32 target60 remains seed-sensitive: seed `1` and seed `2` land below the pass gate.
- Lower flow, cosine schedule, and lower LR are not useful enough to keep pursuing immediately.

Next experiments:

```text
c62-sourcecoord-target60-b196-s12000
c62-sourcecoord-target60-b196-s14000
c62-sourcecoord-target60-b196-seed1-s10000
c62-sourcecoord-target60-b196-seed2-s10000
c62-sourcecoord-target60-b196-seed3-s10000
c62-sourcecoord-target60-b196-edge06-s10000
c62-sourcecoord-target60-b196-edge12-s10000
c62-sourcecoord-target60-c24h128-seed1-s12000
c62-sourcecoord-target60-c24h128-seed2-s12000
c62-sourcecoord-target60-c24h128-b196-s10000
```

C62 hypothesis:

- If the C61 B196 result is robust, seed repeats should stay near the pass gate and at least one should approach the C57 peak.
- Longer B196 optimization may improve text without spending as much latency as larger render capacity.
- Edge-weight variants test whether the B196 win needs less or more high-frequency pressure.
- C24/H128 seed and B196 variants test whether the small-model regularization signal is stable enough to become the fast baseline.

Completed C62 results:

```text
c62-sourcecoord-target60-c24h128-seed2-s12000: OCR 0.6634, segment 765.292ms, motion_delta 0.0523, pass
c62-sourcecoord-target60-b196-seed1-s10000: OCR 0.5646, segment 821.384ms, motion_delta 0.0470, pass
c62-sourcecoord-target60-b196-edge06-s10000: OCR 0.5566, segment 791.012ms, motion_delta 0.0490, pass
c62-sourcecoord-target60-b196-s14000: OCR 0.5031, segment 860.361ms, motion_delta 0.0534, quality_fail
c62-sourcecoord-target60-b196-seed3-s10000: OCR 0.5000, segment 825.320ms, motion_delta 0.0519, quality_fail
c62-sourcecoord-target60-b196-seed2-s10000: OCR 0.4625, segment 677.876ms, motion_delta 0.0505, quality_fail
c62-sourcecoord-target60-b196-s12000: OCR 0.4568, segment 940.404ms, motion_delta 0.0503, quality_fail
c62-sourcecoord-target60-b196-edge12-s10000: OCR 0.4403, segment 801.896ms, motion_delta 0.0527, quality_fail
c62-sourcecoord-target60-c24h128-seed1-s12000: OCR 0.4403, segment 747.446ms, motion_delta 0.0494, quality_fail
c62-sourcecoord-target60-c24h128-b196-s10000: OCR 0.4286, segment 756.564ms, motion_delta 0.0507, quality_fail
```

Interpretation:

- C62 gives the strongest positive proof so far that the pure neural-canvas reflow path can preserve text while changing the layout: the C24/H128 seed2 run reaches OCR `0.6634`, above the previous C57 frontier.
- The result is not yet reliable. The same C24/H128 recipe spans OCR `0.4403` to `0.6634`, so this is a high basin, not a stable recipe.
- B196 target60 is not the robust fix. Longer B196 optimization regresses, and seed repeats cluster below the old C57 peak.
- Lighter edge pressure helps B196 a little (`edge06` passes), while heavier edge pressure hurts. This suggests over-sharpening pressure can break global reflow text rather than rescue it.

Next experiments:

```text
c63-sourcecoord-target60-c24h128-seed3-s12000
c63-sourcecoord-target60-c24h128-seed4-s12000
c63-sourcecoord-target60-c24h128-seed5-s12000
c63-sourcecoord-target50-c24h128-seed2-s12000
c63-sourcecoord-target55-c24h128-seed2-s12000
c63-sourcecoord-target65-c24h128-seed2-s12000
c63-sourcecoord-target60-c24h128-seed2-s10000
c63-sourcecoord-target60-c24h128-seed2-s14000
c63-sourcecoord-target60-c24h128-edge06-seed2-s12000
c63-sourcecoord-target60-c24h128-edge12-seed2-s12000
```

C63 hypothesis:

- If the C24/H128 `0.6634` result is a real optimization basin, additional seeds should produce at least one more frontier-level result and several pass-quality runs.
- Target ratios around `0.60` test whether the seed2 result depends on the exact target-side sampling mix.
- Shorter and longer seed2 runs test whether the high result is a transient optimum or improves with more steps.
- Edge variants test whether C24/H128 also prefers lower high-frequency pressure, as B196 did in C62.

Completed C63 results:

```text
c63-sourcecoord-target65-c24h128-seed2-s12000: OCR 0.5524, segment 760.141ms, motion_delta 0.0511, pass
c63-sourcecoord-target60-c24h128-seed3-s12000: OCR 0.5000, segment 667.048ms, motion_delta 0.0477, quality_fail
c63-sourcecoord-target60-c24h128-seed5-s12000: OCR 0.5000, segment 774.616ms, motion_delta 0.0525, quality_fail
c63-sourcecoord-target55-c24h128-seed2-s12000: OCR 0.4969, segment 776.702ms, motion_delta 0.0541, quality_fail
c63-sourcecoord-target60-c24h128-edge12-seed2-s12000: OCR 0.4906, segment 768.339ms, motion_delta 0.0491, quality_fail
c63-sourcecoord-target60-c24h128-seed4-s12000: OCR 0.4643, segment 757.827ms, motion_delta 0.0524, quality_fail
c63-sourcecoord-target50-c24h128-seed2-s12000: OCR 0.4568, segment 1060.318ms, motion_delta 0.0567, quality_fail
c63-sourcecoord-target60-c24h128-seed2-s10000: OCR 0.4500, segment 749.205ms, motion_delta 0.0518, quality_fail
c63-sourcecoord-target60-c24h128-edge06-seed2-s12000: OCR 0.4277, segment 963.938ms, motion_delta 0.0515, quality_fail
c63-sourcecoord-target60-c24h128-seed2-s14000: OCR 0.2927, segment 768.867ms, motion_delta 0.0509, quality_fail
```

Interpretation:

- C63 does not reproduce the C62 `0.6634` high-water result. The high basin is real enough to have happened, but not reliable enough to treat as a recipe.
- Additional C24/H128 target60 seeds are stable in speed and motion but not text quality; they cluster around OCR `0.46-0.50`.
- More steps are not a fix: the 14k seed2 repeat collapses, while the 10k seed2 repeat misses.
- Target ratio `0.65` is the only pass in C63, but it is a modest pass at OCR `0.5524`, not a frontier.
- This should move the next work from seed search to training dynamics or architecture. The likely failure is early optimization getting trapped in a blurry/repainted text solution before the full reflow mapping is learned.

Next experiments:

```text
c64-sourcecoord-target60-c24h128-curr25-seed2-s12000
c64-sourcecoord-target60-c24h128-curr50-seed2-s12000
c64-sourcecoord-target60-c24h128-curr25s025-seed2-s12000
c64-sourcecoord-target60-c24h128-curr50s025-seed2-s12000
c64-sourcecoord-target60-c24h128-curr25s025-seed3-s12000
c64-sourcecoord-target60-c24h128-curr25s025-seed4-s12000
c64-sourcecoord-target60-c24h128-curr25s025-seed5-s12000
c64-sourcecoord-target65-c24h128-curr25s025-seed2-s12000
c64-sourcecoord-target60-c32h160-curr25s025-seed1-s14000
c64-sourcecoord-target75-c32h160-curr25s025-seed1-s14000
```

C64 hypothesis:

- A layout-motion curriculum may stabilize text by letting the canvas/MLP lock onto source detail before solving full midpoint reflow.
- If this is the right lever, C24/H128 seed repeats should move upward together rather than producing one lucky high outlier.
- The C32/H160 seed1 repeats test whether curriculum also rescues previously weak C32 source-coordinate seeds.
- Full evaluation still uses full layout reflow; only the training schedule changes.

Completed C64 results:

```text
c64-sourcecoord-target60-c24h128-curr50-seed2-s12000: OCR 0.6077, segment 758.183ms, motion_delta 0.0496, pass
c64-sourcecoord-target75-c32h160-curr25s025-seed1-s14000: OCR 0.5714, segment 814.836ms, motion_delta 0.0498, pass
c64-sourcecoord-target60-c24h128-curr25s025-seed2-s12000: OCR 0.5596, segment 773.672ms, motion_delta 0.0488, pass
c64-sourcecoord-target60-c24h128-curr50s025-seed2-s12000: OCR 0.5258, segment 771.843ms, motion_delta 0.0485, quality_fail
c64-sourcecoord-target60-c32h160-curr25s025-seed1-s14000: OCR 0.4972, segment 802.758ms, motion_delta 0.0507, quality_fail
c64-sourcecoord-target65-c24h128-curr25s025-seed2-s12000: OCR 0.4906, segment 801.374ms, motion_delta 0.0497, quality_fail
c64-sourcecoord-target60-c24h128-curr25s025-seed5-s12000: OCR 0.4875, segment 765.546ms, motion_delta 0.0541, quality_fail
c64-sourcecoord-target60-c24h128-curr25s025-seed4-s12000: OCR 0.4717, segment 769.537ms, motion_delta 0.0484, quality_fail
c64-sourcecoord-target60-c24h128-curr25s025-seed3-s12000: OCR 0.4528, segment 781.857ms, motion_delta 0.0530, quality_fail
c64-sourcecoord-target60-c24h128-curr25-seed2-s12000: OCR 0.4500, segment 766.914ms, motion_delta 0.0493, quality_fail
```

Interpretation:

- Curriculum helps a narrow slice: the 50% zero-start curriculum recovers OCR `0.6077` on seed2, close to the best post-C57 B196 run.
- Curriculum does not yet stabilize the basin. Seed3/4/5 with the same 25% start-at-0.25 curriculum remain below OCR `0.49`.
- The C32 target75 seed1 rescue is useful: C60 target75 seed1 was OCR `0.4750`, while C64 target75 seed1 reaches `0.5714`.
- The grounding review of Flipbook's public language matters here. Flipbook currently describes static image generation and live video as two systems that will eventually merge. That suggests the next overfit proof should explicitly anchor crisp static source/target pages, then train the transition.

Next experiments:

```text
c65-sourcecoord-target60-c24h128-end25-seed2-s12000
c65-sourcecoord-target60-c24h128-end50-seed2-s12000
c65-sourcecoord-target60-c24h128-end75-seed2-s12000
c65-sourcecoord-target60-c24h128-end50-curr50-seed2-s12000
c65-sourcecoord-target60-c24h128-end50-curr25s025-seed2-s12000
c65-sourcecoord-target60-c24h128-end50-seed3-s12000
c65-sourcecoord-target60-c24h128-end50-seed4-s12000
c65-sourcecoord-target60-c24h128-end50-seed5-s12000
c65-sourcecoord-target75-c32h160-end50-seed1-s14000
c65-sourcecoord-target60-c32h160-end50-seed1-s14000
```

C65 hypothesis:

- Endpoint anchoring should help because Flipbook's current public architecture separates static generated pages from video animation.
- Training exact source and reflow-midpoint endpoint frames should make text/layout sharper before the model spends capacity on continuous transition frames.
- If endpoint anchoring is useful, the C24/H128 seed family should improve more consistently than C63/C64.

Completed C65 results:

```text
c65-sourcecoord-target60-c24h128-end50-curr50-seed2-s12000: OCR 0.5207, segment 747.910ms, motion_delta 0.0488, quality_fail
c65-sourcecoord-target60-c24h128-end50-seed5-s12000: OCR 0.5031, segment 681.363ms, motion_delta 0.0486, quality_fail
c65-sourcecoord-target60-c32h160-end50-seed1-s14000: OCR 0.5031, segment 826.452ms, motion_delta 0.0514, quality_fail
c65-sourcecoord-target60-c24h128-end50-seed4-s12000: OCR 0.4906, segment 788.691ms, motion_delta 0.0497, quality_fail
c65-sourcecoord-target60-c24h128-end25-seed2-s12000: OCR 0.4780, segment 759.518ms, motion_delta 0.0489, quality_fail
c65-sourcecoord-target60-c24h128-end50-curr25s025-seed2-s12000: OCR 0.4780, segment 656.867ms, motion_delta 0.0485, quality_fail
c65-sourcecoord-target60-c24h128-end75-seed2-s12000: OCR 0.4780, segment 1050.756ms, motion_delta 0.0511, quality_fail
c65-sourcecoord-target75-c32h160-end50-seed1-s14000: OCR 0.4695, segment 674.206ms, motion_delta 0.0494, quality_fail
c65-sourcecoord-target60-c24h128-end50-seed2-s12000: OCR 0.4133, segment 756.136ms, motion_delta 0.0496, quality_fail
c65-sourcecoord-target60-c24h128-end50-seed3-s12000: OCR 0.4133, segment 761.889ms, motion_delta 0.0512, quality_fail
```

Interpretation:

- Endpoint anchoring is a clean negative. It made the static/source-target story explicit in training, but every run missed the OCR gate.
- The best C65 result (`0.5207`) is below the C64 best (`0.6077`) and far below the C62 high point (`0.6634`).
- Motion and speed remain healthy, so the failure is still text/layout reconstruction, not realtime budget or movement magnitude.
- This argues for a model-layer architecture change instead of more endpoint/mask/compositing pressure.

Next experiments:

```text
c66-neighbor-cross1-target60-c24h128-seed2-s12000
c66-neighbor-cross2-target60-c24h128-seed2-s12000
c66-neighbor-grid1-target60-c24h128-seed2-s12000
c66-neighbor-grid2-target60-c24h128-seed2-s12000
c66-neighbor-cross1-target60-curr50-seed2-s12000
c66-neighbor-grid1-target60-curr50-seed2-s12000
c66-neighbor-cross1-target60-c24h128-seed3-s12000
c66-neighbor-cross1-target60-c24h128-seed4-s12000
c66-neighbor-cross1-target75-c32h160-seed1-s14000
c66-neighbor-cross1-target60-c32h160-seed1-s14000
```

C66 hypothesis:

- A single bilinear latent sample may be too pointwise for reflowed glyphs; the MLP can lose local stroke context while solving transport.
- A small latent neighborhood (`cross` or `grid`, 1-2px radius) keeps the renderer pure neural-canvas pixels while giving the decoder local evidence for glyph/detail reconstruction.
- If the bottleneck is local context, C66 should improve OCR without needing render-time text overlays or rectangular masking tricks.

Completed C66 results:

```text
c66-neighbor-cross1-target60-c32h160-seed1-s14000: OCR 0.6178, segment 1093.608ms, motion_delta 0.0503, pass
c66-neighbor-cross1-target60-c24h128-seed4-s12000: OCR 0.5529, segment 826.475ms, motion_delta 0.0553, pass
c66-neighbor-grid1-target60-c24h128-seed2-s12000: OCR 0.5476, segment 798.603ms, motion_delta 0.0505, quality_fail
c66-neighbor-grid1-target60-curr50-seed2-s12000: OCR 0.5355, segment 909.371ms, motion_delta 0.0499, quality_fail
c66-neighbor-cross1-target75-c32h160-seed1-s14000: OCR 0.5288, segment 926.430ms, motion_delta 0.0514, quality_fail
c66-neighbor-cross1-target60-c24h128-seed2-s12000: OCR 0.5251, segment 842.422ms, motion_delta 0.0534, quality_fail
c66-neighbor-cross2-target60-c24h128-seed2-s12000: OCR 0.5189, segment 831.506ms, motion_delta 0.0540, quality_fail
c66-neighbor-cross1-target60-c24h128-seed3-s12000: OCR 0.4780, segment 823.712ms, motion_delta 0.0466, quality_fail
c66-neighbor-grid2-target60-c24h128-seed2-s12000: OCR 0.4625, segment 912.708ms, motion_delta 0.0503, quality_fail
c66-neighbor-cross1-target60-curr50-seed2-s12000: OCR 0.4500, segment 873.610ms, motion_delta 0.0505, quality_fail
```

Interpretation:

- Latent-neighborhood decoding is a positive architecture signal. It does not beat the C62 high (`0.6634`), but C32/H160 cross1 reaches OCR `0.6178`, close to the C57/C64 frontier and well above the C65 endpoint sweep.
- The useful region appears to be small: 1px neighborhoods help; 2px grid/cross variants regress or blur.
- C32/H160 benefits more than C24/H128. The small model gets one modest pass and one near-pass, while C32/H160 target60 is substantially stronger.
- Curriculum is not compatible with this branch yet; both cross/grid curriculum variants underperform their non-curriculum counterparts.
- The best run is still under the 1.3s budget (`~1.094s` segment), so the architecture has enough latency headroom for a focused sweep.

Next experiments:

```text
c67-neighbor-cross1-target60-c32h160-seed2-s14000
c67-neighbor-cross1-target60-c32h160-seed3-s14000
c67-neighbor-cross1-target60-c32h160-seed4-s14000
c67-neighbor-cross1-target55-c32h160-seed1-s14000
c67-neighbor-cross1-target65-c32h160-seed1-s14000
c67-neighbor-cross05-target60-c32h160-seed1-s14000
c67-neighbor-cross15-target60-c32h160-seed1-s14000
c67-neighbor-grid1-target60-c32h160-seed1-s14000
c67-neighbor-cross1-target60-b196-c32h160-seed1-s10000
c67-neighbor-cross1-target60-c40h192-seed1-s12000
```

C67 hypothesis:

- If the C66 C32/H160 win is a real basin, target60 seed repeats should produce multiple pass-quality runs, not one seed1 outlier.
- Target-ratio `0.55/0.65` and radius `0.5/1.5px` test whether the C66 best is sitting on a narrow hyperparameter edge.
- B196 and C40/H192 test whether the neighborhood decoder can convert extra training signal or capacity into a new frontier while staying inside the realtime segment budget.

Completed C67 results:

```text
c67-neighbor-cross05-target60-c32h160-seed1-s14000: OCR 0.5957, segment 1265.377ms, motion_delta 0.0538, pass
c67-neighbor-cross1-target60-c40h192-seed1-s12000: OCR 0.5521, segment 1074.821ms, motion_delta 0.0499, pass
c67-neighbor-grid1-target60-c32h160-seed1-s14000: OCR 0.5233, segment 872.636ms, motion_delta 0.0504, quality_fail
c67-neighbor-cross1-target65-c32h160-seed1-s14000: OCR 0.5176, segment 1098.704ms, motion_delta 0.0501, quality_fail
c67-neighbor-cross1-target60-c32h160-seed4-s14000: OCR 0.5146, segment 1017.327ms, motion_delta 0.0510, quality_fail
c67-neighbor-cross15-target60-c32h160-seed1-s14000: OCR 0.4970, segment 1099.051ms, motion_delta 0.0499, quality_fail
c67-neighbor-cross1-target60-b196-c32h160-seed1-s10000: OCR 0.4750, segment 906.667ms, motion_delta 0.0494, quality_fail
c67-neighbor-cross1-target55-c32h160-seed1-s14000: OCR 0.4520, segment 940.797ms, motion_delta 0.0515, quality_fail
c67-neighbor-cross1-target60-c32h160-seed3-s14000: OCR 0.4368, segment 926.499ms, motion_delta 0.0516, quality_fail
c67-neighbor-cross1-target60-c32h160-seed2-s14000: OCR 0.4267, segment 1057.804ms, motion_delta 0.0492, quality_fail
```

Interpretation:

- C67 does not make C66 robust. The C66 seed1 C32/H160 `0.6178` result did not reproduce on seed2/3/4.
- Smaller radius helps the seed1 family (`0.5px` reaches OCR `0.5957`), but it comes close to the latency ceiling at `1265ms`.
- C40/H192 passes but only at OCR `0.5521`; more capacity alone is not the missing piece.
- B196, target55, target65, grid1, and radius1.5 all regress. The neighborhood branch is useful, but the model still lacks a stabilizing representation for page-level context.

C68 hypothesis:

- A single high-resolution latent grid plus local taps may overfit local strokes without a stable coarse page representation.
- Add a coarse latent context canvas sampled alongside the local latent neighborhood, then let one MLP fuse local glyph detail with broader page/layout context.
- This remains pure neural-canvas pixel generation: no overlays, no text compositing, no render-time layout engine.

Next experiments:

```text
c68-context16s025-cross1-target60-c32h160-seed1-s14000
c68-context16s050-cross1-target60-c32h160-seed1-s14000
c68-context32s025-cross1-target60-c32h160-seed1-s14000
c68-context8s025-cross1-target60-c32h160-seed1-s14000
c68-context16s025-cross05-target60-c32h160-seed1-s14000
c68-context16s025-cross1-target60-c32h160-seed2-s14000
c68-context16s025-cross1-target60-c32h160-seed3-s14000
c68-context16s025-cross1-target60-c32h160-seed4-s14000
c68-context16s025-cross1-target60-c24h128-seed2-s12000
c68-context16s025-grid1-target60-c24h128-seed2-s12000
```

Completed C68 results:

```text
c68-context8s025-cross1-target60-c32h160-seed1-s14000: OCR 0.6269, segment 998.129ms, motion_delta 0.0525, pass
c68-context16s050-cross1-target60-c32h160-seed1-s14000: OCR 0.6214, segment 988.723ms, motion_delta 0.0495, pass
c68-context16s025-cross1-target60-c32h160-seed4-s14000: OCR 0.5701, segment 972.935ms, motion_delta 0.0497, pass
c68-context16s025-grid1-target60-c24h128-seed2-s12000: OCR 0.5302, segment 978.481ms, motion_delta 0.0495, quality_fail
c68-context16s025-cross1-target60-c32h160-seed1-s14000: OCR 0.5000, segment 980.266ms, motion_delta 0.0501, quality_fail
c68-context16s025-cross05-target60-c32h160-seed1-s14000: OCR 0.4750, segment 833.710ms, motion_delta 0.0519, quality_fail
c68-context16s025-cross1-target60-c32h160-seed2-s14000: OCR 0.4596, segment 822.816ms, motion_delta 0.0474, quality_fail
c68-context32s025-cross1-target60-c32h160-seed1-s14000: OCR 0.4250, segment 1159.785ms, motion_delta 0.0501, quality_fail
c68-context16s025-cross1-target60-c24h128-seed2-s12000: OCR 0.4172, segment 732.374ms, motion_delta 0.0551, quality_fail
c68-context16s025-cross1-target60-c32h160-seed3-s14000: OCR 0.3959, segment 975.005ms, motion_delta 0.0529, quality_fail
```

Interpretation:

- C68 is the strongest architecture signal since source-coordinate conditioning. Light coarse context helps: `c8/scale0.25` reaches OCR `0.6269`, above C66 and C64, close to C62's one-off high.
- `c16/scale0.5` also works at OCR `0.6214`, suggesting useful context can come from either fewer coarse channels or a less-compressed context grid.
- Heavy context is harmful: `c32/scale0.25` collapses to OCR `0.4250`, and `c16/scale0.25` is unstable across seeds.
- The best C68 runs remain under the 1.3s segment budget, around `~999ms`.
- The right next question is robustness, not another mechanism.

Next experiments:

```text
c69-context8s025-cross1-target60-c32h160-seed2-s14000
c69-context8s025-cross1-target60-c32h160-seed3-s14000
c69-context8s025-cross1-target60-c32h160-seed4-s14000
c69-context8s025-cross1-target60-c32h160-seed5-s14000
c69-context16s050-cross1-target60-c32h160-seed2-s14000
c69-context16s050-cross1-target60-c32h160-seed3-s14000
c69-context16s050-cross1-target60-c32h160-seed4-s14000
c69-context8s050-cross1-target60-c32h160-seed1-s14000
c69-context4s025-cross1-target60-c32h160-seed1-s14000
c69-context12s025-cross1-target60-c32h160-seed1-s14000
```

C69 hypothesis:

- If light context is the stabilizer, c8/scale0.25 and c16/scale0.5 should produce multiple pass-quality seed repeats.
- c4/c8/c12 and scale0.25/0.50 test whether there is a narrow context-capacity sweet spot.
- If the seed repeats collapse again, the bottleneck is not just coarse context; it is probably the training distribution or objective.

Completed C69 results:

```text
c69-context8s025-cross1-target60-c32h160-seed3-s14000: OCR 0.6019, segment 970.229ms, motion_delta 0.0512, pass
c69-context4s025-cross1-target60-c32h160-seed1-s14000: OCR 0.5746, segment 811.086ms, motion_delta 0.0524, pass
c69-context8s025-cross1-target60-c32h160-seed2-s14000: OCR 0.5525, segment 984.923ms, motion_delta 0.0504, pass
c69-context12s025-cross1-target60-c32h160-seed1-s14000: OCR 0.5486, segment 989.633ms, motion_delta 0.0526, quality_fail
c69-context16s050-cross1-target60-c32h160-seed2-s14000: OCR 0.5476, segment 979.132ms, motion_delta 0.0536, quality_fail
c69-context8s025-cross1-target60-c32h160-seed5-s14000: OCR 0.5318, segment 970.567ms, motion_delta 0.0602, quality_fail
c69-context8s050-cross1-target60-c32h160-seed1-s14000: OCR 0.5294, segment 1113.000ms, motion_delta 0.0515, quality_fail
c69-context8s025-cross1-target60-c32h160-seed4-s14000: OCR 0.5031, segment 1305.045ms, motion_delta 0.0508, quality_fail
c69-context16s050-cross1-target60-c32h160-seed3-s14000: OCR 0.4845, segment 974.191ms, motion_delta 0.0493, quality_fail
c69-context16s050-cross1-target60-c32h160-seed4-s14000: OCR 0.4400, segment 977.897ms, motion_delta 0.0478, quality_fail
```

Interpretation:

- Light context is real, but it is not a full robustness solution. Counting the original C68 seed1, the c8/scale0.25 family has three passes and two near-misses across seed1-5.
- c16/scale0.5 did not reproduce the strong C68 seed1 result; the C69 repeats range from OCR `0.4400-0.5476`.
- c4/scale0.25 passing at OCR `0.5746` suggests the useful context signal is compact, not high capacity.
- Most runs remain inside the realtime budget; the failure is still text/layout fidelity. The next move should keep the light-context architecture and change the training distribution around target-layout text positions.

Next experiments:

```text
c70-mid10-c8s025-seed4-s14000
c70-mid20-c8s025-seed4-s14000
c70-mid35-c8s025-seed4-s14000
c70-mid20w012-c8s025-seed4-s14000
c70-mid20-c8s025-seed5-s14000
c70-mid20-c8s025-seed2-s14000
c70-mid20-c4s025-seed2-s14000
c70-mid20-c4s025-seed3-s14000
c70-mid20-c8s025-target45-seed4-s14000
c70-mid20-c8s025-text65-seed4-s14000
```

C70 hypothesis:

- C69 may still undersample the actual reflowed target-layout glyph positions, especially on weak seeds.
- Add direct target-midpoint glyph/text sampling during training: some samples are drawn from the synthetic reflowed midpoint's glyph/text distribution with time near `t=0.5`.
- This is not a render-time text mask or overlay; it is only a training distribution change. If it helps seed4/5, the bottleneck is target-layout data coverage. If it regresses, C69's variance is more likely an architectural representation issue.

Completed C70 results:

```text
c70-mid10-c8s025-seed4-s14000: OCR 0.5822, segment 1006.430ms, motion_delta 0.0460, pass
c70-mid20-c4s025-seed3-s14000: OCR 0.5792, segment 1230.247ms, motion_delta 0.0472, pass
c70-mid35-c8s025-seed4-s14000: OCR 0.5497, segment 1072.882ms, motion_delta 0.0474, quality_fail
c70-mid20-c4s025-seed2-s14000: OCR 0.5444, segment 1161.753ms, motion_delta 0.0481, quality_fail
c70-mid20-c8s025-seed5-s14000: OCR 0.4906, segment 992.803ms, motion_delta 0.0509, quality_fail
c70-mid20-c8s025-seed2-s14000: OCR 0.4875, segment 988.047ms, motion_delta 0.0514, quality_fail
c70-mid20-c8s025-text65-seed4-s14000: OCR 0.4780, segment 982.695ms, motion_delta 0.0471, quality_fail
c70-mid20w012-c8s025-seed4-s14000: OCR 0.4780, segment 1182.926ms, motion_delta 0.0501, quality_fail
c70-mid20-c8s025-seed4-s14000: OCR 0.4750, segment 1003.310ms, motion_delta 0.0493, quality_fail
c70-mid20-c8s025-target45-seed4-s14000: OCR 0.4691, segment 1173.680ms, motion_delta 0.0474, quality_fail
```

Interpretation:

- Direct target-mid sampling has a narrow positive signal. `mid10/c8/seed4` rescues the exact C69 weak seed4 from OCR `0.5031` to `0.5822` and passes.
- Too much target-mid sampling is harmful for c8: `mid20` regresses seed2/4/5, and lowering target-side reflow sampling to `0.45` does not help.
- c4 context remains interesting: `mid20/c4/seed3` passes and `mid20/c4/seed2` lands just below the gate, though both are slower.
- Explicit OCR text-box training does not rescue the seed4 case. The `text65` ablation lands at OCR `0.4780`, which supports staying with general glyph/layout sampling rather than leaning on text-box supervision.

Next experiments:

```text
c71-mid05-c8s025-seed4-s14000
c71-mid075-c8s025-seed4-s14000
c71-mid15-c8s025-seed4-s14000
c71-mid05-c8s025-seed5-s14000
c71-mid10-c8s025-seed5-s14000
c71-mid10-c8s025-seed2-s14000
c71-mid10-c4s025-seed2-s14000
c71-mid10-c4s025-seed3-s14000
c71-mid10-c4s025-seed4-s14000
c71-mid15-c4s025-seed2-s14000
```

C71 hypothesis:

- The useful C70 region is a low direct target-mid sampling dose, not the heavier `0.20-0.35` range.
- C71 tests whether `0.05/0.075/0.10/0.15` can make weak c8 seeds more stable and whether c4 context is a better compact-context basin.
- A strong outcome would be multiple c8/c4 weak-seed passes without enabling OCR-box text supervision.

Completed C71 results:

```text
c71-mid05-c8s025-seed5-s14000: OCR 0.5905, segment 987.250ms, motion_delta 0.0508, pass
c71-mid15-c4s025-seed2-s14000: OCR 0.5701, segment 989.769ms, motion_delta 0.0503, pass
c71-mid10-c4s025-seed4-s14000: OCR 0.5581, segment 1352.030ms, motion_delta 0.0471, latency_fail
c71-mid10-c8s025-seed5-s14000: OCR 0.5106, segment 1162.595ms, motion_delta 0.0530, quality_fail
c71-mid10-c8s025-seed2-s14000: OCR 0.5000, segment 803.845ms, motion_delta 0.0507, quality_fail
c71-mid10-c4s025-seed2-s14000: OCR 0.4780, segment 1005.385ms, motion_delta 0.0478, quality_fail
c71-mid10-c4s025-seed3-s14000: OCR 0.4750, segment 994.048ms, motion_delta 0.0510, quality_fail
c71-mid05-c8s025-seed4-s14000: OCR 0.4725, segment 988.146ms, motion_delta 0.0502, quality_fail
c71-mid075-c8s025-seed4-s14000: OCR 0.4528, segment 1002.821ms, motion_delta 0.0566, quality_fail
c71-mid15-c8s025-seed4-s14000: OCR 0.4267, segment 1212.909ms, motion_delta 0.0511, quality_fail
```

Interpretation:

- The low-dose signal is real but not globally robust. `c8/mid05` rescues seed5, while seed4 only passed in the earlier `c70-mid10` run.
- The c4 branch still looks like the more compact basin: `c4/mid15/seed2` passes, and `c4/mid10/seed4` clears OCR but misses latency.
- This is not enough to declare the pure neural-canvas path solved. It does, however, narrow the next robustness check to two plausible recipes: `c8/mid05` and `c4/mid15`.

Next experiments:

```text
c72-c8mid05-seed1-s14000
c72-c8mid05-seed2-s14000
c72-c8mid05-seed3-s14000
c72-c8mid05-seed4-s14000
c72-c8mid05-seed6-s14000
c72-c4mid15-seed1-s14000
c72-c4mid15-seed3-s14000
c72-c4mid15-seed4-s14000
c72-c4mid15-seed5-s14000
c72-c4mid20-seed4-s14000
```

C72 hypothesis:

- If either low-dose recipe is real, it should produce several pass/near-pass seeds without further tuning.
- `c8/mid05` tests the lowest-dose rescue path that helped seed5.
- `c4/mid15` tests whether the smaller context canvas is a more stable representation than c8 for target-mid sampling.

Completed C72 results:

```text
c72-c4mid20-seed4-s14000: OCR 0.5389, segment 833.356ms, motion_delta 0.0479, quality_fail
c72-c8mid05-seed1-s14000: OCR 0.5294, segment 987.852ms, motion_delta 0.0523, quality_fail
c72-c4mid15-seed1-s14000: OCR 0.5150, segment 997.445ms, motion_delta 0.0538, quality_fail
c72-c8mid05-seed2-s14000: OCR 0.5000, segment 981.260ms, motion_delta 0.0487, quality_fail
c72-c8mid05-seed4-s14000: OCR 0.5000, segment 1177.482ms, motion_delta 0.0493, quality_fail
c72-c4mid15-seed5-s14000: OCR 0.4938, segment 1000.736ms, motion_delta 0.0550, quality_fail
c72-c4mid15-seed4-s14000: OCR 0.4906, segment 1015.182ms, motion_delta 0.0471, quality_fail
c72-c8mid05-seed3-s14000: OCR 0.4906, segment 1171.951ms, motion_delta 0.0495, quality_fail
c72-c4mid15-seed3-s14000: OCR 0.4654, segment 816.381ms, motion_delta 0.0497, quality_fail
c72-c8mid05-seed6-s14000: OCR 0.4500, segment 1178.060ms, motion_delta 0.0504, quality_fail
```

Interpretation:

- C72 is a robustness negative. Neither `c8/mid05` nor `c4/mid15` produces repeatable passes.
- The target-mid sampler can rescue individual seeds, but it is not the stabilizing mechanism we need.
- This pushes the next move back to model architecture. The current coarse context is sampled at the source/warped coordinate, which helps content identity but may not give the decoder a destination-layout memory.

Next experiments:

```text
c73-c8target-seed1-s14000
c73-c8target-seed2-s14000
c73-c8target-seed4-s14000
c73-c8both-seed1-s14000
c73-c8both-seed2-s14000
c73-c8both-seed4-s14000
c73-c4target-seed1-s14000
c73-c4target-seed2-s14000
c73-c4both-seed1-s14000
c73-c4both-seed2-s14000
```

C73 hypothesis:

- Source-coordinate context may preserve glyph/source detail but underrepresent the destination page layout.
- Target-coordinate context samples the coarse context canvas at the output coordinate, giving the decoder destination-layout memory.
- Both-mode context concatenates source-sampled and target-sampled coarse features, testing whether the model needs both content identity and destination layout. This remains pure neural-canvas pixel generation.

Completed C73 results:

```text
c73-c8both-seed1-s14000: OCR 0.5614, segment 1149.288ms, motion_delta 0.0527, pass
c73-c8target-seed4-s14000: OCR 0.5031, segment 983.480ms, motion_delta 0.0494, quality_fail
c73-c4both-seed2-s14000: OCR 0.5000, segment 974.030ms, motion_delta 0.0487, quality_fail
c73-c8both-seed4-s14000: OCR 0.5000, segment 993.664ms, motion_delta 0.0499, quality_fail
c73-c4both-seed1-s14000: OCR 0.4906, segment 960.361ms, motion_delta 0.0502, quality_fail
c73-c4target-seed1-s14000: OCR 0.4906, segment 1171.539ms, motion_delta 0.0514, quality_fail
c73-c4target-seed2-s14000: OCR 0.4780, segment 980.857ms, motion_delta 0.0492, quality_fail
c73-c8both-seed2-s14000: OCR 0.4780, segment 824.284ms, motion_delta 0.0507, quality_fail
c73-c8target-seed1-s14000: OCR 0.4750, segment 1153.291ms, motion_delta 0.0508, quality_fail
c73-c8target-seed2-s14000: OCR 0.4750, segment 985.001ms, motion_delta 0.0501, quality_fail
```

Interpretation:

- Coarse target-only context is not useful. It misses every run and does not improve the weak seeds.
- Coarse both-mode context gives one pass (`c8both/seed1`) but does not beat the earlier source-context seed1 frontier and does not reproduce on seed2/4.
- Destination information may need to arrive at high-resolution latent detail scale, not only coarse-context scale.

Next experiments:

```text
c74-latentboth-c8-seed1-s14000
c74-latentboth-c8-seed2-s14000
c74-latentboth-c8-seed4-s14000
c74-latenttarget-c8-seed1-s14000
c74-latenttarget-c8-seed2-s14000
c74-latentboth-c4-seed1-s14000
c74-latentboth-c4-seed2-s14000
c74-latentboth-c4-seed4-s14000
c74-latentboth-nocontext-seed1-s14000
c74-latentboth-nocontext-seed2-s14000
```

C74 hypothesis:

- The decoder may need high-resolution target-coordinate latent features, not just coarse target context.
- `latentboth` concatenates high-resolution source-sampled and target-sampled latent neighborhoods.
- `latenttarget` tests whether destination detail alone is useful; no-context dual-latent tests whether the high-res dual sample can replace coarse context.

Completed C74 results:

```text
c74-latentboth-nocontext-seed1-s14000: OCR 0.5150, segment 1125.600ms, motion_delta 0.0512, quality_fail
c74-latentboth-c4-seed4-s14000: OCR 0.5031, segment 1493.471ms, motion_delta 0.0519, quality_fail
c74-latentboth-c8-seed1-s14000: OCR 0.5000, segment 1248.325ms, motion_delta 0.0523, quality_fail
c74-latentboth-c8-seed4-s14000: OCR 0.4906, segment 1240.517ms, motion_delta 0.0484, quality_fail
c74-latentboth-c4-seed1-s14000: OCR 0.4780, segment 980.285ms, motion_delta 0.0535, quality_fail
c74-latentboth-c4-seed2-s14000: OCR 0.4780, segment 1245.005ms, motion_delta 0.0473, quality_fail
c74-latenttarget-c8-seed1-s14000: OCR 0.4654, segment 987.915ms, motion_delta 0.0527, quality_fail
c74-latentboth-c8-seed2-s14000: OCR 0.4654, segment 1388.499ms, motion_delta 0.0476, quality_fail
c74-latenttarget-c8-seed2-s14000: OCR 0.4625, segment 986.443ms, motion_delta 0.0502, quality_fail
c74-latentboth-nocontext-seed2-s14000: OCR 0.4400, segment 973.454ms, motion_delta 0.0512, quality_fail
```

Interpretation:

- C74 is a clean negative for simple source/target latent concatenation. No run clears OCR; several dual-latent runs also pressure or miss the 1.3s segment budget.
- Target-only high-resolution latent features are not enough to redraw destination-local text/detail.
- The next model-layer move should separate roles inside the decoder instead of handing one MLP a larger pile of coordinates and features.

Next experiments:

```text
c75-dualres-s025-c8-seed1-s14000
c75-dualres-s025-c8-seed2-s14000
c75-dualres-s025-c8-seed4-s14000
c75-dualres-s050-c8-seed1-s14000
c75-dualres-s050-c8-seed2-s14000
c75-dualres-s050-c8-seed4-s14000
c75-dualres-s050-c4-seed1-s14000
c75-dualres-s050-c4-seed2-s14000
c75-dualres-s050-c4-seed4-s14000
c75-dualres-s050-nocontext-seed1-s14000
```

C75 hypothesis:

- A source branch can preserve content identity from the warped/source coordinate, while a gated target-position residual branch can repair destination-local layout/detail.
- Initializing the target residual branch at zero keeps the model near the source-only baseline early in training, then lets it learn only useful destination corrections.
- This remains pure neural-canvas rendering: every output pixel is produced by the model, with no overlay, mask compositing, or layout runtime at render time.

Completed C75 results:

```text
c75-dualres-s025-c8-seed2-s14000: OCR 0.6415, segment 1079.082ms, motion_delta 0.0500, pass
c75-dualres-s050-nocontext-seed1-s14000: OCR 0.5771, segment 1224.590ms, motion_delta 0.0502, pass
c75-dualres-s050-c8-seed1-s14000: OCR 0.5488, segment 1106.636ms, motion_delta 0.0469, quality_fail
c75-dualres-s025-c8-seed4-s14000: OCR 0.5476, segment 1373.106ms, motion_delta 0.0533, quality_fail
c75-dualres-s050-c8-seed2-s14000: OCR 0.5446, segment 1323.006ms, motion_delta 0.0487, quality_fail
c75-dualres-s050-c4-seed2-s14000: OCR 0.5238, segment 1336.352ms, motion_delta 0.0475, quality_fail
c75-dualres-s050-c4-seed1-s14000: OCR 0.4906, segment 1172.646ms, motion_delta 0.0503, quality_fail
c75-dualres-s025-c8-seed1-s14000: OCR 0.4654, segment 1327.246ms, motion_delta 0.0511, quality_fail
c75-dualres-s050-c8-seed4-s14000: OCR 0.4400, segment 1334.983ms, motion_delta 0.0491, quality_fail
c75-dualres-s050-c4-seed4-s14000: OCR 0.4267, segment 1524.649ms, motion_delta 0.0520, quality_fail
```

Interpretation:

- C75 is the strongest architecture signal since source-coordinate conditioning. It produces a new high-quality C75 pass at OCR `0.6415`, close to the old C62 high point and above the C68/C69 compact-context band.
- The result is still seed-sensitive. c8/scale0.25 seed2 is excellent, seed4 nearly clears OCR but misses latency, and seed1 is weak.
- c8/scale0.50 is not better than scale0.25. c4 context is weak. The no-context pass is important because it suggests the branch separation itself carries value, not just more context features.
- Latency is now part of the problem: several near-misses clear or nearly clear quality but land around `1.32-1.37s`.

Next experiments:

```text
c76-dualres-s025-c8-th48-seed1-s14000
c76-dualres-s025-c8-th48-seed2-s14000
c76-dualres-s025-c8-th48-seed4-s14000
c76-dualres-s035-c8-th64-seed1-s14000
c76-dualres-s035-c8-th64-seed2-s14000
c76-dualres-s035-c8-th64-seed4-s14000
c76-dualres-s050-nocontext-th64-seed1-s14000
c76-dualres-s050-nocontext-th64-seed2-s14000
c76-dualres-s050-nocontext-th64-seed4-s14000
c76-dualres-s025-nocontext-th64-seed2-s14000
```

C76 hypothesis:

- A smaller target residual branch (`h48/h64`) may keep the useful branch separation while pulling latency back under budget.
- `s0.25/c8` is the quality anchor; `s0.35/c8` tests whether the near-miss seeds need slightly more target correction without the instability of `s0.50`.
- No-context repeats test whether coarse context is optional once the decoder roles are separated.

Completed C76 results:

```text
c76-dualres-s035-c8-th64-seed1-s14000: OCR 0.6154, segment 1313.923ms, motion_delta 0.0510, latency_fail
c76-dualres-s025-c8-th48-seed2-s14000: OCR 0.4875, segment 1272.405ms, motion_delta 0.0474, quality_fail
c76-dualres-s050-nocontext-th64-seed4-s14000: OCR 0.4780, segment 1204.973ms, motion_delta 0.0493, quality_fail
c76-dualres-s025-c8-th48-seed4-s14000: OCR 0.4654, segment 1042.119ms, motion_delta 0.0504, quality_fail
c76-dualres-s050-nocontext-th64-seed2-s14000: OCR 0.4625, segment 990.261ms, motion_delta 0.0511, quality_fail
c76-dualres-s035-c8-th64-seed2-s14000: OCR 0.4444, segment 1309.871ms, motion_delta 0.0488, quality_fail
c76-dualres-s025-nocontext-th64-seed2-s14000: OCR 0.4430, segment 1204.061ms, motion_delta 0.0507, quality_fail
c76-dualres-s050-nocontext-th64-seed1-s14000: OCR 0.4403, segment 1239.462ms, motion_delta 0.0507, quality_fail
c76-dualres-s025-c8-th48-seed1-s14000: OCR 0.4264, segment 1437.339ms, motion_delta 0.0494, quality_fail
c76-dualres-s035-c8-th64-seed4-s14000: OCR 0.3841, segment 1299.373ms, motion_delta 0.0499, quality_fail
```

Interpretation:

- C76 is not a consolidation win. Smaller target heads usually improve speed but lose the high-quality C75 behavior.
- The exception is `s0.35/c8/h64/seed1`, which clears OCR strongly (`0.6154`) and misses latency by only `13.9ms`. That means the architecture still has a real basin, but branch capacity/optimization remains unstable.
- No-context repeats did not reproduce the C75 no-context pass once the target branch changed from `h80` to `h64`.

Next experiments:

```text
c77-map-s025-c8-h80-seed5-s14000
c77-map-s025-c8-h80-seed6-s14000
c77-map-s025-c8-h80-seed7-s14000
c77-map-s025-c8-h80-seed8-s14000
c77-map-s035-c8-h64-seed5-s14000
c77-map-s035-c8-h64-seed6-s14000
c77-map-s035-c8-h64-seed7-s14000
c77-map-s035-c8-h64-seed8-s14000
c77-stab-s025-c8-h80-lr007-seed1-s14000
c77-stab-s025-c8-h80-clip025-seed4-s14000
```

C77 hypothesis:

- If the dual-residual architecture is viable, the C75/C76 high-quality basin should appear in more seeds for either `s0.25/c8/h80` or `s0.35/c8/h64`.
- Lower LR on the weak seed1 and tighter clipping on the near-miss seed4 test whether the instability is optimizer noise rather than architectural insufficiency.

Completed C77 results:

```text
c77-map-s025-c8-h80-seed5-s14000: OCR 0.5660, segment 1456.163ms, motion_delta 0.0477, quality_fail
c77-map-s025-c8-h80-seed7-s14000: OCR 0.5357, segment 1335.632ms, motion_delta 0.0508, quality_fail
c77-map-s035-c8-h64-seed7-s14000: OCR 0.5278, segment 1306.513ms, motion_delta 0.0483, quality_fail
c77-map-s025-c8-h80-seed6-s14000: OCR 0.5234, segment 1335.926ms, motion_delta 0.0498, quality_fail
c77-map-s035-c8-h64-seed6-s14000: OCR 0.5233, segment 1309.011ms, motion_delta 0.0498, quality_fail
c77-map-s025-c8-h80-seed8-s14000: OCR 0.4906, segment 1109.897ms, motion_delta 0.0523, quality_fail
c77-map-s035-c8-h64-seed8-s14000: OCR 0.4875, segment 1507.711ms, motion_delta 0.0513, quality_fail
c77-stab-s025-c8-h80-clip025-seed4-s14000: OCR 0.4875, segment 1336.055ms, motion_delta 0.0504, quality_fail
c77-stab-s025-c8-h80-lr007-seed1-s14000: OCR 0.4742, segment 1336.149ms, motion_delta 0.0520, quality_fail
c77-map-s035-c8-h64-seed5-s14000: OCR 0.4625, segment 1338.574ms, motion_delta 0.0520, quality_fail
```

Interpretation:

- C77 is a negative basin map. The C75 high-quality result does not appear frequently across new seeds.
- The best new seed (`s0.25/c8/h80/seed5`) clears OCR but misses latency badly. The optimizer tweaks do not rescue the weak/near-miss seeds.
- Dual-residual remains a useful clue, but the branch design is brittle. The next move should make the residual branch more informed rather than just changing seed or optimizer.

Next experiments:

```text
c78-fused-s025-c8-h80-seed1-s14000
c78-fused-s025-c8-h80-seed2-s14000
c78-fused-s025-c8-h80-seed4-s14000
c78-fused-s025-c8-h80-seed5-s14000
c78-fused-s025-c8-h80-seed6-s14000
c78-fused-s035-c8-h80-seed1-s14000
c78-fused-s035-c8-h80-seed2-s14000
c78-fused-s035-c8-h80-seed4-s14000
c78-fused-s025-c8-h64-seed2-s14000
c78-fused-s025-c8-h64-seed5-s14000
```

C78 hypothesis:

- Keep the C75 source-branch/residual-branch separation, but let the zero-initialized residual branch see both source-sampled and target-position latent features.
- This differs from C74's failed concatenation because the main source renderer remains intact; the fused path can only learn a gated residual correction.
- If the target repair branch was under-informed in C75-C77, fused residuals should improve pass frequency without returning to C74's single-MLP confusion.

Completed C78 results:

```text
c78-fused-s025-c8-h64-seed2-s14000: OCR 0.6038, segment 1499.870ms, motion_delta 0.0475, latency_fail
c78-fused-s035-c8-h80-seed4-s14000: OCR 0.5357, segment 1197.911ms, motion_delta 0.0475, quality_fail
c78-fused-s025-c8-h64-seed5-s14000: OCR 0.5465, segment 1480.895ms, motion_delta 0.0526, quality_fail
c78-fused-s025-c8-h80-seed5-s14000: OCR 0.4906, segment 1689.149ms, motion_delta 0.0507, quality_fail
c78-fused-s035-c8-h80-seed1-s14000: OCR 0.4780, segment 1522.793ms, motion_delta 0.0501, quality_fail
c78-fused-s035-c8-h80-seed2-s14000: OCR 0.4780, segment 1514.992ms, motion_delta 0.0512, quality_fail
c78-fused-s025-c8-h80-seed1-s14000: OCR 0.4654, segment 1630.933ms, motion_delta 0.0512, quality_fail
c78-fused-s025-c8-h80-seed6-s14000: OCR 0.4625, segment 1532.631ms, motion_delta 0.0489, quality_fail
c78-fused-s025-c8-h80-seed2-s14000: OCR 0.4417, segment 1509.706ms, motion_delta 0.0487, quality_fail
c78-fused-s025-c8-h80-seed4-s14000: OCR 0.3947, segment 1510.334ms, motion_delta 0.0508, quality_fail
```

Interpretation:

- C78 does not stabilize dual-residual. The best OCR run is a latency miss, and most fused residual runs are both slower and below the quality gate.
- The useful lesson is negative: simply exposing the target repair branch to both source and target latent features adds cost/confusion. The bottleneck now looks more like spatial high-frequency representation than missing MLP inputs.
- The next branch should make text/detail easier to preserve as spatial content while keeping the renderer pixel-native.

Next experiments:

```text
c79-rgbskip-s025-c8-seed1-s14000
c79-rgbskip-s025-c8-seed2-s14000
c79-rgbskip-s025-c8-seed4-s14000
c79-rgbskip-s050-c8-seed1-s14000
c79-rgbskip-s050-c8-seed2-s14000
c79-rgbskip-s050-c8-seed4-s14000
c79-rgbskip-s100-c8-seed2-s14000
c79-rgbskip-s100-c8-seed5-s14000
c79-rgbskip-s050-nocontext-seed1-s14000
c79-rgbskip-s050-nocontext-seed2-s14000
```

C79 hypothesis:

- A learned RGB neural texture initialized from the page can carry high-frequency strokes as model parameters, while the MLP learns bounded corrections for layout reflow.
- Source-mode RGB sampling should behave like neural texture transport rather than an overlay: the output is still produced through the neural renderer and evaluated under reflow/resize.
- If text blur is caused by reconstructing glyphs from a compressed latent feature grid, C79 should improve OCR without needing rectangular masks, OCR replacement, or a DOM/layout layer.

Completed C79 results:

```text
c79-rgbskip-s100-c8-seed2-s14000: OCR 0.4952, segment 990.376ms, motion_delta 0.0228, quality_fail
c79-rgbskip-s050-c8-seed2-s14000: OCR 0.3495, segment 984.223ms, motion_delta 0.0126, quality_fail
c79-rgbskip-s050-c8-seed4-s14000: OCR 0.3396, segment 962.059ms, motion_delta 0.0132, quality_fail
c79-rgbskip-s050-nocontext-seed2-s14000: OCR 0.3188, segment 908.605ms, motion_delta 0.0122, quality_fail
c79-rgbskip-s050-c8-seed1-s14000: OCR 0.2949, segment 970.575ms, motion_delta 0.0134, quality_fail
c79-rgbskip-s050-nocontext-seed1-s14000: OCR 0.2574, segment 1110.597ms, motion_delta 0.0125, quality_fail
c79-rgbskip-s025-c8-seed4-s14000: OCR 0.1905, segment 972.520ms, motion_delta 0.0000, quality_fail
c79-rgbskip-s025-c8-seed1-s14000: OCR 0.1281, segment 978.889ms, motion_delta 0.0068, quality_fail
c79-rgbskip-s025-c8-seed2-s14000: OCR 0.0421, segment 1020.991ms, motion_delta 0.0000, quality_fail
c79-rgbskip-s100-c8-seed5-s14000: OCR 0.0247, segment 951.048ms, motion_delta 0.0029, quality_fail
```

Interpretation:

- C79 is a negative result but it is informative: the source RGB neural texture became too rigid. It preserved/corrupted source detail instead of cleanly reflowing it.
- The best OCR run uses the largest residual scale and still misses both OCR and motion gates. That says the issue is not speed; it is inability to erase/repaint around the transported texture.
- Visual review of the best run shows ghosting and red/cyan smear around text/diagram lines, consistent with source texture dominance.

Next experiments:

```text
c80-rgbbase025-res100-c8-seed2-s14000
c80-rgbbase025-res200-c8-seed2-s14000
c80-rgbbase025-res400-c8-seed2-s14000
c80-rgbbase050-res200-c8-seed2-s14000
c80-rgbbase050-res400-c8-seed2-s14000
c80-rgbbase075-res200-c8-seed2-s14000
c80-rgbbase025-res200-c8-seed4-s14000
c80-rgbbase050-res400-c8-seed4-s14000
c80-rgbbase050-res400-c8-seed1-s14000
c80-rgbbase025-res200-nocontext-seed2-s14000
```

C80 hypothesis:

- The RGB texture can still be useful if it is a detail prior rather than an uneraseable source copy.
- Attenuating base logits (`0.25-0.75`) and increasing bounded residual scale (`1-4`) should let the renderer erase/repaint while keeping a spatial hint for strokes.
- If C80 remains below C75/C62, the project should stop pursuing direct RGB skips and return to structured transport/decoder architectures.

Completed C80 results:

```text
c80-rgbbase025-res200-nocontext-seed2-s14000: OCR 0.5967, segment 757.305ms, motion_delta 0.0416, quality_fail
c80-rgbbase050-res400-c8-seed1-s14000: OCR 0.5357, segment 801.038ms, motion_delta 0.0484, quality_fail
c80-rgbbase050-res400-c8-seed2-s14000: OCR 0.5000, segment 970.779ms, motion_delta 0.0484, quality_fail
c80-rgbbase025-res200-c8-seed2-s14000: OCR 0.4941, segment 806.203ms, motion_delta 0.0375, quality_fail
c80-rgbbase050-res400-c8-seed4-s14000: OCR 0.4906, segment 975.696ms, motion_delta 0.0505, quality_fail
c80-rgbbase025-res200-c8-seed4-s14000: OCR 0.4654, segment 979.569ms, motion_delta 0.0374, quality_fail
c80-rgbbase025-res100-c8-seed2-s14000: OCR 0.4476, segment 1016.571ms, motion_delta 0.0235, quality_fail
c80-rgbbase025-res400-c8-seed2-s14000: OCR 0.4304, segment 964.514ms, motion_delta 0.0484, quality_fail
c80-rgbbase050-res200-c8-seed2-s14000: OCR 0.3926, segment 969.812ms, motion_delta 0.0435, quality_fail
c80-rgbbase075-res200-c8-seed2-s14000: OCR 0.0357, segment 949.416ms, motion_delta 0.0000, quality_fail
```

Interpretation:

- C80 rescues the RGB texture idea from the C79 failure mode. Base attenuation plus more residual capacity raises the best OCR from `0.4952` to `0.5967`.
- The best run is a near-miss on motion, not quality or latency. That is materially different from C79's frozen/ghosted behavior.
- Context hurts this branch: no-context base `0.25` / residual `2.0` beats the c8-context equivalent by about `0.10` OCR. Coarse context may be fighting the RGB texture transport.

Next experiments:

```text
c81-nctx-b025-r200-a110-seed2-s14000
c81-nctx-b025-r250-a100-seed2-s14000
c81-nctx-b025-r250-a110-seed2-s14000
c81-nctx-b025-r300-a100-seed2-s14000
c81-nctx-b020-r250-a100-seed2-s14000
c81-nctx-b030-r250-a100-seed2-s14000
c81-nctx-b025-r250-a100-seed1-s14000
c81-nctx-b025-r250-a100-seed4-s14000
c81-nctx-b025-r250-a110-seed4-s14000
c81-nctx-b050-r400-a100-seed2-s14000
```

C81 hypothesis:

- The best C80 point needs a small motion push, not a new mechanism.
- No-context RGB texture runs should be tested around the base `0.25` / residual `2.0` basin with residual `2.5-3.0`, base `0.20-0.30`, and layout amount `1.10`.
- If the near-miss does not turn into a pass across seeds, RGB texture should be treated as a diagnostic branch rather than the main architecture path.

Completed C81 results:

```text
c81-nctx-b025-r250-a110-seed2-s14000: OCR 0.5556, segment 963.710ms, motion_delta 0.0460, pass
c81-nctx-b025-r200-a110-seed2-s14000: OCR 0.5870, segment 902.571ms, motion_delta 0.0418, quality_fail
c81-nctx-b025-r300-a100-seed2-s14000: OCR 0.5780, segment 930.290ms, motion_delta 0.0441, quality_fail
c81-nctx-b025-r250-a100-seed4-s14000: OCR 0.5647, segment 923.077ms, motion_delta 0.0412, quality_fail
c81-nctx-b025-r250-a110-seed4-s14000: OCR 0.5444, segment 911.905ms, motion_delta 0.0451, quality_fail
c81-nctx-b025-r250-a100-seed1-s14000: OCR 0.5083, segment 919.523ms, motion_delta 0.0426, quality_fail
c81-nctx-b020-r250-a100-seed2-s14000: OCR 0.5031, segment 928.246ms, motion_delta 0.0422, quality_fail
c81-nctx-b050-r400-a100-seed2-s14000: OCR 0.4750, segment 923.858ms, motion_delta 0.0477, quality_fail
c81-nctx-b030-r250-a100-seed2-s14000: OCR 0.4684, segment 940.731ms, motion_delta 0.0440, quality_fail
c81-nctx-b025-r250-a100-seed2-s14000: OCR 0.3834, segment 922.591ms, motion_delta 0.0416, quality_fail
```

Interpretation:

- C81 gives the first pass for the attenuated RGB neural-texture branch. The winning recipe is no-context, base `0.25`, residual `2.5`, amount `1.10`, seed2.
- The pass is narrow. Several neighbors are one gate away: residual `2.0` at amount `1.10` has higher OCR but too little motion; residual `3.0` at amount `1.0` is also close on motion.
- Human review shows visible ghosting remains. This branch is viable but not mature.

Next experiments:

```text
c82-nctx-b025-r250-a110-seed0-s14000
c82-nctx-b025-r250-a110-seed1-s14000
c82-nctx-b025-r250-a110-seed3-s14000
c82-nctx-b025-r250-a110-seed5-s14000
c82-nctx-b025-r200-a120-seed2-s14000
c82-nctx-b025-r225-a115-seed2-s14000
c82-nctx-b025-r300-a105-seed2-s14000
c82-nctx-b025-r300-a110-seed2-s14000
c82-nctx-b025-r225-a115-seed4-s14000
c82-nctx-b025-r275-a110-seed4-s14000
```

C82 hypothesis:

- If the C81 pass is a real basin, the base `0.25` / residual `2.5` / amount `1.10` recipe should repeat on at least one additional seed.
- The high-OCR/low-motion neighbors may become stronger passes by nudging amount upward (`r2.0/a1.20`, `r2.25/a1.15`, `r3.0/a1.05-1.10`).
- If C82 only reproduces seed2, the branch is still seed-sensitive and should be combined with a separate stabilization mechanism rather than promoted directly.

Completed C82 results:

```text
c82-nctx-b025-r275-a110-seed4-s14000: OCR 0.7087, segment 923.432ms, motion_delta 0.0457, pass
c82-nctx-b025-r250-a110-seed1-s14000: OCR 0.6702, segment 1116.819ms, motion_delta 0.0462, pass
c82-nctx-b025-r250-a110-seed0-s14000: OCR 0.6635, segment 1101.598ms, motion_delta 0.0473, pass
c82-nctx-b025-r300-a110-seed2-s14000: OCR 0.6073, segment 914.467ms, motion_delta 0.0470, pass
c82-nctx-b025-r250-a110-seed5-s14000: OCR 0.5780, segment 912.392ms, motion_delta 0.0465, pass
c82-nctx-b025-r250-a110-seed3-s14000: OCR 0.5161, segment 990.854ms, motion_delta 0.0464, quality_fail
c82-nctx-b025-r225-a115-seed4-s14000: OCR 0.4790, segment 942.244ms, motion_delta 0.0418, quality_fail
c82-nctx-b025-r225-a115-seed2-s14000: OCR 0.4359, segment 935.617ms, motion_delta 0.0441, quality_fail
c82-nctx-b025-r300-a105-seed2-s14000: OCR 0.4304, segment 960.797ms, motion_delta 0.0491, quality_fail
c82-nctx-b025-r200-a120-seed2-s14000: OCR 0.3846, segment 930.194ms, motion_delta 0.0403, quality_fail
```

Interpretation:

- C82 validates the basin. The C81 pass is not a one-seed accident: four additional same-recipe seeds pass, and one adjacent residual setting reaches OCR `0.7087`.
- The current best learned layout-reflow recipe is no-context, RGB base scale `0.25`, residual scale `2.5-2.75`, amount `1.10`, source-coordinate features, cross latent neighborhood, and target-side sampling.
- The remaining visual issue is ghosting/source remnants, not speed. The branch is now worth refining.

Next experiments:

```text
c83-nctx-b025-r275-a110-seed0-s14000
c83-nctx-b025-r275-a110-seed1-s14000
c83-nctx-b025-r275-a110-seed2-s14000
c83-nctx-b025-r275-a110-seed3-s14000
c83-nctx-b025-r275-a110-seed5-s14000
c83-nctx-b020-r275-a110-seed4-s14000
c83-nctx-b030-r275-a110-seed4-s14000
c83-nctx-b025-r325-a110-seed4-s14000
c83-nctx-b025-r275-a100-seed4-s14000
c83-nctx-b025-r275-a115-seed4-s14000
```

C83 hypothesis:

- Residual `2.75` may be the cleaner point between the OCR/motion tradeoff, so it should be seed-mapped like the C82 residual `2.5` recipe.
- Base `0.20` may reduce ghosting, while base `0.30` may preserve text; the seed4 best gives a useful bracket.
- Amount `1.00/1.15` around the seed4 winner tests whether motion can be reduced/increased without creating more source remnants.

Completed C83 results:

```text
c83-nctx-b025-r275-a110-seed5-s14000: OCR 0.6458, segment 915.505ms, motion_delta 0.0472, pass
c83-nctx-b025-r325-a110-seed4-s14000: OCR 0.6269, segment 926.264ms, motion_delta 0.0502, pass
c83-nctx-b030-r275-a110-seed4-s14000: OCR 0.5930, segment 769.325ms, motion_delta 0.0474, pass
c83-nctx-b025-r275-a110-seed3-s14000: OCR 0.5525, segment 756.287ms, motion_delta 0.0453, pass
c83-nctx-b025-r275-a110-seed1-s14000: OCR 0.5349, segment 766.226ms, motion_delta 0.0471, quality_fail
c83-nctx-b020-r275-a110-seed4-s14000: OCR 0.5263, segment 922.511ms, motion_delta 0.0473, quality_fail
c83-nctx-b025-r275-a110-seed0-s14000: OCR 0.4970, segment 793.527ms, motion_delta 0.0453, quality_fail
c83-nctx-b025-r275-a100-seed4-s14000: OCR 0.4654, segment 946.530ms, motion_delta 0.0435, quality_fail
c83-nctx-b025-r275-a115-seed4-s14000: OCR 0.4359, segment 916.550ms, motion_delta 0.0475, quality_fail
c83-nctx-b025-r275-a110-seed2-s14000: OCR 0.3875, segment 1182.094ms, motion_delta 0.0493, quality_fail
```

Interpretation:

- C83 confirms the branch is real, but residual `2.75` is not a monotonic improvement over C82. The best C82 run remains the peak at OCR `0.7087`.
- Base `0.30` helps seed4 pass, while base `0.20` misses quality. Stronger residual `3.25` also passes on seed4.
- Visual review still shows source ghosts. The next model change should modulate where the RGB texture is trusted rather than only changing scalar base/residual strength.

Next experiments:

```text
c84-gateedge-b025-r275-a110-seed0-s14000
c84-gateedge-b025-r275-a110-seed1-s14000
c84-gateedge-b025-r275-a110-seed4-s14000
c84-gateedge-b025-r275-a110-seed5-s14000
c84-gateedge-b025-r325-a110-seed4-s14000
c84-gateedge-b030-r275-a110-seed4-s14000
c84-gatelearn035-b025-r275-a110-seed4-s14000
c84-gatelearn050-b025-r275-a110-seed4-s14000
c84-gatelearn035-b025-r325-a110-seed4-s14000
c84-gateedge-b020-r275-a110-seed4-s14000
```

C84 hypothesis:

- A learned gate canvas can reduce background/source ghosting by letting the model suppress the RGB texture outside useful stroke/detail regions.
- Edge-initialized gates should preserve high-frequency text/diagram strokes while fading low-detail page areas.
- Constant learned gates test whether the benefit is the gate capacity itself or specifically the edge initialization.

Completed C84 results:

```text
c84-gatelearn035-b025-r275-a110-seed4-s14000: OCR 0.6863, segment 927.308ms, motion_delta 0.0469, pass
c84-gateedge-b025-r275-a110-seed0-s14000: OCR 0.5746, segment 963.276ms, motion_delta 0.0456, pass
c84-gatelearn050-b025-r275-a110-seed4-s14000: OCR 0.5521, segment 916.584ms, motion_delta 0.0460, pass
c84-gatelearn035-b025-r325-a110-seed4-s14000: OCR 0.5380, segment 773.360ms, motion_delta 0.0463, quality_fail
c84-gateedge-b025-r275-a110-seed4-s14000: OCR 0.5269, segment 938.992ms, motion_delta 0.0435, quality_fail
c84-gateedge-b020-r275-a110-seed4-s14000: OCR 0.5202, segment 937.987ms, motion_delta 0.0438, quality_fail
c84-gateedge-b025-r325-a110-seed4-s14000: OCR 0.5176, segment 1062.213ms, motion_delta 0.0470, quality_fail
c84-gateedge-b025-r275-a110-seed5-s14000: OCR 0.4651, segment 1073.714ms, motion_delta 0.0431, quality_fail
c84-gateedge-b030-r275-a110-seed4-s14000: OCR 0.4625, segment 783.168ms, motion_delta 0.0432, quality_fail
c84-gateedge-b025-r275-a110-seed1-s14000: OCR 0.4528, segment 943.584ms, motion_delta 0.0431, quality_fail
```

Interpretation:

- The constant learned gate is the useful branch. Init `0.35` gets close to the C82 peak while staying under `1s`, but does not beat C82's OCR `0.7087`.
- Edge initialization mostly hurts. It may over-trust source edges and reinforce old-layout traces instead of suppressing them.
- Human review of C82/C84 midpoint frames shows the remaining failure is not just token readability. The model still leaves visible source-layout remnants, and the synthetic target itself is tolerant of transition traces.
- This is still aligned with Flipbook only as a model-owned pixel prior. It is not an overlay, but the repo should not mistake it for the final architecture.

Next experiments:

```text
c85-gatelearn025-b025-r275-a110-seed4-s14000
c85-gatelearn030-b025-r275-a110-seed4-s14000
c85-gatelearn040-b025-r275-a110-seed4-s14000
c85-gatelearn045-b025-r275-a110-seed4-s14000
c85-gatelearn035-b025-r275-a110-seed0-s14000
c85-gatelearn035-b025-r275-a110-seed1-s14000
c85-gatelearn035-b025-r275-a110-seed2-s14000
c85-gatelearn035-b025-r275-a110-seed3-s14000
c85-gatelearn035-b025-r275-a110-seed5-s14000
c85-gatelearn035-b025-r300-a110-seed4-s14000
```

C85 hypothesis:

- If learned constant gating is real, init `0.35` should reproduce on at least two of the C85 seed repeats.
- Lower gate init (`0.25-0.30`) may reduce source remnants at the cost of OCR; higher init (`0.40-0.45`) may preserve text but increase ghosting.
- A post-hoc change-region/source-remnant proxy should be tracked alongside OCR so the loop does not optimize toward readable but visually stale frames.

Completed C85 results:

```text
c85-gatelearn030-b025-r275-a110-seed4-s14000: OCR 0.5714, segment 1079.571ms, motion_delta 0.0444, quality_fail
c85-gatelearn045-b025-r275-a110-seed4-s14000: OCR 0.5497, segment 925.386ms, motion_delta 0.0455, quality_fail
c85-gatelearn035-b025-r300-a110-seed4-s14000: OCR 0.5434, segment 929.031ms, motion_delta 0.0436, quality_fail
c85-gatelearn035-b025-r275-a110-seed1-s14000: OCR 0.5294, segment 1101.215ms, motion_delta 0.0455, quality_fail
c85-gatelearn035-b025-r275-a110-seed2-s14000: OCR 0.5275, segment 937.884ms, motion_delta 0.0462, quality_fail
c85-gatelearn035-b025-r275-a110-seed3-s14000: OCR 0.5233, segment 944.503ms, motion_delta 0.0462, quality_fail
c85-gatelearn040-b025-r275-a110-seed4-s14000: OCR 0.5029, segment 932.207ms, motion_delta 0.0460, quality_fail
c85-gatelearn035-b025-r275-a110-seed0-s14000: OCR 0.4970, segment 931.150ms, motion_delta 0.0435, quality_fail
c85-gatelearn025-b025-r275-a110-seed4-s14000: OCR 0.4780, segment 919.638ms, motion_delta 0.0423, quality_fail
c85-gatelearn035-b025-r275-a110-seed5-s14000: OCR 0.4780, segment 767.399ms, motion_delta 0.0449, quality_fail
```

Interpretation:

- C85 is a stop sign for learned gate scalar tuning. It does not beat C82/C84 and does not visibly remove source remnants.
- The new change-region proxy is useful but not sufficient; the next benchmark must use a cleaner target state so OCR cannot hide old-layout ghosts.
- The 2026-04-25 Flipbook re-check reinforces this: the target is model-rendered page pixels, including text, not protected text boxes or runtime overlays.

Next experiments:

```text
c86-clean-c32h160-target60-mid20-seed0-s12000
c86-clean-c32h160-target60-mid20-seed1-s12000
c86-clean-c32h160-target60-mid20-seed2-s12000
c86-clean-c32h160-target60-mid20-seed4-s12000
c86-clean-c32h160-target80-mid20-seed0-s12000
c86-clean-c32h160-target60-mid35-seed0-s12000
c86-clean-c24h128-target60-mid20-seed0-s12000
c86-clean-c40h192-target60-mid20-seed0-s12000
c86-clean-c32h160-context8-target60-mid20-seed0-s12000
c86-clean-c32h160-dualres-target60-mid20-seed0-s12000
```

C86 hypothesis:

- If the Track C path is viable, at least one compact renderer should learn `source -> clean target page -> source` without using a warped target image as a crutch.
- OCR should now be scored against the clean target midpoint, while human review should focus on whether source-page ghosts disappear.
- Capacity/context variants matter less than the qualitative question: can the model paint a different page state cleanly and still stay near the 33-frame realtime budget?

Completed C86 results:

```text
c86-clean-c32h160-target60-mid20-seed1-s12000: OCR 0.7527, segment 752.003ms, motion_delta 0.0600, pass
c86-clean-c40h192-target60-mid20-seed0-s12000: OCR 0.7391, segment 1218.898ms, motion_delta 0.0609, pass
c86-clean-c32h160-target60-mid20-seed4-s12000: OCR 0.7368, segment 1112.650ms, motion_delta 0.0606, pass
c86-clean-c32h160-target60-mid35-seed0-s12000: OCR 0.7347, segment 942.174ms, motion_delta 0.0606, pass
c86-clean-c32h160-target60-mid20-seed0-s12000: OCR 0.7216, segment 925.425ms, motion_delta 0.0608, pass
c86-clean-c32h160-dualres-target60-mid20-seed0-s12000: OCR 0.6742, segment 1318.826ms, motion_delta 0.0606, latency_fail
c86-clean-c32h160-target60-mid20-seed2-s12000: OCR 0.6735, segment 787.858ms, motion_delta 0.0602, pass
c86-clean-c32h160-target80-mid20-seed0-s12000: OCR 0.4808, segment 921.003ms, motion_delta 0.0609, pass
c86-clean-c24h128-target60-mid20-seed0-s12000: OCR 0.3548, segment 824.892ms, motion_delta 0.0594, pass
c86-clean-c32h160-context8-target60-mid20-seed0-s12000: OCR 0.3492, segment 813.604ms, motion_delta 0.0592, quality_fail
```

Interpretation:

- C86 is a major positive. The no-context C32/H160 recipe passes on seeds `0,1,2,4`, with OCR `0.6735-0.7527`; the best high-quality segment is `752.003ms`, well under the `1.3s` realtime target.
- Human review of the best strip (`c86-review-strip.jpg`) shows the midpoint closely matches the clean target page. This looks like a new page state, not the old source layout stretched into a new position.
- Context and dual-residual decoding are not needed here; context hurts quality and dual-residual misses latency.
- The caveat: the target is still a deterministic second fixture. The next proof should vary target layout/content so the loop does not overfit to this one clean page.

Next experiments:

```text
c87-v1-c32h160-target60-mid20-seed0-s12000
c87-v1-c32h160-target60-mid20-seed1-s12000
c87-v1-c32h160-target60-mid20-seed2-s12000
c87-v1-c32h160-target60-mid20-seed4-s12000
c87-v2-c32h160-target60-mid20-seed0-s12000
c87-v2-c32h160-target60-mid20-seed1-s12000
c87-v2-c32h160-target60-mid20-seed2-s12000
c87-v2-c32h160-target60-mid20-seed4-s12000
c87-v1-c32h160-target60-mid35-seed0-s12000
c87-v2-c32h160-target60-mid35-seed0-s12000
```

C87 hypothesis:

- If C86 is not just target-fixture overfit, the same C32/H160 recipe should pass on both `right-diagram` and `stacked` clean target variants.
- Failure on one variant would point to target distribution sensitivity rather than renderer speed/capacity.
- Passing both variants would justify moving from single-pair neural canvas to multi-state or generated-target tests.

Completed C87 results:

```text
c87-v2-c32h160-target60-mid20-seed1-s12000: OCR 1.0000, segment 941.761ms, motion_delta 0.0619, pass
c87-v2-c32h160-target60-mid20-seed4-s12000: OCR 1.0000, segment 925.172ms, motion_delta 0.0620, pass
c87-v2-c32h160-target60-mid20-seed0-s12000: OCR 0.9565, segment 923.025ms, motion_delta 0.0622, pass
c87-v1-c32h160-target60-mid20-seed0-s12000: OCR 0.9000, segment 920.211ms, motion_delta 0.0598, pass
c87-v2-c32h160-target60-mid20-seed2-s12000: OCR 0.8800, segment 1130.668ms, motion_delta 0.0620, pass
c87-v2-c32h160-target60-mid35-seed0-s12000: OCR 0.8800, segment 756.538ms, motion_delta 0.0632, pass
c87-v1-c32h160-target60-mid20-seed4-s12000: OCR 0.8372, segment 927.614ms, motion_delta 0.0602, pass
c87-v1-c32h160-target60-mid35-seed0-s12000: OCR 0.8095, segment 923.887ms, motion_delta 0.0604, pass
c87-v1-c32h160-target60-mid20-seed2-s12000: OCR 0.7907, segment 916.258ms, motion_delta 0.0614, pass
c87-v1-c32h160-target60-mid20-seed1-s12000: OCR 0.7442, segment 764.879ms, motion_delta 0.0602, pass
```

Interpretation:

- C87 strongly validates that C86 was not only fitting one clean target page. The same compact no-context C32/H160 recipe passes on both `right-diagram` and `stacked`.
- The best `stacked` runs hit perfect token OCR under the normalized eval, and both variants stay comfortably under the `1.3s` 33-frame plus encode target.
- Human review is mostly positive: the midpoint visibly becomes the new target page. The remaining concern is faint source-remnant text in some large diagram bands, especially on stacked layouts.
- C88 should make the target harder by removing neat card boxes and using floating callout text. If that passes, the next proof should move toward multi-state or generated-target tests.

Next experiments:

```text
c88-v3-unboxed-target60-mid20-seed0-s12000
c88-v3-unboxed-target60-mid20-seed1-s12000
c88-v3-unboxed-target60-mid20-seed2-s12000
c88-v3-unboxed-target60-mid20-seed4-s12000
c88-v4-callout-target60-mid20-seed0-s12000
c88-v4-callout-target60-mid20-seed1-s12000
c88-v4-callout-target60-mid20-seed2-s12000
c88-v4-callout-target60-mid20-seed4-s12000
c88-v3-unboxed-target60-mid35-seed0-s12000
c88-v4-callout-target60-mid35-seed0-s12000
```

Completed C88 results:

```text
c88-v3-unboxed-target60-mid20-seed1-s12000: OCR 0.9302, segment 927.622ms, motion_delta 0.0641, pass
c88-v3-unboxed-target60-mid20-seed0-s12000: OCR 0.9091, segment 765.567ms, motion_delta 0.0637, pass
c88-v3-unboxed-target60-mid20-seed2-s12000: OCR 0.9091, segment 921.649ms, motion_delta 0.0640, pass
c88-v3-unboxed-target60-mid20-seed4-s12000: OCR 0.9091, segment 920.433ms, motion_delta 0.0639, pass
c88-v3-unboxed-target60-mid35-seed0-s12000: OCR 0.8889, segment 942.074ms, motion_delta 0.0645, pass
c88-v4-callout-target60-mid35-seed0-s12000: OCR 0.7826, segment 772.390ms, motion_delta 0.0557, pass
c88-v4-callout-target60-mid20-seed0-s12000: OCR 0.7347, segment 914.757ms, motion_delta 0.0561, pass
c88-v4-callout-target60-mid20-seed2-s12000: OCR 0.7083, segment 907.009ms, motion_delta 0.0565, pass
c88-v4-callout-target60-mid20-seed1-s12000: OCR 0.6939, segment 919.974ms, motion_delta 0.0566, pass
c88-v4-callout-target60-mid20-seed4-s12000: OCR 0.6939, segment 902.172ms, motion_delta 0.0562, pass
```

Interpretation:

- C88 is another strong positive: removing neat card boxes did not break the clean page-state renderer.
- `unboxed-columns` is visually the strongest target so far. The midpoint keeps open text columns readable and does not depend on card-shaped text containers.
- `callout-map` is a useful harder case. It passes quantitatively, but human review shows smaller text and leader-line areas remain weaker and show faint source remnants.
- The next stress should change the target wording, not just the layout. A Flipbook-like renderer must be able to repaint new visible text pixels, not only move the same semantic copy.

Next experiments:

```text
c89-v5-changed-unboxed-target60-mid20-seed0-s12000
c89-v5-changed-unboxed-target60-mid20-seed1-s12000
c89-v5-changed-unboxed-target60-mid20-seed2-s12000
c89-v5-changed-unboxed-target60-mid20-seed4-s12000
c89-v6-changed-callout-target60-mid20-seed0-s12000
c89-v6-changed-callout-target60-mid20-seed1-s12000
c89-v6-changed-callout-target60-mid20-seed2-s12000
c89-v6-changed-callout-target60-mid20-seed4-s12000
c89-v5-changed-unboxed-target60-mid35-seed0-s12000
c89-v6-changed-callout-target60-mid35-seed0-s12000
```

Completed C89 visual review:

```text
c89-v6-changed-callout-target60-mid20-seed0-s12000: OCR 0.9259, segment 1057.956ms, pass
c89-v6-changed-callout-target60-mid20-seed2-s12000: OCR 0.8846, segment 1196.854ms, pass
c89-v6-changed-callout-target60-mid35-seed0-s12000: OCR 0.7407, segment 743.559ms, pass
c89-v5-changed-unboxed-target60-mid20-seed4-s12000: OCR 0.6111, segment 756.906ms, pass
```

Human read:

- Best `changed-callout` is a strong positive. It visibly repaints the changed headings and body copy as part of the generated page, not as an overlay.
- Best `changed-unboxed` is visually more readable than the OCR number suggests; dense small text likely hurts token-F1.
- The old-source ghost problem remains visible as faint left-side remnants in open whitespace. It is subtle, but it matters because Flipbook's claim is a clean generated page surface.
- C90 should therefore be treated as a hard generalization test: changed illustration structure plus changed text. Passing C90 would be stronger evidence than further text/layout variants around the same oval diagram.

Completed C90 visual review:

```text
c90-v7-timeline-illustration-target60-mid20-seed0-s12000: OCR 0.9091, segment 929.222ms, pass
c90-v7-timeline-illustration-target60-mid35-seed0-s12000: OCR 0.8421, segment 741.483ms, pass
c90-v8-transit-illustration-target60-mid20-seed0-s12000: OCR 0.7805, segment 912.081ms, pass
c90-v8-transit-illustration-target60-mid20-seed1-s12000: OCR 0.7368, segment 922.412ms, pass
```

Human read:

- C90 is a real generality jump. The model redraws timeline bars, year markers, route lines, map grid, route labels, and new section text.
- The best timeline render looks close to the target and no longer resembles the old oval diagram.
- The best transit render preserves the route-map geometry, including crossing colored routes and the small arena label.
- Faint old-source haze is still visible near the far right edge/open whitespace. This is not blocking, but it remains the clearest quality gap.
- C91 should change topic entirely, not only the representation style, to test whether this is becoming a page-state renderer rather than a Colosseum-specific renderer.

Completed C91 visual review:

```text
c91-v10-orbit-topic-target60-mid20-seed0-s12000: OCR 1.0000, segment 904.111ms, pass
c91-v10-orbit-topic-target60-mid20-seed1-s12000: OCR 0.9286, segment 906.867ms, pass
c91-v10-orbit-topic-target60-mid35-seed0-s12000: OCR 0.9333, segment 967.322ms, pass
c91-v9-reef-topic-target60-mid35-seed0-s12000: OCR 0.8485, segment 950.039ms, pass
```

Human read:

- C91 is a useful anti-overfit signal: the target can become a reef page or orbit page with new title, new body copy, and new diagram vocabulary.
- Orbit is visually cleaner than reef and reads very well by OCR.
- Crop inspection still shows faint source-page haze in open regions, especially where the new target has pale backgrounds or sparse diagram detail.
- C92 should deliberately use an illustration style and palette that expose source remnants: an 1800s naturalist-style etched plate for thin-line art, plus a dark scientific page where old paper/text leakage is immediately obvious.
