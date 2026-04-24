from __future__ import annotations

from time import perf_counter


def setup(config):
    return None


def generate(input_image, config, state=None):
    """Lower-bound recipe: return the unchanged first frame for every frame.

    This is not a model-quality baseline. It gives us the fixed-cost floor for
    preprocessing, frame handling, and MP4 encoding before LTX is connected.
    """
    start = perf_counter()
    frames = [input_image.copy() for _ in range(config.frames)]
    model_ms = (perf_counter() - start) * 1000

    return {
        "frames": frames,
        "timings": {
            "model_ms": model_ms,
            "denoise_ms": 0.0,
            "decode_ms": 0.0,
        },
        "quality": {
            "text_score": 1.0,
            "layout_score": 1.0,
            "motion_score": 0.0,
            "loop_error": 0.0,
        },
        "description": "stub freeze lower-bound, no generated motion",
    }
