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

## Results

Evaluation artifact: `docs/experiments/track-c/eval-results-c124.tsv`

| Run | Status | OCR min | Motion | Target-mid delta | Transition-crop delta | Transition source bias | Failed gates |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| `c124-v13-glacier-geom-midforced-rgbskip-scoord-seed21-s12000` | quality_fail | 0.1857 | 0.0872 | 0.0188 | 0.0542 | -0.2176 | `ocr_token_f1<0.4500,source_frame_ocr<0.3500,last_frame_ocr<0.3500` |
| `c124-v13-glacier-geom-oracle-rgbskip-scoord-seed21-s12000` | quality_fail | 0.2675 | 0.0914 | 0.0135 | 0.0179 | -0.3069 | `ocr_token_f1<0.4500,source_frame_ocr<0.3500,last_frame_ocr<0.3500` |
| `c124-v14-microchip-geom-midforced-rgbskip-scoord-seed22-s12000` | quality_fail | 0.2794 | 0.0830 | 0.0190 | 0.0633 | -0.1854 | `ocr_token_f1<0.4500,source_frame_ocr<0.3500,last_frame_ocr<0.3500` |
| `c124-v14-microchip-geom-oracle-rgbskip-scoord-seed22-s12000` | quality_fail | 0.3111 | 0.0861 | 0.0136 | 0.0177 | -0.2857 | `ocr_token_f1<0.4500,source_frame_ocr<0.3500,last_frame_ocr<0.3500` |
| `c124-v15-mycology-geom-midforced-rgbskip-scoord-seed23-s12000` | quality_fail | 0.2099 | 0.0938 | 0.0144 | 0.0608 | -0.2374 | `ocr_token_f1<0.4500,source_frame_ocr<0.3500,last_frame_ocr<0.3500` |
| `c124-v15-mycology-geom-oracle-rgbskip-scoord-seed23-s12000` | quality_fail | 0.1988 | 0.0942 | 0.0141 | 0.0180 | -0.3376 | `ocr_token_f1<0.4500,last_frame_ocr<0.3500` |

## Visual Read

The generated-source runs do not look like semantic page re-layout. They look like transported page regions: broad figure masses move into the right geometry, but text and fine structure smear or ghost. Oracle flow improves the transported figure crop, but it still behaves like image-space warping/alpha relocation rather than re-authoring a layout.

This is a useful negative result. C124 shows that the generated-source case does not merely need another seed or a stricter target-mid loss. The current architecture is strongly biased toward source-coordinate texture transport, especially with RGB skip enabled. It can move pixels into the expected target geometry, but it is not parsing page objects and re-rendering them as a new document.

## Interpretation

C124 should be treated as a transport-generalization failure, not as evidence of successful re-layout. The metrics still show target closeness because the target itself is geometric transport. The human read is more decisive here: the output resembles masks/flows moving rendered content, and OCR confirms that the document state is not preserved.

The next useful diagnostic should remove the transport shortcut (`rgb_skip_scale=0`, target-coordinate latent sampling, no source-coordinate features) or compare directly to a simple masked-warp baseline. If performance collapses, we have confirmed that the apparent progress depended on image transport rather than re-layout. If it holds, then the model is at least learning a direct keyframe renderer, but that still needs a separate test for object-level layout semantics.
