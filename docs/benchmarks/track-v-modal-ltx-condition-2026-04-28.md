# Track V Modal LTX Condition Probe - 2026-04-28

## Question

Can self-hosted open LTX reproduce the hosted API's useful first/last-frame anchor trick at lower resolution and lower latency?

This is not LTX 2.3. It uses the public Diffusers `LTXConditionPipeline` with `Lightricks/LTX-Video-0.9.7-distilled`, because that path does not require the missing Hugging Face/Gemma token. The probe pins the same source page at frame 0 and the final frame.

## Harness

Script:

```text
scripts/track_v/modal_ltx_condition_probe.py
```

Command shapes:

```bash
tmux new-session -d -s track-v-modal-ltx-condition-probe \
  "cd /Users/dennisonbertram/Develop/flipbook-research && modal run scripts/track_v/modal_ltx_condition_probe.py --max-runs 1 --resolution 768x448 --frames 49 --fps 24 --steps 8 > docs/experiments/track-v/modal-ltx-condition-probe.log 2>&1"
```

```bash
tmux new-session -d -s track-v-modal-ltx-condition-960 \
  "cd /Users/dennisonbertram/Develop/flipbook-research && modal run scripts/track_v/modal_ltx_condition_probe.py --max-runs 1 --resolution 960x544 --frames 49 --fps 24 --steps 8 > docs/experiments/track-v/modal-ltx-condition-960.log 2>&1"
```

Results append to:

```text
docs/experiments/track-v/modal-ltx-condition-results.tsv
```

## Results

| Run | Shape | Wall | Model | Encode | Peak VRAM | Text | Layout | Motion | Status |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `20260428T003648Z-modal-ltx-condition-anchor-s8-seed0-768x448` | 49f, 24fps, 8 steps, `768x448` | `6.492s` | `5.458s` | `0.454s` | `36.59GB` | `0.4604` | `0.9999` | `0.0017` | quality fail |
| `20260428T003851Z-modal-ltx-condition-anchor-s8-seed0-960x544` | 49f, 24fps, 8 steps, `960x544` | `9.766s` | `8.812s` | `0.597s` | `36.82GB` | `0.2184` | `0.9999` | `0.0017` | quality fail |

The contact sheets are visually stable and stay in page coordinates. They do not show the free-run LTX page-turn/crop collapse. But the text is softened and mutated, and the motion is nearly zero. Higher resolution made the OCR proxy worse, not better, likely because the model still repaints small glyphs while the input OCR sees more dense text.

## Read

This answers the immediate Modal question:

- Self-hosted old LTX can be faster than hosted LTX: `6.5-9.8s` wall versus the hosted 2s anchor at about `14.7s`.
- It does not pass dense text quality.
- It uses `36-37GB` VRAM on L40S for this small run.
- It creates almost no useful motion.
- It is lower resolution than the hosted pass, and hosted gives better dense-text OCR at 1080p.

So old open LTX with first/last condition is not the path for dense pages. It is also not a compelling background enhancement path if the output is near-static but text-damaged.

## Decision

For dense pages, stop spending time on old self-hosted LTX. The remaining LTX self-host question is specifically LTX-2.3/FP8/one-stage or keyframe interpolation, which requires a Hugging Face token with access to the required text encoder assets.

The product path remains:

1. deterministic Track B-style immediate motion for realtime response;
2. hosted 2s LTX 2.3 Fast anchored clips only as background enhancement when they pass gates;
3. future Modal LTX-2.3 only after `HF_TOKEN` is available, and only as a bounded `<=5s` warm probe.

