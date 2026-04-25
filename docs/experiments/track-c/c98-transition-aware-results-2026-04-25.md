# C98 Transition-Aware Move/Reveal Results

Date: 2026-04-25

## Summary

C98 is the first Track C wave that treats transition frames as first-class artifacts instead of judging only the clean target midpoint. It adds:

- `layout-clean-move-reveal`, where the source layer moves/fades while the clean target page eases in.
- `target-crop-2x.png`, a transition target crop at `t=0.25`.
- `target-mid-crop-2x.png`, a clean target crop at `t=0.5`.
- normalized transition metrics in `eval-results.tsv`.

Important correction: the original remote C98 `quality.json` files compared OCR against the source input because the clean-reference mode allowlist did not include `layout-clean-move-reveal`. Local quality/eval was recomputed against `target-mid.png`, which is the correct reference for this clean target branch.

## Results

| Run | Status | OCR | Segment | Effective FPS | Transition Similarity | Transition Source Gain |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| `c98-v12-deep-sea-movereveal-tblend-init02-rem050-mid20-seed0-s12000` | pass | 0.8966 | 939.032ms | 35.14 | 0.9657 | -0.0310 |
| `c98-v12-deep-sea-movereveal-base-rem050-mid20-seed0-s12000` | pass | 0.8571 | 917.112ms | 35.98 | 0.9643 | -0.0315 |
| `c98-v12-deep-sea-movereveal-statesplit-init02-rem050-mid20-seed1-s12000` | pass | 0.8276 | 1019.813ms | 32.36 | 0.9668 | -0.0289 |
| `c98-v12-deep-sea-movereveal-tblend-init02-rem050-mid20-seed1-s12000` | pass | 0.7222 | 1097.338ms | 30.07 | 0.9653 | -0.0349 |
| `c98-v11-naturalist-movereveal-base-rem025-mid35-seed0-s12000` | pass | 0.4839 | 1074.523ms | 30.71 | 0.9657 | 0.1051 |
| `c98-v11-naturalist-movereveal-tblend-init02-rem025-mid35-seed0-s12000` | pass | 0.4330 | 1099.476ms | 30.01 | 0.9699 | 0.0551 |
| `c98-v11-naturalist-movereveal-tblend-init02-rem025-mid50-seed0-s12000` | quality_fail | 0.2857 | 1135.674ms | 29.06 | 0.9706 | 0.0802 |
| `c98-v11-naturalist-movereveal-statesplit-init02-rem025-mid50-seed0-s12000` | quality_fail | 0.0702 | 1134.158ms | 29.10 | 0.9698 | 0.0872 |

## Readout

C98 is positive for transition-aware target definition and negative for state-split as a general fix. Deep-sea move/reveal is strong: it reaches OCR `0.8966` under `1.0s` for 33 frames plus encode. Naturalist remains harder, especially with state-split, because thin etched lines and small labels lose text quality under the harder transition target.

The new transition crop metrics are useful. Deep-sea runs show negative transition source-residual gain, which means the render is less source-like than the source page in changed regions. Naturalist has positive transition source gain, so source persistence is still more visible there.

## Next Step

C99 should not be another scalar sweep. It should test independent page-region recomposition: source regions translate separately while the target page arrives through its own region-specific motion field. This is closer to the resize/re-layout behavior the Flipbook direction needs to prove.
