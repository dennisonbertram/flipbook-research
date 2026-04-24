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
  run:     20260424T195138593473Z-c2-lite-glyph-static-layout-frame-scale-c36-frame-scale-014-edge09-1280x736-s4500
  segment: 547.378ms
  OCR F1:  0.5634
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

C3.8 moves from parameter bracketing to model/render diagnosis. It tests whether resize text loss is mostly sampling aliasing (`1.5x` and `2x` neural supersampling), representational capacity (`24` channels, `128` hidden), coordinate frequency (`freq_bands=10`), or seed variance at the `0.125` and `0.14` resize brackets.

Suggested `results.tsv` header:

```text
run_id	commit	canvas_type	compile_ms	render_960_ms	render_33_wall_ms	encode_ms	ocr_similarity	resize_consistency	temporal_consistency	status	description
```

`eval-results.tsv` is the normalized scenario-level leaderboard:

```text
run_id	commit	scenario_id	renderer_family	status	segment_wall_ms	render_33_wall_ms	encode_ms	effective_generated_fps	ocr_token_f1_min	ocr_token_f1_mean	layout_similarity	resize_consistency	temporal_consistency	motion_delta	loop_error	pixel_source_class	failed_gates
```

Suggested artifact shape:

```text
outputs/track-c/<run-id>/
  input.png
  render-512.png
  render-960.png
  crop-2x.png
  output.mp4
  metrics.json
  quality.json
```
