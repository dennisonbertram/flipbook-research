# Track C Experiment Logs

Track C experiments measure neural canvas rendering: compile once, then render pixels for multiple viewports, resolutions, and times.

Use compact TSV summaries here and keep generated images/videos under `outputs/track-c/`.

Latest result:

```text
20260424T155913Z-c2-lite-text-static-layout-element-frame-scale-1280x736-s4500
33 renders: 401.190ms
encode:     546.285ms
OCR F1:     0.4124
status:     pass
```

The glyph-weighted sampler/loss preserved speed but did not beat the previous unweighted C2-lite OCR score of `0.8326`. The OCR-box-weighted C2.1 run did improve the OCR score to `0.8545`.

C2.2 frame-scale stress shows that jiggle is not enough as a benchmark. Moderate frame scaling and viewport zoom keep latency under budget but collapse text quality to `0.1053`; strong scaling collapses OCR to `0.0000`.

C2.3 layout-transform rendering recovers much of that quality by keeping content stable and applying frame sizing as a query transform: moderate stress rises to `0.7091`, strong stress rises to `0.3610`.

C2.4 adds OCR line anchors. It improves moderate resize OCR from `0.7091` to `0.7321` and strong resize OCR from `0.3610` to `0.4124`, with extra render cost from sequential patch queries.

Suggested `results.tsv` header:

```text
run_id	commit	canvas_type	compile_ms	render_960_ms	render_33_wall_ms	encode_ms	ocr_similarity	resize_consistency	temporal_consistency	status	description
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
