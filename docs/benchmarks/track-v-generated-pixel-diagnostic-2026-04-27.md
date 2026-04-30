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
| Official LTX 2.3 Fast dense text, source image as last frame | near-copy, `0.854` | partially crop-explainable, `0.455` | near-copy, `0.931` | Anchoring first and last frame makes the model return to the document, but it still invents a page-fold/collapse artifact in the middle. |
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

## Last-Frame Anchor Test

Run:

`outputs/track-v/20260427T235031Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-lastframe-1920x1080/output.mp4`

Command shape:

- model: `ltx-2-3-fast`
- input: dense Roman Colosseum page
- last frame: same dense Roman Colosseum page
- duration/fps/resolution: `6s`, `24fps`, `1920x1080`
- API wall: `18.426s`

Result:

- overall text score: `0.6861`, just below the `0.70` gate;
- layout score: `0.9895`;
- motion score: `0.1020`;
- loop error: `0.0226`;
- first frame text score: `0.9588`;
- mid frame text score: `0.1636`;
- last frame text score: `0.9358`.

This is the best dense-text hosted LTX signal so far. It still fails, but it fails differently and more usefully: the model can be anchored back to the real page. The failure is concentrated in the middle, where LTX invents a page-turn/fold artifact.

That suggests the next hosted-model test should not be "free-run LTX plus repair." It should be constrained generation:

- use source-as-first and source-as-last;
- reduce duration or ask for a very small midpoint change;
- test whether the middle collapse shrinks when the temporal span is shorter;
- reject runs where the mid frame becomes less crop-explainable than a threshold.

## Short Anchor Probe

Follow-up runs on 2026-04-28 tested exactly that constraint.

| Run | Shape | API wall | Status | Read |
| --- | --- | ---: | --- | --- |
| `20260428T002049Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-anchor-3s-locked-1920x1080` | 3s, 72 frames, 1080p, source as first and last frame | `18.953s` | pass | Better than the 6s anchor, but the midpoint is still only partially crop-explainable and text drops to `0.4931` at mid frame. |
| `20260428T002056Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-anchor-2s-locked-1920x1080` | 2s, 48 frames, 1080p, source as first and last frame | `14.762s` | pass | Best dense-text hosted LTX run so far: overall text `0.8099`, layout `0.9992`, all sampled frames classify as near-copy. |
| `20260428T002253Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-anchor-2s-defaultprompt-1920x1080` | 2s, anchored, default prompt | `15.814s` | quality fail | Shows the strict "locked document/no camera/no page turn" prompt matters; same anchor and duration still loses text. |
| `20260428T002259Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-noanchor-2s-locked-1920x1080` | 2s, locked prompt, no last frame | `13.555s` | quality fail | Shows the last-frame anchor matters; without it, the page crops/recomposes. |

The current hosted recipe is therefore conditional:

1. source image as both first and last frame;
2. 2 second duration;
3. strict no-camera/no-page-turn/no-crop prompt;
4. family-specific negatives in the positive prompt, because the API does not expose a `negative_prompt` parameter.

The official docs list the image-to-video endpoint parameters `image_uri`, `last_frame_uri`, `duration`, `resolution`, `fps`, and `camera_motion`, and note that `last_frame_uri` is only supported by `ltx-2-3` models. The live API accepted 2s and 3s requests even though the public model matrix lists longer durations; it rejected 1s and rejected `960x540`.

## Protected Composite Test

Run:

`outputs/track-v/20260427T234946Z-track-v-composite-ltx2-fast-text-protected-composite-1920x1080/output.mp4`

Method:

- take the free-running `ltx-2-fast` dense-text output;
- build a protected source mask from dark text and hard linework;
- composite the original source pixels over the generated video with `scripts/track_v/protected_composite.py`.

Result:

- source LTX text score: `0.3633`;
- protected composite text score: `0.5009`;
- source LTX layout score: `0.9881`;
- protected composite layout score: `0.9938`;
- composite time: `912 ms` for the 153-frame 1080p clip.

This improves OCR but is visually incoherent: the fixed source layer floats over a generated page that has zoomed/recomposed itself. It is therefore not a good product path unless the video model is already constrained to stay in the original page coordinate system.

## Next Experiment

The next promising path is not Track B-style whole-plate drift, and it is not post-hoc compositing over a collapsed LTX run. It is a controlled hybrid:

1. Segment/freeze text and hard linework.
2. Constrain the video model with first/last source-frame anchors.
3. Let the model repaint only illustration/background regions or very small lighting changes.
4. Composite model-generated regions back under the frozen document layer only if the generated run stays in source-page coordinates.
5. Use this diagnostic to reject runs where the model drifts away from the canonical page.

That would let us keep the one good thing LTX is showing here, real generated pixels, without accepting its tendency to rewrite the document.

The caveat is now sharper: the successful 2s LTX clip is also near-copy and almost static. Hosted LTX should be a background enhancement path, not the realtime or re-layout path.
