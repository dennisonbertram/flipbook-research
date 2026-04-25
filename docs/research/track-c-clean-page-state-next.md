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

C90 is queued as the next stress if C89 holds up. It changes the illustration grammar itself: `timeline-illustration` redraws the target as a construction timeline, and `transit-illustration` redraws it as a route map. This matters because a Flipbook-like neural canvas cannot only preserve a known diagram while text moves around it. It has to repaint different visual explanations as page pixels.
