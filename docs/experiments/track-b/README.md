# Track B Experiments

Track B is the hybrid product path: preserve the source page image, protect text/linework, add deterministic motion to safe regions, and optionally use video models later as background enhancement.

The first runner is:

```bash
python3 scripts/track_b/hybrid_animation.py --help
```

The main result table is `results.tsv`.

## Fastest Path

The current fastest reproducible MP4 path is `--motion-mode ffmpeg-drift`.
It matches the hosted Kling reference more closely than the earlier lighting-only pass because it animates the whole plate like a subtle camera drift instead of only changing illumination.

Best current rows:

- Full 121-frame, 5.04s clip from prepared 960x540 input: `20260427T004208Z-track-b-hybrid-naturalist-ffmpeg-drift-121-klingish-prefit-copy-960x540`, 196.438 ms wall time, motion score 0.0169.
- Short 33-frame, 1.375s clip from prepared 960x540 input: `20260427T004228Z-track-b-hybrid-naturalist-ffmpeg-drift-33-klingish-prefit-copy-960x540`, 123.498 ms wall time, motion score 0.0169.

The hosted Kling reference is `outputs/track-v/20260425T144658Z-fal-kling-fal-kling-naturalist-etching-960x540-960x540/output.mp4`: 121 frames, 5.041667s duration, 47176.049 ms API wall time, motion score 0.0149.

## Sweep Driver

`scripts/track_b/ffmpeg_drift_sweep.py` prepares page plates once, then reruns the `ffmpeg-drift` product path with `--reuse-input --skip-mask --skip-ocr`. This measures the part of Track B that would sit on the realtime UX path rather than the slower research artifacts around it.

Run profiles:

- `quick`: smoke test over naturalist, canal, and dense-text pages.
- `focused`: current default serious run over 10 page families.
- `overnight`: larger variance grid.

Sweep outputs live in `docs/experiments/track-b/sweeps/`.

Use `--drift-fill overscan` for a targeted sweep when a full-bleed illustration shows edge padding. Keep `pad` for document-like plates unless manual review shows a gutter artifact.
