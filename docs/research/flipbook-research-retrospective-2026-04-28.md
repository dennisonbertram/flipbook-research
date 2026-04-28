# What We Learned About Realtime Generated Pages

Date: 2026-04-28

## Short Version

We set out to understand whether a rich generated page could become a live, responsive visual experience: something that feels animated and model-generated, but still preserves text, diagrams, layout, and identity.

The main lesson is simple:

**Video generation is not yet a reliable page renderer.**

Full-frame video models can produce beautiful motion, but when asked to animate a document-like page they tend to repaint the page itself. That is exciting when the goal is cinematic imagery, but dangerous when the page contains words, labels, charts, or UI. They preserve the vibe of a document better than the document.

The path that still looks real is a hybrid:

1. Keep a canonical page image or page representation as the source of truth.
2. Produce immediate motion deterministically: camera drift, parallax, lighting, local safe-region movement.
3. Optionally run a video model in the background for enhancement.
4. Only publish the enhanced clip if it passes text, layout, and identity gates.

This is not the dream of a model freely re-layouting pixels in realtime. But it is a workable product path: instant, stable page liveness now; richer generative enhancement later.

## The Original Hope

The motivating question was:

Can we make a generated page feel alive without re-rendering the whole thing through a slow image or video model every frame?

That breaks into several sub-questions:

- Can a video model animate a page while preserving exact text and layout?
- Can a lightweight neural canvas render page-like pixels in realtime?
- Can deterministic animation provide enough perceived life while preserving fidelity?
- Can we combine these into a system that feels immediate to a user?

The most important constraint was not beauty. It was control.

For page-like content, text and layout are not decoration. They are the product.

## What Worked

### 1. Deterministic Motion Is Fast Enough

Track B tested codec-style animation: start with a high-quality page image, then add small controlled motion using deterministic transforms.

The strongest result:

- 121 frames at 960x540 in roughly 100-200 ms across many page families.
- 33-frame preview clips in roughly 47-123 ms depending on resolution.
- Text and layout remain stable because the original page remains the source.

This is not generative video. It is controlled page liveness.

That sounds modest, but it matters. It means a product can show motion immediately while heavier model work happens in the background.

### 2. Hosted LTX Can Be Useful If It Is Strongly Anchored

Free-running hosted LTX failed on dense text. Six-second clips drifted into document-like hallucinations: the model kept the idea of a page, but lost the actual page.

The useful discovery was first/last-frame anchoring.

Best hosted LTX result:

- Model: `ltx-2-3-fast`
- Duration: 2 seconds
- Resolution: 1920x1080
- Source image supplied as both first and last frame
- Strict prompt: no camera movement, no crop, no page turn, no fold, preserve every word and margin
- API wall time: 14.762 seconds
- Text score: 0.8099
- Layout score: 0.9992

This was the first dense-text hosted LTX result that both passed our proxy gates and looked plausible on review.

But the result is nearly static. The video model is useful here only when tightly constrained into "living paper" rather than free animation.

### 3. Prompting Has To Be Conditional By Page Family

The same broad LTX recipe did not generalize as one universal prompt.

Dense text pages needed:

- locked document scan language;
- no camera;
- no crop;
- no page turn;
- no fold or curl;
- exact preservation of words, typography, and margins.

Naturalist illustration plates needed an extra constraint:

- no new foreground objects;
- no shadows;
- no overlays;
- no extra leaves or visual motifs.

Without that, the model preserved the plate layout but invented a large translucent foreground fern/shadow. The proxy metrics passed, but visual review failed.

So the method generalizes as a conditional policy, not a universal recipe.

### 4. Diagnostics Matter

We added a camera-path diagnostic to ask whether generated frames are simply crops of the source page or whether the model has repainted the page.

That helped separate three different outcomes:

- Deterministic near-copy motion: safe, fast, but not generative.
- Anchored generated near-copy motion: real model pixels, but low motion.
- Free generated document collapse: real model pixels, but the page identity is lost.

This distinction is important. A low crop-match score can mean the model is doing something interesting, or it can mean the model destroyed the document.

For page products, "interesting" is not enough. The page has to survive.

## What Failed

### 1. Free-Running Video Models Do Not Preserve Dense Pages

The most repeated failure was simple: video models rewrite text.

They often keep:

- broad page shape;
- visual style;
- approximate blocks;
- document-like texture.

They lose:

- exact words;
- small labels;
- diagram fidelity;
- stable margins;
- layout identity over time.

This is why full-frame video generation should not own the canonical page.

### 2. Post-Hoc Compositing Is Not Enough

We tried protecting text and linework by compositing original source pixels back over a generated LTX clip.

That improved OCR, but looked incoherent when the video model had already zoomed, folded, or recomposed the page. The source text layer floated over a different generated page.

The control has to happen before or during generation. Post-hoc repair cannot rescue a clip that left the original page coordinate system.

### 3. Self-Hosted Old LTX Is Faster, But Not Good Enough

We tested the public Diffusers `LTXConditionPipeline` on Modal with the source image pinned at the first and last frame.

Results:

| Shape | Wall time | Model time | Text | Layout | Motion | Status |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 49 frames, 768x448, 8 steps | 6.492s | 5.458s | 0.4604 | 0.9999 | 0.0017 | quality fail |
| 49 frames, 960x544, 8 steps | 9.766s | 8.812s | 0.2184 | 0.9999 | 0.0017 | quality fail |

This is a useful negative result.

The model stayed in page coordinates, so anchoring worked. But text softened and mutated, and the output had almost no useful motion. It was faster than hosted LTX, but not a product path for dense pages.

### 4. We Did Not Solve Re-Layout

This is the hard truth.

We did not yet find a system that can take a page image and genuinely re-layout it as new model-generated pixels while preserving all semantics.

Most attempts either:

- moved an existing plate around;
- produced alpha-mask-like transformations;
- hallucinated a new document;
- preserved the page only by making the motion tiny.

That does not mean the goal is impossible. It means the next version needs a page representation, not just pixels.

## What Is Possible Now

### Immediate Product: Live Generated Pages

A useful product can be built now with:

- a high-quality static generated page;
- deterministic animation for immediate response;
- text/layout preservation by construction;
- optional background enhancement.

The user would see the page become alive immediately. Then, if a generated enhancement passes gates, the product can crossfade to the richer clip.

This is especially plausible for:

- illustrated articles;
- educational pages;
- product explainers;
- naturalist plates;
- visual essays;
- ambient hero pages;
- generated reports where most motion can live outside text.

It is less appropriate for:

- dashboards;
- tables;
- dense labels;
- code;
- financial/legal/medical text;
- any interface where exact text is the experience.

### Background Enhancement

Hosted LTX 2.3 Fast can be used as a background enhancement engine when constrained:

- use the source image as first and last frame;
- keep duration short, around 2 seconds;
- use a page-family-specific lock prompt;
- reject any clip that fails OCR, layout, crop, or visual-review gates.

This is not realtime. The best hosted result took about 15 seconds.

But background work can still be valuable if the immediate layer is already good.

### Research Product: Page-Aware Generative Rendering

The more ambitious path is a page-aware renderer:

```text
canonical page representation
+ explicit text/layout anchors
+ region masks or semantic layers
+ lightweight renderer
+ optional video-model texture enhancement
= controllable generated page motion
```

The page representation might include:

- text boxes;
- linework;
- diagrams;
- semantic regions;
- depth or pseudo-depth;
- safe motion regions;
- locked identity regions.

The video model should not be asked to remember all of this implicitly. It should be given constraints.

## The Path Forward

### Near Term

Build the hybrid lane.

1. Generate or receive a canonical page image.
2. Detect text, labels, diagrams, and safe motion regions.
3. Animate safe regions deterministically.
4. Keep text and key linework fixed or separately composited.
5. Render a fast preview immediately.
6. Run hosted LTX enhancement in the background only for suitable pages.
7. Gate all generated clips before showing them.

The immediate metric should be user-perceived responsiveness, not pure generative purity.

### Medium Term

Develop a router by page family.

| Page family | Primary path | Video model role |
| --- | --- | --- |
| Dense text | deterministic, text locked | off by default |
| Diagrams and labels | deterministic with protected linework | only if gated |
| Illustration-rich pages | deterministic now, LTX later | background enhancement |
| Ambient visual pages | video model acceptable | precompute or async |
| True layout changes | page/state renderer | not video generation |

This router is probably more important than any single model prompt.

### Longer Term

Test LTX-2.3 self-hosting only as a bounded probe after Hugging Face token access is available.

The question is not "can we run it?" The question is:

Can distilled or FP8 LTX-2.3 produce an illustration-rich, anchored enhancement in under 5 seconds warm without destroying the page?

If not, hosted/background enhancement is enough for now.

## The Core Principle

The page must remain sovereign.

Video models are good at motion, texture, style, and plausible continuity. They are not yet trustworthy custodians of text, layout, or interface state.

So the best architecture is not:

```text
image -> video model -> product
```

It is:

```text
page state -> controlled renderer -> immediate experience
          -> optional video model -> gated enhancement
```

That framing turns the negative results into progress. The work showed where not to put the model, which is often the most important part of making a real system.

## What I Would Share Publicly

The public claim I would make is:

> We found that current video models are impressive motion priors but unreliable page renderers. The viable path for live generated pages is hybrid: preserve a canonical page, animate it deterministically for instant response, and use video generation only as a gated background enhancement.

The part I would not overclaim:

- We did not solve realtime generated re-layout.
- We did not make a video model preserve arbitrary dense documents.
- We did not prove a general neural page renderer.

The part that is genuinely exciting:

- Stable page liveness is already fast.
- Anchored video generation can add subtle generated-pixel life.
- The right product architecture is becoming clear.
- The failure modes are legible enough to route around.

## References In This Repo

- [Track B Hybrid Fastest Probe](../benchmarks/track-b-hybrid-fastest-2026-04-27.md)
- [Track V LTX Short Anchor Probe](../benchmarks/track-v-ltx-anchor-short-2026-04-28.md)
- [Track V Modal LTX Condition Probe](../benchmarks/track-v-modal-ltx-condition-2026-04-28.md)
- [Track V Generated Pixel Diagnostic](../benchmarks/track-v-generated-pixel-diagnostic-2026-04-27.md)
- [Track V Modal LTX And Hybrid Product Path](../planning/track-v-modal-ltx-hybrid-exploration-2026-04-26.md)

