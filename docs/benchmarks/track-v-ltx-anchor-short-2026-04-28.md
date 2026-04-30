# Track V LTX Short Anchor Probe - 2026-04-28

## Question

Can hosted LTX 2.3 Fast become useful if we stop asking it to invent a 6 second page animation and instead force it into a short, source-anchored, page-locked clip?

This tests the path suggested by the 6 second first/last-frame run: LTX can return to the document at the endpoint, but the midpoint collapses unless the temporal span and prompt are constrained.

## Result

The best hosted-LTX recipe so far is:

```text
ltx-2-3-fast
duration: 2s
fps: 24
resolution: 1920x1080
image_uri: source page
last_frame_uri: same source page
prompt: locked-off flat document scan, no zoom/crop/page turn/fold/curl/camera motion
```

Dense text result:

| Run | API wall | Frames | Status | Text | Layout | Motion | Read |
| --- | ---: | ---: | --- | ---: | ---: | ---: | --- |
| `20260428T002056Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-anchor-2s-locked-1920x1080` | `14.762s` | 48 | pass | `0.8099` | `0.9992` | `0.0082` | Best dense-text hosted LTX result. Very stable, readable enough, but nearly static. |
| `20260428T002049Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-anchor-3s-locked-1920x1080` | `18.953s` | 72 | pass | `0.7200` | `0.9978` | `0.0305` | Passes aggregate gate, but midpoint already shows perspective/page skew and weaker text. |

The 2s run is the first hosted LTX dense-text pass that also looks plausible on the contact sheet. It is not re-layout. It is closer to generated-pixel paper breathing: tiny lighting/texture drift while preserving the page.

## Ablations

| Probe | API wall | Status | Text | Motion | Read |
| --- | ---: | --- | ---: | ---: | --- |
| 2s anchor + default prompt | `15.814s` | quality fail | `0.6476` | `0.0091` | Geometry stays near-copy, but OCR still degrades. The strict prompt matters. |
| 2s locked prompt, no last-frame anchor | `13.555s` | quality fail | `0.3196` | `0.0902` | The model crops/recomposes the page. The last-frame anchor matters. |
| 1s locked anchor | `0.408s` | API reject | n/a | n/a | API returned HTTP 400: duration 1 is unsupported for this model/resolution/fps. |
| 2s locked anchor at `960x540` | `0.358s` | API reject | n/a | n/a | API returned HTTP 400: `960x540` is unsupported. |

The shortest observed accepted hosted request is therefore `2s` at `1920x1080`. The official docs list longer model-duration options, but the live API currently accepts 2s and 3s for `ltx-2-3-fast` image-to-video and rejects 1s.

## Illustration Plate Probe

The same broad recipe is conditional by page family.

| Run | API wall | Status | Layout | Motion | Manual read |
| --- | ---: | --- | ---: | ---: | --- |
| `20260428T002306Z-ltx-api-ltx-2-3-fast-official-ltx-api-naturalist-anchor-2s-locked-1920x1080` | `15.063s` | proxy pass | `0.9968` | `0.0376` | Visual fail: midpoint invents a large foreground fern/shadow overlay. |
| `20260428T002357Z-ltx-api-ltx-2-3-fast-official-ltx-api-naturalist-anchor-2s-noshadow-1920x1080` | `14.707s` | pass | `0.9993` | `0.0114` | Visual pass: explicit "no new objects/shadows/overlays" prompt keeps the plate stable. |

This is the clearest generalization read so far: the method generalizes as a conditional policy, not as one universal recipe. Dense text needs a document-lock prompt. Illustration plates need an additional "no new foreground/shadow/overlay" constraint.

## Crop/Generated-Pixel Diagnostic

`scripts/track_v/camera_path_diagnostic.py` now handles runs whose input path is stored in `metrics.json`, so it can compare Track B and Track V runs directly.

Key updated readings:

| Run | First | Mid | Last | Read |
| --- | --- | --- | --- | --- |
| 6s LTX 2.3 Fast, no anchor | near-copy `0.743` | not crop-explainable `0.233` | not crop-explainable `0.235` | Real generated pixels, but document identity collapses. |
| 6s LTX 2.3 Fast, source as last frame | near-copy `0.854` | partial `0.455` | near-copy `0.931` | Endpoint anchor works; midpoint still fails. |
| 3s locked anchor | near-copy `0.855` | partial `0.515` | near-copy `0.946` | Shorter helps, but midpoint still repaints/skews. |
| 2s locked anchor | near-copy `0.856` | near-copy `0.907` | near-copy `0.927` | Best stable dense-text result. |
| Track B deterministic baseline | near-copy `0.846` | near-copy `0.837` | near-copy `0.846` | Similar stability and motion, but deterministic and about 100x faster. |

The 2s LTX output is real model-generated pixels, but by the diagnostic it behaves like a near-copy of the source page. That is good for preservation and bad for the original "re-layout" dream.

## Product Read

Hosted LTX is not the realtime path. The best 2s clip still takes about `14.7s` wall time and has motion comparable to Track B. It should be treated as a background "enhanced clip" generator, not as the immediate interaction layer.

The useful path is now:

1. Immediate response: deterministic Track B-style layout/parallax/lighting at `~70-200ms`.
2. Background enhancement: hosted LTX 2s anchored clips for page families where subtle generated texture is valuable.
3. Hard reject: run OCR/layout/crop diagnostics and discard any clip that leaves source-page coordinates.
4. Realtime research: move to Modal/self-hosted LTX only if we can bring the anchored 2s recipe down to low resolution or one-stage generation while preserving text. The hosted API rejects `960x540`, so this must be self-hosted.

This gives us a path, but it is not "video model re-layout." It is "preserve the canonical page, add subtle generated-pixel life, and never let the video model own text or layout."

