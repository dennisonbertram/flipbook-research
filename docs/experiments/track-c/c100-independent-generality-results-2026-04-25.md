# C100 Independent Generality Results

Date: 2026-04-25

## Question

C99 showed that independent recomposition can work on the two source-remnant stress fixtures, especially `deep-sea-lab`. C100 asks whether that direction generalizes to other target pages or whether it is only tuned to naturalist/deep-sea.

The output remains direct neural-canvas pixels. The target pages and regions define the synthetic training/eval target only.

## Results

| Run | Status | Segment | FPS | Mid OCR | Source OCR | Last OCR | Transition Sim | Source Residual Gain |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `c100-v07-timeline-indrecomp-tblend-mid35-seed0-s12000` | pass | `1283.815ms` | `25.705` | `0.9375` | `0.7658` | `0.7945` | `0.9679` | `0.0969` |
| `c100-v08-transit-indrecomp-tblend-mid35-seed0-s12000` | pass | `1082.884ms` | `30.474` | `0.7179` | `0.8128` | `0.8037` | `0.9664` | `0.1039` |
| `c100-v09-reef-indrecomp-tblend-mid35-seed0-s12000` | pass | `1106.804ms` | `29.816` | `0.5116` | `0.7964` | `0.7838` | `0.9692` | `0.0683` |
| `c100-v10-orbit-indrecomp-tblend-mid35-seed0-s12000` | pass | `1099.643ms` | `30.010` | `0.8235` | `0.8161` | `0.8182` | `0.9706` | `0.1072` |
| `c100-v11-naturalist-indrecomp-tblend-mid60-seed1-s12000` | pass | `1144.546ms` | `28.832` | `0.3968` | `0.7431` | `0.7685` | `0.9606` | `0.1963` |
| `c100-v11-naturalist-indrecomp-statesplit-mid60-seed1-s12000` | pass | `1151.211ms` | `28.665` | `0.4138` | `0.5562` | `0.4194` | `0.9594` | `0.1885` |
| `c100-v12-deep-sea-indrecomp-tblend-mid25-seed1-s12000` | pass | `1101.345ms` | `29.963` | `0.8000` | `0.7873` | `0.7465` | `0.9661` | `-0.0174` |
| `c100-v12-deep-sea-indrecomp-statesplit-mid25-seed2-s12000` | pass | `1265.331ms` | `26.080` | `0.8276` | `0.8311` | `0.8037` | `0.9672` | `-0.0172` |

## Read

C100 is a strong positive for generalization of clean page-state rendering. Timeline, transit, reef, orbit, naturalist, and deep-sea all pass the endpoint-aware gates. The model is not just overfit to the two C99 stress targets.

The visual read is more specific:

- Target midpoint pages are genuinely different pages.
- Source and final loop endpoints remain readable.
- Transition crops still contain source haze over the old diagram/text regions.
- Deep-sea is the only family with negative transition source-residual gain in C100.

That means the branch is good at endpoint/midpoint neural rendering, but the transition path still needs sharper anti-source pressure. The next work should not be another endpoint tuning sweep. It should change the transition loss so the model is penalized when transition-frame pixels remain closer to the source page than the synthetic transition target.

## Decision

C100 upgrades independent recomposition from "promising on one or two fixtures" to "viable general model-layer direction."

C101 should be a transition-specific source-remnant wave:

- keep the C100 independent-recomposition target;
- compare clean-target remnant loss against transition-target remnant loss;
- run the comparison on timeline, orbit, reef, naturalist, and deep-sea;
- keep endpoint OCR gates mandatory so anti-source pressure cannot corrupt clean endpoints.
