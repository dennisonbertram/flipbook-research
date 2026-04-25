# Track C Progress Assessment

Date: 2026-04-25

## Short Answer

Track C has made real progress, but the most recent waves show a plateau.

The positive result is substantial: the neural canvas can render a page as model-owned pixels, change layout/content/illustration state, and produce 33-frame 1536x864 clips under the `1.3s` segment budget in many runs. That was not true at the start.

The negative result is also substantial: close crops still reveal old source-page structure underneath new target states. C92 and C93 make this visible. The issue is no longer "can it wiggle" or "can it pass OCR"; the issue is clean repainting of a new page state.

## Evidence Of Real Progress

- C86 proved a clean two-state page reflow with separately rendered target midpoint, not just a warped source image. Best run: OCR `0.7527`, segment `752.003ms`.
- C87 passed two materially different clean target layouts. Stacked layout reached OCR `1.0000` in multiple runs under the realtime segment budget.
- C88 removed neat card-box protection and still passed unboxed/callout layouts.
- C89 changed the visible copy itself; best changed-callout run reached OCR `0.9259`.
- C90 changed illustration grammar, redrawing timeline and transit-map page states.
- C91 changed topic entirely; orbit runs reached OCR `0.9286-1.0000`.

This means Track C is not just text masking, not just global wiggle, and not just one-layout memorization.

## Evidence Of Plateau

- C92 naturalist/deep-sea stress targets passed numerically, but close crops exposed old Colosseum text and oval-diagram remnants underneath the new page.
- C93 contrastive source-remnant loss improved some OCR numbers but did not remove the visual source layer.
- Scalar pressure on midpoint/remnant loss can reduce readability without solving the underlying leak.

That pattern suggests the current single source-biased latent/decoder is not cleanly separating "what content to preserve" from "what new page state to paint."

## Decision

Track C should keep running only if the next experiments are architecture tests, not more scalar sweeps around the same representation.

C94 was therefore the right next wave: target-state residual, fused residual, dual-gate, and latent-both controls on the naturalist/deep-sea source-remnant stress cases.

C94 did still show the source layer in crops. C95 tested a dual-state representation with a separate target latent canvas, but because the target canvas was concatenated beside source features, crop-level source remnants remained. C96 forced the midpoint latent state to blend/switch from source canvas to target canvas, but close crops still showed the same old source layer. The next viable Track C step is C97: split the decoder into separate source and target-state branches, with an independent target latent canvas and final output blending by midpoint progress.

## Current Status

As of this assessment update, C96 is complete and is another partial/negative architecture result. It keeps render time stable (`~1.1s` segments for most passes), but best naturalist OCR (`0.5310`) trails C95 and the crop review still reveals source remnants. C97 is implemented as a stricter state-split decoder test. Track C is scientifically useful, but it is not yet a product proof.
