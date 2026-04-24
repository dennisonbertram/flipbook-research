# Track A Benchmark Harness

This is the runnable starting point for Track A.

The benchmark owns:

- fixture/input handling
- fixed resolution and frame count
- MP4 encoding
- artifact layout
- metrics JSON
- optional experiment TSV logging

Recipes under `recipes/` own the model-layer experiment.

## Lower-Bound Run

```bash
python3 scripts/track_a/benchmark.py \
  --recipe stub_freeze \
  --resolution 960x544 \
  --append-results
```

This produces:

```text
outputs/track-a/<run-id>/
  input.png
  output.mp4
  metrics.json
  preview.jpg
```

The `stub_freeze` recipe is not a quality baseline. It measures the fixed-cost floor for resizing, frame handling, and MP4 encoding.

## LTX Diffusers Run

The experimental `ltx_diffusers_i2v` recipe follows the current Diffusers LTX image-to-video API shape.

```bash
python3 scripts/track_a/benchmark.py \
  --recipe ltx_diffusers_i2v \
  --model-id Lightricks/LTX-Video \
  --device cuda \
  --dtype bfloat16 \
  --resolution 960x544 \
  --frames 33 \
  --steps 4 \
  --guidance-scale 1.0 \
  --append-results
```

Cold model setup is measured separately as `setup_ms_excluded` and excluded from the Track A wall-clock score.

## Modal Overnight Loop

Use this when the local machine does not have an NVIDIA GPU. It builds a Modal GPU container, keeps the LTX pipeline warm, runs a small step/resolution matrix until the local morning deadline, and writes local artifacts after each attempt.

```bash
tmux new-session -d -s track-a-overnight \
  "cd /Users/dennisonbertram/Develop/flipbook-research && modal run scripts/track_a/modal_ltx_benchmark.py --until 08:00 > docs/experiments/track-a/overnight-modal-ltx.log 2>&1"
```

Check progress:

```bash
tmux capture-pane -pt track-a-overnight
tail -f docs/experiments/track-a/overnight-modal-ltx.log
```

## Text Quality Watcher

The Modal loop logs latency first. Run the local quality watcher alongside it to OCR-check completed videos and write `quality.json` per run plus `docs/experiments/track-a/quality.tsv`.

```bash
tmux new-session -d -s track-a-quality \
  "cd /Users/dennisonbertram/Develop/flipbook-research && python3 scripts/track_a/evaluate_text_quality.py --watch --until 08:00 --interval 20 > docs/experiments/track-a/text-quality-watch.log 2>&1"
```

The score is a proxy: OCR similarity against the input image plus a low-resolution layout similarity check. Manual review is still required for any candidate winner.
