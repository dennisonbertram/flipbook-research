# C123 Geometric Relayout Diagnostic

Date: 2026-04-26

## Question

Are the recent clean-page runs showing real re-layout, or mostly a learned source-to-target fade?

C123 removes the clean-target crossfade escape hatch. The target is the original source page geometrically re-laid out by moving/resizing page regions, so a fade/static explanation should score poorly against `target-mid.png` and transition-crop metrics.

## Matrix

| Run | Purpose |
| --- | --- |
| `c123-geom-rgbskip-scoord-seed20-s14000` | C82-style geometric reflow baseline using source RGB skip and learned flow. |
| `c123-geom-midforced-rgbskip-scoord-seed20-s14000` | Same baseline, but samples the target midpoint directly and adds paired target loss to pressure actual relocation. |
| `c123-geom-flowloss-rgbskip-scoord-seed20-s14000` | Adds explicit source-coordinate flow supervision. If this helps, the bottleneck is learned motion/where-to-sample. |
| `c123-geom-oracle-rgbskip-scoord-seed20-s14000` | Uses oracle inverse layout flow. This is the upper bound: can the decoder render relocated source pixels when given the correct correspondence? |

## Readout

Useful evidence is not just OCR pass/fail. The important fields are:

- `target_mid_delta`: midpoint render vs geometric relayout target.
- `transition_crop_delta`: transition crop vs geometric transition target.
- `change_region_source_bias`: whether changed regions remain closer to the source than target.
- visual contact sheet: whether moved panels appear as relocated source content or as ghosted interpolation.

If the oracle run is clean and learned-flow runs are not, the current architecture can render re-layout but does not learn correspondence robustly. If oracle also looks like a fade, the decoder/canvas representation is the bottleneck.

## Results

Evaluation artifact: `docs/experiments/track-c/eval-results-c123.tsv`

| Run | Status | OCR min | Motion | Target-mid delta | Transition-crop delta | Transition source bias | Failed gates |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `c123-geom-rgbskip-scoord-seed20-s14000` | pass | 0.6354 | 0.0470 | 0.0132 | 0.0392 | -0.2287 | - |
| `c123-geom-midforced-rgbskip-scoord-seed20-s14000` | pass | 0.6120 | 0.0463 | 0.0147 | 0.0561 | -0.1808 | - |
| `c123-geom-oracle-rgbskip-scoord-seed20-s14000` | quality_fail | 0.5294 | 0.0470 | 0.0136 | 0.0183 | -0.3036 | `ocr_token_f1<0.5500` |
| `c123-geom-flowloss-rgbskip-scoord-seed20-s14000` | quality_fail | 0.5116 | 0.0466 | 0.0136 | 0.0535 | -0.1952 | `ocr_token_f1<0.5500` |

## Visual Read

The learned-flow and mid-forced runs are not just leaving the source page in place: the midpoint frame is close to the geometric target (`target_mid_delta` near 0.013-0.015), and changed regions are closer to target than source (`transition_change_region_source_bias` is negative).

But the transition crops still look like soft relocation with ghosting, especially around the diagram and text edges. The oracle-flow run has the best transition crop (`transition_crop_delta=0.0183`) and looks visibly cleaner in the moved diagram region, but it drops below the OCR gate. Explicit flow loss did not help in this configuration.

## Interpretation

C123 weakens the pure-crossfade explanation: when the target is a geometric relayout of the source page, the model can produce target-like midpoint frames rather than merely blending between unrelated clean pages.

It does not yet prove robust semantic re-layout. The current learned-flow policy seems to move page mass into the right broad geometry, but with blur/ghosting instead of crisp, object-preserving transport. The oracle result points toward a correspondence bottleneck more than a total decoder bottleneck, though the OCR drop says the decoder/render path still degrades fine text under stronger geometric sampling.

The next diagnostic should combine this crossfade-resistant geometric target with the generated holdout page families from C121/C122.
