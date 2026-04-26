# C121-C122 Generated Holdout Families

Date: 2026-04-26

## Question

Does the C120 conclusion generalize to unseen page families when the target page uses generated bitmap illustrations rather than only deterministic PIL diagrams?

This is a holdout probe, not a new tuning loop. Each family gets two policy variants: one policy suggested by the C120 conditional rule and one nearby counter-policy.

## Generated Assets

GPT Image 2 generated three no-text illustration fixtures:

- `fixtures/track-c/generated-holdouts/glacier-field-guide.png`
- `fixtures/track-c/generated-holdouts/microchip-teardown.png`
- `fixtures/track-c/generated-holdouts/mycology-field-guide.png`

The clean target page wrappers are deterministic PIL layouts. The generated bitmap is pasted into the main figure panel and page text/callouts are drawn by the fixture code.

## Matrix

| Family | Target Variant | Candidate Policy | Counter-Policy |
| --- | --- | --- | --- |
| Glacier field guide | `glacier-field-guide` | no source-coordinate | midpoint-gated source-coordinate scale 0 |
| Microchip teardown | `microchip-teardown` | no source-coordinate | full source-coordinate |
| Mycology field guide | `mycology-field-guide` | no source-coordinate | midpoint-gated source-coordinate scale 0.25 |

## Results

| Run | Policy | Status | OCR F1 | Motion | Loop Error | Failed Gates |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `c121-v13-glacier-indrecomp-blend-noscoord-truthrem075-tpow1-seed14-s12000` | no source-coordinate | pass | 0.5714 | 0.1014 | 0.0020 | - |
| `c121-v13-glacier-indrecomp-blend-scoordmid0-truthrem075-tpow1-seed14-s12000` | midpoint-gated source-coordinate scale 0 | latency_fail | 0.6429 | 0.1020 | 0.0025 | `segment_wall_ms>1300` |
| `c121-v14-microchip-indrecomp-talways-noscoord-truthrem075-tpow1-seed15-s12000` | no source-coordinate | pass | 0.7018 | 0.1126 | 0.0015 | - |
| `c121-v14-microchip-indrecomp-talways-scoordfull-truthrem075-tpow1-seed15-s12000` | full source-coordinate | pass | 0.6923 | 0.1109 | 0.0008 | - |
| `c121-v15-mycology-indrecomp-talways-noscoord-truthrem075-tpow025-seed16-s12000` | no source-coordinate | quality_fail | 0.3478 | 0.1064 | 0.0015 | `ocr_token_f1<0.3500` |
| `c121-v15-mycology-indrecomp-talways-scoordmid025-truthrem075-tpow025-seed16-s12000` | midpoint-gated source-coordinate scale 0.25 | pass | 0.3692 | 0.1065 | 0.0012 | - |

## C122 Seed Repeat

C122 repeats the same generated holdout assets and policy pairs with fresh training seeds. This tests whether the C121 policy preference was stable or just one-seed noise.

| Run | Policy | Status | OCR F1 | Motion | Loop Error | Failed Gates |
| --- | --- | --- | ---: | ---: | ---: | --- |
| `c122-v13-glacier-indrecomp-blend-noscoord-truthrem075-tpow1-seed17-s12000` | no source-coordinate | pass | 0.5600 | 0.1010 | 0.0016 | - |
| `c122-v13-glacier-indrecomp-blend-scoordmid0-truthrem075-tpow1-seed17-s12000` | midpoint-gated source-coordinate scale 0 | pass | 0.4789 | 0.1012 | 0.0013 | - |
| `c122-v14-microchip-indrecomp-talways-noscoord-truthrem075-tpow1-seed18-s12000` | no source-coordinate | pass | 0.7857 | 0.1131 | 0.0014 | - |
| `c122-v14-microchip-indrecomp-talways-scoordfull-truthrem075-tpow1-seed18-s12000` | full source-coordinate | pass | 0.6786 | 0.1100 | 0.0007 | - |
| `c122-v15-mycology-indrecomp-talways-noscoord-truthrem075-tpow025-seed19-s12000` | no source-coordinate | pass | 0.5854 | 0.1068 | 0.0015 | - |
| `c122-v15-mycology-indrecomp-talways-scoordmid025-truthrem075-tpow025-seed19-s12000` | midpoint-gated source-coordinate scale 0.25 | pass | 0.4615 | 0.1068 | 0.0011 | - |

## Interpretation

C121 does not support a single universal policy, but it also does not look like complete overfitting to the original six target families.

What held:

- All three generated families produced a recognizably separate clean midpoint state with strong motion (`motion_delta` about 0.10-0.11) and low loop error.
- Four of six policy runs passed outright.
- The two failures were near misses: glacier midpoint-gated source-coordinate improved OCR but missed latency by 15.1 ms; mycology no-source missed the OCR threshold by 0.0022.

What changed:

- Glacier preferred midpoint-gated source-coordinate on quality, but no-source was the passing policy under the strict latency gate.
- Microchip did not need full source-coordinate; no-source was slightly better and faster.
- Mycology reversed the C120 naturalist result in C121: the source-coordinate midpoint gate rescued OCR, while no-source fell just below threshold.

C122 strengthens the mechanism result and weakens the hand-written routing result. Across C121-C122, ten of twelve generated-holdout runs pass, and the two C121 failures were near misses. The C122 seed repeat passes all six runs, with no-source-coordinate taking the best OCR on glacier, microchip, and mycology. But the C121-to-C122 preference movement is real: glacier midpoint-gated source-coordinate moved from quality-better/latency-fail to lower-OCR/pass, and mycology moved from midpoint-gated rescue to no-source winner.

Conclusion: the mechanism generalizes beyond the original deterministic page families. The current hand-written policy router does not generalize cleanly yet. The next useful evidence should use fresh generated assets, not more seed repeats on these exact three images; if no-source-coordinate keeps winning on fresh generated assets, it becomes a good default for generated illustration pages while source-coordinate gating remains a fallback rather than a routed rule.
