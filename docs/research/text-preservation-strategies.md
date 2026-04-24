# Text Preservation Strategies

## Problem

Full-frame image-to-video models tend to repaint text. Even when the page layout stays stable, letters become soft, mutate, or shimmer across frames.

For Flipbook-style pages, this is a product-level failure. A video can be slightly imperfect, but explanatory text and labels must stay readable.

## Strongest Approach: Text As Overlay

The most reliable solution is to avoid asking the video model to generate text at all.

```text
page renderer -> background/image layer
page renderer -> text/label layer
video model   -> animate background/image layer only
compositor    -> text/label layer over animated video
```

This turns text preservation from a model problem into a rendering and compositing problem.

Requirements:

- keep source text, font, size, color, and positions as structured data
- render text layer at final display resolution
- dilate text masks slightly so generated pixels cannot bleed into glyph edges
- keep labels, chart annotations, borders, and important linework either in the overlay or in a protected mask

This is the likely product path for text-heavy pages.

## Model-Layer Approach: Freeze Text During Denoising

If Track A remains full-frame, the model needs a hard constraint:

```text
text mask = 1 where pixels must not change
nontext mask = 1 where generation is allowed
```

For latent diffusion, a practical experiment is:

1. encode the input page into latents
2. project the text mask into latent resolution
3. at each denoising timestep, replace masked text latents with the corresponding noised original latents
4. denoise only the non-text regions
5. after decode, pixel-composite the original text layer back on top as a final safety pass

This should reduce repainting, but VAE compression can still damage small glyphs. Pixel-level overlay is still the safer final step.

## Model-Layer Approach: Residual Motion

Instead of generating full frames, train or prompt a model to predict a residual:

```text
frame_t = input_image + motion_residual_t
```

Then force the residual to zero inside text regions:

```text
motion_residual_t[text_mask] = 0
```

This keeps Track A's interface as a video generator, but changes the internal target from "paint every pixel" to "move only allowed pixels."

## Control Inputs

Useful conditioning signals:

- text mask
- OCR boxes
- edge map / line-art map
- saliency map
- depth map
- protected-region mask

Prompts like "preserve text" are too weak. The model needs spatial constraints.

## Evaluation Gate

Every candidate should pass both latency and preservation gates:

```text
wall_time_ms <= 1300
ocr_similarity >= baseline_threshold
layout_similarity >= baseline_threshold
loop_error <= threshold
```

The current OCR watcher is only a proxy, but it is already good enough to catch the failure mode.

## Immediate Next Experiment

Build a hybrid compositor:

1. detect or provide text boxes/masks on the input fixture
2. remove or blur text from the layer sent to LTX
3. run LTX on the non-text visual layer
4. composite the original text layer back onto each output frame
5. compare OCR score, layout score, and latency against full-frame LTX

Expected result:

- text score should jump close to the freeze baseline
- latency should stay near the existing LTX result plus small compositing cost
- visual motion may need masks/dilation cleanup near text edges
