# Track C Experiment Logs

Track C experiments measure neural canvas rendering: compile once, then render pixels for multiple viewports, resolutions, and times.

Use compact TSV summaries here and keep generated images/videos under `outputs/track-c/`.

Track C is intentionally a one-page overfit renderer lab. It answers whether the neural canvas renderer can preserve identity and run fast after compile. Generalization moves to Track D: `docs/research/track-d-general-neural-canvas.md`.

Current reference results:

```text
Local-motion winner:
  run:     20260424T193446279047Z-c2-lite-glyph-c33-general-flow-014-edge1-1280x736-s4500
  segment: 565.333ms
  OCR F1:  0.8767
  motion:  0.0371
  status:  pass

Resize/reposition stress:
  run:     20260424T203639915770Z-c2-lite-glyph-static-layout-frame-scale-c43-frame-scale-014-edge09-freq10-train1536-clip05-1536x864-s5500
  segment: 566.234ms
  OCR F1:  0.7281
  motion:  0.0592
  status:  pass
```

The glyph-weighted sampler/loss preserved speed but did not beat the previous unweighted C2-lite OCR score of `0.8326`. The OCR-box-weighted C2.1 run did improve the OCR score to `0.8545`.

C2.2 frame-scale stress shows that jiggle is not enough as a benchmark. Moderate frame scaling and viewport zoom keep latency under budget but collapse text quality to `0.1053`; strong scaling collapses OCR to `0.0000`.

C2.3 layout-transform rendering recovers much of that quality by keeping content stable and applying frame sizing as a query transform: moderate stress rises to `0.7091`, strong stress rises to `0.3610`.

C2.4 adds OCR line anchors. It improves moderate resize OCR from `0.7091` to `0.7321` and strong resize OCR from `0.3610` to `0.4124`, with extra render cost from sequential patch queries.

C2.5 starts replacing rectangular text-line patch replacement with glyph-shaped `text-alpha` masks. The RGB still comes from neural canvas queries; the mask is a selection signal so illustrations caught in a line box are less likely to move with the text.

C2.6-C2.8 show that text-alpha masks are too sparse, while line rectangles with a low element scale ratio are the best strong-stress path so far. The strongest quantitative result is `c27-line-rect-r0025` at OCR `0.7097` and segment `841.603ms`; batching keeps line anchors fast but needs exact ratio checks because `c28-line-batched-r005` landed lower at OCR `0.4928`.

C2.9 adds the human note that less aggressive motion can look good with text. The measured boundary matches that: `c29-gentle-flow-010` passes at OCR `0.8402` with motion `0.0297`, while `c29-gentle-flow-020` drops to OCR `0.7123`. The best pleasant-layout run, `c29-product-layout-r0025`, passes at OCR `0.7713` and segment `627.449ms`.

C3.0 tightens the pleasant-motion boundary. `c30-gentle-flow-0125` keeps OCR at `0.8545`, reaches motion `0.0353`, and finishes the 33-frame segment in `525.153ms`; `c30-gentle-flow-015` drops to OCR `0.7615`. The current text-friendly learned-flow boundary is therefore between `0.0125` and `0.015`.

The C3.0 batched strong-control result, `c30-line-batched-r0025-strong`, is fast at `627.692ms` for render plus encode, but OCR drops to `0.4976`. The best strong-stress quality is still the earlier sequential `c27-line-rect-r0025` result at OCR `0.7097`; batching needs a quality-preserving implementation before it can replace the sequential anchor path.

C3.1 pivots toward the more general path while keeping the bridge path alive. The general runs use learned-flow neural canvas rendering without OCR boxes, line anchors, word anchors, or rectangular text replacement. The text-aware bridge runs keep OCR boxes as a training signal only, not a render-time mask. A lower-stress alpha-layout run tests whether glyph-shaped selection can help without assuming clean rectangular text regions.

Early C3.1 results support testing both tracks. The best no-OCR run so far, `c31-general-flow-0125-edge1`, reaches OCR `0.8219` and segment `521.440ms`; heavier edge weighting gets worse. The best bridge run so far, `c31-text-flow-0135-box8`, reaches OCR `0.8440`, motion `0.0384`, and segment `546.841ms` while still avoiding render-time masks.

C3.2 makes the pure no-OCR path the leading candidate: `c32-general-flow-0135-edge1` reaches OCR `0.8519`, segment `560.209ms`, and motion `0.0358` without OCR boxes, masks, or anchors. C3.3 scales Modal concurrency to `10` by default and launches a wider pure neural-canvas wave across flow, edge weighting, model capacity, optimization steps, and one responsive-squeeze stress case.

C3.3 found a new pure no-OCR local-motion winner: `c33-general-flow-014-edge1` reaches OCR `0.8767`, segment `565.333ms`, and motion `0.0371`. That is strong but too wiggle-specific. C3.5 pivots the next wave toward aggressive viewport zoom/pan, global frame-scale resize, and responsive squeeze tests so the renderer has to preserve text through query movement and resizing, not just local sinusoidal motion.

C3.5 shows viewport movement is less fragile than resize: all three zoom/pan runs pass with OCR `0.8624-0.8727`, and combined responsive+zoom passes around OCR `0.86`. Frame-scale resize is the active cliff: OCR falls from `0.7558` at strength `0.08` to `0.5806-0.6636` at `0.12`, then `0.4039` at `0.16`.

C3.6 confirms that this is not just a wiggle benchmark. Query-space/global frame-scale rendering remains fast and degrades gradually: the best C36 resize bracket is `c36-frame-scale-014-edge09` at OCR `0.5634`, segment `547.378ms`, and motion `0.0592`. Stronger `0.16` resize improves from OCR `0.2657` to `0.4607` with `6000` steps, which suggests optimization helps but does not solve the cliff. Learned frame-scale motion collapses text directly (`0.1215` and `0.0513` OCR), so the next work should not rely on a generic motion field learning nonlocal resize on its own.

C3.7 narrows the resize/reposition boundary. The best result is `c37-frame-scale-0125-edge09` at OCR `0.6573`, segment `560.983ms`, and motion `0.0574`. More steps rescue the `0.14` bracket somewhat (`0.5860`), but the pan/no-pan results are unstable enough to treat the current renderer as optimization-sensitive. The good news is that this is no longer a wiggle result: it is a resize/reposition stress result running faster than realtime.

C3.8 moves from parameter bracketing to model/render diagnosis. The best fast result is `c38-frame-scale-0125-edge09-freq10` at OCR `0.6912`, segment `562.129ms`, and motion `0.0562`, making higher coordinate frequency the best pure neural-canvas resize improvement so far. Larger capacity at the same bracket is close (`0.6852`) but slower. `2x` neural supersampling helps the `0.14` bracket reach OCR `0.6820`, but it misses the realtime budget at `1456.618ms`; `1.5x` supersampling is not enough.

C3.9 combines the winning signals. The best result is now `c39-frame-scale-0125-edge09-freq10-train1536` at OCR `0.7000`, segment `571.260ms`, and motion `0.0562`. More importantly, the harder `0.14` bracket reaches OCR `0.6667` at segment `560.830ms` with `freq10 + 1536x864` training. `1.75x` supersampling also passes at `0.14` with OCR `0.6635`, but it is slower at `1191.003ms`, so denser latent training is the cleaner model-layer path.

C4.0 focuses on the denser-canvas path: seed robustness, a `freq12` ladder, lighter edge weighting, a `1920x1088` latent-resolution test, and stronger `0.145/0.16` resize stress.

C4.0 improves the best `0.125` resize result again: seed `1` of `1536x864 + freq10` reaches OCR `0.7222`, segment `559.324ms`, and motion `0.0574`. `freq12` at the same bracket is also strong at OCR `0.7032`. The harder `0.14` bracket remains unstable, with seed `1` collapsing to OCR `0.3143` after seed `0` passed in C39; `0.16` still passes at OCR `0.5660`. C4.1 focuses on optimizer stability and seed variance rather than bigger canvases, since `1920x1088` regressed.

C4.1 confirms that stability is the main issue. The `0.125` bracket holds across seeds but ranges from OCR `0.6636` to `0.7222`. The `0.14` bracket can recover with lower LR on some seeds (`lr007-seed1` reaches OCR `0.6849`) but lower LR hurts others, so a single constant LR is not a complete fix. C4.2 tests optimizer schedules: cosine LR decay and gradient clipping.

C4.2 shows gradient clipping is more promising than cosine LR for the hard `0.14` resize bracket. `c42-frame-scale-014-edge09-freq10-train1536-clip1-seed1` reaches OCR `0.6944`, segment `565.820ms`, and motion `0.0601`. Cosine LR helps the weak `0.125` seed (`0.7064`) but does not rescue the `0.14` bracket reliably. C4.3 expands gradient clipping across clip strengths and seeds.

C4.3 confirms gradient clipping is the best stability lever so far. The hard `0.14` global resize bracket reaches OCR `0.7281` at segment `566.234ms` with clip `0.5`, and another clip `1.0` seed also reaches OCR `0.7281` at segment `570.829ms`. This beats the earlier `0.125` resize reference while running a harder transform. Seed variance is still real, so clipping improves the ceiling without fully solving robustness.

C4.4 pivots beyond global warp. A single frame-scale transform is too easy because every item moves together. The next suite adds an `independent-regions` layout mode: several coarse page regions are blanked and re-rendered through separate neural-canvas query transforms, each with different pan, scale, speed, and phase. This is still not the final general renderer, but it is a much better stress test for neural-canvas pixels than text wiggle or one camera-like resize.

C4.4 confirms independent item motion is the new hard problem. All ten runs stay fast (`605-1048ms` per 33-frame segment including encode), but text quality drops sharply: the best moderate run is `c44-regions-010-pan024-clip05-seed1` at OCR `0.5055`, and the strongest useful run is `c44-regions-014-pan030-clip05` at OCR `0.5000` with motion `0.0365`. Human inspection shows hard rectangular tearing from the coarse region compositor, so C4.5 splits into two better tests: a smooth blended independent-region query field, and a learned independent-field mode where the model must synthesize multi-region motion directly from `x,y,t`.

C4.5 removes the artificial hard rectangles and confirms the smooth-field direction is cleaner. The best query-time smooth field is `c45-field-010-pan024-clip05-seed1` at OCR `0.8165`, segment `601.358ms`, with no visible block seams; `c45-field-010-pan024-clip05` also reaches OCR `0.7818` at `584.763ms`. The catch is motion: measured deltas stay around `0.0128-0.0224`, so this mostly proves quality recovery, not enough visible independent translation. The learned `x,y,t` field branch keeps moderate text quality at mild motion (`0.6393` OCR for flow `0.04`, `0.6036` for flow `0.06 + freq12 + clip0.5`) but motion remains low, and flow `0.08` collapses OCR to `0.2289`.

C4.6 makes the benchmark stricter: translation is separated from stretch. The new `independent-translate` layout mode disables local scale and only pans page regions on separate timelines, while `independent-translate` as a learned motion mode asks the model to synthesize those local translations directly from `x,y,t`. This should tell us whether we are actually moving regions independently or merely producing an easier elastic wiggle.

C4.6 is still not the final proof. The best query-time translation controls are near-misses: `c46-translate-pan030-clip05` reaches OCR `0.6948` but motion `0.0184`, while `c46-translate-pan045-clip05` reaches OCR `0.6606` and motion `0.0241`. Stronger pan crosses the motion direction but loses text quality. The learned branch is more important: `c46-learned-translate-004-s7000` reaches motion `0.0257` and OCR `0.3892`, narrowly missing its `0.4000` OCR gate. This shows the path is not blocked, but it does not prove a Flipbook-like renderer yet because it is still region translation rather than new layout synthesis.

C4.7 pivots to the real viability proof: learned layout reflow. The target now moves text/content blocks and resizes/repositions the illustration into a different page layout at the video midpoint, then loops back. Boxes are used only to synthesize the training target; the rendered frames remain direct neural-canvas pixels from `x,y,t`. This is the right test for whether the model can produce a new page layout rather than merely wiggle or elastically distort the existing one.

C4.7 gives the first credible positive signal for the path. Multiple learned layout-reflow runs pass under the 1.3s segment budget while clearing motion and OCR gates. The best run is `c47-layout-reflow-100-c32h160-s10000`: OCR `0.5193`, motion `0.0520`, segment `620.732ms`. Human review shows the page is actually re-laid out: the diagram changes position/scale and the content bands move. The weak point is still text sharpness and visual inspectability, so C4.8 saves the synthetic target midpoint next to the model output and pushes higher-capacity, text-weighted, and higher-resolution reflow variants.

C4.8 shows that brute-force capacity is not the missing piece. All ten stricter reflow runs stay well under the `1.3s` 33-frame plus encode budget, but none beat the C47 OCR peak. The best C48 result is `c48-layout-reflow-100-train1920-c24h128-s10000` at OCR `0.4739`, motion `0.0488`, segment `634.374ms`; the strongest `1536x864` variant is `c48-layout-reflow-100-c32h160-lr007-s12000` at OCR `0.4557`, motion `0.0514`, segment `623.097ms`. The new `target-mid.png` contact-sheet tile confirms the intended layout target is crisp while the learned midpoint is still soft.

C4.9 changes the training distribution instead of only scaling the model. Layout-reflow training now has optional target-side sampling, target-side glyph/text loss weighting, and midpoint-biased time sampling. This directly addresses the C48 failure mode: source-side glyph sampling undersamples text after it moves into its target layout position.

C4.9 produced the new learned layout-reflow best. `c49-reflow-target-b196-c32h160-s10000` reaches OCR `0.5761`, motion `0.0517`, segment `867.931ms`. Two other variants also beat C47: `c49-reflow-target-mid60-c32h160-s14000` at OCR `0.5714`, segment `724.892ms`, and `c49-reflow-target-train1920-c32h160-s11000` at OCR `0.5497`, segment `631.621ms`. The most important signal is that target-side sampling helped more than raw capacity did in C48.

C5.0 is queued behind C4.9 as an ablation wave. It separates target-side sampling, target-side weighting, and midpoint time bias, then tests a few sharper variants (`freq12`, `c40h192`, cosine LR, clip `1.0`, and `1920x1088` text-weighting). The goal is to learn which part of the C4.9 intervention matters before adding another model abstraction.

Suggested `results.tsv` header:

```text
run_id	commit	canvas_type	compile_ms	render_960_ms	render_33_wall_ms	encode_ms	ocr_similarity	resize_consistency	temporal_consistency	status	description
```

`eval-results.tsv` is the normalized scenario-level leaderboard:

```text
run_id	commit	scenario_id	renderer_family	status	segment_wall_ms	render_33_wall_ms	encode_ms	effective_generated_fps	ocr_token_f1_min	ocr_token_f1_mean	layout_similarity	resize_consistency	temporal_consistency	motion_delta	loop_error	target_mid_delta	target_mid_similarity	pixel_source_class	failed_gates
```

Suggested artifact shape:

```text
outputs/track-c/<run-id>/
  input.png
  render-512.png
  render-960.png
  crop-2x.png
  target-mid.png
  contact-sheet.jpg
  output.mp4
  metrics.json
  quality.json
```
