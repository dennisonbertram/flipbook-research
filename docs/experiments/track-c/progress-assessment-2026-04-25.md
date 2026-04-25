# Track C Progress Assessment

Date: 2026-04-25

## Short Answer

Track C has made real progress, and the most recent crop audit clarifies the plateau.

The positive result is substantial: the neural canvas can render a page as model-owned pixels, change layout/content/illustration state, and produce 33-frame 1536x864 clips under the `1.3s` segment budget in many runs. That was not true at the start.

The negative result is more specific than the earlier notes suggested: the target midpoint can be repainted cleanly, but transition crops still reveal old source-page structure because the current clean-reflow target is effectively a source-to-target page-state blend. The issue is no longer "can it wiggle" or "can it pass OCR"; the issue is convincing transition behavior between clean page states.

## Evidence Of Real Progress

- C86 proved a clean two-state page reflow with separately rendered target midpoint, not just a warped source image. Best run: OCR `0.7527`, segment `752.003ms`.
- C87 passed two materially different clean target layouts. Stacked layout reached OCR `1.0000` in multiple runs under the realtime segment budget.
- C88 removed neat card-box protection and still passed unboxed/callout layouts.
- C89 changed the visible copy itself; best changed-callout run reached OCR `0.9259`.
- C90 changed illustration grammar, redrawing timeline and transit-map page states.
- C91 changed topic entirely; orbit runs reached OCR `0.9286-1.0000`.

This means Track C is not just text masking, not just global wiggle, and not just one-layout memorization.

## Evidence Of Plateau

- C92-C96 naturalist/deep-sea stress targets pass numerically, but the `t=0.25` transition crop exposes old Colosseum text and oval-diagram remnants during the transition.
- C93 contrastive source-remnant loss improved some OCR numbers but did not produce a more convincing transition.
- Scalar pressure on midpoint/remnant loss can reduce readability without solving the transition-frame persistence.

That pattern suggests the current model can memorize/render clean endpoint states, but the learned temporal path is still too close to crossfade/source persistence.

## Decision

Track C should keep running only if the next experiments are architecture tests, not more scalar sweeps around the same representation.

C94 was therefore the right next wave: target-state residual, fused residual, dual-gate, and latent-both controls on the naturalist/deep-sea source-remnant stress cases.

C94-C96 should be read as target-state positive and transition-quality unresolved. The old-source-heavy crop was `crop-2x.png` at `t=0.25`, not a midpoint target crop. The next viable Track C step is still C97: split the decoder into separate source and target-state branches, with an independent target latent canvas and final output blending by midpoint progress, then evaluate endpoint quality separately from transition quality.

## Current Status

As of this assessment update, C97 is complete. It is a mixed endpoint result and a negative transition result: best deep-sea improves to OCR `0.8387` at `1002.438ms`, while best naturalist drops to OCR `0.4463` (`0.4298` for the faster no-source-coordinate variant). Corrected `render-mid` crops are clean, while `t=0.25` crops reveal source persistence. Track C is scientifically useful, but it is not yet a product proof.

The next step is transition-aware C98: save explicit transition target crops, evaluate `t=0.25/0.75` separately from `t=0.5`, and train against a deterministic moving-layout transition instead of only a source/target endpoint blend. C98 is implemented as `layout-clean-move-reveal`, where the source layer moves/fades while the target page eases in.

The evaluator now also reports source-residual gain/cosine and source-only edge bias in changed regions. These metrics should be read separately for target-midpoint frames and transition frames; the transition-frame metric is the more relevant one for the source-persistence problem.
