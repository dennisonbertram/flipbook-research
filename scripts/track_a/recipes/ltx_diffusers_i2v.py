from __future__ import annotations

from time import perf_counter


def setup(config):
    try:
        import torch
        from diffusers import LTXImageToVideoPipeline
    except ImportError as exc:
        raise RuntimeError(
            "The ltx_diffusers_i2v recipe requires torch and diffusers. "
            "Install the optional Track A dependencies before running it."
        ) from exc

    device = config.device
    if device == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA was requested but torch.cuda.is_available() is false.")

    dtype_by_name = {
        "bfloat16": torch.bfloat16,
        "float16": torch.float16,
        "float32": torch.float32,
    }
    dtype = dtype_by_name.get(config.dtype)
    if dtype is None:
        raise RuntimeError(f"Unsupported dtype: {config.dtype}")

    start = perf_counter()
    pipe = LTXImageToVideoPipeline.from_pretrained(config.model_id, torch_dtype=dtype)
    pipe.to(device)
    setup_ms = (perf_counter() - start) * 1000

    return {
        "pipeline": pipe,
        "torch": torch,
        "setup_ms": setup_ms,
    }


def generate(input_image, config, state):
    torch = state["torch"]
    pipe = state["pipeline"]
    generator = torch.Generator(device=config.device).manual_seed(config.seed)

    start = perf_counter()
    with torch.inference_mode():
        result = pipe(
            image=input_image,
            prompt=config.prompt,
            negative_prompt=config.negative_prompt,
            width=config.width,
            height=config.height,
            num_frames=config.frames,
            num_inference_steps=config.steps,
            guidance_scale=config.guidance_scale,
            generator=generator,
        )
    model_ms = (perf_counter() - start) * 1000

    frames = result.frames[0]
    return {
        "frames": frames,
        "timings": {
            "model_ms": model_ms,
            "denoise_ms": model_ms,
            "decode_ms": 0.0,
        },
        "quality": {
            "text_score": None,
            "layout_score": None,
            "motion_score": None,
            "loop_error": None,
        },
        "description": f"LTX diffusers I2V, steps={config.steps}, guidance={config.guidance_scale}",
    }
