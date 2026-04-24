# Nano Banana Latency Benchmark

Date: 2026-04-24

## Purpose

Measure whether Google's Nano Banana image model is fast enough to be a candidate for the static-image generation stage in a Flipbook-style pipeline.

This test only measures text-to-image API latency. It does not measure animation, video generation, WebSocket transport, or browser playback.

## Models Tested

Official Google docs map the names as:

- Nano Banana: `gemini-2.5-flash-image`
- Nano Banana 2: `gemini-3.1-flash-image-preview`

## Prompt

```text
Generate a low-resolution 16:9 clean visual test image, about 512 pixels wide. White background, simple black line diagram of a browser window with a small mountain icon. Include only the large readable text FAST TEST. Keep it minimal.
```

## Results

| Model | Run | Latency | Output | Notes |
| --- | ---: | ---: | --- | --- |
| `gemini-2.5-flash-image` | 1 | 4.556s | 1024x1024 PNG | Text correct; ignored requested 16:9 / 512px shape. |
| `gemini-2.5-flash-image` | 2 | 4.961s | 1024x1024 PNG | Text correct; same square output. |
| `gemini-2.5-flash-image` | 3 | 5.234s | 1024x1024 PNG | Text correct; same square output. |
| `gemini-3.1-flash-image-preview` | 1 | 11.842s | 1376x768 JPEG | Text correct; followed 16:9 better but much slower. |

Fast-model sample:

```text
min:    4.556s
median: 4.961s
max:    5.234s
```

## 512 Image Config Test

The second test used explicit image configuration:

```json
{
  "imageConfig": {
    "aspectRatio": "16:9",
    "imageSize": "512"
  }
}
```

Google's docs list `16:9` at `512` resolution for `gemini-3.1-flash-image-preview` as `688x384`. The generated files matched that exactly.

| Model | Prompt Type | Run | Latency | Output | Notes |
| --- | --- | ---: | ---: | --- | --- |
| `gemini-3.1-flash-image-preview` | Minimal diagram | 1 | 8.209s | 688x384 JPEG | Explicit `512` config accepted. |
| `gemini-2.5-flash-image` | Minimal diagram | 1 | 0.139s | Error | API rejected `imageSize: "512"`: `Image size 512 is not supported for this model`. |
| `gemini-3.1-flash-image-preview` | Simple flat illustration | 1 | 6.315s | 688x384 JPEG | Explicit `512` config accepted; readable `FAST TEST` text. |
| `gemini-3.1-flash-image-preview` | Simple flat illustration | 2 | 6.208s | 688x384 JPEG | Explicit `512` config accepted; readable `FAST TEST` text. |

Illustration prompt:

```text
Create a very simple 512 pixel wide 16:9 flat vector-style illustration. White background. One smiling sun, two green hills, one tiny blue house, and the words FAST TEST in large clean black letters. Minimal shapes, solid colors, no texture, no photorealism.
```

512-config artifacts:

```text
outputs/nano-banana/latest-512-results.json
outputs/nano-banana/latest-512-illustration-results.json
```

## Artifacts

Generated outputs are stored under:

```text
outputs/nano-banana/
```

The latest raw result file is:

```text
outputs/nano-banana/latest-results.json
```

## Takeaways

- Nano Banana is not close to the `<= 1.3s` target in this direct text-to-image API test.
- It may still be useful for the static first image, because that stage does not necessarily need to happen inside the live video budget.
- The fast model produced readable simple text reliably in this tiny sample.
- Low-resolution control was weak through prompting alone; `gemini-2.5-flash-image` returned 1024x1024 images even when asked for about 512px wide 16:9 output.
- Nano Banana 2 produced a more relevant 16:9 output, but the single measured call was much slower.
- Explicit `512` output is available on `gemini-3.1-flash-image-preview`, but the measured calls still landed around 6.2-8.2s.
- Simpler illustration content may help a little in this tiny sample, but it does not get close to the `<= 1.3s` live-segment target.

## Implication For The PoC

Do not count Nano Banana latency inside the 33-frame live segment budget. Treat it as a candidate for the static page generator or for offline/preloaded still images.

For the live animation benchmark, the static image should be assumed already available.

## Sources

- Google Nano Banana image generation docs: https://ai.google.dev/gemini-api/docs/image-generation
