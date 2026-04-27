# Track B Hybrid Fastest Probe - 2026-04-27

## Question

Can Track B animate more like the hosted Kling naturalist plate while getting as close as possible to realtime or faster-than-realtime generation?

Reference:

- `outputs/track-v/20260425T144658Z-fal-kling-fal-kling-naturalist-etching-960x540-960x540/output.mp4`
- 121 frames at 24 fps, 5.041667s duration
- Hosted API wall time: 47176.049 ms
- Quality proxies: layout 0.9990, motion 0.0149, loop error 0.0121

## Result

The gate is not plausible for hosted generative video, but it is easy for deterministic Track B motion.

Best current reproducible Track B run:

- `outputs/track-b/20260427T004208Z-track-b-hybrid-naturalist-ffmpeg-drift-121-klingish-prefit-copy-960x540/output.mp4`
- Mode: `ffmpeg-drift`
- Input: already prepared 960x540 plate
- 121 frames at 24 fps, 5.041667s duration
- Wall time before evaluation: 196.438 ms
- ffmpeg synth+encode time: 152.206 ms
- Effective generated fps: 616.0
- Quality proxies: layout 0.9997, motion 0.0169, loop error 0.0012

With product-path switches enabled (`--reuse-input --skip-mask --skip-ocr`), the same 121-frame setting measured 179.312 ms on a follow-up run. This removes mask generation and OCR from the realtime path while preserving frame extraction and quality checks after the timed section.

Short immediate-response run:

- `outputs/track-b/20260427T004228Z-track-b-hybrid-naturalist-ffmpeg-drift-33-klingish-prefit-copy-960x540/output.mp4`
- 33 frames at 24 fps, 1.375s duration
- Wall time before evaluation: 123.498 ms
- ffmpeg synth+encode time: 78.556 ms
- Quality proxies: layout 0.9997, motion 0.0169, loop error 0.0012

## Interpretation

This is not re-layout and not generative video. It is a stable page plate with a tiny closed-loop camera drift, which is why it can be hundreds of times faster than the hosted Kling call.

That makes it a useful product path for immediate motion:

- Show deterministic Track B motion instantly.
- Keep hosted or self-hosted video generation as an optional background enhancement for cases where illustration-rich generative motion matters.
- Treat "re-layout the image" as a separate research problem; this Track B path deliberately preserves the page image.

## Current Recommendation

Use `ffmpeg-drift` as the Track B baseline for Kling-like page liveness. Keep the motion amplitude near `--pan-x 2 --pan-y 1` for this plate; the earlier `--pan-x 6 --pan-y 3` run was fast but too visibly mechanical, with motion score 0.0439 versus Kling's 0.0149.

Run `scripts/track_b/ffmpeg_drift_sweep.py --profile focused` to measure the speed/quality frontier across page families.

## Focused Sweep

Focused sweep:

- TSV: `docs/experiments/track-b/sweeps/ffmpeg-drift-sweep-20260427T022749Z.tsv`
- Summary: `docs/experiments/track-b/sweeps/ffmpeg-drift-sweep-20260427T022749Z.md`
- Rows: 540
- Passed rows: 414
- All 126 quality failures came from `--pan-x 1 --pan-y 0.5`, which was too subtle for the min-motion gate on some page families.

Median 121-frame wall time by family, using only passing runs:

| family | p50 wall ms | p95 wall ms |
| --- | ---: | ---: |
| article | 102.831 | 110.538 |
| canal | 194.435 | 273.876 |
| dashboard | 99.466 | 101.324 |
| dense-text | 107.174 | 133.869 |
| diagram | 99.147 | 111.603 |
| illustration | 106.523 | 134.081 |
| map-labels | 103.303 | 119.416 |
| microtext | 107.905 | 117.272 |
| naturalist | 172.472 | 223.427 |
| product-grid | 101.790 | 105.490 |

Best 121-frame candidate per core family:

| family | setting | median wall ms | motion | layout | loop |
| --- | --- | ---: | ---: | ---: | ---: |
| naturalist | `pan=2,1 crf=28` | 192.399 | 0.0169 | 0.9997 | 0.0016 |
| canal | `pan=1,0.5 crf=28` | 175.707 | 0.0131 | 0.9999 | 0.0020 |
| dense-text | `pan=2,1 crf=23` | 112.684 | 0.0118 | 0.9996 | 0.0007 |

## Resolution Frontier

Targeted resolution sweep:

- `docs/experiments/track-b/sweeps/ffmpeg-drift-sweep-20260427T023312Z-768x432.tsv`
- `docs/experiments/track-b/sweeps/ffmpeg-drift-sweep-20260427T023312Z-640x360.tsv`
- `docs/experiments/track-b/sweeps/ffmpeg-drift-sweep-20260427T023312Z-480x270.tsv`

Core-family median for `pan=2,1 crf=23`:

| resolution | 33-frame wall ms | 121-frame wall ms |
| --- | ---: | ---: |
| 960x540 | 87.030 | 187.164 |
| 768x432 | 66.985 | 118.836 |
| 640x360 | 56.260 | 92.447 |
| 480x270 | 47.043 | 69.799 |

Recommendation:

- Use 960x540 when the output is an inspectable saved clip.
- Use 640x360 for the fastest still-useful generated preview clip.
- Use 480x270 only as an ultra-fast motion placeholder; it is fast, but likely too small for text/detail inspection.

## Edge Fill

`ffmpeg-drift` now has `--drift-fill pad` and `--drift-fill overscan`.

- `pad` remains the baseline for page plates because it preserves layout metrics and is fastest.
- `overscan` avoids edge gutters on full-bleed/color illustrations, but it introduces a slight zoom crop. In a canal test at 960x540/121 frames, `overscan pan=1,0.5` measured 184.703 ms, layout 0.9975, motion 0.0246.

Overscan core sweep:

- TSV: `docs/experiments/track-b/sweeps/ffmpeg-drift-sweep-20260427T023312Z-overscan-core.tsv`
- Rows: 54
- Passed rows: 54
- Naturalist best close-to-Kling 121-frame setting: `pan=1,0.5`, 170.722 ms, motion 0.0143, layout 0.9988.
- Canal best close-to-Kling 121-frame setting still measured motion 0.0246, so overscan is too active for that illustration family.
- Dense-text best close-to-Kling 121-frame setting: `pan=2,1`, 113.010 ms, motion 0.0178, layout 0.9988.

Conclusion: keep `pad` as the general Track B baseline. Use `overscan` only when visual review shows an exposed gutter and accept that the amplitude may need to be halved.
