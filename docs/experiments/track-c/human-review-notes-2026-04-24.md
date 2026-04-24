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
