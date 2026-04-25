# Flipbook Public Claims Grounding

Date: 2026-04-25

Sources:

- https://flipbook.page/
- https://xcancel.com/zan2434/status/2046982383430496444

## What Flipbook Says It Is

Flipbook describes itself as an infinite visual browser generated on demand in real time. The important product claim is not "animated images" by itself; it is that each page is an image, and the browsing surface is generated pixels rather than HTML, code, links, fields, or a fixed layout engine.

The X launch thread phrases the same thesis as every pixel being streamed from a model, with no HTML or layout engine. It also says the lack of a strict layout engine lets illustrations reshape to the window and lets any image region become interactive.

Re-review note: this is still the north star. The breakthrough claim is not a better UI renderer around model assets; it is a page/runtime where the visible surface is model-rendered pixels and interaction happens by asking the model/system to produce the next visible state.

## Text Claim

Flipbook explicitly says the text is rendered by the image model as pixels, with no text overlays applied to the images. It also acknowledges that text can be imperfect or misplaced today.

Implication for this repo: text overlays, OCR patch replacement, and mask compositing are useful diagnostics, but they are not the target architecture. Track C should keep moving toward generated text as model output pixels, even when the text benchmark is painful.

## Video Claim

Flipbook describes live video as an experimental feature that animates static images and creates seamless transitions. The site says it currently combines two separate systems: a custom optimized video generation model plus the image generation system, with an expectation that these eventually become one system.

The launch thread says the video path used a heavily optimized LTXStudio video model, streaming 1080p at 24fps through websockets to Modal GPU infrastructure.

Implication for this repo: the model layer is still the core bottleneck, but it may be acceptable for the proof of concept to separate image/page generation from video animation at first. A single unified neural canvas remains the cleaner long-term target.

Observed client hint from the public page bundle: the live stream path sends a current page image to a websocket endpoint and requests `frame_rate: 24` with `num_frames` defaulting to 33 for page animation. That reinforces the idea that the static page generator and video animator are separable today, even if Flipbook's stated long-term direction is a unified system.

## What This Means For Track C

Track C is on the right path when it tests:

- direct neural-canvas pixels, including text;
- reflow and resize, not just local wiggle;
- generated page states that can move content and change layout;
- latency against a 33-frame segment budget;
- no render-time text overlays or layout framework.
- independent region motion, because real interaction and resize are not just global elastic distortion;
- model changes that make the generated surface more general rather than more tuned to a single demo image.

Track C is drifting when it optimizes:

- rectangular text anchoring as a product technique;
- global wobble that preserves everything elastically;
- query-time compositing tricks that would not generalize to arbitrary page content;
- OCR alone without visual layout change.
- masks that protect one known text box while the rest of the page stays structurally static.

## Current Alignment

C57-C64 were aligned with Flipbook's public claim because they used learned layout reflow where the midpoint is a different page layout and the model rendered the output pixels. The C62 high-water result proved the path could hit high text quality once, but C63 showed it was not stable enough.

C65-C69 are still aligned because they keep the output as generated pixels while testing model-layer mechanisms for stability under page changes:

- C65 endpoint anchoring was a useful negative result; it did not solve text stability.
- C66 latent-neighborhood decoding was the first positive architectural signal after source-coordinate conditioning, but it was seed-sensitive.
- C68 coarse context improved the frontier with light context, while heavy context regressed.
- C69 is the current robustness check: if light context holds across seeds, Track C should consolidate around that architecture; if it collapses, the next move should shift toward objective/data distribution rather than more context capacity.

The key open question remains: can this become robust across seeds and prompts without adding a hidden layout engine? If not, the next model-layer move should be architectural, not another mask or overlay.

## Direction Check

The project is on the right path if it treats Flipbook as evidence for a two-stage near-term path and a one-stage long-term path:

1. Near term: generate a full page as pixels, then animate or transition that page with a fast neural video/canvas layer.
2. Long term: merge page generation, animation, resize, scrolling, and interaction into one model-rendered surface.

The current Track C work is trying to prove the hard part of the long-term path in miniature: can a compact neural renderer preserve readable semantic structure while content moves, reflows, and changes? That is the correct bottleneck to attack. The only caution is benchmark overfit. Every new win should be followed by stress tests that change layout, move regions independently, and alter illustration structure, not just make the same page wiggle more cleanly.
