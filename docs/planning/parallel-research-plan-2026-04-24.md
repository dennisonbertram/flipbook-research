# Parallel Research Plan

Date: 2026-04-24

## Goal

Move from a promising one-page neural canvas prototype to a research loop that can discover whether the full Flipbook-like premise is real:

```text
world state -> learned canvas -> model-rendered pixels
```

The current bottleneck is no longer raw 33-frame render speed. Track C already renders 33 frames faster than realtime at `960x544`. The next bottleneck is identity under interaction: text, diagrams, and layout must remain the same world while the viewport, time, resolution, and frame geometry change.

## Current Baseline

Best current evidence:

```text
C2.1 static text-box-weighted canvas:
  OCR token-F1: 0.8545
  33-frame render: ~301ms

C2.2 learned dense frame-scale motion:
  moderate OCR: 0.1053
  strong OCR:   0.0000

C2.3 stable canvas + render-time layout transform:
  moderate OCR: 0.7091
  strong OCR:   0.3610

C2.4 stable canvas + OCR line anchors:
  moderate OCR: 0.7321
  strong OCR:   0.4124
  33-frame render: ~401-442ms
```

Interpretation:

- Persistent canvas identity is working.
- Dense learned flow is the wrong mechanism for layout-like resizing.
- Render/query transforms preserve identity better than repainting.
- Element anchors help, but the current implementation is sequential and too OCR-derived to be the final answer.

## Workstreams

### A. Eval Harness

Purpose: make every experiment comparable.

Immediate outputs:

- canonical fixture set
- scenario matrix for static, crop, zoom, aspect change, and frame-scale stress
- per-frame OCR/layout/temporal metrics
- human review rubric
- artifact schema and scorecard

First success condition:

```text
one command can evaluate C2.4 against all stress scenarios and write a single report
```

### B. C2.5 Element-Aware Renderer

Purpose: keep the C2.4 quality gain while recovering speed and reducing rectangular patch artifacts.

Experiments:

- batch all text/element anchor queries per frame
- replace rectangular patch overwrite with text-shaped soft alpha masks
- test word, line, paragraph, diagram, and title anchors
- measure whether anchors improve strong resize without breaking model-rendered pixel purity

First success condition:

```text
strong resize OCR > 0.45 and 33-frame render+encode <= 1.3s
```

### C. C1 Multiscale Latent Canvas

Purpose: stop relying on one full-resolution feature grid.

Experiments:

- feature pyramid with high-frequency detail levels
- sharper decoder with skip access to local high-res features
- train high resolution, render lower resolution
- compare memory, compile time, static OCR, crop quality, and resize stability

First success condition:

```text
static OCR >= C2.1 while reducing memory or improving zoom/crop fidelity
```

### D. Model-Layer Acceleration Research

Purpose: identify which real model families can become the compiler or renderer, not merely serve as inspiration.

Questions:

- What is the fastest plausible generative renderer: feed-forward, one-step flow, few-step diffusion, or latent decoder?
- Which models preserve text well enough to be teachers?
- Can a slower text-capable image model compile a latent canvas for a tiny realtime renderer?
- Can we distill a fixed interaction distribution: resize, crop, pan, subtle motion, and stable text?

First success condition:

```text
ranked model candidate list with one concrete POC recipe per candidate
```

### E. Fixture And Data Program

Purpose: avoid overfitting our thinking to one page.

Fixture queue:

- dense text article with headings and small body text
- table/dashboard with numbers
- diagram with labels and arrows
- product-card grid
- map-like layout with labels
- low-text illustration
- adversarial page with tiny text and mixed font sizes

First success condition:

```text
five fixtures, each with source image, OCR baseline, region annotations, and expected stress scenarios
```

### F. Identity Losses

Purpose: make the model learn that text and diagrams are identity-bearing, not texture.

Experiments:

- OCR token/character loss as evaluation first, training later
- text-box weighted reconstruction
- line/word anchor consistency across frames
- edge/Sobel loss inside text regions
- perceptual loss outside text regions
- crop-consistency loss: render crop directly and compare to crop of full render
- resize-consistency loss: render at two resolutions and compare after resampling

First success condition:

```text
one identity metric predicts human-readable failure better than whole-image MSE
```

### G. Pure Neural Canvas Guardrails

Purpose: keep the research aimed at model-rendered pixels, not a disguised web/layout stack.

Allowed as research scaffolding:

- OCR boxes as supervision
- text-shaped alpha masks as selection signals
- anchor manifests for diagnostics and stress tests
- human review of text and layout identity

Not accepted as evidence for the Track C thesis:

- DOM/CSS text painted over the result
- source glyph pixels copied back onto frames
- hand-authored responsive layout as the final renderer
- benchmark changes that make the page easier instead of the model better

The strongest version of this project is a generated page/world that can be animated, scrolled, resized, and changed because the same persistent representation is queried differently. All visible content pixels in the core claim should come from the neural canvas renderer.

## Parallel Agents Running

This wave is split into three independent research artifacts:

```text
eval-framework      -> docs/teams/eval-framework/exploration/
model-speed         -> docs/teams/model-speed/exploration/
experiment-roadmap  -> docs/teams/experiment-roadmap/exploration/
```

Local integration target:

```text
docs/evaluation/neural-canvas-eval-framework.md
docs/planning/parallel-research-plan-2026-04-24.md
```

## Next Seven Steps

1. Lock the eval schema and scorecard.
2. Add a small runner that evaluates existing Track C output directories without rerunning training.
3. Convert C2.4 into a named baseline across static, moderate, and strong resize scenarios.
4. Implement C2.5 text-alpha element masks, then batched element rendering.
5. Add two more fixtures so the eval stops rewarding one-page overfitting.
6. Start C1 multiscale latent canvas as a separate script, preserving the same eval contract.
7. Pick one teacher model path for canvas compilation and one student renderer path for realtime output.

## Decision Rules

Prefer a change when it improves identity under interaction without missing the segment budget:

```text
render+encode 33 frames <= 1.3s
OCR/layout/temporal score improves
same canvas can answer multiple viewport queries
no hidden DOM/CSS/text overlay is required for the measured pixels
```

Reject or quarantine a change when:

```text
it only improves static frames
it breaks resize/crop consistency
it needs a hand-authored layout framework at inference time
it preserves text by placing non-model text on top of the render
it wins by weakening the benchmark
```

## Morning-Level Milestone

The next convincing demo should show:

```text
one fixture
one learned canvas
three viewport sizes
one dramatic resize/reposition animation
33-frame video under the live budget
per-frame OCR/layout metrics
contact sheet showing visible motion and stable identity
```

That would move the project from "fast neural image reconstruction" to "credible neural UI rendering research."
