# Track V Generated Pixel Diagnostic - 2026-04-27

## Question

The official LTX 2 Fast dense-text run looks more interesting than Track B because it appears to create real generated pixels rather than shifting a fixed plate:

`outputs/track-v/20260426T234547Z-ltx-api-ltx-2-fast-official-ltx2-fast-text-preservation-1920x1080/output.mp4`

This diagnostic asks whether the generated frames are merely explainable as crops of the input page, or whether the model is actually repainting/recomposing the page.

## Method

`scripts/track_v/camera_path_diagnostic.py` compares each extracted first/mid/last frame against a grid search of crop/zoom candidates from the input image.

It is intentionally simple:

- high crop score means the frame is close to a source-page crop/copy;
- low crop score means the frame is not well explained as source pixels;
- low crop score is not automatically good, because it may mean the model has destroyed readable content.

Report artifacts:

- `docs/experiments/track-v/track-v-camera-path-diagnostic-2026-04-27.md`
- `docs/experiments/track-v/track-v-camera-path-diagnostic-2026-04-27.json`

## Key Reads

| Run | First | Mid | Last | Interpretation |
| --- | --- | --- | --- | --- |
| Official LTX 2 Fast dense text | near-copy, `0.846` | not crop-explainable, `0.316` | not crop-explainable, `0.255` | The clip is not just deterministic drift or a literal crop. It generates new pixels, but those pixels lose the document. |
| Official LTX 2.3 Fast dense text | near-copy, `0.743` | not crop-explainable, `0.233` | not crop-explainable, `0.235` | More aggressive repaint/collapse than LTX 2 Fast on this dense page. |
| Official LTX 2.3 Fast naturalist | near-copy, `0.771` | partially crop-explainable, `0.351` | partially crop-explainable, `0.355` | Better fit for illustration-first pages; the model repaints but keeps enough plate-level structure to remain useful. |
| Kling naturalist reference | near-copy, `0.997` | near-copy, `0.916` | near-copy, `0.939` | Very stable plate. More conservative, less generated, visually coherent. |
| Track B deterministic baseline | near-copy, `0.998` | near-copy, `0.785` | near-copy, `0.999` | Fast and stable, but not real generated motion. |

## Interpretation

The user read is right: the LTX 2 Fast dense-text clip is interesting precisely because it is not merely moving the existing text around. It appears to invoke the video model's learned page prior and generate fresh pixels.

But it fails the product goal for dense documents:

- first frame preserves the page reasonably well;
- mid and last frames become generated document-like imagery rather than the same document;
- OCR text score falls to `0.3633` overall, with mid/last frame text scores near zero;
- loop error is `0.0729`, far higher than the stable Kling or Track B baselines.

So the current classification is:

**LTX is useful as a generated-pixel research signal, not as a dense-page preservation solution.**

## Next Experiment

The next promising path is not Track B-style whole-plate drift. It is a controlled hybrid:

1. Segment/freeze text and hard linework.
2. Let a video model repaint only illustration/background regions.
3. Composite model-generated regions back under the frozen document layer.
4. Use this diagnostic to reject runs where the model drifts away from the canonical page.

That would let us keep the one good thing LTX is showing here, real generated pixels, without accepting its tendency to rewrite the document.
