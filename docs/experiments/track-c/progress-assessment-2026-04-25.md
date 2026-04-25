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

As of this assessment update, C99 is complete. It is a stronger transition/recomposition result than C98 because page regions move and resolve independently rather than sharing one move/reveal field. Five of six C99 runs pass after adding endpoint OCR gates. Deep-sea is the clearest positive: target-blend reaches midpoint OCR `0.8667`, source-frame OCR `0.8054`, last-frame OCR `0.8326`, and segment `1121.871ms`. The faster deep-sea base run reaches midpoint OCR `0.8276` at `936.786ms`.

C99's lesson is that independent recomposition is viable but still not robust across visual styles. Naturalist target-blend and state-split preserve endpoints, but midpoint text is weak (`0.4590` and `0.3967` OCR) and transition source-residual gain remains positive. The naturalist base run is now correctly marked `quality_fail`: midpoint OCR alone looked borderline, but source-frame OCR fell to `0.1379` and last-frame OCR fell to `0.1677`.

C100 is now complete and upgrades independent recomposition from promising to viable. All eight runs pass endpoint-aware gates across timeline, transit, reef, orbit, naturalist, and deep-sea. Timeline reaches midpoint OCR `0.9375`, orbit `0.8235`, transit `0.7179`, reef `0.5116`, deep-sea `0.8000-0.8276`, and naturalist remains the weak style at `0.3968-0.4138`.

The next step is C101: transition-target source-remnant pressure. The endpoint/midpoint result now generalizes; the remaining visible failure is transition source haze. C101 should compare the current clean-target remnant loss with a transition-target remnant loss that penalizes pixels which remain closer to the source page than the synthetic transition target.

C101 is complete. It confirms that the transition-target reference is the right comparison point, but not yet enough pressure timing. Five of six runs pass; the naturalist state-split variant only misses the segment gate at `1303.659ms`. Timeline reaches OCR `0.9677`, reef `0.7742`, orbit `0.8000`, deep-sea `0.8276`, and naturalist `0.4737`. The remaining issue is that transition source-residual gain stays positive for most non-deep-sea targets (`0.0557-0.1523`), so C102 lowers the remnant time exponent from squared weighting to earlier-on `1.0`/`0.5` probes.

The evaluator now reports endpoint OCR, source-residual gain/cosine, source-only edge bias, and transition-crop equivalents. These metrics should be read separately for endpoint frames, target-midpoint frames, and transition frames; transition-frame residuals are the most relevant metrics for the source-persistence problem.
