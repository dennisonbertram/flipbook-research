# Text-Specialized Model Search

Date: 2026-04-24

## Question

Can a text-specialized model help with the Track A failure mode where full-frame LTX meets latency targets but repaints/mangles page text?

## Short Answer

Yes, but mostly for still images and editing, not live video.

The best current text-specialized candidates are image generation or image editing models. They are useful for:

- creating the canonical first page image
- generating a clean text layer
- editing or repairing text-heavy stills
- teaching us how to train/evaluate text preservation

They do not directly solve low-latency image-to-video text preservation. For video, the more realistic path is still:

```text
text-specialized/static renderer -> stable text layer
video model -> non-text motion layer
compositor -> crisp final frames
```

## Candidate Models

| Candidate | Type | Why It Matters | Fit For Flipbook |
| --- | --- | --- | --- |
| Ideogram 3.0 | Hosted image generation/editing API | Strong typography/design focus, API supports generate/remix/edit/reframe/background replacement. | Strong candidate for static page/image generation and text-heavy design assets. |
| Qwen-Image / Qwen-Image-Edit | Open image generation/editing model | Open weights, strong complex text rendering, especially Chinese/English, precise image editing. | Best open-source candidate to run on Modal for text-heavy static pages and maybe text repair. |
| Google Gemini image / Imagen 4 | Hosted image generation | Official docs emphasize high-fidelity text rendering for logos, diagrams, posters; Imagen 4 has better text rendering than prior Imagen models. | Already partially tested via Nano Banana; useful for static first image, not live loop. |
| OpenAI GPT Image | Hosted image generation/editing | Official docs position GPT Image as strong for instruction following, text rendering, and detailed editing. | Strong static/editor candidate if API access and latency are acceptable. |
| Recraft API | Hosted image/vector generation/editing | Production-design focus, consistent text rendering, clean geometry, vectors. | Interesting for structured illustration/text layers, especially if vector output is useful. |
| FLUX.2 / FLUX Kontext | Hosted/open image generation/editing family | BFL docs emphasize typography/design and high-fidelity image generation/editing. | Worth testing for static pages and text-aware edits; not a video solution. |
| AnyText2 | Open research model | Designed specifically for visual text generation/editing with controllable font/color attributes. | Useful research direction for text-preservation adapters or training losses. |
| TextDiffuser-2 | Research model | Uses language-model layout planning plus diffusion text rendering. | Useful design pattern: make text content and position explicit, not implicit in a prompt. |

## Video Model Reality Check

I did not find a clearly text-specialized image-to-video model.

Runway's image-to-video guidance says the input image establishes composition and the prompt should focus on motion. That is helpful, but it is not a hard text-preservation guarantee.

For our current results, the evidence says:

- layout can remain stable
- text pixels still get repainted
- higher resolution and more steps improve text but miss the `<= 1.3s` target

So video-specific text preservation probably needs masks, overlays, or training, not just a different prompt.

## Recommended Benchmark Order

### 1. Static Text Renderer Bake-Off

Use the same text-heavy page prompt and measure:

```text
latency
OCR score
layout correctness
visual quality
API/control surface
cost
```

Candidates:

1. Qwen-Image on Modal
2. Ideogram 3.0 API
3. Google Imagen 4 / Gemini image
4. OpenAI GPT Image
5. Recraft
6. FLUX.2

### 2. Text-Layer Extraction / Repair Test

Given a degraded LTX output frame, test whether an image editor can restore only text while preserving the rest of the frame.

This is lower priority than overlay compositing, but it answers whether a model can act as a post-processor.

### 3. Hybrid Animation Test

Use the best static renderer only to create:

```text
background layer
text layer
text mask
```

Then run LTX or procedural motion on the background layer and composite text on top.

This is the path most likely to preserve readability while keeping the live video budget.

## Notes For Track A

If we continue model-layer Track A research, AnyText2 and TextDiffuser-2 are more useful as ideas than as drop-in replacements:

- explicit glyph/text conditioning
- text bounding boxes
- OCR-aware loss
- font/color control
- layout planning before generation
- hard protected-region masks

The core lesson is the same: text must be represented explicitly.

## Sources

- Ideogram API docs: https://developer.ideogram.ai/
- Ideogram text and typography guide: https://docs.ideogram.ai/using-ideogram/prompting-guide/2-prompting-fundamentals/text-and-typography
- Qwen-Image model card: https://huggingface.co/Qwen/Qwen-Image
- Qwen-Image GitHub: https://github.com/QwenLM/Qwen-Image
- Google Gemini image generation docs: https://ai.google.dev/gemini-api/docs/image-generation
- Google Imagen model docs: https://ai.google.dev/gemini-api/docs/imagen
- OpenAI image generation docs: https://platform.openai.com/docs/guides/image-generation
- Recraft API: https://www.recraft.ai/api
- FLUX.2 docs: https://docs.bfl.ai/flux_2/flux2_text_to_image
- AnyText2 paper: https://huggingface.co/papers/2411.15245
- AnyText2 GitHub: https://github.com/tyxsspa/AnyText2
- TextDiffuser-2: https://www.microsoft.com/en-us/research/publication/textdiffuser-2-unleashing-the-power-of-language-models-for-text-rendering/
- Runway image-to-video prompting guide: https://help.runwayml.com/hc/en-us/articles/48324313115155
