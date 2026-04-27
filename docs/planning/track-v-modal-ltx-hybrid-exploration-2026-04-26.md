# Track V Modal LTX-2.3 And Hybrid Product Path

Date: 2026-04-26

## Short Read

Self-hosting LTX on Modal is the only plausible way to beat the hosted `17-22s` LTX API timing, but LTX-2.3 is materially heavier than the older Diffusers LTX path we already tested. It is worth one bounded H100/A100 probe, not a long optimization loop yet.

The hybrid product path is the stronger near-term product answer: generate immediate deterministic motion from the source page, preserve text by construction, and run LTX only as a background enhancement for illustration-rich pages.

## What We Know Locally

The existing old-LTX Modal runner, [modal_ltx_benchmark.py](/Users/dennisonbertram/Develop/flipbook-research/scripts/track_a/modal_ltx_benchmark.py), already proved the speed side at lower resolution:

| Shape | Prior result |
| --- | --- |
| `768x448`, 2-4 steps | roughly `0.88-1.00s` warm |
| `896x512`, 2-4 steps | pass or near gate |
| `960x544`, 2-3 steps | sometimes `1.13-1.29s` |
| `1280x736`, 2+ steps | roughly `2.0-2.5s` |

But those speed passes were not product passes: dense text was damaged. That result is still the main warning for every full-frame LTX plan.

The hosted official LTX API result gives the current external baseline:

| Model | Shape | Time | Quality |
| --- | --- | ---: | --- |
| `ltx-2-3-fast` official API | 6s / 144 frames / 1080p dense page | `17.400s` | quality fail |
| `ltx-2-3-fast` official API | 6s / 144 frames / 1080p naturalist plate | `22.081s` | visual pass |
| `ltx-2-fast` official API | 6s / 153 frames / 1080p dense page | `36.783s` | quality fail |

## Modal LTX-2.3 Reality Check

LTX-2.3 native self-hosting is likely an H100/A100-80 job for serious testing:

- LTX docs list minimum `32GB+` VRAM and recommend `A100 (80GB)` or `H100`.
- Modal supports `L40S`, `A100-80GB`, `H100`, `H200`, and larger GPUs. For benchmarking, use `H100!` to avoid automatic H200 upgrades; for product exploration, `H100` is fine.
- Modal’s LTX example shows the right deployment pattern: Modal Volumes for Hugging Face/model caches, warm `@modal.cls` containers, and model load in `@modal.enter()`.

Hugging Face metadata checked on 2026-04-26:

| Asset | Size / access note |
| --- | ---: |
| `Lightricks/LTX-2.3` distilled checkpoint | `46.15 GB` |
| `Lightricks/LTX-2.3-fp8` distilled checkpoint | `29.53 GB` |
| spatial upscaler | about `1.0 GB` |
| distilled LoRA for two-stage full pipeline | `7.61 GB` |
| `google/gemma-3-4b-it` | gated/manual, about `8.64 GB` selected model files |
| `google/gemma-3-12b-it` | gated/manual, about `24.41 GB` selected model files |

We have an LTX API key now, but we do not yet have `HF_TOKEN` / `HUGGINGFACE_HUB_TOKEN`. If the native pipeline needs local Gemma, this blocks a clean self-host run until a Hugging Face token with Gemma access is available. LTX Desktop can use the LTX API key for cloud text encoding, but the native `ltx-pipelines` Python path documents local Gemma paths, so do not assume the API key alone is enough.

## Which LTX-2.3 Pipeline To Try

Start with `DistilledPipeline`:

- It is documented as the fastest inference path.
- It uses the distilled model and predefined sigma schedules: 8 stage-1 sigmas and 4 stage-2 sigmas.
- It supports image conditioning.
- It still requires a spatial upsampler and Gemma root.

Second probe: `TI2VidOneStagePipeline`:

- Single-stage, no upsampling, image-conditioned.
- Faster in principle.
- Docs call it educational/prototyping and lower quality, so it is a speed boundary, not a likely product candidate.

Only try production `TI2VidTwoStagesPipeline` / HQ after a fast path gives a useful quality signal. Full two-stage is more likely to improve naturalist/illustration quality than dense text.

## Bounded Modal Experiment

Goal: decide if self-hosting has a path below hosted latency without pretending it solves text.

Minimum setup:

1. Get `HF_TOKEN` with access to the needed Gemma repo.
2. Create a Modal secret for the Hugging Face token.
3. Create Modal volumes for model weights and compiler/cache artifacts.
4. Build a new script, not a mutation of Track A old LTX:
   `scripts/track_v/modal_ltx23_probe.py`

Probe matrix:

| Probe | GPU | Pipeline | Shape | Success bar |
| --- | --- | --- | --- | --- |
| A | `H100!` | Distilled FP8 | `768x512`, 65 frames | returns valid clip, logs model/decode/encode time |
| B | `H100!` | Distilled FP8 | `768x512`, 97 frames | `<=5s` and naturalist visual pass |
| C | `H100!` | Distilled FP8 | `1024x576`, 97 frames | beats hosted by a lot, even if not realtime |
| D | `H100!` | One-stage FP8/full | `768x512`, 65 frames | speed lower bound, quality inspected manually |

Stop conditions:

- Stop the self-host branch if `768x512 / 97 frames` cannot get under `5s` warm.
- Stop the self-host branch for dense text unless text overlay/masking is part of the pipeline.
- Continue only if naturalist/illustration clips are clearly better than deterministic motion and substantially faster than hosted LTX.

## Hybrid Product Path

This is the more credible product architecture:

```text
source page image + metadata
  -> immediate deterministic motion clip
  -> optional background LTX enhancement
  -> publish enhanced clip only if quality gates pass
```

Immediate lane:

- Render a crisp first frame immediately from the generated page.
- Animate with deterministic transforms:
  - tiny camera drift / slow zoom
  - depth or pseudo-depth parallax
  - local safe-region warps for non-text illustration areas
  - subtle light/material shimmer
- Preserve text by construction:
  - lock the full page when text density is high, or
  - separate text/label overlay from background motion, or
  - freeze OCR/text masks with dilation.
- Target latency: `<=1.3s` for 33 frames server-side, or browser-native realtime if rendered client-side.

Background enhancement lane:

- Submit official LTX async or self-host LTX only for pages that are illustration/photo-rich.
- Use the deterministic clip as the instant preview.
- Replace/crossfade only if the enhanced clip passes gates:
  - OCR/text score above threshold for labeled pages.
  - Layout/region identity stable.
  - Manual/contact-sheet visual check for early research runs.

Router:

| Page family | Primary path | LTX role |
| --- | --- | --- |
| Dense text, dashboards, tables, labels | deterministic / Track C | off by default |
| Naturalist plate, illustration, photo-heavy page | deterministic now + LTX enhancement | background candidate |
| Layout reflow / interaction / resize | Track C clean page-state renderer | not LTX |
| Marketing/ambient hero image | LTX acceptable | background or precompute |

## Recommendation

Build the hybrid lane first. It aligns with our strongest negative evidence: full-frame video models preserve broad layout but repaint text. For realtime product feel, the static page should remain the source of truth.

Then run exactly one bounded Modal LTX-2.3 probe after getting a Hugging Face token. The only question for that probe is whether self-hosted distilled/FP8 LTX can produce illustration-rich enhancement clips in `<=5s` warm. If not, hosted LTX remains an offline/background reference, and we should not spend more time making it pretend to be realtime.

## Sources

- LTX-2 GitHub: https://github.com/Lightricks/LTX-2
- LTX open-source overview: https://docs.ltx.video/open-source-model/getting-started/overview
- LTX system requirements: https://docs.ltx.video/open-source-model/getting-started/system-requirements
- LTX PyTorch API: https://docs.ltx.video/open-source-model/integration-tools/pytorch-api
- LTX image-to-video guide: https://docs.ltx.video/open-source-model/usage-guides/image-to-video
- LTX pipelines README: https://raw.githubusercontent.com/Lightricks/LTX-2/main/packages/ltx-pipelines/README.md
- Modal LTX example: https://modal.com/docs/examples/ltx
- Modal GPU docs: https://modal.com/docs/guide/gpu
