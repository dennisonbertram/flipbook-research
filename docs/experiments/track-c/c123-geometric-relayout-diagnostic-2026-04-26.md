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
