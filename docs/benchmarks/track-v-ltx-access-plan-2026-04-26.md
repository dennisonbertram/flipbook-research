# Track V LTX Access Plan

Date: 2026-04-26

## Current Access State

The fastest usable route right now is fal-hosted LTX because `FAL_KEY` is already present in the local environment. The benchmark harness now supports:

```text
ltx23-fast -> fal-ai/ltx-2.3/image-to-video/fast
ltx23-pro  -> fal-ai/ltx-2.3/image-to-video
ltx2-fast  -> fal-ai/ltx-2/image-to-video/fast
ltx2-pro   -> fal-ai/ltx-2/image-to-video
```

The official LTX API route needs an API key. Official docs name the environment variable `LTXV_API_KEY`; the local benchmark also accepts `LTX_API_KEY` as an alias. Browser automation reached `console.ltx.video`, but the console is currently behind Cloudflare human verification and login. Do not automate that challenge. Once the user completes the verification and login in the visible Chrome session, create/copy the API key and store it only in a local secret path or environment variable, never in docs or logs.

Modal access is already available locally: `modal` CLI and Python package are installed, and Modal environment credentials are present. Running LTX on Modal therefore does not require an LTX API key. The existing Track A Modal runner uses the older Diffusers LTX pipeline and has already produced sub-1.3s speed passes at smaller resolutions, though dense text quality failed.

LTX 2.3 self-hosting on Modal is likely the more current path. The LTX 2.3 Hugging Face repos are public/ungated, but the LTX-2 repository lists Gemma 3 as a required text encoder asset. `google/gemma-3-4b-it` is manually gated, so a Hugging Face token may be needed if the selected LTX 2.3 pipeline downloads Gemma from Hugging Face at runtime.

Agent-browser status:

- `console.ltx.video` currently resolves to Cloudflare human verification. Manual user verification/login is required before the key can be created.
- `huggingface.co/settings/tokens` redirects to login and currently returns a 403 in the connected browser, so a Hugging Face token cannot be created through agent-browser yet.
- `FAL_KEY` and Modal auth are present locally. `LTXV_API_KEY` is present through the local ignored file `tmp/secrets/ltxv.env`. `HF_TOKEN` and `HUGGINGFACE_HUB_TOKEN` are missing locally.

## Timing Bookmark

For `ltx-2-3-fast`, generating a 6 second, 144 frame, 1080p image-to-video clip through the hosted sync API currently takes about `17-22s` wall time:

- Dense text page: `17.400s` API wall time.
- Naturalist illustration plate: `22.081s` API wall time.

The fal-hosted LTX 2.3 Fast wrapper is in the same range but slightly slower on these two samples:

- Dense text page: `21.898s` API wall time.
- Naturalist illustration plate: `22.774s` API wall time.

Rule of thumb: hosted LTX 2.3 Fast is roughly a `20s` generation call for our 6s/1080p test clips. It is useful as a quality/reference benchmark, not as a realtime path.

The older official `ltx-2-fast` is not faster on the dense text page: the 6 second, 25 fps, 1080p control took `36.783s` and still failed text quality.

## Recommended Order

1. **fal LTX 2.3 Fast smoke tests now**
   Use existing `FAL_KEY` to benchmark quality and service latency immediately. This is not the final realtime proof, but it tells us whether LTX 2.3 behaves materially better than the old fal LTX 13B endpoint.

2. **Modal old-LTX control**
   Keep `scripts/track_a/modal_ltx_benchmark.py` as the known working self-host baseline. It uses public LTX weights through Diffusers and needs no new keys beyond Modal.

3. **Modal LTX 2.3 runner**
   Build a separate runner around `Lightricks/LTX-2` / `ltx-pipelines`, not by bending the old Diffusers script. Start with `DistilledPipeline` or `TI2VidOneStagePipeline`, then test FP8 and attention optimizations.

4. **Official LTX API**
   Once `LTXV_API_KEY` or `LTX_API_KEY` is available, benchmark `ltx-2-3-fast` through `https://api.ltx.video/v1/image-to-video` as the cleanest vendor-hosted reference.

## Source Notes

- Official LTX API docs say API keys are created in the LTX developer console and image-to-video calls use `Authorization: Bearer YOUR_API_KEY`.
- Official LTX input docs allow `image_uri` as cloud upload, HTTPS URL, or data URI; data URI image inputs are limited to 7 MB encoded.
- Official LTX models list `ltx-2-3-fast` and `ltx-2-3-pro`; Fast is the recommended exploration model.
- Official pricing lists image-to-video `ltx-2-3-fast` at `$0.06/s` for 1080p and `ltx-2-3-pro` at `$0.08/s` for 1080p.
- LTX 2.3 Hugging Face notes the full and distilled checkpoints, FP8 variants, and that Diffusers support is still coming soon.
- The LTX-2 GitHub repo recommends the `DistilledPipeline` for fastest inference, FP8 quantization, xFormers or Flash Attention 3, and one-stage generation when high resolution is not required.

## Hosted LTX 2.3 Fast Results

| Run | Shape | API wall | Status | Read |
| --- | --- | ---: | --- | --- |
| `20260426T191224Z-fal-ltx23-fast-ltx23-fast-text-preservation-1920x1080` | 6s, 144 frames, 1080p | `21.898s` | quality fail | Starts near the source, then dense text mutates badly; OCR proxy drops to `0.4603`. |
| `20260426T191331Z-fal-ltx23-fast-ltx23-fast-naturalist-1920x1080` | 6s, 144 frames, 1080p | `22.774s` | visual fail | Proxy layout score passes, but manual contact-sheet review shows the composition collapses into a close-up linework/texture hallucination by mid/last frame. |

Conclusion: fal-hosted LTX 2.3 Fast is much faster than the older fal LTX endpoint, but it does not solve our page-preserving animation problem. It is currently a fast repaint/motion prior, not a trustworthy document or plate re-layout engine.

## Official LTX API Results

| Run | Shape | API wall | Status | Read |
| --- | --- | ---: | --- | --- |
| `20260426T233957Z-ltx-api-ltx-2-3-fast-official-ltx-api-text-preservation-1920x1080` | 6s, 144 frames, 1080p | `17.400s` | quality fail | First frame preserves the page, but mid/last frames invent lower-page cards and unreadable pseudo-text. OCR proxy falls from `0.9488` on first frame to near zero by mid/last. |
| `20260426T234111Z-ltx-api-ltx-2-3-fast-official-ltx-api-naturalist-1920x1080` | 6s, 144 frames, 1080p | `22.081s` | visual pass / proxy pass | Better than fal-hosted naturalist: preserves the full plate composition through mid/last, with softening and small label drift rather than collapse into close-up linework. |
| `20260426T234547Z-ltx-api-ltx-2-fast-official-ltx2-fast-text-preservation-1920x1080` | 6s, 153 frames, 1080p | `36.783s` | quality fail | Slower than `ltx-2-3-fast` on the same dense page and still loses text by mid/last frame. |

Conclusion: the official sync API is a cleaner and slightly faster hosted LTX reference than fal for this test. It still fails dense document preservation, but it may be viable as a bridge model for illustration-first pages where exact labels are not the product promise.

## Commands

Hosted LTX 2.3 Fast dense text smoke:

```bash
tmux new-session -d -s track-v-ltx23-fast-text \
  "cd /Users/dennisonbertram/Develop/flipbook-research && python3 scripts/track_v/fal_video_benchmark.py --model ltx23-fast --label ltx23-fast-text-preservation --input fixtures/track-a/text-heavy-page.png --prep-resolution 1920x1080 --duration 6 --fps 24 --ltx-resolution 1080p --aspect-ratio 16:9 --append-results > docs/experiments/track-v/ltx23-fast-text.log 2>&1"
```

Hosted LTX 2.3 Fast illustration smoke:

```bash
tmux new-session -d -s track-v-ltx23-fast-naturalist \
  "cd /Users/dennisonbertram/Develop/flipbook-research && python3 scripts/track_v/fal_video_benchmark.py --model ltx23-fast --label ltx23-fast-naturalist --input fixtures/track-v/gpt-image-2-naturalist-etching-plate.png --prep-resolution 1920x1080 --duration 6 --fps 24 --ltx-resolution 1080p --aspect-ratio 16:9 --skip-text-gate --append-results > docs/experiments/track-v/ltx23-fast-naturalist.log 2>&1"
```

Official LTX API key check, without printing the key:

```bash
source tmp/secrets/ltxv.env
if [ -n "$LTXV_API_KEY$LTX_API_KEY" ]; then echo LTX_API_KEY=present; else echo LTX_API_KEY=missing; fi
```

Official LTX API dry run, no key required:

```bash
python3 scripts/track_v/ltx_api_benchmark.py \
  --dry-run \
  --model ltx-2-3-fast \
  --label official-ltx-api-dryrun \
  --input fixtures/track-a/text-heavy-page.png \
  --prep-resolution 1920x1080 \
  --duration 6 \
  --fps 24 \
  --resolution 1920x1080
```

Official LTX API measured run once a key is available:

```bash
tmux new-session -d -s track-v-ltx-api-text \
  "cd /Users/dennisonbertram/Develop/flipbook-research && python3 scripts/track_v/ltx_api_benchmark.py --model ltx-2-3-fast --label official-ltx-api-text-preservation --input fixtures/track-a/text-heavy-page.png --prep-resolution 1920x1080 --duration 6 --fps 24 --resolution 1920x1080 --append-results > docs/experiments/track-v/ltx-api-text.log 2>&1"
```
