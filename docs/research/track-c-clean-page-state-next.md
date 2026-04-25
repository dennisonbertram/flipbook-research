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
