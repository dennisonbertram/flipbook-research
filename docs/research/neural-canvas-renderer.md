# Neural Canvas Renderer Research

## Thesis

The brilliant version of Flipbook is not a conventional web page with AI-generated assets. It is a learned renderer:

```text
world state -> model -> pixels
```

The hard part is not merely making image-to-video faster. It is giving the model a persistent world representation so it can render, resize, animate, crop, and update the same world without repainting it from scratch.

## Mental Model

Think of the system as three layers:

```text
1. world compiler
   prompt, search result, facts, history -> persistent latent canvas

2. neural canvas
   multiscale latent representation of the page/world

3. renderer
   latent canvas + viewport + resolution + time -> pixels
```

The renderer is still model-generated pixels. The canvas is not HTML or CSS. But the model is no longer asked to invent the whole page every frame.

## Why Full-Frame Video Is Not Enough

Our Track A LTX sweep showed that low-latency full-frame video is plausible, but the representation is wrong for text-heavy pages:

- fast runs preserve layout but damage text
- higher-resolution runs preserve text better but miss the latency target
- each frame behaves like a repaint, not a stable render of one world

This points to a representation problem more than a transport problem.

## What The Canvas Must Store

The neural canvas must preserve:

- semantic objects
- exact text strings or text-equivalent identity
- diagram geometry
- spatial relationships
- visual style
- latent features needed for high-resolution rendering
- temporal state for subtle motion

It does not have to store CSS boxes. But it probably needs more than an RGB image latent. It needs identity-bearing state.

## Relevant Research Threads

### Few-Step Generative Rendering

Latent Consistency Models, rectified-flow distillation, and related few-step generators show that expensive iterative generation can be compressed into one or a few model evaluations.

Usefulness:

- train/distill a fast renderer
- support interactive refresh rates
- reduce denoising steps from "generation" to "rendering"

### Streamed Diffusion

StreamDiffusion-style systems show that diffusion pipelines can be rearranged for interactive continuous input.

Usefulness:

- batch and pipeline denoising work
- reuse state across frames
- reduce redundant computation when inputs change slowly

### Realtime Video Latent Diffusion

LTX-Video shows that video latent spaces and video VAEs can be designed for fast generation.

Usefulness:

- compact video latent space
- fast temporal decoding
- practical baseline for the renderer speed target

### Neural Fields / Implicit Representations

Coordinate networks and neural graphics primitives show that a scene can be represented as a learned function queried by coordinates.

Usefulness:

- crop/resize as coordinate queries
- persistent representation independent of output resolution
- render many views from one compiled object

## Key Open Questions

1. Can one canvas preserve text better than repeated image-to-video repainting?
2. Can a small renderer hit `33` frames plus encode in `<= 1.3s`?
3. Does compile-time matter if the result can be reused for many interactions?
4. Can the canvas support zoom/crop without a layout engine?
5. Does the canvas need symbolic text conditioning, or can it store exact text visually?
6. Can a slower teacher create training data for a fast canvas renderer?

## Training Path

The long-term model recipe probably looks like:

```text
teacher model generates rich page/world examples
structured facts/text are kept as supervision
student compiler predicts latent canvas
student renderer predicts pixels from canvas + viewport + time
OCR/layout/video losses enforce identity
few-step or feed-forward distillation makes rendering realtime
```

Important losses:

- OCR/text identity loss
- perceptual reconstruction loss
- layout/edge consistency loss
- resize consistency loss
- temporal consistency loss
- loop boundary loss
- adversarial/detail loss for sharpness

## First Practical Experiment

Do not start by training the full compiler. Start by proving the renderer interface.

Overfit one text-heavy page into a neural canvas, then query it:

```text
same canvas -> full 512x288 render
same canvas -> full 960x544 render
same canvas -> 2x zoom crop
same canvas -> shifted crop
same canvas + time -> 33-frame clip
```

This tells us whether the learned canvas/renderer abstraction is promising before we ask it to generalize.

## Relationship To Track B

Track B is the pragmatic compositor path. Track C is the purist model-rendered-pixels path.

They can still inform each other:

- Track B gives us masks and metrics.
- Track C gives us a target representation.
- Track A gives us video latency baselines.

The north star remains Track C: every pixel rendered by a model from persistent world state.

## Sources

- LTX-Video paper summary: https://huggingface.co/papers/2501.00103
- LTX public site: https://ltx.dev/
- Latent Consistency Models: https://huggingface.co/papers/2310.04378
- StreamDiffusion: https://huggingface.co/papers/2312.12491
- InstaFlow / one-step rectified flow: https://huggingface.co/papers/2309.06380
