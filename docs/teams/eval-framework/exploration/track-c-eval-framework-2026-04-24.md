# Track C Eval Framework

Date: 2026-04-24

## Eval Goals

Track C should be evaluated as a persistent renderer contract, not as a one-off image generator:

- Prove that the same learned canvas preserves identity across resolution, viewport, time, and layout transforms.
- Separate compile cost from live render cost; compile can be slow in C0/C2, but render and encode must stay inside the interactive budget.
- Catch the current failure boundary: learned dense motion can animate pixels quickly, but frame-scale/layout stress can smear text unless stable content is moved by render-time transforms or anchors.
- Compare variants at the scenario level, so a run cannot pass only because the easiest still render is good.
- Preserve enough artifacts for automated scoring and fast human review.

## Benchmark Tasks And Scenarios

Use the current text-heavy page as the seed fixture, then expand to a small suite:

- `text-heavy-page`: dense text, labels, diagram, callouts, and small glyphs.
- `diagram-labels`: line art plus short labels that must remain attached to objects.
- `dashboard-table`: tabular text, numbers, axes, and compact UI-like layout.
- `mixed-media-article`: image region plus headline/body/captions.
- `low-contrast-small-text`: hard legibility case for glyph fidelity.

Scenario matrix:

| Scenario | Purpose | Required artifacts |
| --- | --- | --- |
| `still-full-resize` | Same canvas renders full page at `512x288`, `960x544`, `1280x736`, optional `1536x864` downsample. | `render-512.png`, `render-960.png`, `render-1280.png` if available |
| `crop-identity` | 2x zoom and shifted crops preserve local text and diagram identity. | `crop-2x.png`, `crop-shifted.png` |
| `subtle-motion-loop` | Motion is visible without rewriting content, and loop boundary is quiet. | `render-960.png`, `render-mid.png`, `render-last.png`, `output.mp4` |
| `viewport-zoom-pulse` | Query-time pan/zoom does not regenerate the page. | `render-viewport-mid.png`, `output.mp4` |
| `frame-scale-moderate` | Moderate layout stress, matching the C2.2 failure and C2.3/C2.4 recovery path. | `render-layout-mid.png` or `render-element-mid.png`, `output.mp4` |
| `frame-scale-strong` | Strong resize/reposition pressure; expected to expose current gaps. | `render-layout-mid.png` or `render-element-mid.png`, `output.mp4` |
| `element-anchor-stress` | Text lines, labels, and diagram anchors move by constraints while pixels still come from the neural canvas. | anchor manifest, `render-element-mid.png`, masks |
| `responsive-squeeze` | Nonuniform layout pressure approximating mobile or narrow-window changes. | mid-frame PNGs, scenario config |
| `prompt-adherence-c3` | Future compiler eval: generated world must include required facts, strings, labels, and relationships. | prompt manifest, rendered frames, OCR/object checks |
| `single-update` | Future interaction eval: one fact/text/selection changes while unrelated identity stays stable. | before/after frames, diff mask |

Every scenario should include a zero-motion or static-control run when practical. Static controls catch fake stability from no motion; stress controls catch fake motion from destructive repainting.

## Metrics

Primary gates should be reported per scenario and aggregated by worst-case, median, and best current run.

| Category | Metrics | Initial gate |
| --- | --- | --- |
| Latency | `compile_ms`, cold `render_960_ms`, warm per-frame `p50/p95`, `render_33_wall_ms`, `encode_ms`, `render_plus_encode_ms`, FPS-equivalent throughput. | Still `960x544 <= 40ms`; `33` frames plus encode `<= 1300ms`; report compile separately. |
| Temporal stability | `motion_delta`, `loop_error`, `temporal_consistency`, frame-to-frame LPIPS/SSIM, text-mask pixel variance after inverse transform, OCR token-F1 min/mean across sampled frames. | Visible motion `motion_delta >= 0.001`; loop error `<= 0.01`; no sampled-frame OCR collapse. |
| Resize/layout stress | Cross-resolution SSIM/LPIPS after canonical resampling, crop consistency, anchor IoU/drift, OCR under moderate/strong frame-scale, diagram edge consistency, invalid-background cleanliness. | Moderate stress should beat C2.3 baseline `0.7091` OCR token-F1; strong stress should beat C2.4 baseline `0.4124` and trend toward `>= 0.65`. |
| Text legibility | OCR token-F1, character error rate, word error rate, Tesseract confidence, per-box recall, small-text recall, line-order consistency, protected text-mask fidelity. | Still/subtle target `>= 0.85`; scenario pass should use the minimum per text region, not only page-level average. |
| Prompt/source adherence | Required strings present, forbidden strings absent, required labels attached to correct objects, diagram relationships intact, source-vs-render text facts unchanged for overfit runs. | All required facts/strings present for C3; no critical label-object swaps. |
| Layout identity | Low-res layout similarity, OCR box geometry drift, connected-component drift for labels/linework, source-to-render keypoint alignment. | High page-level similarity is necessary but not sufficient; region-level failures should fail the scenario. |
| Human review | 1-5 ratings for text readability, identity stability, layout/anchor correctness, motion quality, artifacts, prompt adherence, overall product plausibility. | No category below `3`; text and layout must be `4+` for a strategic pass. |

Human review rubric:

- `5`: Product-plausible; exact text and labels survive the scenario, motion helps rather than distracts.
- `4`: Minor visual softness or tiny OCR misses, but the page identity is clearly stable.
- `3`: Understandable but not shippable; localized text or layout damage.
- `2`: Major identity loss, label drift, text smear, or distracting artifacts.
- `1`: Scenario failure; page is effectively repainted or unreadable.

## Artifact Schema

Add `eval.json` beside each run's existing `metrics.json` and `quality.json`. Keep existing fields stable, and wrap them with scenario-level results.

```json
{
  "schema_version": "track-c-eval-v0.1",
  "run_id": "20260424T155703Z-c2-lite-text-static-layout-element-frame-scale-1280x736-s4500",
  "created_utc": "2026-04-24T00:00:00Z",
  "commit": "nogit",
  "track": "C",
  "renderer_variant": "stable-latent-feature-grid-element-anchor-layout-text-box-weighted",
  "fixture": {
    "fixture_id": "text-heavy-page",
    "source_image": "outputs/track-c/<run-id>/input.png",
    "source_resolution": [1280, 736],
    "text_boxes": "outputs/track-c/<run-id>/text-boxes.json",
    "prompt_manifest": null
  },
  "config": {
    "train_resolution": "1280x736",
    "frames": 33,
    "fps": 24,
    "motion_mode": "static",
    "video_layout_mode": "element-frame-scale",
    "layout_transform_strength": 0.08,
    "element_scale_ratio": 0.25
  },
  "scenarios": [
    {
      "scenario_id": "frame-scale-moderate",
      "status": "pass",
      "viewport": {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0},
      "output": {"width": 960, "height": 544},
      "stress": {"layout_transform_strength": 0.08, "layout_transform_pan": 0.015},
      "artifacts": {
        "first": "render-960.png",
        "mid": "render-element-mid.png",
        "last": "render-last.png",
        "video": "output.mp4",
        "text_mask": "text-mask.png"
      },
      "metrics": {
        "latency": {
          "render_960_ms": 14.513,
          "render_33_wall_ms": 441.822,
          "encode_ms": 244.547,
          "render_plus_encode_ms": 686.369
        },
        "text": {
          "ocr_token_f1": 0.7321,
          "ocr_char_similarity": 0.1857,
          "min_region_ocr_token_f1": null
        },
        "temporal": {
          "motion_delta": 0.0447,
          "loop_error": 0.0005,
          "temporal_consistency": 0.9921
        },
        "resize_layout": {
          "layout_similarity": 0.99997,
          "anchor_drift_px_p95": null,
          "crop_consistency": null
        },
        "prompt_adherence": {
          "required_text_recall": null,
          "label_attachment_errors": null,
          "critical_fact_errors": null
        }
      },
      "human_review": {
        "reviewer": null,
        "text_readability": null,
        "identity_stability": null,
        "layout_correctness": null,
        "motion_quality": null,
        "artifact_severity": null,
        "prompt_adherence": null,
        "notes": null
      }
    }
  ],
  "summary": {
    "status": "pass",
    "failed_gates": [],
    "best_metric": "render_plus_encode_ms",
    "worst_metric": "text.ocr_token_f1"
  }
}
```

Also emit:

- `eval-summary.md`: one-page run readout with contact sheet links.
- `review.json`: human rubric ratings, kept separate so rerunning automated eval does not overwrite review.
- `scenario-frames/`: sampled first/mid/last/stress PNGs for every scenario.
- `eval-results.tsv`: flattened leaderboard fields for quick comparison across runs.

## Immediate Implementation Plan

1. Create `scripts/track_c/evaluate_run.py` that ingests a run directory, reads `metrics.json`, `quality.json`, `text-boxes.json`, and writes `eval.json` plus `eval-summary.md`.
2. Add `scripts/track_c/eval_scenarios.json` with the current matrix: still resize, crop identity, subtle loop, viewport zoom pulse, moderate/strong frame-scale, element-anchor stress, and responsive squeeze.
3. Extend the Modal runner to tag every output with `scenario_id` and save sampled scenario frames. Keep today's artifact names as compatibility aliases.
4. Replace page-only OCR with per-region scoring: full page, title, body text, labels, small text, diagram captions, and anchor boxes.
5. Add resize/crop consistency scoring by rendering equivalent canonical regions, resampling to a shared size, and comparing SSIM/LPIPS plus OCR.
6. Add temporal scoring over sampled frames from `output.mp4`: OCR min/mean, loop error, text-mask variance, and motion-delta bounds.
7. Add a lightweight human-review template and contact sheet generator so reviewers score the same frames every time.
8. Wire a leaderboard append to `docs/experiments/track-c/eval-results.tsv`, with scenario-level pass/fail instead of one global status.

Near-term acceptance target for C2.5: keep `33` frames plus encode under `1.3s`, beat C2.4 on moderate and strong frame-scale OCR, and show no human-review text/layout score below `3`.
