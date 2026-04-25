# Track C Clean Page-State Stress

Date: 2026-04-25

## Why This Exists

The latest Flipbook re-check keeps the target clear:

- every page is an image;
- text is rendered as image-model pixels;
- no HTML/layout framework/text overlay is supposed to carry the visible page;
- live video currently appears to be a two-system path, but the long-term claim is one generated visual surface.

Track C is therefore on the right path only if it proves clean generated page states, not just readable transitional frames.

## Current Gap

C82-C85 are testing whether a learned RGB neural texture can preserve high-frequency text/detail while the page reflows. This is useful because the RGB texture is a model parameter, not a runtime compositor.

The weak spot is that the synthetic `target-mid.png` can itself contain transition traces. That makes OCR too generous: a frame can read well while still looking like the old page is faintly stuck underneath the new layout.

The new `change_region_*` eval fields help, but they are still only proxies. They compare model output against source and target in regions where source and target differ; they do not replace human inspection or a cleaner target fixture.

## C86 Direction

C86 should create a clean two-state layout stress:

1. Generate or render a source page image.
2. Generate or render a separate target page image with the same semantic content but a genuinely different layout.
3. Train the neural canvas/video layer to transition between those two clean page states.
4. Evaluate the midpoint and target-side frames against the clean target, not against a region-warped transitional target.

The output must still be direct neural-canvas pixels. Boxes are allowed to synthesize training data and evaluation masks, but not to composite the final visible frame.

## Pass Criteria

A C86 candidate should be considered stronger than C82/C84 only if it improves at least two of these:

- OCR token-F1 at target-heavy frames.
- Change-region target delta.
- Visual absence of old-layout remnants.
- Segment wall time under `1.3s` for 33 frames plus encode.
- Seed repeatability.

It should not be promoted on OCR alone.

## Candidate Implementation

Start with the existing page fixture, but add a second deterministic renderer for the target state:

- move title/subtitle to a narrower header;
- move the diagram into one side panel or a larger central panel;
- move text blocks into different columns;
- change the diagram scale/position enough that a copy-forward solution is visibly wrong;
- keep the text content the same so OCR can still compare against the source transcript.

Then train:

- source frame at `t=0`;
- target frame at `t=0.5`;
- source frame at `t=1`;
- optional in-between interpolation targets, but not if they introduce source ghosts into the target state.

## Decision Rule After C85

If C85 finds a new high-OCR pass with no visual improvement over C82, move directly to C86.

If C85 improves both OCR and change-region target delta, keep one more gate sweep, but still run C86 next. Flipbook's claim is a clean neural page surface, so the next proof needs a cleaner target page either way.

## Implementation Note

C85 did not improve the branch, so C86 is now implemented as `layout-clean-reflow` in `scripts/track_c/modal_canvas_c2_lite.py`. The target midpoint is a separate deterministic page renderer, OCR uses `target-mid.png` as the active reference for clean runs, and `scripts/track_c/autoresearch_loop.py` now queues ten C86 variants ahead of older C85/C84 experiments.

## C87 Generality Check

C86 is a positive proof for the pure neural-canvas direction, but it is still only one clean source-target pair. That is not enough to match Flipbook's public claim. Flipbook is pointing at a renderer where the visible page can become a different generated pixel state under resize, scroll, animation, or interaction.

C87 therefore keeps the C86 winning recipe and changes only the clean target layout family. The two new targets, `right-diagram` and `stacked`, reposition the same semantic content into materially different page states. A pass across these variants would suggest the renderer is learning a more general state-to-state page transform. A failure would mean C86 was more likely a target-fixture fit than a reusable neural page renderer.

## C87 Result And C88 Direction

C87 passed all ten runs. The strongest `right-diagram` run reached OCR `0.9000` at `920.211ms`, while the strongest `stacked` runs reached OCR `1.0000` at `925-942ms`. This is the best evidence so far that the clean page-state result is not just one target fixture.

The remaining visual concern is faint old-source text in some broad diagram regions. C88 therefore removes the easy card-box structure from the target: `unboxed-columns` uses open text columns, and `callout-map` places floating callout text around the diagram. This keeps the Flipbook-aligned target strict: the output is still one generated pixel surface, but the page state is less protected by rectangular text containers.

C88 also passed all ten runs. The strongest `unboxed-columns` run reached OCR `0.9302`, and the harder `callout-map` target still reached OCR `0.7826`. Human review shows the open-column layout is a real improvement over card-box dependence, while callout text is still fragile.

C89 should now change the target copy itself. That matters because Flipbook's claim is not only that existing text can move; the generated page should be able to contain newly rendered words as pixels. The next target variants, `changed-unboxed` and `changed-callout`, keep the layout family but replace section headings/body text with new copy at the target midpoint.

C89 held up well enough to move forward. All ten runs pass the current normalized gates; `changed-callout` is strongest, reaching OCR `0.9259` at `1057.956ms` and OCR `0.8846` at `1196.854ms`, while the fastest good `changed-callout` pass lands at `743.559ms`. `changed-unboxed` is visually readable but weaker by OCR (`0.5000-0.6111`). Human review says the important thing: the new target words are present as model-rendered pixels, but faint old-source remnants remain in open whitespace.

C90 is now running as the next stress. It changes the illustration grammar itself: `timeline-illustration` redraws the target as a construction timeline, and `transit-illustration` redraws it as a route map. This matters because a Flipbook-like neural canvas cannot only preserve a known diagram while text moves around it. It has to repaint different visual explanations as page pixels.

C90 passed all ten runs and is the best generality signal so far. The strongest timeline run reached OCR `0.9091` at `929.222ms`, another timeline run reached OCR `0.8421` at `741.483ms`, and the strongest transit run reached OCR `0.7805` at `912.081ms`. Human review confirms the model redraws a timeline and a route-map page state rather than simply preserving the earlier oval diagram. The next overfit check is C91: unrelated new-topic targets where the title, body copy, and illustration subject all change together.

C91 also passed all ten runs. The strongest orbit-topic run reached OCR `1.0000`, another orbit run reached OCR `0.9286`, and the strongest reef-topic run reached OCR `0.8485`. That is a useful sign that the clean page-state branch is not only a Colosseum layout memorizer. Human crop review still shows faint old-source haze in open regions, so C92 is explicitly a source-remnant stress test.

C92 adds two target styles that should make leakage easier to see. `naturalist-plate` uses a 1800s naturalist-inspired specimen page with engraved fern linework, pinnae labels, and field-note columns. `deep-sea-lab` uses a dark high-contrast scientific cross-section where any light Colosseum/paper remnants should stand out immediately. Both remain pure generated page pixels at render time; the target fixtures exist only as training/evaluation states.

C92 passed all ten initial runs, but the human review exposed a more subtle problem: full-frame midpoints look convincing, while the `crop-2x.png` transition crop exposes old Colosseum text/diagram remnants during the move toward the new page. `deep-sea-lab` reaches much higher OCR (`0.6190-0.8966`) than `naturalist-plate` (`0.4082-0.4964`). C93 therefore adds a model-layer contrastive source-remnant loss as an initial attempt to reduce source persistence.

C93 improved some numbers but did not solve the transition failure. The best naturalist run rose to OCR `0.5424`, and the best deep-sea run held OCR `0.8276`, but the transition crop still shows the source page underneath. C94 moves from loss tuning to decoder architecture: target-state residual, fused residual, gated dual-branch, and latent-both variants.

C94 was a useful endpoint/transition split. Deep-sea full frames can score highly (`0.8667` OCR on dual-residual and dual-gate variants), while naturalist remains worse, topping out at OCR `0.5000`. Corrected midpoint crops look like the new target state; the old `Velarium`/`Materials`/old-diagram ghosts are concentrated in the transition crop rendered at `t=0.25`.

C95 therefore adds a separate learned target-state latent canvas. This is not a text overlay or render-time compositor: the final frame is still generated by the neural canvas MLP. The new target canvas is an additional model-owned latent field sampled at output coordinates, optionally gated by `sin(pi*t)^2` so it has maximum influence near the target midpoint and fades at the source endpoints. The test is whether giving the model an explicit target-state memory reduces source ghosts without giving up the sub-`1.3s` 33-frame budget.

C95 passed numerically and renders clean target midpoint frames, but it does not make the transition crop feel like object/page motion. Concatenating target-state features beside the source latent still leaves the temporal path looking like source persistence. C96 changes the state mechanism from concatenation to midpoint blending: the sampled source latent features are interpolated toward a separate target canvas by `sin(pi*t)^2`, so the midpoint is forced to decode primarily from target-state memory. This is a stricter model-layer test and should be cheaper than C95 because it does not widen the decoder input.

C96 is complete and should be read as target-state positive. It makes render time very consistent and keeps most candidates under the `1.3s` segment budget. A corrected audit shows the target midpoint crop is clean; the old source page appears in `crop-2x.png` because that artifact is a transition frame at `t=0.25`.

C97 therefore splits the renderer more aggressively. The source branch samples the source latent canvas and source-aware coordinates. The target branch samples an independent target latent canvas at output coordinates and does not receive source-coordinate features. The final RGB logits are blended by `sin(pi*t)^2`, so the midpoint is rendered by the target branch rather than a shared source decoder. This is still a pure neural-canvas output: there is no text overlay, mask compositor, or CSS layout at render time. The goal is to test whether harder endpoint isolation changes latency, OCR, and transition-frame persistence.

C97 is complete. It improves the deep-sea endpoint on one seed (`0.8387` OCR at `1002.438ms`) but weakens naturalist relative to C95/C96 (`0.4463` best OCR). The important conclusion is not that state split failed to repaint the target; target midpoint frames are clean. The conclusion is that endpoint isolation does not address the transition path because the current `layout-clean-reflow` target is a source/target blend.

C98 made transition quality explicit. It saves and scores target crops at `t=0.25` and `t=0.50`, and trains `layout-clean-move-reveal` instead of only endpoint interpolation. After correcting the OCR reference for this clean mode, six of eight runs pass. The best deep-sea move/reveal run reaches OCR `0.8966` at `939.032ms`; the best naturalist move/reveal run reaches OCR `0.4839` at `1074.523ms`.

C98 is not the end state. It shows that transition targets are useful and that deep-sea-style page repainting can survive a harder moving target. It also shows that naturalist etching/text is still brittle and that state-split does not generalize as a fix. C99 therefore moves to independent recomposition: source regions translate separately while the target page arrives through region-specific motion fields. That is closer to resize/re-layout behavior than a single global move/reveal.

C99 is complete and gives the strongest transition-specific signal after C98. Deep-sea independent recomposition passes across base, target-blend, and state-split variants; the best target-blend run reaches midpoint OCR `0.8667`, endpoint OCR `0.8054/0.8326`, and segment `1121.871ms`. Naturalist is still the brittle target: target-blend and state-split preserve endpoints but mid-transition text remains weak, and the base run now fails after endpoint OCR gating catches source/final-frame collapse.

The next step is C100, a generalization wave. It applies independent recomposition to timeline, transit, reef, and orbit page targets so the branch does not overfit only to naturalist/deep-sea stress fixtures. It also repeats naturalist/deep-sea with the endpoint-preserving variants. If C100 generalizes, the branch should become a serious candidate for the Track D model-layer prototype; if it fails outside the two stress fixtures, the next move should be a broader target distribution rather than more scalar tuning.

C100 did generalize. All eight independent-recomposition runs pass endpoint-aware gates across timeline, transit, reef, orbit, naturalist, and deep-sea. This is now a serious Track D candidate for the model-layer prototype: it can render materially different target pages as pixels while preserving readable source/final endpoints.

The caveat is still transition cleanliness. Timeline, transit, reef, orbit, and naturalist all retain positive transition source-residual gain, even when target midpoint pages look good. Deep-sea is the exception, with negative transition source-residual gain. C101 should therefore change the source-remnant loss itself: compare pixels against the synthetic transition target, not only the static clean target midpoint, so transition frames are penalized when they remain closer to the old source page than to the intended in-between page state.

C101 is a partial improvement, not a cleanup proof. Five of six runs pass; the naturalist state-split run only misses latency at `1303.659ms`. Midpoint OCR is strong for timeline (`0.9677`), deep-sea (`0.8276`), orbit (`0.8000`), and reef (`0.7742`), while naturalist remains usable but weak (`0.4737`). Transition source-residual gain is lower for several targets but still positive for timeline (`0.0844`), orbit (`0.0557`), reef (`0.0701`), and naturalist (`0.1510-0.1523`); deep-sea is effectively neutral (`-0.0016`). C102 should keep the truth-referenced remnant loss but lower the transition time exponent so anti-source pressure turns on earlier than the current squared midpoint weighting.

C102 confirms that earlier remnant timing helps the residual metric, but the cleanest timing is target-dependent. The `time_power=1.0` runs pass for timeline, reef, orbit, and deep-sea, with transition source-residual gain improving to `0.0633`, `0.0313`, `0.0488`, and `0.0043` respectively. Naturalist `time_power=1.0` fails OCR at `0.3208`, while naturalist `time_power=0.5` passes at OCR `0.4118` and improves residual gain to `0.1136`. C103 should consolidate `time_power=0.5` across the non-naturalist targets and probe naturalist with both earlier timing and stronger remnant weight.

C103 shows scalar timing alone is not enough. The `time_power=0.5` consolidation keeps OCR healthy, but transition source-residual gain does not consistently improve over C102: timeline is `0.0654`, orbit `0.0546`, reef `0.0406`, and deep-sea `0.0135`. Naturalist `time_power=0.25` is the best same-seed naturalist probe (`0.1324` gain, OCR `0.4000`), while stronger remnant weight misses latency and does not improve residual gain. C104 should target the sampling distribution itself by reserving training points on source-only remnant edges at transition times.

C104 is a useful negative for heavy source-only remnant-edge sampling. The `srcsample18` reserve keeps most runs passing, but it does not produce a cleanup breakthrough: timeline worsens to `0.0783` transition source-residual gain, reef to `0.0520`, and naturalist remains weak (`0.1390` at OCR `0.3519`; the `time_power=0.25` variant fails OCR). Orbit improves slightly to `0.0452` and deep-sea remains near-neutral at `0.0021`, but both lose OCR relative to their best C102/C103 probes. C105 should repeat the same seed/variant matrix with a lighter `srcsample06` reserve to separate "sampling helps if gentle" from "sampling is the wrong lever."

C105 keeps OCR healthier but does not make source-edge sampling the next lever. Timeline (`0.0691`), reef (`0.0598`), orbit (`0.0550`), and deep-sea (`0.0133`) remain worse than their best C102/C103 residual points. Naturalist `time_power=0.25` is the only useful pass (`0.1235` gain, OCR `0.3689`), while `time_power=0.5` misses latency at `1303.764ms`. C106 should stop moving sampling mass around and instead make the loss less permissive: keep the truth-referenced contrastive margin, but add direct weighted L1 pressure toward the synthetic transition target on source-remnant regions.
