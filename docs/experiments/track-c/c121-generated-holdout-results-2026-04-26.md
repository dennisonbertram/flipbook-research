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

Pending C121 runs:

- `c121-v13-glacier-indrecomp-blend-noscoord-truthrem075-tpow1-seed14-s12000`
- `c121-v13-glacier-indrecomp-blend-scoordmid0-truthrem075-tpow1-seed14-s12000`
- `c121-v14-microchip-indrecomp-talways-noscoord-truthrem075-tpow1-seed15-s12000`
- `c121-v14-microchip-indrecomp-talways-scoordfull-truthrem075-tpow1-seed15-s12000`
- `c121-v15-mycology-indrecomp-talways-noscoord-truthrem075-tpow025-seed16-s12000`
- `c121-v15-mycology-indrecomp-talways-scoordmid025-truthrem075-tpow025-seed16-s12000`

## Interpretation

Pending.
