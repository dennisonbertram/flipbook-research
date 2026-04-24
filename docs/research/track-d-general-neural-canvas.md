# Track D: General Neural Canvas Model

Track C is currently an overfit renderer lab. It fits one page into a compact neural canvas, then asks whether that canvas can render animation, resize, crops, and text-like detail fast enough.

That is useful, but it is not yet the product model. Track D is the path from one-page overfitting to a general neural canvas compiler.

## Current Status

The current C-series model is intentionally overfit:

- It optimizes a latent feature canvas and renderer for one page.
- It measures whether the renderer class can preserve identity under motion.
- It proves realtime render/encode feasibility after compile.
- It does not prove that a new page can be rendered without per-page optimization.

The strongest current signal is that no-OCR-box runs are now competitive with text-weighted runs. That matters because the more general direction cannot depend on clean rectangular text regions.

## Why Overfitting Is Acceptable For Now

Overfitting answers a narrow but necessary question:

```text
If the exact page identity is known, can this renderer query pixels quickly while preserving high-frequency detail during interaction?
```

If the answer were no, a general model would not save the architecture. The renderer would be wrong.

Now that the answer is increasingly yes, the next question changes:

```text
Can a model infer a useful neural canvas for a new page without optimizing from scratch?
```

## Track D Target

The target is an amortized neural canvas compiler:

```text
input page/image/prompt/state
  -> encoder/prior predicts persistent latent canvas + motion/render parameters
  -> renderer queries pixels at resolution, viewport, and time
```

The core product claim remains unchanged: visible pixels should come from the neural renderer, not DOM/CSS overlays.

## Model Path

1. Multi-page fixture set
   - Build many synthetic pages with varied layouts, fonts, diagrams, labels, dense text, curved labels, small captions, UI controls, and illustrations.
   - Keep source truth: rendered image, text strings, text positions, semantic regions, and motion programs.
   - Split into train, validation, and held-out test pages.

2. Amortized initialization
   - Train an encoder to predict the latent canvas initialization from an input image/page.
   - Keep the current renderer as the decoder/query function.
   - Compare zero-step prediction against a small number of adaptation steps.

3. Prior plus adaptation
   - Measure `0`, `1`, `4`, `16`, and `64` test-time optimization steps.
   - The goal is to replace a 30-second per-page compile with a fast initialization plus tiny refinement, then eventually no refinement.

4. General motion model
   - Learn motion fields that preserve high-frequency identity across page types.
   - Avoid OCR-box-specific assumptions in the default path.
   - Keep text-aware signals as optional training losses, not render-time masks.

5. Held-out eval
   - A run only counts as general if it passes on pages never seen during training.
   - Report train/validation/test separately.
   - Track OCR, layout similarity, temporal consistency, motion delta, loop error, and render latency.

## First Milestone

Train on `N` synthetic pages and evaluate on held-out pages:

```text
zero-step held-out OCR >= 0.75
16-step held-out OCR >= 0.82
33 frames + encode <= 1.3s
no render-time text masks
```

These numbers are deliberately below the best one-page overfit result. Generalization should first be real, then excellent.

## Open Risks

- The renderer may be fast because it memorizes one page, but encoder-predicted canvases may blur text.
- OCR may reward familiar fonts and miss failures in diagrams or UI symbols.
- Synthetic fixtures may be too clean unless they include noisy real-world screenshots and generated illustrations.
- Adaptation steps can quietly become overfitting again if they are too expensive.

## Next Work

- Create a synthetic page fixture generator.
- Add Track D eval tables with train/validation/test splits.
- Add a tiny amortized encoder that predicts the current latent grid.
- Compare zero-step, few-step, and full-overfit compile paths.
- Keep Track C running as the renderer laboratory while Track D tests generalization.
