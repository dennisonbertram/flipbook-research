# Model-Layer Acceleration Options For The Next PoC

Date: 2026-04-24

Target: `33` frames generated + decoded/composited + encoded in `<= 1.3s` at useful UI quality.

## Baseline Read

Track A already shows that raw speed is close but quality is not solved. Recent LTX runs pass at `768x448` with `2-4` steps around `1.20-1.28s`; `896x512` and `960x544` are mostly near misses in the latest rows. OCR-proxy quality is the bigger blocker: low-res passing clips preserve broad layout but mangle dense text. Encoding is not free either: local fixed-cost floor at `960x544` was `416ms`, with `374ms` in encode, and Modal runs spend roughly `185-250ms` in encode for many sizes.

The next PoC should optimize for less model work and explicit identity preservation. A full-frame video model that repaints every latent token is the hardest path for text-heavy UI.

## Ranked Options

### 1. Protected Text + Distilled LTX Motion Layer

Use the existing LTX image-to-video path, but stop asking it to generate glyphs. Feed a text-removed or text-muted visual layer to the video model, generate subtle background/motion, then composite the original text/linework layer back over every frame. Also test latent mask replacement during denoising so protected regions remain close to the noised source latents.

Why it matters:

- It is the closest path to the current harness and latency envelope.
- LTX-Video is explicitly designed for fast video generation with a high-compression Video-VAE, and Diffusers documents guidance/timestep-distilled variants using `guidance_scale=1.0` and few-step schedules.
- It turns text preservation from "hope the video model obeys" into a hard rendering constraint.

Risks:

- Edges around text may show halos unless masks are dilated and antialiased carefully.
- Full-frame denoising still touches every latent token, so it may not scale to `1280x736`.
- VAE decode can still blur protected glyphs if preservation happens only in latent space. Pixel overlay should be the final safety pass.

Concrete experiments:

- Benchmark `Lightricks/LTX-Video-0.9.8-13B-distilled`, `0.9.8-13B-distilled-fp8`, and the `0.9.8` 2B distilled variants if available in the local runner.
- Fixed matrix: `768x448`, `896x512`, `960x544`; `33` frames; `2`, `3`, `4` steps; `guidance_scale=1.0`; prompt embeddings cached.
- Add three modes: full-frame baseline, pixel overlay only, latent text-freeze + pixel overlay.
- Success gate: `960x544 <= 1.3s`, OCR within 10% of the static source overlay, no obvious text-edge shimmer.
- If `960x544` misses, generate motion at `768x448` or `896x512`, upscale/background-resize, and overlay final-resolution text.

### 2. Tile/Windowed Residual Renderer

Render only what needs to move. Divide the page into protected static regions and active motion windows. For each frame, generate a residual or replacement only for non-text windows, then composite against the canonical page. This can start without a new foundation model: use deterministic masks, optical-style warps, and small learned residual heads before trying video diffusion per tile.

Why it matters:

- Model cost scales with active pixels/tokens instead of the whole page.
- UI pages have large stable areas; text, labels, grids, charts, and borders can often be frozen.
- This aligns with the longer Track C direction: a persistent canvas with time-conditioned rendering.

Risks:

- Seam artifacts between generated and frozen regions.
- Local windows may lose global lighting/camera coherence.
- Needs careful invalidation logic for interactions and viewport changes.

Concrete experiments:

- Build a `4x4` or content-aware tile mask over the existing fixture; mark text/linework frozen.
- Generate three motion modes: procedural parallax, local warp field, learned residual over active tiles.
- Encode the same `33` frame output and compare against LTX full-frame on OCR, layout similarity, loop error, and wall time.
- Add overlapping windows only where seams are visible. MultiDiffusion-style fusion is a quality reference, but not the speed goal.
- Success gate: `960x544` render+composite+encode `<= 1.3s` with OCR near source and visible intentional motion.

### 3. Video Diffusion Caching + Fast Attention Stack

Apply training-free cache/attention accelerators to a DiT video model, especially once a candidate is under `3s` with acceptable quality. Prioritize methods with video-DiT evidence: Pyramid Attention Broadcast, TeaCache/DeepCache/Taylor-style cache, FasterCache, and attention kernels such as SageAttention or FlashAttention-3 where compatible.

Why it matters:

- The target likely needs another `1.3x-2x` after model choice, decode, and encode improvements.
- Caching attacks repeated denoising work without retraining.
- HunyuanVideo-1.5 already advertises cache inference support and a selective/sliding tile attention design, making it a useful reference implementation.

Risks:

- Cache thresholds can create temporal artifacts that OCR/layout proxies may miss.
- CFG-cache benefits are limited for guidance-distilled LTX runs because they use `guidance_scale=1.0`.
- Kernel swaps can be brittle across model implementations and GPU types.

Concrete experiments:

- For each model, measure denoise-only first, then end-to-end wall time including VAE decode and encode.
- Add cache modes one at a time: conservative TeaCache, aggressive TeaCache, PAB if implemented, then attention-kernel swap.
- Test at the current near-miss setting first: `896x512` and `960x544`, `2-4` steps for LTX; `4/8` step-distilled variants for HunyuanVideo-1.5.
- Reject any cache mode that improves latency but lowers OCR or introduces visible local flicker on text borders.

### 4. Few-Step UI Motion Student

Train a specialized student that predicts a short UI animation or residual from a static page representation. The teacher can be LTX, Wan, Hunyuan, or procedural/graphics motion. The student target should not be "paint a page"; it should be "produce a time-varying residual that is zero in protected regions."

Why it matters:

- Consistency models, LCMs, rectified flow, and adversarial diffusion distillation all point toward high-quality one/few-step generation.
- The project target is narrow: subtle UI/video motion from a known page, not arbitrary cinematic generation.
- A student can bake in `33`-frame segment length, text masks, fixed resolution buckets, and no-CFG inference.

Risks:

- Requires a curated training set and objective, not just inference tuning.
- Student quality is capped by teacher/data quality and can overfit to easy motion.
- Training may solve latency but still fail identity unless text/layout losses are explicit.

Concrete experiments:

- Create `1k-10k` synthetic page animations with exact text masks, procedural depth/parallax, and teacher-enhanced non-text motion.
- Train a LoRA first if the base supports it; move to a compact student only if LoRA inference remains too slow.
- Losses: RGB/reconstruction, zero residual inside protected mask, OCR/text-box consistency, temporal smoothness, and loop-boundary error.
- First target: `768x448` one-page overfit, `33` frames in `<= 500ms` before encode. Then generalize to multiple generated pages.

### 5. Higher-Quality Teacher/Reference Models

Use stronger image/video models to create canonical pages, masks, teacher clips, and evaluation references, but do not assume they are real-time candidates.

Why it matters:

- Text-capable still-image models can generate the canonical page and structured text layer better than video models.
- High-quality video models can teach motion style or provide ablation baselines.

Risks:

- Hosted APIs may be too slow or too costly for live generation.
- Open 14B-22B video models can be quality wins but are usually latency losses.
- Text rendering in still images does not guarantee text preservation across video denoising.

Concrete experiments:

- Static renderer bake-off: Qwen-Image/Qwen-Image-Edit, Ideogram V3, GPT Image, and the existing Nano Banana path. Score OCR, layout, editability, mask extraction, latency, and cost.
- Use the winning still renderer to produce source page, clean text mask, text layer, and no-text background layer.
- Use high-quality video models only as teachers or comparison baselines unless they can approach `<= 3s` end-to-end.

## Candidate Model Families

### Immediate Candidates

1. `LTX-Video 0.9.8 distilled / FP8`
   - Best current fit for the latency target. The model card claims real-time high-resolution video, and Diffusers documents distilled custom timestep schedules, latent upscalers, `guidance_scale=1.0`, FP8 loading, and LoRA support.
   - Use for Track A continuation, especially with protected text compositing.

2. `HunyuanVideo-1.5`
   - Interesting next benchmark because it is `8.3B`, supports T2V/I2V, has a 3D causal VAE with `16x` spatial and `4x` temporal compression, uses selective/sliding tile attention, advertises cache inference, and includes step-distilled I2V.
   - It is unlikely to hit `1.3s` out of the box, but its architecture is directly relevant to tile/window acceleration.

3. `Wan2.2 TI2V-5B`
   - Worth a limited benchmark because it is a smaller unified text/image-to-video model, supports `720P` at `24 FPS`, and uses a high-compression VAE.
   - Wan2.1/2.2 are notable for visual text generation, but published runtime examples are far from the target, so this is likely a teacher or architecture reference, not the first live path.

### Teacher/Control Candidates

4. `LTX-2.3`
   - Newer LTX line with `22B` full/distilled FP8 checkpoints, `8`-step distilled inference, spatial/temporal latent upscalers, and trainable LoRA/IC-LoRA paths.
   - More attractive as a teacher/control model or source of upscaler ideas than as the immediate `<= 1.3s` generator.

5. `Wan2.2 I2V-A14B / T2V-A14B`
   - Strong open video quality and MoE architecture, but the documented hardware profile points to high-end `80GB` GPUs. Use as teacher/baseline.

6. `Qwen-Image / Qwen-Image-Edit`
   - Best open still-image candidate for dense UI/text assets. The model card emphasizes complex text rendering and precise editing; Qwen-Image-Edit can preserve font, size, and style during text edits.
   - Use for canonical page generation, text repair, masks, and training data, not live video segments.

7. `Ideogram V3 / GPT Image`
   - Strong hosted still-image/text candidates. Ideogram's docs emphasize text and typography generation; OpenAI's image API docs and release notes emphasize image generation/editing and accurate text rendering.
   - Useful for static assets and evaluation references; live video latency is out of scope.

## Recommended Next Experiment Order

1. `LTX protected-text benchmark`
   - Add text mask, no-text background, pixel overlay, and optional latent freeze.
   - Run the fixed `768/896/960` matrix with `2-4` steps.
   - This is the fastest way to learn whether Track A can become useful, not merely fast.

2. `HunyuanVideo-1.5 480p I2V step-distill/cache smoke test`
   - Benchmark `4`, `8`, and `12` step modes if available; enable official cache modes one at a time.
   - If it is `>3s`, stop live-path work and keep it as a teacher/reference.

3. `Windowed residual renderer`
   - Implement a learned-or-procedural active-tile residual path over the same fixture.
   - Compare against LTX protected-text on end-to-end latency and OCR.

4. `Static text renderer bake-off`
   - Generate source pages and masks with Qwen-Image/Edit, Ideogram, GPT Image, and the existing static path.
   - Pick the best canonical page generator for training and demos.

5. `Few-step student training`
   - Start only after the protected-text and windowed experiments define the desired target representation.
   - Distill toward residual motion with hard protected-region losses.

## Sources

- Local benchmark target: `docs/poc/benchmark-target.md`
- Local Track A notes and current results: `docs/poc/track-a-full-ltx.md`, `docs/benchmarks/track-a-ltx-modal-2026-04-24.md`, `docs/experiments/track-a/results.tsv`, `docs/experiments/track-a/quality.tsv`
- LTX-Video Diffusers docs: https://huggingface.co/docs/diffusers/en/api/pipelines/ltx_video
- LTX-Video model card: https://huggingface.co/Lightricks/LTX-Video
- LTX-2.3 model card: https://huggingface.co/Lightricks/LTX-2.3
- LTX-2.3 FP8 model card: https://huggingface.co/Lightricks/LTX-2.3-fp8
- LTX open-source docs: https://docs.ltx.video/open-source-model/getting-started/overview
- LTX-2 trainer docs: https://docs.ltx.video/open-source-model/ltx-2-trainer/ltx-2-training
- HunyuanVideo-1.5 model card: https://huggingface.co/tencent/HunyuanVideo-1.5
- HunyuanVideo-1.5 GitHub: https://github.com/Tencent-Hunyuan/HunyuanVideo-1.5
- Wan2.1 GitHub: https://github.com/Wan-Video/Wan2.1
- Wan2.2 GitHub: https://github.com/Wan-Video/Wan2.2
- Consistency Models: https://openai.com/index/consistency-models/
- Latent Consistency Models: https://huggingface.co/papers/2310.04378
- Flow Matching: https://huggingface.co/papers/2210.02747
- Rectified Flow implementation/paper links: https://github.com/gnobitab/RectifiedFlow
- Latent Adversarial Diffusion Distillation: https://huggingface.co/papers/2403.12015
- Pyramid Attention Broadcast: https://huggingface.co/papers/2408.12588
- FasterCache: https://huggingface.co/papers/2410.19355
- TeaCache overview/reference implementation notes: https://docs.vllm.ai/projects/vllm-omni/en/latest/design/feature/teacache/
- SageAttention: https://huggingface.co/papers/2410.02367
- FlashAttention-3 PyTorch post: https://docs.pytorch.org/blog/flashattention-3/
- Token Merging for Fast Stable Diffusion: https://huggingface.co/papers/2303.17604
- MultiDiffusion docs: https://huggingface.co/docs/diffusers/v0.14.0/en/api/pipelines/stable_diffusion/panorama
- Qwen-Image model card: https://huggingface.co/Qwen/Qwen-Image
- Qwen-Image GitHub: https://github.com/QwenLM/Qwen-Image
- Qwen-Image-Edit model card: https://huggingface.co/Qwen/Qwen-Image-Edit
- Ideogram typography docs: https://docs.ideogram.ai/using-ideogram/prompting-guide/2-prompting-fundamentals/text-and-typography
- Ideogram API docs: https://developer.ideogram.ai/
- OpenAI image generation docs: https://platform.openai.com/docs/guides/images/image-generation
- OpenAI image generation API release: https://openai.com/index/image-generation-api/
- FineTrainers LTX-Video training docs: https://paragekbote.github.io/finetrainers/models/ltx_video/
- FineTrainers HunyuanVideo training docs: https://paragekbote.github.io/finetrainers/models/hunyuan_video/
