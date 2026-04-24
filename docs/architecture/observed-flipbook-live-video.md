# Observed Flipbook Live Video Architecture

Date: 2026-04-23

## What Is Publicly Confirmed

- Zain Shah's launch thread says Flipbook streams model-generated pixels, uses an optimized LTX Studio video model, sends live 1080p video at 24 fps over WebSockets, and connects directly to Modal serverless GPU infrastructure.
- The Flipbook page copy says the live video feature animates each generated image and creates transitions between explored pages.
- Modal supports GPU-backed web endpoints, ASGI apps, WebSockets, warm containers, Volumes for model caches, and memory snapshots.
- Public LTX-Video material says LTX is designed for fast / real-time video generation, with image-to-video support. Modal's own LTX examples are a useful baseline, though not yet the Flipbook-style live stream.

## What The Shipped Flipbook Client Reveals

Flipbook's public JS bundle includes the live-video client protocol.

Observed WebSocket endpoint:

```text
wss://tmalive--ltx-stream-diffusersltx2streamingengine-streaming-app.modal.run/ws/stream
```

Observed client start message:

```json
{
  "action": "start",
  "session_id": "ltx_stream_<uuid>",
  "prompt": "Seamless continuous perfect loop, natural motion, movement, cinematic lighting, high quality, small objects idly animated, people walking, cars driving, boats moving, etc.",
  "width": 1920,
  "height": 1088,
  "num_frames": 33,
  "frame_rate": 24,
  "max_segments": 9999,
  "loopy_mode": true,
  "loopy_strategy": "mirror",
  "start_image": "<jpeg data url>",
  "target_image": "<jpeg data url>",
  "position": 1
}
```

Other observed client control messages:

```json
{ "action": "set_target_image", "image": "<jpeg data url>", "position": 1 }
{ "action": "stop" }
```

Observed stream packet format:

```text
bytes 0..3   ASCII "LTXF"
bytes 4..7   big-endian uint32 JSON header length
bytes 8..N   UTF-8 JSON header
remaining   MP4/fMP4 segment payload
```

The client reads `header.media_type` with a default of `video/mp4`, infers the codec from the first MP4 payload by inspecting MP4 boxes, creates a browser `MediaSource`, creates a `SourceBuffer`, sets `sourceBuffer.mode = "sequence"`, and appends each binary payload. It also stores the segment blobs for later share-preview video export.

The target render sizes are aspect-ratio dependent:

```text
16:9 => 1920x1088
3:4  => 1088x1920
1:1  => 1088x1088
```

The 1088 dimension is almost certainly deliberate: it is close to 1080p while staying divisible by model / codec-friendly block sizes.

## Likely End-To-End Shape

1. The normal page generation path creates a static page image first.
2. The browser turns that image into a JPEG data URL through canvas.
3. When the user enables live video, the browser opens a WebSocket directly to a Modal ASGI app.
4. The Modal app owns one WebSocket session per browser connection and keeps stream state in memory.
5. A warmed GPU container runs an optimized LTX image-to-video loop.
6. The server repeatedly generates short video segments from the latest image target.
7. Each segment is encoded as browser-playable fragmented MP4, wrapped in an `LTXF` packet, and sent over the WebSocket.
8. The browser appends chunks into MediaSource, so playback starts after the first chunk and continues as more chunks arrive.
9. When the user navigates to a new image, the browser sends `set_target_image`; the server retargets the next segment instead of starting a totally separate video player.

## Clone-Relevant Architecture

The public client points to a two-system product architecture:

```text
static page image generator
  -> high-quality visual page with good text
  -> browser converts page image to JPEG data URL
  -> live-video stream animates or transitions from that canonical image
```

This matters because the video model does not need to render the page text from scratch. It can preserve and animate an already-good still image.

## Implementation Implications

### Transport Prototype

- Build a Modal `@modal.asgi_app()` FastAPI app with `/ws/stream`.
- Accept `start`, `set_target_image`, and `stop`.
- Return `session_started` as JSON.
- Stream fake pre-encoded fMP4 chunks wrapped as `LTXF`.
- Build a browser page using `WebSocket + MediaSource + SourceBuffer(mode="sequence")`.

This proves the browser-side streaming contract before spending GPU money.

### Full-Frame LTX Baseline

- Start from Modal's official LTX image-to-video example.
- Cache model weights in a Modal Volume.
- Load the model in `@modal.enter()` so warm requests avoid reloads.
- Use `gpu="H100"` first; later test L40S / B200 depending cost and availability.
- Use fixed shapes only: `1920x1088`, `1088x1920`, `1088x1088`.
- Generate short clips: `num_frames=33`, `fps=24`.
- Encode clips to H.264 fragmented MP4 and send packets.

### Low-Latency Optimization

- Use distilled / fast LTX weights first.
- Use bf16 or FP8 where supported.
- Try LTX FP8 kernels on Ada/Hopper-class GPUs.
- Warm up the model with representative shapes.
- Preallocate tensors and avoid request-path model construction.
- Keep Modal containers warm with `scaledown_window`, and consider `min_containers` once usage justifies cost.
- Use GPU/NVENC encoding if available; CPU ffmpeg encoding can become the bottleneck.
- Keep each WebSocket message under Modal's 2 MiB message limit by using short segments and sane bitrate.

### Retargeting And UX

- Keep the old video visible until the next target chunk arrives.
- Send `set_target_image` for same-shape retargets.
- Reconnect only when stream config changes.
- Capture the current video frame to use as continuity input for tap/explore actions.
- Add a subtle loading/ripple overlay to hide retarget latency.

## Open Questions

- Whether their server emits one complete small MP4 per segment or a true init segment followed by `moof` / `mdat` fragments. The client can support either, but true fMP4 is the cleaner target.
- Whether "heavily optimized LTX" means custom LTX code, diffusers with compile/FP8, TensorRT, a custom distilled checkpoint, or all of the above.
- Whether they rely on H.264, HEVC, or switch by browser. The client parses both AVC and HEVC codec boxes.
- Whether the stream is truly generating at or above real-time continuously, or whether it relies on chunk buffering and forgiving looped motion.

## Sources

- Launch thread mirror: https://threadreaderapp.com/thread/2046982383430496444.html
- Flipbook site: https://flipbook.page/
- Flipbook public JS bundle: https://flipbook.page/assets/main-BlQciK5m.js
- Modal Web endpoints and WebSockets: https://modal.com/docs/guide/webhooks
- Modal streaming endpoints: https://modal.com/docs/guide/streaming-endpoints
- Modal cold start performance: https://modal.com/docs/guide/cold-start
- Modal memory snapshots: https://modal.com/docs/guide/memory-snapshots
- Modal LTX text-to-video example: https://modal.com/docs/examples/ltx
- Modal LTX image-to-video example: https://modal.com/docs/examples/image_to_video
- LTX-Video repository: https://github.com/Lightricks/LTX-Video
- LTX-Video model card: https://huggingface.co/Lightricks/LTX-Video
