# Track B: Codec-Style Static Image Animation

## Goal

Treat the high-quality static image as the canonical frame and animate only what should move.

```text
static page image
  -> masks / depth / motion plan
  -> local warps, parallax, optional masked generation
  -> composite 33 frames
  -> playable segment
```

This track tests whether a Flipbook-like live feeling can be achieved without full-frame video diffusion.

## Core Hypothesis

The static page image is the source of truth. Text, labels, diagram edges, UI chrome, and important layout elements should stay locked. Motion should be layered on top of or behind the page, similar to old-school video codecs:

```text
I-frame: original page image
P-like frames: motion fields, masks, residuals, local animated crops
```

This is likely faster and more stable than asking a video model to repaint the full page every frame.

## First Experiment

Build a no-diffusion baseline:

```text
input:       one generated page image
resolution:  960x544
frames:      33
fps:         24
motion:      depth parallax + local sinusoidal warps
freeze:      detected text and high-contrast linework
output:      mp4
```

The output does not need to be magical. It needs to prove that the page can feel alive while text remains clean and latency is comfortably below `1.3s`.

## Pipeline

1. Detect text and linework.
2. Build a freeze mask for text, labels, borders, and diagram-critical edges.
3. Estimate depth or pseudo-depth.
4. Create a small set of layers.
5. Apply low-amplitude motion:
   - global camera drift
   - depth parallax
   - local flow fields for water/cloud/tree-like regions
   - small object bobbing where safe
6. Composite moving layers back under/around the freeze mask.
7. Encode the 33-frame segment.

## Optional Model Assistance

Use models only where they pay for themselves:

- segmentation model for text/non-text masks
- depth estimation model for parallax layers
- optical flow model for plausible motion fields
- masked LTX crop generation for regions where procedural motion looks cheap

The important constraint is that any model use must not threaten the `<= 1.3s` gate.

## Optimization Ladder

1. Start with CPU/OpenCV-style warps to establish the visual baseline.
2. Move compositing and warps to GPU if CPU time is meaningful.
3. Cache masks and depth per static page image.
4. Generate motion plans once per page, then render frames quickly for every segment.
5. Use fixed output sizes and preallocated frame buffers.
6. Add masked video generation only for regions where procedural motion fails.
7. Encode with the same fast fMP4 path used by Track A.

## Candidate Success Shape

The likely early winner is:

```text
original image preserved
text freeze mask
depth parallax
small masked local warps
33 frames rendered/composited in << 1.3s
```

If this looks convincing, it becomes the primary product path. Track A can still be used selectively for animated crops or transitions.

## Product Risks

- Cheap parallax can look like a slideshow effect.
- Bad masks can make text edges swim.
- Procedural motion may not understand semantic objects.
- Depth maps from diagrams/infographics may be noisy or misleading.

## Decision Rule

Prefer Track B if it clears the latency target while preserving text and layout. It does not need to be as generative as Track A if it produces the perceived effect: a rich page that feels alive.

## Hybrid Text Overlay Note

A promising variant is to treat text as a separate semantic/render layer rather than asking the video model to regenerate it.

In this shape, the static page renderer owns:

- text content
- font choice
- text layout
- labels and captions
- high-contrast diagram annotations

The video model owns only the non-text visual layer. Final frames composite the stable text layer on top of generated or warped imagery.

This may be the product-correct answer for Flipbook-style pages: the model can create ambience and motion, while text stays crisp by construction.
