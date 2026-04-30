# Track B Hybrid Animation

Track B treats the generated page image as the source of truth and animates only safe regions around protected text and linework.

```bash
python3 scripts/track_b/hybrid_animation.py \
  --input fixtures/track-a/text-heavy-page.png \
  --label dense-text-hybrid \
  --resolution 960x544 \
  --append-results
```

Outputs are written to `outputs/track-b/<run-id>/` and compact rows are appended to `docs/experiments/track-b/results.tsv`.

For the fastest Kling-style "living plate" motion, use the ffmpeg path. It synthesizes a tiny closed-loop camera drift and encodes in one pass:

```bash
python3 scripts/track_b/hybrid_animation.py \
  --input outputs/track-v/20260425T144658Z-fal-kling-fal-kling-naturalist-etching-960x540-960x540/input.png \
  --label naturalist-ffmpeg-drift-121-klingish-prefit-copy \
  --resolution 960x540 \
  --motion-mode ffmpeg-drift \
  --frames 121 \
  --fps 24 \
  --pan-x 2 \
  --pan-y 1 \
  --crf 23 \
  --skip-text-gate \
  --append-results
```

Use `fast-drift` when you need numpy-side frame access for later compositing experiments. Use `ffmpeg-drift` when the goal is the fastest reproducible MP4.

`ffmpeg-drift` supports two edge strategies:

- `--drift-fill pad`: fastest and best for page plates with margins.
- `--drift-fill overscan`: slightly enlarge/crop the plate to avoid exposed edges on full-bleed illustrations; this can measure as more motion because the clip starts from a tiny crop.

To sweep the ffmpeg path across page families and motion settings:

```bash
python3 scripts/track_b/ffmpeg_drift_sweep.py --profile quick
```

Profiles:

- `quick`: naturalist/canal/dense text smoke test.
- `focused`: 10 page families, 3 durations, 3 drift amplitudes, 3 CRFs, 2 repeats.
- `overnight`: larger grid for deeper variance checks.

Sweep TSV and Markdown summaries are written under `docs/experiments/track-b/sweeps/`.
