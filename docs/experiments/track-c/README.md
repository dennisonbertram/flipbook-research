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

C5.0 confirms the useful ingredient is target-side loss weighting plus enough optimization budget. The best ablation is target-weight-only at OCR `0.5000`, motion `0.0488`, segment `620.067ms`; target-sample-only drops to OCR `0.4277`, and midpoint-only lands near the gate at `0.4767`. C5.1 therefore focuses on the C4.9 winner family: larger batches, longer runs, high-res `c32h160`, and seed repeats.

C5.1 shows more target sampling and more batch are not monotonic. Early C5.1 results regress from C4.9, while `weightonly-c32h160-s14000` stays strong at OCR `0.5614`. C5.2 adds partial target-sampling ratios (`0.25/0.50/0.75`) and a weight-only scale/seed sweep.

C5.2 stays near the frontier without beating it: partial target sampling ratio `0.50` reaches OCR `0.5742`, while `weightonly-b196-s14000` reaches `0.5729`. C5.3 changes the loss itself by adding an L1 term to the weighted MSE objective, testing whether sharper pointwise error reduces text blur/ghosting at the reflow midpoint.

C5.3 is a useful negative result: simple L1 sharpening did not solve reflow blur. The best L1 run, `c53-reflow-target-full-l1-025-c32h160-s14000`, reaches OCR `0.5604`, motion `0.0473`, and segment `848.440ms`, below the C49/C52 frontier. Stronger L1 often regresses text quality, and `l1=1.0` collapses. The next loss experiment should be more local and structural rather than just increasing pointwise absolute error.

C5.4 tests that next step: a local gradient-consistency term on reflowed output coordinates. Instead of only asking each sampled pixel to match RGB, it also asks one-pixel x/y differences to match the crisp synthetic midpoint target. This directly targets doubled strokes and blurred glyph edges while keeping the renderer pure neural-canvas pixels.

C5.4 is negative/neutral. The best gradient run, `c54-reflow-grad050-r00625-weightonly-c32h160-s14000`, reaches OCR `0.5614`, motion `0.0496`, and segment `720.876ms`, matching an older weight-only result but not the C49/C52 frontier. Partial-target sampling plus gradient loss regresses sharply. C5.5 switches from target replacement to paired target loss: keep the original source-focused sample, then add a second loss at that same content point's reflowed target coordinate.

C5.5 is also negative. The best paired-loss run, `c55-reflow-pair009-w050-b196-s10000`, reaches OCR `0.5495`, motion `0.0485`, and segment `697.042ms`, below the C49/C52 frontier. The broader set ranges from OCR `0.4000` to `0.5161` and does not show a monotonic pair-weight signal. The lesson is that more target-side loss pressure is not enough; the model appears capacity-entangled between coarse layout transport and high-frequency text/detail reconstruction.

C5.6 starts an architecture branch. The renderer now has an optional residual detail canvas/head: the base latent canvas still learns the page and flow, while a small second latent grid and MLP can add bounded high-frequency RGB-logit corrections at the same neural-canvas query coordinates. The C56 queue tests detail channels `8/16`, scales `0.125/0.25/0.50`, and both target-sampling and weight-only variants around the strongest C49/C52 reflow families. This keeps the output pure neural-canvas pixels while asking whether text strokes need a separate detail path instead of more hand-written masking or loss tricks.

C5.6 is a useful negative. The best residual-detail run, `c56-detail16h128-025-target50-s14000`, reaches OCR `0.5514`, motion `0.0491`, and segment `875.921ms`. That is a pass, but it is below the C49/C52 frontier and below the best C55 pass. The detail head also raises render time from the `~700ms` family into roughly `825-1116ms`, so this branch spends budget without improving text enough.

C5.7 switches to a cheaper architecture idea: source-coordinate conditioning. Instead of adding another canvas, the renderer MLP can see both the output coordinate and the learned warped/source coordinate used to sample the latent canvas. The hypothesis is that layout position and source-space glyph phase are separate facts; giving both to the model may preserve text strokes through reflow without masks, overlays, or a second render path.

C5.7 is the first clear architecture win after the C49/C52 frontier. `c57-sourcecoord-target75-c32h160-s14000` reaches OCR `0.6264`, motion `0.0494`, and segment `817.800ms`, beating the previous learned layout-reflow best (`0.5761`) while staying under the `1.3s` 33-frame plus encode budget. Two more source-coordinate variants also beat the old frontier: `c57-sourcecoord-target50-c24h128-s12000` at OCR `0.6000` and `c57-sourcecoord-target-b196-s10000` at OCR `0.5981`. The useful signal is specific: exposing source-space phase helped more than residual detail, L1, gradient loss, or paired loss.

C5.8 follows the transport hypothesis. The current learned-flow budget was only about `0.14` normalized-coordinate travel, but the layout-reflow target moves some bands by roughly `0.45`. That means the renderer may still be repainting too much detail from memory instead of moving source detail through the latent canvas. C5.8 tests larger learned-flow ranges (`0.20-0.45`) and an optional inverse-layout-flow supervision term, while keeping the output pure neural-canvas pixels.

C5.8 is a sharp negative. Larger learned-flow range destabilizes text instead of improving transport: the best run, `c58-flow028-target50-c32h160-s12000`, reaches only OCR `0.4286` at segment `822.649ms`. Flow supervision does not rescue it; the best supervised variant, `c58-flowsup035-w0025-target50-c32h160-s12000`, reaches OCR `0.3727`. The likely lesson is that the renderer needs structured transport, not merely a wider unconstrained flow field.

C5.9 adds an oracle-flow diagnostic. The neural canvas still generates every pixel, but the sampling coordinate is provided by the known inverse synthetic layout-reflow map instead of the learned flow network. If this recovers text quality, the bottleneck is learning the transport field. If it does not, the bottleneck is in the latent canvas/MLP reconstruction after transport.

C5.9 is also negative as a transport-only explanation. The best oracle-flow result, `c59-oracleflow-target75-c24h128-s10000`, reaches OCR `0.5207`, motion `0.0500`, and segment `671.665ms`, below C57's OCR `0.6264` source-coordinate result. Oracle flow avoids the C58 collapse but does not beat learned flexible flow, which suggests the useful C57 ingredient is not rigidly correct box transport. It is source-coordinate conditioning plus a small learned, flexible warp and target-side sampling.

C6.0 consolidates the C57 source-coordinate family instead of adding another mechanism. The queue sweeps target-side sampling ratios around the C57 winner (`0.60/0.70/0.80/0.90/1.00`), repeats the `0.75` winner on additional seeds, and tests C24/H128, B196, and C40/H192 capacity/speed points. The goal is to determine whether the C57 win is robust enough to become the next base model before adding more structural machinery.

C6.0 does not beat the C57 frontier, but it narrows the source-coordinate recipe. The best C60 run is `c60-sourcecoord-target60-c32h160-s14000` at OCR `0.5933`, motion `0.0450`, and segment `1061.855ms`; the best smaller model is `c60-sourcecoord-target75-c24h128-s12000` at OCR `0.5837`, motion `0.0492`, and segment `1013.454ms`. Ratios above `0.70`, C40/H192, and B196 all regress. C6.1 therefore treats C57's `0.75` win as seed-sensitive and tests the lower `0.55-0.65` target-ratio region, seed repeats at `0.60`, a lower flow cap, C24/H128 variants, and two optimizer variants around the C60 winner.

C6.1 makes the fast B196 path look more promising than ordinary C32 target-ratio tuning. `c61-sourcecoord-target60-b196-s10000` reaches OCR `0.6077`, motion `0.0509`, and segment `712.728ms`, making it the best post-C57 result and faster than the C57 peak. `c61-sourcecoord-target60-c24h128-s12000` is close at OCR `0.5972`, motion `0.0492`, and segment `669.808ms`. The wider target-ratio sweep, lower flow cap, and optimizer variants do not help.

C6.2 is mixed but important. It finds a new learned layout-reflow OCR frontier with the small C24/H128 model: `c62-sourcecoord-target60-c24h128-seed2-s12000` reaches OCR `0.6634`, motion `0.0523`, and segment `765.292ms`, beating the previous C57 peak (`0.6264`) while staying under the `1.3s` budget. But the same family is seed-sensitive: `c24h128-seed1` falls to OCR `0.4403`, and `c24h128-b196` falls to `0.4286`. The C61 B196 signal also does not hold up under longer runs or seed repeats; its best C62 repeats are `b196-seed1` at OCR `0.5646` and `b196-edge06` at `0.5566`.

C6.3 is a clear robustness negative around the C62 small-model high point. Extra C24/H128 seeds at target ratio `0.60` cluster around OCR `0.4643-0.5000`, the shorter seed2 run falls to `0.4500`, and the longer seed2 run collapses to `0.2927`. The only pass is `c63-sourcecoord-target65-c24h128-seed2-s12000` at OCR `0.5524`, motion `0.0511`, and segment `760.141ms`, far below the C62 frontier.

C6.4 adds a training-layer layout-motion curriculum: train from easier partial reflow toward full reflow, while still rendering/evaluating the full motion target. It helps some runs, but does not solve robustness. The best C64 run is `c64-sourcecoord-target60-c24h128-curr50-seed2-s12000` at OCR `0.6077`, motion `0.0496`, and segment `758.183ms`; the C32 target75 weak-seed rescue reaches OCR `0.5714`. The broader seed set still ranges from OCR `0.4500-0.5258`.

C6.5 tests endpoint anchoring after a fresh grounding review of Flipbook's public claims. The idea was to reflect Flipbook's current two-system story: static generated pages first, live video transition second. This is a clean negative. All ten C65 runs miss the OCR gate; the best is `c65-sourcecoord-target60-c24h128-end50-curr50-seed2-s12000` at OCR `0.5207`, motion `0.0488`, and segment `747.910ms`. Endpoint anchoring did not stabilize the high-text basin, so C6.6 moves back to architecture.

C6.6 adds latent-neighborhood decoding. Instead of giving the renderer MLP one bilinear latent vector at the sampled source coordinate, it can see a tiny learned latent neighborhood (`cross` or `grid`, 1-2px radius). This keeps every output pixel generated by the neural canvas, but gives the model local glyph/detail context during reflow. This is a positive architecture signal: `c66-neighbor-cross1-target60-c32h160-seed1-s14000` reaches OCR `0.6178`, motion `0.0503`, and segment `1093.608ms`. It does not beat the C62 high, but it is close to the C57/C64 frontier and much better than C65 endpoint anchoring. Small 1px neighborhoods are the promising region; 2px and curriculum variants regress. C6.7 consolidates this branch with C32/H160 seed repeats, target-ratio and radius sweeps, plus B196/C40 capacity checks.

C6.7 shows latent-neighborhood decoding is useful but still not robust. The best C67 run is `c67-neighbor-cross05-target60-c32h160-seed1-s14000` at OCR `0.5957`, motion `0.0538`, and segment `1265.377ms`; C40/H192 passes at OCR `0.5521`. But the target60 C32/H160 seed repeats collapse to OCR `0.4267-0.5146`, so the C66 `0.6178` result is not yet a stable recipe. C6.8 therefore adds a coarse latent context canvas alongside the local latent neighborhood, giving the decoder both local glyph detail and broader page/layout context while still generating every pixel directly.

C6.8 gives a strong positive signal for light coarse context. `c68-context8s025-cross1-target60-c32h160-seed1-s14000` reaches OCR `0.6269`, motion `0.0525`, and segment `998.129ms`, while `c68-context16s050-cross1-target60-c32h160-seed1-s14000` reaches OCR `0.6214`. Heavy context regresses (`c32/scale0.25` falls to OCR `0.4250`), so the likely useful region is small context capacity, not simply more latent features. C6.9 tests whether the c8/scale0.25 and c16/scale0.5 wins are robust across seeds.

C6.9 partially validates light context but does not solve robustness. The c8/scale0.25 family gets two more passes: seed3 reaches OCR `0.6019`, seed2 reaches `0.5525`, while seed4/5 land at `0.5031/0.5318`. Counting C68 seed1, that is three passes and two near-misses across seed1-5. The c16/scale0.5 repeats do not hold (`0.4400-0.5476`), while c4/scale0.25 passes at OCR `0.5746`. C7.0 keeps the compact-context architecture and changes the training distribution: direct target-midpoint glyph/text sampling should tell us whether weak seeds are failing because target-layout text positions are underrepresented during training.

C7.0 shows direct target-midpoint sampling can help, but only in a small dose. `c70-mid10-c8s025-seed4-s14000` rescues the C69 weak seed4 from OCR `0.5031` to `0.5822` and passes. Heavier `mid20` generally regresses c8 seeds, `mid35` lands just below the gate at OCR `0.5497`, and the OCR text-box ablation does not help (`0.4780`). c4 context remains promising: `c70-mid20-c4s025-seed3-s14000` passes at OCR `0.5792`, with seed2 near the gate at `0.5444`. C7.1 consolidates low target-mid sampling (`0.05-0.15`) across c8 and c4 weak seeds without text-box supervision.

C7.1 keeps the low-dose target-mid signal alive but does not make it robust. `c71-mid05-c8s025-seed5-s14000` passes at OCR `0.5905`, and `c71-mid15-c4s025-seed2-s14000` passes at OCR `0.5701`. `c71-mid10-c4s025-seed4-s14000` clears OCR at `0.5581` but misses latency at `1352ms`. The rest of the low-dose c8/c4 weak-seed map misses. C7.2 therefore stops adding mechanisms and maps robustness for the two plausible recipes: `c8/mid05` and `c4/mid15`.

C7.2 is a robustness negative. Neither `c8/mid05` nor `c4/mid15` repeats: the best run is `c72-c4mid20-seed4-s14000` at OCR `0.5389`, and all ten runs miss the OCR gate. Target-midpoint sampling can rescue individual seeds, but it is not the stabilizer. C7.3 returns to architecture by changing how coarse context is sampled: source-coordinate context preserves content identity, target-coordinate context may encode destination layout, and both-mode context tests whether the decoder needs both.

C7.3 shows coarse destination context is also not the stabilizer. Target-only context misses all runs; both-mode context gets one pass (`c73-c8both-seed1-s14000`, OCR `0.5614`) but does not reproduce and does not beat the earlier source-context seed1 result. C7.4 moves the destination signal to the high-resolution latent path: sample the main latent neighborhood at source, target, or both coordinates, while keeping the output pure neural-canvas pixels.

C7.4 is a clean negative. High-resolution target/both latent sampling does not solve layout reflow: all ten C74 runs miss the OCR gate, with a best score of `0.5150` from `c74-latentboth-nocontext-seed1-s14000`. The target-only runs land around OCR `0.46`, and some dual-latent runs pressure or miss the `1.3s` segment budget. The lesson is that destination detail cannot simply be concatenated into the same decoder MLP.

C7.5 adds a structural decoder test. The renderer now has a dual-residual mode: a source branch produces the main RGB logits from warped/source content, while a separate target-position branch produces a gated residual correction. The residual branch is initialized at zero so training starts close to the source-only renderer, then learns destination-local repairs only when useful. The C75 queue tests c8/c4/no-context variants and residual scales `0.25/0.50`.

C7.5 is a real positive architecture signal but not robust yet. `c75-dualres-s025-c8-seed2-s14000` reaches OCR `0.6415`, motion `0.0500`, and segment `1079ms`, which is close to the old C62 high point and materially better than C74. `c75-dualres-s050-nocontext-seed1-s14000` also passes at OCR `0.5771`, suggesting branch separation has value even without coarse context. The weak points are seed variance and latency: several near-misses land around OCR `0.545-0.549` or segment `1.32-1.37s`. C7.6 consolidates this branch with smaller target residual heads, c8 scale `0.25/0.35`, and no-context repeats.

C7.6 mostly shows that shrinking the target residual branch trades away quality. The smaller heads are often fast, but only `c76-dualres-s035-c8-th64-seed1-s14000` preserves the C75-quality basin, reaching OCR `0.6154` and missing latency by `13.9ms`. No-context repeats do not reproduce the C75 no-context pass with `h64`. C7.7 maps the basin across new seeds for the two plausible recipes (`s0.25/c8/h80` and `s0.35/c8/h64`) and tries two lightweight optimizer stabilizers on weak/near-miss seeds.

C7.7 is a negative basin map. No C77 run passes; the best new seed reaches OCR `0.5660` but misses latency at `1456ms`, and the optimizer tweaks do not rescue weak seeds. This suggests C75's split-branch decoder found a real but brittle basin. C7.8 keeps the split but makes the residual branch fused: it still starts at zero and cannot replace the source branch, but it can see both source-sampled and target-position features when learning corrections.

C7.8 is also negative. Fusing source and target features into the residual branch raises cost and does not stabilize the basin: the best-quality C78 run reaches OCR `0.6038` but misses latency at `1499.870ms`, while the best fast run stays below the OCR gate. The lesson is that more coordinate/feature concatenation is not enough. C7.9 pivots to a learned RGB neural texture skip: initialize a model parameter with the page RGB logits, sample it through the same source/target coordinate path, and ask the MLP to learn bounded residual corrections. This remains pixel-native model output, not an overlay, and directly tests whether high-frequency strokes need a more spatial base representation than latent-feature reconstruction alone.

C7.9 is a clean negative. The RGB texture made the renderer fast (`~909-1111ms`) but too rigid: the best OCR run is `c79-rgbskip-s100-c8-seed2-s14000` at OCR `0.4952`, with motion only `0.0228`. Lower residual scales often collapse motion to zero. Visual review shows ghosted/smeared source texture rather than a clean new layout. C8.0 keeps the useful idea but attenuates the RGB base logits and increases residual capacity, testing whether the texture can become a detail prior instead of an uneraseable copy of the source page.

C8.0 is a partial recovery. Attenuating the RGB base restores motion and improves quality over C79. The best run is `c80-rgbbase025-res200-nocontext-seed2-s14000` at OCR `0.5967`, segment `757.305ms`, and motion `0.0416`, just below the `0.045` motion gate. Context hurts this branch: the same base/residual with c8 context falls to OCR `0.4941`. C8.1 therefore focuses on no-context variants around base `0.20-0.30`, residual `2.0-3.0`, and slightly stronger layout amount to see whether the near-miss can clear motion without losing text.

C8.1 produces the first attenuated-RGB-skip pass: `c81-nctx-b025-r250-a110-seed2-s14000` reaches OCR `0.5556`, segment `963.710ms`, and motion `0.0460`. It is still visibly ghosted, but it proves the RGB texture can be used as a detail prior without a render-time overlay, while still meeting the learned layout-reflow gates. C8.2 consolidates that basin across seeds and adjacent amount/residual settings before treating it as a new base architecture.

C8.2 is the strongest Track C layout-reflow signal so far. The same no-context base `0.25`, residual `2.5`, amount `1.10` recipe passes on several new seeds, and the best adjacent setting, `c82-nctx-b025-r275-a110-seed4-s14000`, reaches OCR `0.7087`, motion `0.0457`, and segment `923.432ms`. This is still visibly ghosted, so C8.3 refines around residual `2.75`, base `0.20-0.30`, and amount `1.00-1.15` before promoting the recipe.

C8.3 confirms residual `2.75` is viable but not strictly better than the C82 frontier. Passes include `c83-nctx-b025-r275-a110-seed5-s14000` at OCR `0.6458`, `c83-nctx-b025-r325-a110-seed4-s14000` at OCR `0.6269`, and `c83-nctx-b030-r275-a110-seed4-s14000` at OCR `0.5930`, all under `1.0s`. The remaining failure mode is visible source ghosting, so C8.4 adds a learned RGB-skip gate canvas initialized either from source edges or a constant gate.

C8.4 shows the gate idea is only partially useful. The constant learned gate at init `0.35` keeps the high-quality basin alive (`c84-gatelearn035-b025-r275-a110-seed4-s14000`: OCR `0.6863`, segment `927.308ms`, motion `0.0469`), while init `0.50` barely passes quality and edge-initialized gates mostly regress. Visual review does not show a decisive ghosting fix. The gate should therefore be treated as a model-owned detail prior worth consolidating, not as a solved source-remnant mechanism.

C8.5 follows the Flipbook grounding review: the public claim is still that every page, including text, is model-rendered pixels with no overlays. The next queue consolidates only constant learned gates (`0.25-0.45` init and `0.35` seed repeats) and adds a change-region/source-remnant proxy to the eval TSV. OCR remains necessary, but no longer sufficient: a candidate that reads well while leaving old source layout traces should be treated as unfinished.

C8.5 is a negative consolidation result. All ten learned-gate runs miss the pass gate. The closest quality run is `c85-gatelearn030-b025-r275-a110-seed4-s14000` at OCR `0.5714`, segment `1079.571ms`, and motion `0.0444`, failing motion only; the closest gate-threshold run is `c85-gatelearn045-b025-r275-a110-seed4-s14000` at OCR `0.5497`. Change-region target deltas stay clustered around `0.028-0.032`, and the visual failure remains old-layout source remnants under the new layout. The gating branch should not receive more scalar tuning until the benchmark itself is cleaner.

C8.6 moves to a clean two-state page stress. The renderer now has `layout-clean-reflow`, where `t=0` and `t=1` are the original page and `t=0.5` is a separately rendered clean target page with the same semantic content but a genuinely different layout. The target frame is not a warped/composited transitional image, and C8.6 OCR scoring uses `target-mid.png` as the reference. The initial queue runs ten no-overlay neural-canvas variants around source-coordinate decoding, cross-neighborhood latent sampling, light context, and one dual-residual decoder check.

C8.6 is the strongest evidence so far for the pure neural-canvas path. Eight of ten runs pass the clean page-state gate, with median OCR `0.6979` and median segment wall time `923.214ms`. The best run, `c86-clean-c32h160-target60-mid20-seed1-s12000`, reaches OCR `0.7527`, motion `0.0600`, and segment `752.003ms`. Visual review shows the midpoint closely matches the separately rendered target page rather than leaving the old page visibly stretched underneath. The caveat is important: the target is still a deterministic fixture, not a generated open-world page, so C8.7 should stress multiple clean target layouts before claiming generality.

C8.7 starts that generality check. It keeps the C86 winning recipe (`C32/H160`, no context, source-coordinate features, cross latent neighborhood, target ratio `0.60`, target-mid ratio `0.20`) and swaps in two new clean target variants: `right-diagram` and `stacked`. The question is whether the success survives materially different page geometry, not whether another capacity trick can overfit the original target.

C8.7 is a strong positive. All ten clean target-variant runs pass. `right-diagram` reaches OCR `0.9000` at `920.211ms`, and `stacked` reaches OCR `1.0000` at `925-942ms`; the fastest strong stacked run reaches OCR `0.8800` at `756.538ms`. Human review confirms real relayout into the target state, but faint source remnants are still visible in some large diagram bands. C8.8 therefore keeps the same recipe and changes the target distribution again toward unboxed text layouts and floating callouts, where text is not protected by neat card backgrounds.

C8.8 passes the unboxed stress. All ten runs pass: `unboxed-columns` reaches OCR `0.9302` at `927.622ms` and a fast OCR `0.9091` at `765.567ms`; `callout-map` is harder but still reaches OCR `0.7826` at `772.390ms`. Visual review shows the unboxed target is clean and the callout target is usable, though small callout text remains the weaker surface. C8.9 should now change the target copy itself, so the model has to repaint new words rather than only move existing semantic text.

C8.9 is a real positive on changed copy. All ten runs pass the current gates. The strongest `changed-callout` run reaches OCR `0.9259` at `1057.956ms`, another reaches OCR `0.8846` at `1196.854ms`, and the fastest `changed-callout` pass reaches OCR `0.7407` at `743.559ms`. The `changed-unboxed` family is visually readable but lower by OCR (`0.5000-0.6111`), likely because the dense right-column body text is a harder small-text target. Human review shows the new headings and body copy are genuinely present as pixels, while faint source remnants remain in open whitespace. C9.0 therefore changes the illustration grammar itself with `timeline-illustration` and `transit-illustration` targets.

C9.0 is a stronger positive because the target is no longer the same oval diagram. All ten changed-illustration runs pass. `timeline-illustration` reaches OCR `0.9091` at `929.222ms` and OCR `0.8421` at `741.483ms`; `transit-illustration` reaches OCR `0.7805` at `912.081ms` with repeated transit passes at OCR `0.7368`. Visual review shows the timeline bars, year markers, route lines, grid, and new labels are genuinely redrawn as the target page state. The remaining caveat is the same: faint source haze can still appear in open whitespace. C9.1 should move to unrelated new-topic target pages so the target title, body, and illustration all change together.

C9.1 passes all ten new-topic runs. Orbit is especially strong (`0.9286-1.0000` OCR on the best mid20 seeds), and reef reaches `0.8485` on the stronger mid35 run. The branch now needs to prove cleaner repainting, not just stronger fixture variety, because crop review still catches faint old-source remnants in open visual areas.

C9.2 is queued as the source-remnant stress wave. It keeps the C91 recipe and introduces `naturalist-plate`, an 1800s naturalist-style fern specimen with etched linework and labels, plus `deep-sea-lab`, a dark high-contrast scientific cross-section. The goal is to make old page leakage visible while testing a richer illustration style.

C9.2 passed all ten initial stress runs, but it also proved the current gate is too lenient. Full-frame midpoint renders look like the new target pages; close crops still show old Colosseum text and diagram remnants. `deep-sea-lab` is quantitatively strong (`0.6190-0.8966` OCR), while `naturalist-plate` is harder (`0.4082-0.4964` OCR) because thin etched linework and small labels are more demanding. C9.3 adds a contrastive source-remnant loss at clean-reflow midpoints so the model is explicitly penalized when changed pixels are still closer to the source page than the clean target.

C9.3 is a useful partial result, not a solution. The best naturalist run improves to OCR `0.5424`, and the best deep-sea contrast run still reaches OCR `0.8276`, but the transition crop remains visibly source/target blended. The failure is now more specific: the model can hit a clean target page state, but the in-between frames still behave like a soft crossfade rather than a convincing page transform.

C9.4 confirms that target-side decoder paths can render a clean midpoint but do not solve transition realism. Deep-sea midpoint frames score well (`0.8667` OCR for both dual-residual and dual-gate, with `1265-1266ms` segment times), and the fastest latent-both deep-sea control reaches OCR `0.8000` at `922.816ms`. Naturalist remains much weaker (`0.5000` best OCR). The `crop-2x.png` artifact is rendered at `t=0.25`, so old `Velarium`/`Materials`/diagram content there should be read as transition-frame persistence, not target-midpoint failure.

C9.5 tests a separate learned target-state latent canvas concatenated beside the source latent features. All ten runs pass under the `1.3s` segment budget (`913-1172ms`). The best naturalist run improves slightly to OCR `0.5546`, while the best deep-sea result reaches OCR `0.8000`, below C94's `0.8667` deep-sea score. Midpoint frames look close to the target state; the old-source-heavy crop is the `t=0.25` transition crop. C9.6 therefore makes the state test stricter by blending/switching between source and target latent canvases, with the expectation that midpoint decoding is primarily target-state memory while transition frames still need better motion structure.

C9.6 is a positive target-state result and a transition-quality warning. The stricter target-canvas blend keeps most runs under budget and makes render time very consistent (`~852ms` render, `~1.1s` segment for most passes). Best naturalist is `0.5310` OCR, and best deep-sea remains `0.8000` OCR. A corrected crop audit shows `render-mid.png` is clean at the target state; the old source text appears in `crop-2x.png` because that artifact is rendered at `t=0.25`. C9.7 still runs a harder state split, but the question is now endpoint isolation, latency, and whether transition frames can move beyond crossfade/source persistence.

C9.7 is a mixed endpoint result and a negative transition result. The state-split decoder improves deep-sea slightly (`0.8387` OCR, `1002.438ms` segment on the best seed) but does not beat the C94 deep-sea high (`0.8667`) and weakens naturalist versus C95/C96 (`0.4463` best naturalist OCR; `0.4298` for the faster no-source-coordinate variant). Midpoint frames remain clean. The `t=0.25` crop still shows source/target persistence, which is now understood as a target-definition issue: `layout-clean-reflow` trains an endpoint blend, not a real moving/reflowing transition. C9.8 is implemented as the first transition-aware wave: it saves explicit transition target crops and trains `layout-clean-move-reveal`, where the source layer moves/fades while the target page eases in.

C9.8 is a useful positive once the OCR reference is corrected to `target-mid.png` for `layout-clean-move-reveal`. Six of eight runs pass. Deep-sea is strongest: `c98-v12-deep-sea-movereveal-tblend-init02-rem050-mid20-seed0-s12000` reaches OCR `0.8966` at `939.032ms`, and the base deep-sea run reaches OCR `0.8571` at `917.112ms`. Naturalist remains harder: the base run passes at OCR `0.4839`, while target-blend mid50 and state-split fail. Transition-crop similarity clusters around `0.964-0.971`; deep-sea source-residual gain is negative, while naturalist remains positive, so source persistence is still more visible in the etched naturalist target. C9.9 therefore moves beyond a single move/reveal field and tests independent region recomposition.

C9.9 is real progress, but not a final proof. Independent recomposition forces source and target page regions to move/arrive separately, so it is a harder test than global wiggle or a single move/reveal transition. Five of six runs pass after adding endpoint OCR gates. Deep-sea is strong: the target-blend run reaches midpoint OCR `0.8667`, source-frame OCR `0.8054`, last-frame OCR `0.8326`, and segment `1121.871ms`; the faster base run reaches midpoint OCR `0.8276` at `936.786ms`. Naturalist is weaker but informative: target-blend and state-split preserve endpoints, while the base run is now correctly marked `quality_fail` because it destroys the clean source/final frames. The next queue is C10.0: apply independent recomposition to timeline, transit, reef, and orbit pages, while repeating naturalist/deep-sea on the endpoint-preserving variants to check that this is not just a two-fixture overfit.

C10.0 is a strong generalization result. All eight runs pass endpoint-aware gates. Timeline reaches midpoint OCR `0.9375`, orbit `0.8235`, transit `0.7179`, reef `0.5116`, deep-sea `0.8000-0.8276`, and naturalist remains weak but above gate at `0.3968-0.4138`. All runs stay under the `1.3s` segment budget. Visual review says the target midpoints are genuinely different pages, not stretched source layouts. The remaining problem is transition cleanliness: transition source-residual gain stays positive for timeline/transit/reef/orbit/naturalist and only goes negative for deep-sea. C10.1 should therefore target transition-frame source persistence directly rather than tuning endpoints again.

C10.1 adds truth-referenced source-remnant pressure against the synthetic transition target. It is directionally useful but incomplete: five of six runs pass, the naturalist state-split run misses latency by `3.659ms`, and OCR remains strong for timeline (`0.9677`), orbit (`0.8000`), reef (`0.7742`), and deep-sea (`0.8276`). The transition source-residual gain still stays positive for most targets, with naturalist still worst at `0.1510-0.1523`. C10.2 keeps the same truth reference but changes the timing curve from squared midpoint pressure to earlier-on `1.0` and `0.5` probes.

C10.2 says earlier pressure is worth keeping. Timeline, reef, orbit, and deep-sea all pass with `time_power=1.0`, and their transition source-residual gains improve to `0.0633`, `0.0313`, `0.0488`, and `0.0043`. Naturalist `time_power=1.0` fails OCR at `0.3208`, but the `time_power=0.5` probe passes at `0.4118` and improves residual gain to `0.1136`. C10.3 should therefore run `time_power=0.5` across the non-naturalist targets and keep pressure probes focused on naturalist.

C10.3 is a useful negative on scalar timing. It mostly preserves OCR, including orbit OCR `0.9286`, reef `0.6897`, timeline `0.9677`, and naturalist `0.4000-0.4444`, but residual gains do not keep improving: timeline `0.0654`, orbit `0.0546`, reef `0.0406`, deep-sea `0.0135`, and naturalist best same-seed `0.1324`. Stronger naturalist remnant weight misses latency at `1388.021ms`. C10.4 should change sampling instead: reserve source-only remnant-edge samples near transition times.

C10.4 is complete and says the heavy sampling reserve is too sharp. `srcsample18` keeps timeline (`0.9677` OCR), reef (`0.7500`), orbit (`0.7429`), and deep-sea (`0.7059`) passing, but transition source-residual gains are not better enough: timeline regresses to `0.0783`, reef to `0.0520`, orbit only reaches `0.0452`, and deep-sea is near-neutral at `0.0021` with lower OCR. Naturalist remains the weak fixture: `time_power=0.5` barely passes OCR (`0.3519`) and `time_power=0.25` fails. C10.5 should repeat the same matrix with a smaller `srcsample06` reserve.

C10.5 is complete. Smaller source-only sampling restores OCR and pass status for most variants, but it is not the cleanup lever: timeline `0.0691`, reef `0.0598`, orbit `0.0550`, and deep-sea `0.0133` do not beat the best C10.2/C10.3 residuals. Naturalist `time_power=0.25` improves to `0.1235` and passes at OCR `0.3689`; the `time_power=0.5` same-seed run misses latency at `1303.764ms`. C10.6 should add direct weighted transition-target loss on remnant regions instead of reserving more sample mass.

C10.6 is complete. Direct transition-target L1 across all changed regions is too broad: all six runs pass and naturalist OCR improves (`0.3922`/`0.4808`), but transition source-residual gain worsens for timeline (`0.0709`), reef (`0.0759`), orbit (`0.0566`), and deep-sea (`0.0353`), with naturalist still high (`0.1341-0.1529`). C10.7 should restrict the direct term to source-only remnant regions.

C10.7 is complete. Restricting direct loss to source-only remnants is more promising but over-weighted at `0.50`: timeline returns near the C10.2 residual (`0.0641`), orbit improves to `0.0467`, and naturalist `time_power=0.25` reaches `0.1163`, but both naturalist variants fail OCR (`0.3200` and `0.2982`). C10.8 should keep the source-only region and lower direct weight to `0.25`.

C10.8 is complete. Source-only direct `0.25` gives the best orbit residual in the branch (`0.0384`) and naturalist residual improves to `0.1081-0.1096`, but naturalist OCR remains just under the gate (`0.3396-0.3434`). Timeline and reef do not benefit enough (`0.0728`, `0.0528`). C10.9 should focus on naturalist source-only direct weights `0.15-0.18`, with one orbit robustness repeat.

Next experiments:

```text
C109 naturalist source-only direct calibration:
c109-v11-naturalist-indrecomp-truthrem075-tpow025-directsrc015-seed5-s12000
c109-v11-naturalist-indrecomp-truthrem075-tpow025-directsrc018-seed5-s12000
c109-v11-naturalist-indrecomp-truthrem075-tpow05-directsrc015-seed5-s12000
c109-v11-naturalist-indrecomp-truthrem075-tpow05-directsrc018-seed5-s12000
c109-v10-orbit-indrecomp-truthrem075-tpow1-directsrc025-seed5-s12000
c109-v12-deep-sea-indrecomp-truthrem075-tpow1-directsrc015-seed6-s12000
```

Suggested `results.tsv` header:

```text
run_id	commit	canvas_type	compile_ms	render_960_ms	render_33_wall_ms	encode_ms	ocr_similarity	resize_consistency	temporal_consistency	status	description
```

`eval-results.tsv` is the normalized scenario-level leaderboard:

```text
run_id	commit	scenario_id	renderer_family	status	segment_wall_ms	render_33_wall_ms	encode_ms	effective_generated_fps	ocr_token_f1_min	ocr_token_f1_mean	source_frame_ocr_f1	last_frame_ocr_f1	layout_similarity	resize_consistency	temporal_consistency	motion_delta	loop_error	target_mid_delta	target_mid_similarity	transition_crop_delta	transition_crop_similarity	transition_change_region_fraction	transition_change_region_target_delta	transition_change_region_source_delta	transition_change_region_source_bias	transition_source_residual_gain	transition_source_residual_cosine	transition_source_only_edge_fraction	transition_source_only_edge_target_delta	transition_source_only_edge_source_delta	transition_source_only_edge_bias	change_region_fraction	change_region_target_delta	change_region_source_delta	change_region_source_bias	change_region_source_residual_gain	change_region_source_residual_cosine	source_only_edge_fraction	source_only_edge_target_delta	source_only_edge_source_delta	source_only_edge_bias	pixel_source_class	failed_gates
```

Suggested artifact shape:

```text
outputs/track-c/<run-id>/
  input.png
  render-512.png
  render-960.png
  crop-2x.png
  target-mid.png
  target-crop-2x.png
  target-mid-crop-2x.png
  contact-sheet.jpg
  output.mp4
  metrics.json
  quality.json
```
