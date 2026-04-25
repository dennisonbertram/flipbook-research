# Flipbook Public Claims Grounding

Date: 2026-04-25

Sources:

- https://flipbook.page/
- https://xcancel.com/zan2434/status/2046982383430496444
- Agent-browser refresh: `docs/research/flipbook-agent-browser-about-refresh-2026-04-25.txt`

## What Flipbook Says It Is

Flipbook describes itself as an infinite visual browser generated on demand in real time. The important product claim is not "animated images" by itself; it is that each page is an image, and the browsing surface is generated pixels rather than HTML, code, links, fields, or a fixed layout engine.

The X launch thread phrases the same thesis as every pixel being streamed from a model, with no HTML or layout engine. It also says the lack of a strict layout engine lets illustrations reshape to the window and lets any image region become interactive.

Re-review note: this is still the north star. The breakthrough claim is not a better UI renderer around model assets; it is a page/runtime where the visible surface is model-rendered pixels and interaction happens by asking the model/system to produce the next visible state.

Browser refresh note: the live page still says each page contains no HTML, code, specific links, or fields, and that the whole surface is generated pixels. That means a proof of concept should be judged by whether the visual state can be regenerated, resized, animated, and changed as pixels, not by whether hidden DOM/layout machinery can imitate the demo.

Live check on 2026-04-25 via agent-browser still shows the same core language: every page is an image, the visible web is generated pixels on screen, and there are no specific links or fields in the visual page itself. This keeps Track C's current bar high: readable text is not enough if the result only preserves the old page underneath a pretty motion layer.

## Text Claim

Flipbook explicitly says the text is rendered by the image model as pixels, with no text overlays applied to the images. It also acknowledges that text can be imperfect or misplaced today.

Implication for this repo: text overlays, OCR patch replacement, and mask compositing are useful diagnostics, but they are not the target architecture. Track C should keep moving toward generated text as model output pixels, even when the text benchmark is painful.

The same refresh confirms Flipbook claims no text overlays on the images. So the "layer text on top" idea remains a product bridge or diagnostic only; it is not evidence for the pure neural-canvas path.

The live page again states that all text is rendered as pixels by the image model and that no text overlays are applied. So any Track C use of text boxes, masks, OCR crops, or layered text must be labeled as a training/eval aid or bridge experiment, not as the target product architecture.

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

C75-C78 update that conclusion rather than changing it. Dual-residual decoding was a real positive signal because it separates source identity from destination-local correction while still emitting pixels from the model. Fused source/target residual decoding then regressed, which suggests the current bottleneck is spatial/detail representation, not just "show the MLP more coordinates."

The key open question remains: can this become robust across seeds and prompts without adding a hidden layout engine? If not, the next model-layer move should be architectural, not another mask or overlay.

## Direction Check

The project is on the right path if it treats Flipbook as evidence for a two-stage near-term path and a one-stage long-term path:

1. Near term: generate a full page as pixels, then animate or transition that page with a fast neural video/canvas layer.
2. Long term: merge page generation, animation, resize, scrolling, and interaction into one model-rendered surface.

The current Track C work is trying to prove the hard part of the long-term path in miniature: can a compact neural renderer preserve readable semantic structure while content moves, reflows, and changes? That is the correct bottleneck to attack. The only caution is benchmark overfit. Every new win should be followed by stress tests that change layout, move regions independently, and alter illustration structure, not just make the same page wiggle more cleanly.

Immediate direction after the refresh: keep Track C honest by preferring experiments that make the page become a different pixel state. RGB/neural-texture skip experiments are acceptable if they are treated as model parameters and are evaluated under reflow/resize, but they should not become a copy-paste compositor. Track D remains the place to test whether this can generalize beyond the single page.

Direction after the 2026-04-25 live re-check: continue C85 only as a model-layer consolidation branch, add explicit source-remnant evaluation, and keep planning a cleaner two-state/held-out-page test. The current learned RGB texture is acceptable because it is a trainable model parameter, but the repo should reject any result that merely leaves a readable source page ghost in the target layout.

Second live re-check on 2026-04-25 at 07:15 UTC: the app itself was in a wait-room state, but the about panel remained visible and unchanged in substance. It still frames Flipbook as an on-demand visual browser, says the visible page has no HTML/code/links/fields, says screen text is image-model pixels with no overlays, and describes live video as a current two-system bridge between static image generation and an optimized video model. This confirms the next Track C move should be a clean state-to-state neural page test, not more optimization around protected text regions.

Third live re-check on 2026-04-25 at 08:06 UTC: the live about panel was visible again and still made the same product claims. The strongest correction to our work remains that "text quality" is not a separate overlay problem in Flipbook's framing. It is part of the pixel renderer. That keeps C89 aligned: the changed-copy targets ask the neural canvas to repaint new words and a new page state, not merely preserve old readable text while the layout shifts.
