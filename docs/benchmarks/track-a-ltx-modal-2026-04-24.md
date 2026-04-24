# Track A LTX Modal Benchmark

Date: 2026-04-24

## Purpose

Start the real Track A benchmark loop on GPU using Modal and Diffusers LTX image-to-video.

The target remains:

```text
33 frames generated + decoded/composited + encoded in <= 1.3s
```

## Harness

Local fixed-cost floor:

```text
python3 scripts/track_a/benchmark.py --recipe stub_freeze --resolution 960x544 --append-results
```

Modal LTX loop:

```text
modal run scripts/track_a/modal_ltx_benchmark.py --until 08:00
```

The Modal runner keeps the LTX pipeline warm, runs a step/resolution matrix, writes artifacts under `outputs/track-a/`, and appends compact rows to:

```text
docs/experiments/track-a/results.tsv
```

## Early Results

The local fixed-cost lower bound at `960x544` was:

```text
wall_time_ms: 416.229
encode_ms:    374.419
```

Early Modal LTX observations:

| Resolution | Steps | Result Shape |
| --- | ---: | --- |
| `768x448` | 2-4 | Passes comfortably, roughly `0.88-1.00s` in early runs. |
| `896x512` | 2-4 | Passes or sits near the gate; 6-8 steps become near misses. |
| `960x544` | 2-3 | Passes in some warm runs, roughly `1.13-1.29s`. |
| `960x544` | 4+ | Near miss, usually above `1.3s`. |
| `1024x576` | 2+ | Near miss, roughly `1.3-1.9s`. |
| `1280x736` | 2+ | Near miss, roughly `2.0-2.5s`. |

One-step runs crashed in the Diffusers FlowMatch scheduler, so they were removed from the overnight loop.

## Quality Note

The first visual inspection of `960x544` passing outputs showed text degradation. This means speed passes are not yet product passes.

An automated local quality watcher is now running alongside the Modal loop:

```text
scripts/track_a/evaluate_text_quality.py
```

It extracts first/middle/last frames, runs Tesseract OCR, compares OCR text against the input image, computes a low-resolution layout similarity proxy, and writes:

```text
docs/experiments/track-a/quality.tsv
outputs/track-a/<run-id>/quality.json
```

Early OCR-proxy results confirm the visual issue: passing LTX clips can meet the latency gate while badly damaging text.

Track A now needs quality scoring, especially:

- text readability
- layout stability
- loop boundary stability
- motion intentionality

## Current Run

The overnight tmux session is:

```text
track-a-overnight
```

The live log is:

```text
docs/experiments/track-a/overnight-modal-ltx.log
```

## Sources

- Diffusers LTX-Video docs: https://huggingface.co/docs/diffusers/api/pipelines/ltx_video
