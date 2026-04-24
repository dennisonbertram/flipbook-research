# Track A Autoresearch Program

## Purpose

Turn Track A from a one-off LTX benchmark into a repeatable model-research loop.

The goal is not to make the serving stack prettier. The goal is to discover whether a specialized image-to-video model recipe can produce:

```text
static page image -> 33 browser-playable frames at 24fps in <= 1.3s
```

with stable text and intentional motion.

## What We Borrow From `autoresearch`

Karpathy's `autoresearch` pattern is useful because it makes model improvement into a tight experimental loop:

- one small editable code surface
- fixed benchmark budget
- fixed evaluation metric
- first run is always the baseline
- every experiment is logged
- keep improvements, discard regressions
- prefer simpler changes when metrics are tied

For this project, the most important idea is the research harness, not the specific nanochat model.

## Track A Translation

### Fixed Problem

Each experiment must produce the same artifact shape:

```text
input:  one representative text-heavy static page image
output: 33 frames, 24fps, browser-playable MP4/fMP4
```

The first resolution matrix remains:

```text
768x432
960x544
1280x736
```

The first pass should optimize `960x544`, then verify whether the result scales down and up.

### Read-Only Surface

When implementation exists, keep these pieces fixed during Track A autoresearch runs:

- benchmark harness
- input image set
- metric computation
- encode path used by the benchmark
- output artifact contract
- baseline model checkpoint
- result parser

Changing these makes experiments incomparable.

### Editable Surface

Keep the editable research surface intentionally small. A good target is one model-recipe file that owns:

- model variant selection
- denoising step schedule
- guidance settings
- latent resolution strategy
- attention/window strategy
- precision and quantization choices
- optional adapter/student weights
- any Track A-specific temporal or loop objective

Avoid letting the agent freely edit the harness, input data, or reporting code.

## Metrics

The primary metric is wall-clock segment production:

```text
wall_time_ms
```

The keep/discard decision must also consider quality gates:

```text
text_readability_pass
layout_stability_pass
motion_intentionality_pass
loop_boundary_pass
```

Every run should record:

```text
run_id
commit
input_set
resolution
frames
fps
steps
model_ms
denoise_ms
decode_ms
encode_ms
wall_time_ms
effective_generated_fps
peak_vram_gb
text_score
layout_score
motion_score
loop_error
status
description
```

Store the tabular log as TSV so descriptions can contain commas:

```text
docs/experiments/track-a/results.tsv
```

Suggested header:

```text
run_id	commit	resolution	wall_time_ms	model_ms	decode_ms	encode_ms	peak_vram_gb	text_score	layout_score	motion_score	loop_error	status	description
```

## Keep / Discard Rules

Keep a change when one of these is true:

- `wall_time_ms <= 1300` and all quality gates pass.
- `wall_time_ms` improves by at least `15%` with no quality regression.
- quality improves meaningfully while staying under the `3000ms` near-miss threshold.
- complexity decreases while latency and quality are effectively unchanged.

Discard a change when any of these is true:

- text mutates, shimmers, or becomes hard to read.
- the page layout melts or drifts.
- latency regresses without a quality win.
- the change only helps by modifying the benchmark.
- it adds fragile complexity for a tiny metric gain.

Log crashes instead of hiding them.

## First Run

The first run is always the baseline:

```text
model:       LTX distilled FP8
resolution:  960x544
frames:      33
fps:         24
steps:       4
guidance:    off / guidance_scale=1
prompt:      subtle continuous loop, gentle parallax, small ambient motion, preserve text and diagram layout
```

Record it before trying any intervention. The baseline is the anchor for every later keep/discard call.

## Model Research Backlog

These are ordered from least invasive to most like a purpose-built model.

1. Step schedule search

   Test `1`, `2`, `3`, `4`, and `6` step schedules at fixed resolution. The goal is to learn the smallest number of useful denoising passes before investing in training.

2. Guidance-free specialization

   Remove runtime guidance and bake the desired motion prior into the model recipe. A fixed Flipbook-style motion prompt should not require extra inference passes.

3. Latent token sparsity

   Preserve low-motion regions, especially text and diagrams, by reducing or skipping updates for stable latent regions. This keeps Track A full-frame at the interface while making the model do less full-frame work internally.

4. Motion-residual student

   Train a small student to predict temporal residuals or latent deltas from a still image instead of regenerating every pixel of every frame.

5. Teacher-distilled short-loop student

   Use a slower high-quality LTX teacher to generate pseudo-label clips, then distill a student for `33` frame subtle loops. The target distribution is narrow: static educational pages, ambient motion, stable text.

6. Low-res latent generation plus temporal/detail upsampler

   Generate motion at a smaller latent grid, then use a lightweight model to restore display detail without changing text.

7. Loop-aware objective

   Add a training/evaluation objective that penalizes discontinuity between the last and first frames. Flipbook's public client uses loop-oriented settings, so a non-loop-aware model is probably wasting capacity.

8. Text-preservation loss

   Add OCR or embedding-based checks during evaluation, and eventually training, so a model that wins latency by damaging text cannot be selected.

## Agent Loop

Use a dedicated branch per run:

```text
track-a-autoresearch/<date>-<gpu>
```

Loop:

1. inspect current best result
2. make one scoped model-recipe change
3. commit the change
4. run the benchmark with stdout/stderr redirected to a log
5. parse metrics
6. append one row to `docs/experiments/track-a/results.tsv`
7. keep the commit if it improves the score under the rules
8. revert to the previous best if it regresses

The branch should only advance through kept experiments.

## Complexity Criterion

If two runs are tied, prefer the simpler model. For this project, simplicity matters because the final system has to be streamed, debugged, and eventually ported to a production GPU path.

A small latency win is not worth a brittle architecture if it makes text stability harder to reason about.

## Sources

- Karpathy `autoresearch` repository: https://github.com/karpathy/autoresearch
- `program.md` experiment loop: https://raw.githubusercontent.com/karpathy/autoresearch/master/program.md
