# Neural Canvas Eval Framework

## Purpose

The eval must answer the product-level question, not just the demo question:

```text
Can one learned world render stable pixels for changing viewports, time, and resolution?
```

For this project, the hard thing is identity under interaction. A page that looks good once but rewrites text during motion is a failure, even if it is fast. A page that preserves text by overlaying DOM text may be useful as a product fallback, but it is not evidence for the pure neural canvas thesis.

## Eval Contract

Every candidate renderer should expose the same conceptual API:

```json
{
  "canvas_id": "fixture-or-world-id",
  "viewport": {
    "x": 0.0,
    "y": 0.0,
    "width": 1.0,
    "height": 0.5667
  },
  "output": {
    "width": 960,
    "height": 544
  },
  "time": 0.0,
  "interaction_state": {}
}
```

The evaluator should request:

- still renders at multiple resolutions
- crop and zoom renders
- 33-frame clips at `24fps`
- layout/resize stress clips
- optionally, world edits once the compiler exists

## Fixture Tiers

### Tier 0: Dev Fixture

One known text-heavy page image.

Purpose:

- quick iteration
- regression checks
- direct comparison to C0-C2.4

### Tier 1: Identity Suite

Five to seven fixtures that stress different identity types:

- dense article page
- dashboard/table with many numbers
- labeled diagram
- product-card grid
- map or spatial label page
- low-text illustration
- adversarial small-font page

Purpose:

- prevent single-page overfitting
- discover which visual classes fail first
- separate text failure from general layout failure

### Tier 2: Generated Worlds

Prompt or structured input compiled into a canvas by a model.

Purpose:

- test the full compiler path
- evaluate prompt adherence and controllability
- compare teacher and student compilers

## Scenario Matrix

Each fixture should run the same scenarios when possible.

| Scenario | Question | First Metric |
| --- | --- | --- |
| `still-full-resize` | Can the canvas reconstruct the world at `512`, `960`, `1280`, and optionally `1536` widths? | OCR/layout/perceptual |
| `crop-identity` | Can viewport queries avoid repainting? | crop consistency |
| `shifted-crop` | Are labels stable near boundaries? | crop OCR/layout |
| `subtle-motion-loop` | Can time add life without drift? | temporal stability |
| `viewport-zoom-pulse` | Does text survive scale changes? | per-frame OCR |
| `frame-scale-moderate` | Can the page reframe under the current C2.2/C2.3 stress level? | stress OCR/layout |
| `frame-scale-strong` | Where does resize/reposition identity break? | stress OCR/layout |
| `responsive-squeeze` | Does nonuniform aspect pressure behave like a coherent world? | region OCR/layout |
| `element-anchor-stress` | Can identity-bearing regions move by constraints while pixels still come from the canvas? | anchor drift |
| `loop-boundary` | Is the segment streamable? | loop error |

Future compiler scenarios:

| Scenario | Question | First Metric |
| --- | --- | --- |
| `prompt-adherence-c3` | Did the compiled world include required strings, facts, labels, and relationships? | required-fact recall |
| `single-update` | Can one fact or selection change without rewriting unrelated identity? | localized diff accuracy |

## Metrics

### Latency

Record:

```text
compile_ms
first_frame_ms
render_960_ms
render_33_wall_ms
encode_ms
segment_wall_ms
effective_generated_fps
peak_vram_gb
model_calls_per_frame
pixels_per_second
```

Primary live gate:

```text
segment_wall_ms = render_33_wall_ms + encode_ms <= 1300
```

Compile time is tracked separately. It is allowed to be slow while we are proving the renderer, but it becomes central once the world compiler exists.

### Text Identity

Record per still and per video frame:

```text
ocr_token_f1
ocr_char_similarity
word_error_rate
line_count_delta
text_box_iou
small_text_score
min_frame_ocr
mean_frame_ocr
ocr_stability_stddev
```

Why per-frame matters:

```text
mean OCR can hide one catastrophic frame
min OCR catches flicker, melting, and resize peaks
```

### Layout Identity

Record:

```text
ssim_or_dssim
edge_similarity
layout_region_iou
crop_consistency
resize_consistency
anchor_position_error
```

The strongest consistency tests compare two render queries of the same world:

```text
render full -> crop in image space
render crop directly -> compare

render 1280 -> downsample to 960
render 960 directly -> compare
```

### Temporal Quality

Record:

```text
motion_delta
loop_error
temporal_flicker
optical_flow_smoothness
identity_drift
```

Motion must be visible enough to matter, but not so large that the system wins by smearing text. Keep a minimum motion threshold and a separate identity threshold.

### Prompt Or World Adherence

Once the compiler exists, record:

```text
required_facts_present
forbidden_facts_absent
object_count_score
style_match_score
human_adherence_rating
```

This is intentionally absent from early C0-C2 renderer-only runs unless the input fixture itself is generated by the system under test.

### Model-Rendered Pixel Purity

Record how the pixels were produced:

```text
pixel_source_class:
  neural-full-frame
  neural-canvas-query
  neural-canvas-query-with-symbolic-supervision
  neural-canvas-query-plus-compositor
  DOM-or-CSS-overlay

model_rendered_pixel_ratio
symbolic_overlay_pixel_ratio
hand_authored_layout_dependency
```

This does not ban practical product tricks. It keeps the research claim honest.

Text-shaped masks sit in the middle of this scale. They are allowed for C2.5 if the mask only decides where to query or blend model-rendered RGB. They are not acceptable as a source-pixel safety pass. The evaluator should report this as:

```text
pixel_source_class = neural-canvas-query-with-symbolic-supervision
model_rendered_pixel_ratio = 1.0
symbolic_overlay_pixel_ratio = 0.0
```

## Scorecard

Use a two-stage score.

First, hard gates:

```text
segment_wall_ms <= 1300
motion_delta >= scenario_min_motion_delta
static OCR >= fixture_min_static_ocr
min video OCR >= scenario_min_video_ocr
loop_error <= scenario_max_loop_error
```

Then rank passing runs by:

```text
identity_score = 0.35 * text_identity
               + 0.25 * layout_identity
               + 0.20 * temporal_stability
               + 0.10 * resize_crop_consistency
               + 0.10 * human_rating
```

Report latency separately. Do not hide speed/quality tradeoffs behind one scalar.

## Human Review Rubric

Human review should be short and repeatable:

```text
Text exactness:          1-5
Layout stability:        1-5
Motion intentionality:   1-5
Resize/reframe quality:  1-5
Visual sharpness:        1-5
Model-rendered purity:   1-5
Overall demo credibility:1-5
```

Reviewer prompts:

- Did any text become unreadable or change meaning?
- Did labels detach from the things they label?
- Did motion feel like rendering the same world or repainting a new one?
- Did resize/reposition feel like a coherent camera/layout operation?
- Would a viewer trust this as a live interface for dense information?

## Artifact Schema

Each run should write a normalized `eval.json` beside the existing `metrics.json` and `quality.json`:

```text
outputs/<track>/<run_id>/
  metrics.json
  quality.json
  eval.json
  eval-summary.md
  review.json
```

It should also preserve visual artifacts:

```text
outputs/<track>/<run_id>/
  input.png
  output.mp4
  contact-sheet.jpg
  metrics.json
  quality.json
  eval-report.md
  frames/
    frame-000.png
    frame-016.png
    frame-032.png
  ocr/
    input.json
    frame-000.json
    frame-016.json
    frame-032.json
  comparisons/
    crop-direct-vs-full.json
    resize-1280-vs-960.json
```

Each `eval.json` should wrap run-level metadata and scenario-level results. Keep `metrics.json` stable for backwards compatibility.

```json
{
  "schema_version": "track-c-eval-v0.1",
  "run_id": "string",
  "commit": "string",
  "track": "track-c",
  "renderer_family": "stable-latent-feature-grid",
  "fixture_id": "text-heavy-page-v1",
  "pixel_source_class": "neural-canvas-query",
  "model_rendered_pixel_ratio": 1.0,
  "scenarios": [
    {
      "scenario_id": "frame-scale-strong",
      "resolution": "960x544",
      "frames": 33,
      "fps": 24,
      "status": "pass|near_miss|quality_fail|latency_fail|crash",
      "metrics": {
        "compile_ms": 0.0,
        "render_33_wall_ms": 0.0,
        "encode_ms": 0.0,
        "segment_wall_ms": 0.0,
        "peak_vram_gb": null,
        "ocr_token_f1_min": 0.0,
        "ocr_token_f1_mean": 0.0,
        "layout_similarity": 0.0,
        "resize_consistency": 0.0,
        "crop_consistency": 0.0,
        "motion_delta": 0.0,
        "loop_error": 0.0
      },
      "artifacts": {
        "video": "output.mp4",
        "mid_frame": "render-element-mid.png",
        "text_mask": "text-mask.png"
      }
    }
  ],
  "summary": {
    "status": "pass|near_miss|quality_fail|latency_fail|crash",
    "failed_gates": []
  }
}
```

## Immediate Implementation Plan

### E0: Existing Output Evaluator

Build a script that consumes an existing run directory and emits a normalized eval report.

Input:

```text
outputs/track-c/<run-id>/
```

Output:

```text
metrics.normalized.json
eval-report.md
contact-sheet.jpg
```

This avoids rerunning Modal for every eval iteration.

### E1: Scenario Runner

Wrap the Track C Modal script with named scenarios:

```text
static
subtle-motion
moderate-zoom
moderate-frame-scale
strong-frame-scale
responsive-squeeze
aspect-ratio-sweep
```

The runner should append to:

```text
docs/experiments/track-c/eval-results.tsv
```

### E2: Fixture Suite

Add two new fixtures before optimizing further:

```text
dashboard/table
labeled diagram
```

The eval should fail loudly if a model only works on the current text-heavy page.

### E3: C2.4 Baseline Report

Re-score the existing C2.4 output as the named baseline:

```text
baseline: c24-element-frame-scale
moderate stress: OCR 0.7321
strong stress:   OCR 0.4124
```

### E4: C2.5 Acceptance Gate

C2.5 should be accepted only if it beats C2.4 on one of:

```text
same OCR with lower render time
higher strong-stress OCR with segment_wall_ms <= 1300
less patch artifacting under human review
better min-frame OCR, not only mid-frame OCR
```

Initial C2.5 target:

```text
33 frames + encode <= 1.3s
moderate frame-scale OCR > 0.7321
strong frame-scale OCR > 0.4124
no human review text/layout category below 3
```

## Important Non-Goal

Do not optimize toward a hidden DOM layout engine. Symbolic text, OCR boxes, and anchors are allowed as supervision, diagnostics, or compiler-side state. They should not become the thing that paints final pixels in the core Track C claim.
