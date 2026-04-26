# C124 Generated Source Geometric Relayout

Date: 2026-04-26

## Question

Does the C123 geometric-relayout behavior transfer to the generated holdout page families, or was it mostly tuned to the built-in source page?

C124 uses the GPT Image 2 holdout families as the actual source `input.png`, then trains `layout-reflow` geometric movement from that source page. This keeps the C123 crossfade-resistant target while testing unseen page families.

## Matrix

| Run | Source family | Purpose |
| --- | --- | --- |
| `c124-v13-glacier-geom-midforced-rgbskip-scoord-seed21-s12000` | glacier field guide | Learned-flow generated-source baseline. |
| `c124-v13-glacier-geom-oracle-rgbskip-scoord-seed21-s12000` | glacier field guide | Oracle-flow upper bound for the same source. |
| `c124-v14-microchip-geom-midforced-rgbskip-scoord-seed22-s12000` | microchip teardown | Learned-flow generated-source baseline. |
| `c124-v14-microchip-geom-oracle-rgbskip-scoord-seed22-s12000` | microchip teardown | Oracle-flow upper bound for the same source. |
| `c124-v15-mycology-geom-midforced-rgbskip-scoord-seed23-s12000` | mycology field guide | Learned-flow generated-source baseline. |
| `c124-v15-mycology-geom-oracle-rgbskip-scoord-seed23-s12000` | mycology field guide | Oracle-flow upper bound for the same source. |

## Readout

Use the same stricter fields as C123:

- `target_mid_delta`: whether the midpoint hits the generated-source geometric target.
- `transition_crop_delta`: whether transition crops preserve relocated structure.
- `transition_change_region_source_bias`: whether changed pixels are closer to source or target.
- contact sheets and temporal thumbnails: whether this is crisp relayout, blurry relocation, or a source/target fade.

If learned-flow runs degrade while oracle-flow remains clean, the bottleneck is correspondence learning on unseen page families. If both degrade, the current canvas/decoder path is still not robust enough for generated holdout pages.
