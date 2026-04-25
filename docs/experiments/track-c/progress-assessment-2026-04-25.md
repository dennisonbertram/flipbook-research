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

C102 is also complete. Five of six runs pass. The `time_power=1.0` pass set improves transition source-residual gain for timeline (`0.0633`), reef (`0.0313`), orbit (`0.0488`), and deep-sea (`0.0043`). Naturalist is the important branch: `time_power=1.0` drops below OCR gate (`0.3208`), but `time_power=0.5` passes (`0.4118`) and reduces transition residual gain to `0.1136`. C103 should therefore test `time_power=0.5` as the broader candidate and add naturalist-only pressure probes.

C103 is complete and argues against more scalar-only timing sweeps. `time_power=0.5` preserves OCR well, but residual gains mostly rebound versus C102 (`0.0654` timeline, `0.0546` orbit, `0.0406` reef, `0.0135` deep-sea). Naturalist `time_power=0.25` is the best same-seed probe at `0.1324`, but still not clean; stronger remnant weight increases latency and gives `0.1467`. C104 should reserve samples for source-only remnant edges at transition times so the existing truth-referenced loss is applied where the evaluator still sees old-source structure.

C104 is complete. Source-only remnant-edge sampling at `0.18` is too blunt: timeline and reef regress on transition source-residual gain (`0.0783` and `0.0520`), naturalist remains brittle (`0.3519` OCR / `0.1390` gain, plus an OCR-failing `time_power=0.25` variant), and orbit/deep-sea only show small residual wins while losing OCR margin. C105 keeps the same variants/seeds but drops the reserve to `0.06`, which should tell us whether the idea needs gentler pressure or should be abandoned in favor of a more structural change.

C105 is complete. The lower `srcsample06` reserve mostly restores passability, but the residual metric still does not beat the best non-sampling probes: timeline `0.0691`, reef `0.0598`, orbit `0.0550`, and deep-sea `0.0133`. Naturalist `time_power=0.25` is the useful exception (`0.1235` gain, OCR `0.3689`), while naturalist `time_power=0.5` misses latency at `1303.764ms`. C106 pivots from sampling to loss shape by adding a direct weighted remnant-to-transition-target L1 term.

C106 is complete. Direct remnant L1 over all changed regions is not the cleanup path: all six runs pass and naturalist OCR improves, but residual gains worsen or remain high (`0.0709` timeline, `0.0759` reef, `0.0566` orbit, `0.0353` deep-sea, `0.1341-0.1529` naturalist). C107 narrows the direct term to source-only remnant regions so the extra loss attacks old-source residue instead of all transition changes.

C107 is complete. Source-only direct remnant loss is better targeted but too strong at `0.50`: timeline (`0.0641`) and orbit (`0.0467`) move back toward the best residual band, but reef/deep-sea do not, and naturalist `time_power=0.25` trades improved residual (`0.1163`) for an OCR fail (`0.3200`). C108 should reduce source-only direct weight to `0.25`.

C108 is complete. The lighter source-only direct term gives the best orbit residual so far (`0.0384`) and improves naturalist residual (`0.1081-0.1096`), but naturalist remains just under the OCR gate (`0.3396-0.3434`). Timeline regresses to `0.0728`; reef is `0.0528`; deep-sea is `0.0114`. C109 should tune naturalist at direct weights `0.15-0.18` and repeat orbit at `0.25` with a new seed.

C109 is complete. It is useful, but it also marks the point where more scalar tuning would become overfit-prone. Naturalist directsrc `0.18` produces two passing runs: `time_power=0.5` reaches OCR `0.3889`, segment `918.956ms`, and residual gain `0.1215`; `time_power=0.25` reaches OCR `0.3913`, segment `1129.706ms`, and residual gain `0.1261`. The lower `directsrc=0.15/time_power=0.25` probe is interesting but not a winner: OCR rises to `0.4356` and residual improves to `0.1155`, but it misses the segment gate at `1302.489ms`. Orbit `directsrc=0.25` repeats as a pass, but only barely on latency (`1299.982ms`) and with weaker residual (`0.0330`) than C108's seed-4 `0.0384` result. Deep-sea `directsrc=0.15` reaches near-zero residual (`-0.0006`) but misses latency badly (`1484.167ms`), so the branch should not chase deep-sea direct loss.

C110 is therefore a validation wave rather than another knob sweep. It pairs controls against the C109 direct candidates on a new naturalist seed, repeats orbit directsrc `0.25` with a same-seed control, and checks source-only direct `0.18` against reef and transit holdouts. If C110 does not show same-seed improvement over controls across more than one target family, source-only direct loss should be treated as a fixture-specific cleanup trick and the next move should be structural.

C110 is complete and confirms exactly that boundary. Naturalist `time_power=0.25/directsrc=0.18` is a real same-seed improvement over its control: OCR `0.4808` vs `0.4571`, segment `1108.582ms` vs `1108.945ms`, and transition residual gain `0.1129` vs `0.1274`. But the mechanism does not generalize cleanly. Naturalist `time_power=0.5/directsrc=0.18` fails OCR/latency, reef directsrc `0.18` improves residual only slightly while hurting OCR (`0.6154` vs `0.7059`), transit directsrc `0.18` improves OCR but worsens residual (`0.0532` vs `0.0331`), and orbit directsrc `0.25` improves residual but badly hurts OCR (`0.7368` vs `1.0000`). C111 therefore pivots to target-state structure: compare the normal target-canvas blend with an always-visible target canvas and state-split target branch, while carrying naturalist directsrc `0.18` only as a candidate combination rather than a default.

C111 is complete and gives a cleaner structural signal than the direct-loss branch. Target-canvas `always` beats target-canvas `blend` on every matched no-direct pair: naturalist improves to OCR `0.4954` and residual `0.1158` from `0.4771`/`0.1448`, reef improves to `0.7500`/`0.0380` from `0.4783`/`0.0474`, and transit improves to `0.7000`/`0.0421` from `0.6500`/`0.0513`. Directsrc `0.18` is still unstable in the single-decoder blend/always variants, but state-split + direct passes and lowers naturalist residual to `0.0988` with OCR `0.4348`. C112 should validate `target_canvas=always` across timeline/orbit/deep-sea and a fresh naturalist seed, with one state-split/direct naturalist replicate.

The evaluator now reports endpoint OCR, source-residual gain/cosine, source-only edge bias, and transition-crop equivalents. These metrics should be read separately for endpoint frames, target-midpoint frames, and transition frames; transition-frame residuals are the most relevant metrics for the source-persistence problem.
