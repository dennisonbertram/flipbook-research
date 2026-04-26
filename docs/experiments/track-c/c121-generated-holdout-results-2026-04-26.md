# C121 Generated Holdout Families

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

## Interpretation

C121 does not support a single universal policy, but it also does not look like complete overfitting to the original six target families.

What held:

- All three generated families produced a recognizably separate clean midpoint state with strong motion (`motion_delta` about 0.10-0.11) and low loop error.
- Four of six policy runs passed outright.
- The two failures were near misses: glacier midpoint-gated source-coordinate improved OCR but missed latency by 15.1 ms; mycology no-source missed the OCR threshold by 0.0022.

What changed:

- Glacier preferred midpoint-gated source-coordinate on quality, but no-source was the passing policy under the strict latency gate.
- Microchip did not need full source-coordinate; no-source was slightly better and faster.
- Mycology reversed the C120 naturalist result: the source-coordinate midpoint gate rescued OCR, while no-source fell just below threshold.

Conclusion: the mechanism generalizes as a conditional policy family, but the current routing rule is not stable enough yet. The next useful evidence would be a tiny repeat with fresh generated assets or seeds for these same three families. If the policy preference flips again under repeats, the routing is overfit; if the pass/fail pattern is stable, the next step is to learn a family classifier or proxy metric for source-coordinate gating.
