# C99 Independent Recomposition Results

Date: 2026-04-25

## Question

C98 proved that explicit transition targets were more honest than clean midpoint repainting alone, but the transition still behaved too much like a single source/target move-reveal field.

C99 asks a harder question: can the neural canvas render independently moving/recomposing page regions while still resolving to a clean target page and returning to a clean source page?

This is still pure neural-canvas rendering. The boxes and regions define the synthetic training/eval target; the model output is direct pixels from the renderer.

## Evaluator Change

C99 exposed an eval gap: target-mid OCR was not enough. A run can make the midpoint readable while corrupting the clean source or final loop frame.

The evaluator now records and gates:

- `source_frame_ocr_f1`
- `last_frame_ocr_f1`

The default endpoint gate is `0.35`. This correctly marks the naturalist base C99 run as `quality_fail`.

## Results

| Run | Status | Segment | FPS | Mid OCR | Source OCR | Last OCR | Transition Sim | Source Residual Gain |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `c99-v11-naturalist-indrecomp-base-rem025-mid50-seed0-s12000` | quality_fail | `910.482ms` | `36.245` | `0.3636` | `0.1379` | `0.1677` | `0.9448` | `0.2314` |
| `c99-v11-naturalist-indrecomp-tblend-init02-rem025-mid50-seed0-s12000` | pass | `1127.398ms` | `29.271` | `0.4590` | `0.7064` | `0.7156` | `0.9595` | `0.1756` |
| `c99-v11-naturalist-indrecomp-statesplit-init02-rem025-mid50-seed0-s12000` | pass | `1158.505ms` | `28.485` | `0.3967` | `0.8378` | `0.7964` | `0.9592` | `0.1683` |
| `c99-v12-deep-sea-indrecomp-base-rem050-mid35-seed0-s12000` | pass | `936.786ms` | `35.227` | `0.8276` | `0.7143` | `0.6769` | `0.9627` | `-0.0237` |
| `c99-v12-deep-sea-indrecomp-tblend-init02-rem050-mid35-seed0-s12000` | pass | `1121.871ms` | `29.415` | `0.8667` | `0.8054` | `0.8326` | `0.9641` | `-0.0233` |
| `c99-v12-deep-sea-indrecomp-statesplit-init02-rem050-mid35-seed1-s12000` | pass | `1264.919ms` | `26.089` | `0.7027` | `0.8532` | `0.8402` | `0.9671` | `-0.0157` |

## Read

C99 is real progress, but it is not a finished proof.

The positive result is that independent recomposition can preserve endpoints and target-state readability under the `1.3s` 33-frame segment budget. Deep-sea is especially strong: all three runs pass, the best midpoint OCR reaches `0.8667`, and source residual gain is negative.

The negative result is that naturalist remains fragile. Target blend and state split preserve endpoints, but midpoint text is only weakly readable and the transition still carries positive source residual gain. The naturalist base run also shows why endpoint gating matters: it looked barely acceptable by midpoint OCR, but it destroyed the clean source and final loop frames.

## Decision

C99 should be treated as a viable direction because it is no longer a single global wiggle or simple crossfade. It forces regions to move and resolve independently.

The next wave should test generalization rather than only tuning naturalist/deep-sea:

- apply independent recomposition to timeline, transit, reef, and orbit target pages;
- repeat naturalist and deep-sea with the two most useful endpoint-preserving paths;
- keep endpoint OCR and transition residual metrics mandatory.

That queue is C100.
