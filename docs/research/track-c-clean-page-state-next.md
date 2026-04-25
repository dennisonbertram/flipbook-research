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

C92 passed all ten initial runs, but the human review is the real result: full-frame midpoints look convincing, while 2x crops still expose old Colosseum text/diagram remnants under the new page. `deep-sea-lab` reaches much higher OCR (`0.6190-0.8966`) than `naturalist-plate` (`0.4082-0.4964`), but both show the same source-ghost failure in close inspection. C93 therefore adds a model-layer contrastive source-remnant loss that penalizes clean-reflow midpoint pixels when they remain closer to the source page than to the clean target.

C93 improved some numbers but did not solve the visual failure. The best naturalist run rose to OCR `0.5424`, and the best deep-sea run held OCR `0.8276`, but the crop still shows the source page underneath. C94 moves from loss tuning to decoder architecture: target-state residual, fused residual, gated dual-branch, and latent-both variants. The hypothesis is that a single source-biased latent/decoder is not enough to overwrite high-frequency source structure cleanly.

C94 was a useful negative. Deep-sea full frames can score highly (`0.8667` OCR on dual-residual and dual-gate variants) and still show the old source layer in close crops. Naturalist remains worse, topping out at OCR `0.5000`. The important human-read result is that target-branch decoders make attractive full-frame midpoint renders but do not cleanly erase `Velarium`/`Materials`/old-diagram ghosts in inspected crops.

C95 therefore adds a separate learned target-state latent canvas. This is not a text overlay or render-time compositor: the final frame is still generated by the neural canvas MLP. The new target canvas is an additional model-owned latent field sampled at output coordinates, optionally gated by `sin(pi*t)^2` so it has maximum influence near the target midpoint and fades at the source endpoints. The test is whether giving the model an explicit target-state memory reduces source ghosts without giving up the sub-`1.3s` 33-frame budget.
