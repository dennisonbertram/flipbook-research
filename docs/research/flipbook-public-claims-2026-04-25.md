# Flipbook Public Claims Grounding

Date: 2026-04-25

Sources:

- https://flipbook.page/
- https://xcancel.com/zan2434/status/2046982383430496444

## What Flipbook Says It Is

Flipbook describes itself as an infinite visual browser generated on demand in real time. The important product claim is not "animated images" by itself; it is that each page is an image, and the browsing surface is generated pixels rather than HTML, code, links, fields, or a fixed layout engine.

The X launch thread phrases the same thesis as every pixel being streamed from a model, with no HTML or layout engine. It also says the lack of a strict layout engine lets illustrations reshape to the window and lets any image region become interactive.

## Text Claim

Flipbook explicitly says the text is rendered by the image model as pixels, with no text overlays applied to the images. It also acknowledges that text can be imperfect or misplaced today.

Implication for this repo: text overlays, OCR patch replacement, and mask compositing are useful diagnostics, but they are not the target architecture. Track C should keep moving toward generated text as model output pixels, even when the text benchmark is painful.

## Video Claim

Flipbook describes live video as an experimental feature that animates static images and creates seamless transitions. The site says it currently combines two separate systems: a custom optimized video generation model plus the image generation system, with an expectation that these eventually become one system.

The launch thread says the video path used a heavily optimized LTXStudio video model, streaming 1080p at 24fps through websockets to Modal GPU infrastructure.

Implication for this repo: the model layer is still the core bottleneck, but it may be acceptable for the proof of concept to separate image/page generation from video animation at first. A single unified neural canvas remains the cleaner long-term target.

## What This Means For Track C

Track C is on the right path when it tests:

- direct neural-canvas pixels, including text;
- reflow and resize, not just local wiggle;
- generated page states that can move content and change layout;
- latency against a 33-frame segment budget;
- no render-time text overlays or layout framework.

Track C is drifting when it optimizes:

- rectangular text anchoring as a product technique;
- global wobble that preserves everything elastically;
- query-time compositing tricks that would not generalize to arbitrary page content;
- OCR alone without visual layout change.

## Current Alignment

C57-C64 are aligned with Flipbook's public claim because they use learned layout reflow where the midpoint is a different page layout and the model renders the output pixels. The C62 high-water result proves the path can hit high text quality once, but C63 shows it is not stable enough yet. C64's curriculum sweep is therefore a reasonable next step: it changes training dynamics while preserving the pure-pixel full-reflow evaluation.

The key open question remains: can this become robust across seeds and prompts without adding a hidden layout engine? If not, the next model-layer move should be architectural, not another mask or overlay.
