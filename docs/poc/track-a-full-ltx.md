# Track A: Full-Frame LTX

## Goal

Use LTX image-to-video as the primary generator for each live segment.

```text
static page image -> LTX image-to-video -> 33-frame playable segment
```

This track tests whether the public Flipbook-style claim can be reproduced directly with a fast video model and aggressive inference settings.

## Why This Might Work

- The static image already contains the good text and layout.
- LTX is designed for fast image-to-video generation.
- Distilled FP8 variants reduce inference cost.
- The segment is short: `33` frames at `24fps`.
- Motion can be subtle, which allows fewer denoising steps.

## Why This Might Fail

- Full-frame diffusion still touches every latent token every step.
- Text-heavy pages are fragile: diffusion can shimmer or deform labels.
- Generating near-1080p video in <= 1.3s is an extreme target.
- VAE decode and MP4 encoding can become meaningful parts of the budget even if denoising is fast.

## First Experiment

Start with the smallest setup that can answer the core speed question:

```text
model:       LTX distilled FP8
resolution:  960x544
frames:      33
fps:         24
steps:       4
guidance:    guidance_scale=1 / no CFG
prompt:      subtle continuous loop, gentle parallax, small ambient motion, preserve text and diagram layout
```

Measure:

```text
preprocess_ms
image_conditioning_ms
denoise_ms
vae_decode_ms
encode_ms
wall_time_ms
```

The first runnable harness is:

```text
scripts/track_a/benchmark.py
```

The local `stub_freeze` recipe measures the fixed-cost floor. The Modal runner in `scripts/track_a/modal_ltx_benchmark.py` is the first GPU-backed path for real LTX experiments.

## Optimization Ladder

Apply these in order, stopping when the output passes the benchmark target:

1. Use distilled FP8 weights.
2. Disable CFG and any extra guidance pass.
3. Fix shapes to avoid recompilation and memory churn.
4. Cache prompt embeddings for the fixed live-motion prompt.
5. Test `4`, `6`, and `8` denoising steps.
6. Use `torch.compile` or the fastest supported attention backend for the transformer.
7. Preallocate tensors and avoid per-request allocations.
8. Decode only the exact frames needed.
9. Use GPU encoding or an extremely fast fMP4 encoder path.
10. Generate lower-resolution motion and upscale to display resolution.

## Candidate Success Shape

The most plausible early winner is:

```text
960x544
33 frames
4-6 steps
distilled FP8
guidance-free
display-upscaled to 1080p
```

If this cannot approach `<= 1.3s`, then Track A probably requires a specialized distilled student model rather than serving optimizations alone.

## Better-Model Research Mode

Track A should borrow the `autoresearch` operating pattern: establish a baseline, keep the benchmark fixed, make one model-layer change at a time, log the result, keep improvements, and discard regressions.

This matters because the bottleneck is likely not WebSockets or serverless routing. It is whether the model can do less work while preserving a text-heavy page.

Use the research program here:

```text
docs/research/track-a-autoresearch-program.md
```

The first better-model branch should not change the transport or viewer. It should focus on:

- fewer denoising steps
- guidance-free inference
- latent token sparsity
- motion-residual prediction
- short-loop student distillation
- text-preservation evaluation

## Product Risks

- Text shimmer is a product-killer even if latency passes.
- Whole-page motion may feel like the page is melting.
- Prompt changes can increase latency and reduce consistency.
- Segment boundaries may stutter unless the clip is loop-aware or transition-aware.

## Decision Rule

Continue investing in Track A only if one of these is true:

- It passes the primary benchmark target.
- It lands under `3s` with excellent visual quality and an obvious 2x optimization path.
- It produces masked/crop outputs that can be reused inside Track B.
