#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LOG_DIR = ROOT / "docs" / "experiments" / "track-c"
STATE_PATH = LOG_DIR / "autoresearch-state.json"
STATUS_PATH = LOG_DIR / "autoresearch-status.md"
LOOP_LOG = LOG_DIR / "autoresearch-loop.log"
MAX_PARALLEL = 3
COMMIT = os.environ.get("FLIPBOOK_COMMIT", "dirty")


BASE_ARGS = [
    "--steps",
    "4500",
    "--train-resolution",
    "1280x736",
    "--edge-sample-ratio",
    "0.1",
    "--edge-loss-weight",
    "1.0",
    "--text-box-sample-ratio",
    "0.55",
    "--text-box-loss-weight",
    "8.0",
    "--text-box-padding",
    "4",
    "--text-box-min-conf",
    "55",
]


@dataclass(frozen=True)
class Experiment:
    label: str
    args: list[str]
    notes: str

    @property
    def session(self) -> str:
        return f"track-c-{self.label}"

    @property
    def log_path(self) -> Path:
        return LOG_DIR / f"{self.label}.log"


EXPERIMENTS = [
    Experiment(
        label="c30-gentle-flow-0125",
        notes="Pleasant-motion boundary between the C29 0.010 pass and 0.020 quality drop.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0.0125",
            "--motion-mode",
            "jiggle",
            "--motion-strength",
            "0.0125",
            "--experiment-label",
            "c30-gentle-flow-0125",
            "--min-ocr-similarity",
            "0.80",
            "--min-motion-delta",
            "0.012",
        ],
    ),
    Experiment(
        label="c30-gentle-flow-015",
        notes="Pleasant-motion boundary probe near the likely readability cliff.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0.015",
            "--motion-mode",
            "jiggle",
            "--motion-strength",
            "0.015",
            "--experiment-label",
            "c30-gentle-flow-015",
            "--min-ocr-similarity",
            "0.78",
            "--min-motion-delta",
            "0.015",
        ],
    ),
    Experiment(
        label="c30-product-layout-r0025-s008",
        notes="Pleasant layout-motion with best line ratio and moderate layout strength.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0",
            "--motion-mode",
            "static",
            "--motion-strength",
            "0",
            "--video-layout-mode",
            "element-frame-scale",
            "--layout-transform-strength",
            "0.08",
            "--layout-transform-pan",
            "0.015",
            "--element-anchor-mode",
            "line",
            "--element-render-mode",
            "batched",
            "--element-scale-ratio",
            "0.025",
            "--element-anchor-padding",
            "4",
            "--element-mask-mode",
            "rectangle",
            "--experiment-label",
            "c30-product-layout-r0025-s008",
            "--min-ocr-similarity",
            "0.75",
            "--min-motion-delta",
            "0.025",
        ],
    ),
    Experiment(
        label="c30-line-batched-r0025-strong",
        notes="Batched control for the current best strong-stress line ratio.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0",
            "--motion-mode",
            "static",
            "--motion-strength",
            "0",
            "--video-layout-mode",
            "element-frame-scale",
            "--layout-transform-strength",
            "0.18",
            "--layout-transform-pan",
            "0.035",
            "--element-anchor-mode",
            "line",
            "--element-render-mode",
            "batched",
            "--element-scale-ratio",
            "0.025",
            "--element-anchor-padding",
            "4",
            "--element-mask-mode",
            "rectangle",
            "--experiment-label",
            "c30-line-batched-r0025-strong",
            "--min-ocr-similarity",
            "0.65",
        ],
    ),
    Experiment(
        label="c29-gentle-flow-010",
        notes="Pleasant-motion ladder: double the C2.1 flow while trying to preserve text.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0.010",
            "--motion-mode",
            "jiggle",
            "--motion-strength",
            "0.010",
            "--experiment-label",
            "c29-gentle-flow-010",
            "--min-ocr-similarity",
            "0.80",
            "--min-motion-delta",
            "0.010",
        ],
    ),
    Experiment(
        label="c29-gentle-flow-020",
        notes="Pleasant-motion ladder: stronger learned motion, still below resize/reflow stress.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0.020",
            "--motion-mode",
            "jiggle",
            "--motion-strength",
            "0.020",
            "--experiment-label",
            "c29-gentle-flow-020",
            "--min-ocr-similarity",
            "0.75",
            "--min-motion-delta",
            "0.020",
        ],
    ),
    Experiment(
        label="c29-product-layout-r0025",
        notes="Pleasant layout-motion baseline using the best strong-stress line ratio at low layout strength.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0",
            "--motion-mode",
            "static",
            "--motion-strength",
            "0",
            "--video-layout-mode",
            "element-frame-scale",
            "--layout-transform-strength",
            "0.04",
            "--layout-transform-pan",
            "0.008",
            "--element-anchor-mode",
            "line",
            "--element-render-mode",
            "batched",
            "--element-scale-ratio",
            "0.025",
            "--element-anchor-padding",
            "4",
            "--element-mask-mode",
            "rectangle",
            "--experiment-label",
            "c29-product-layout-r0025",
            "--min-ocr-similarity",
            "0.75",
            "--min-motion-delta",
            "0.015",
        ],
    ),
    Experiment(
        label="c28-word-batched-r010",
        notes="Human-positive word anchors with batched patch rendering to recover latency.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0",
            "--motion-mode",
            "static",
            "--motion-strength",
            "0",
            "--video-layout-mode",
            "element-frame-scale",
            "--layout-transform-strength",
            "0.18",
            "--layout-transform-pan",
            "0.035",
            "--element-anchor-mode",
            "word",
            "--element-render-mode",
            "batched",
            "--element-scale-ratio",
            "0.10",
            "--element-anchor-padding",
            "3",
            "--element-mask-mode",
            "rectangle",
            "--experiment-label",
            "c28-word-batched-r010",
            "--min-ocr-similarity",
            "0.35",
        ],
    ),
    Experiment(
        label="c28-word-batched-moderate-r010",
        notes="Human-positive word anchors batched under moderate stress.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0",
            "--motion-mode",
            "static",
            "--motion-strength",
            "0",
            "--video-layout-mode",
            "element-frame-scale",
            "--layout-transform-strength",
            "0.08",
            "--layout-transform-pan",
            "0.015",
            "--element-anchor-mode",
            "word",
            "--element-render-mode",
            "batched",
            "--element-scale-ratio",
            "0.10",
            "--element-anchor-padding",
            "3",
            "--element-mask-mode",
            "rectangle",
            "--experiment-label",
            "c28-word-batched-moderate-r010",
            "--min-ocr-similarity",
            "0.50",
        ],
    ),
    Experiment(
        label="c28-line-batched-r005",
        notes="Batched line-anchor control should match C2.6 quality while confirming batching does not change pixels.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0",
            "--motion-mode",
            "static",
            "--motion-strength",
            "0",
            "--video-layout-mode",
            "element-frame-scale",
            "--layout-transform-strength",
            "0.18",
            "--layout-transform-pan",
            "0.035",
            "--element-anchor-mode",
            "line",
            "--element-render-mode",
            "batched",
            "--element-scale-ratio",
            "0.05",
            "--element-anchor-padding",
            "4",
            "--element-mask-mode",
            "rectangle",
            "--experiment-label",
            "c28-line-batched-r005",
            "--min-ocr-similarity",
            "0.35",
        ],
    ),
    Experiment(
        label="c27-line-rect-r0025",
        notes="Line anchor ratio sweep below current best 0.05.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0",
            "--motion-mode",
            "static",
            "--motion-strength",
            "0",
            "--video-layout-mode",
            "element-frame-scale",
            "--layout-transform-strength",
            "0.18",
            "--layout-transform-pan",
            "0.035",
            "--element-anchor-mode",
            "line",
            "--element-scale-ratio",
            "0.025",
            "--element-anchor-padding",
            "4",
            "--element-mask-mode",
            "rectangle",
            "--experiment-label",
            "c27-line-rect-r0025",
            "--min-ocr-similarity",
            "0.35",
        ],
    ),
    Experiment(
        label="c27-line-rect-r0075",
        notes="Line anchor ratio sweep above current best 0.05 but below previous 0.10.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0",
            "--motion-mode",
            "static",
            "--motion-strength",
            "0",
            "--video-layout-mode",
            "element-frame-scale",
            "--layout-transform-strength",
            "0.18",
            "--layout-transform-pan",
            "0.035",
            "--element-anchor-mode",
            "line",
            "--element-scale-ratio",
            "0.075",
            "--element-anchor-padding",
            "4",
            "--element-mask-mode",
            "rectangle",
            "--experiment-label",
            "c27-line-rect-r0075",
            "--min-ocr-similarity",
            "0.35",
        ],
    ),
    Experiment(
        label="c27-line-rect-r005-pad2",
        notes="Current best ratio with tighter support boxes to reduce unrelated illustration capture.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0",
            "--motion-mode",
            "static",
            "--motion-strength",
            "0",
            "--video-layout-mode",
            "element-frame-scale",
            "--layout-transform-strength",
            "0.18",
            "--layout-transform-pan",
            "0.035",
            "--element-anchor-mode",
            "line",
            "--element-scale-ratio",
            "0.05",
            "--element-anchor-padding",
            "2",
            "--element-mask-mode",
            "rectangle",
            "--experiment-label",
            "c27-line-rect-r005-pad2",
            "--min-ocr-similarity",
            "0.35",
        ],
    ),
    Experiment(
        label="c27-line-rect-r005-pad6",
        notes="Current best ratio with wider support boxes to check whether extra local context improves OCR.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0",
            "--motion-mode",
            "static",
            "--motion-strength",
            "0",
            "--video-layout-mode",
            "element-frame-scale",
            "--layout-transform-strength",
            "0.18",
            "--layout-transform-pan",
            "0.035",
            "--element-anchor-mode",
            "line",
            "--element-scale-ratio",
            "0.05",
            "--element-anchor-padding",
            "6",
            "--element-mask-mode",
            "rectangle",
            "--experiment-label",
            "c27-line-rect-r005-pad6",
            "--min-ocr-similarity",
            "0.35",
        ],
    ),
    Experiment(
        label="c27-responsive-018",
        notes="Responsive-squeeze boundary between strong 0.16 pass and xstrong 0.22 fail.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0.18",
            "--motion-mode",
            "responsive-squeeze",
            "--motion-strength",
            "0.18",
            "--video-viewport-mode",
            "zoom-pulse",
            "--viewport-zoom",
            "0.14",
            "--viewport-pan",
            "0.030",
            "--experiment-label",
            "c27-responsive-018",
            "--min-ocr-similarity",
            "0.25",
        ],
    ),
    Experiment(
        label="c26-word-rect-r010",
        notes="Word-level support rectangles: preserve text background while avoiding large line boxes that can catch illustration pixels.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0",
            "--motion-mode",
            "static",
            "--motion-strength",
            "0",
            "--video-layout-mode",
            "element-frame-scale",
            "--layout-transform-strength",
            "0.18",
            "--layout-transform-pan",
            "0.035",
            "--element-anchor-mode",
            "word",
            "--element-scale-ratio",
            "0.10",
            "--element-anchor-padding",
            "3",
            "--element-mask-mode",
            "rectangle",
            "--experiment-label",
            "c26-word-rect-r010",
            "--min-ocr-similarity",
            "0.35",
        ],
    ),
    Experiment(
        label="c26-word-rect-moderate-r010",
        notes="Moderate stress word-level support rectangle control.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0",
            "--motion-mode",
            "static",
            "--motion-strength",
            "0",
            "--video-layout-mode",
            "element-frame-scale",
            "--layout-transform-strength",
            "0.08",
            "--layout-transform-pan",
            "0.015",
            "--element-anchor-mode",
            "word",
            "--element-scale-ratio",
            "0.10",
            "--element-anchor-padding",
            "3",
            "--element-mask-mode",
            "rectangle",
            "--experiment-label",
            "c26-word-rect-moderate-r010",
            "--min-ocr-similarity",
            "0.50",
        ],
    ),
    Experiment(
        label="c26-line-rect-r005",
        notes="Line anchor scale-ratio refinement below the current best 0.10.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0",
            "--motion-mode",
            "static",
            "--motion-strength",
            "0",
            "--video-layout-mode",
            "element-frame-scale",
            "--layout-transform-strength",
            "0.18",
            "--layout-transform-pan",
            "0.035",
            "--element-anchor-mode",
            "line",
            "--element-scale-ratio",
            "0.05",
            "--element-anchor-padding",
            "4",
            "--element-mask-mode",
            "rectangle",
            "--experiment-label",
            "c26-line-rect-r005",
            "--min-ocr-similarity",
            "0.35",
        ],
    ),
    Experiment(
        label="c26-responsive-xstrong",
        notes="Very strong responsive-squeeze boundary after the strong run still passed.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0.22",
            "--motion-mode",
            "responsive-squeeze",
            "--motion-strength",
            "0.22",
            "--video-viewport-mode",
            "zoom-pulse",
            "--viewport-zoom",
            "0.16",
            "--viewport-pan",
            "0.035",
            "--experiment-label",
            "c26-responsive-xstrong",
            "--min-ocr-similarity",
            "0.25",
        ],
    ),
    Experiment(
        label="c25-alpha-r000",
        notes="Relaunch text-alpha strong stress ratio 0.00 after run-id collision fix.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0",
            "--motion-mode",
            "static",
            "--motion-strength",
            "0",
            "--video-layout-mode",
            "element-frame-scale",
            "--layout-transform-strength",
            "0.18",
            "--layout-transform-pan",
            "0.035",
            "--element-scale-ratio",
            "0.00",
            "--element-anchor-padding",
            "4",
            "--element-mask-mode",
            "text-alpha",
            "--experiment-label",
            "c25-alpha-r000",
            "--min-ocr-similarity",
            "0.35",
        ],
    ),
    Experiment(
        label="c25-alpha-r025",
        notes="Relaunch text-alpha strong stress ratio 0.25 after run-id collision fix.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0",
            "--motion-mode",
            "static",
            "--motion-strength",
            "0",
            "--video-layout-mode",
            "element-frame-scale",
            "--layout-transform-strength",
            "0.18",
            "--layout-transform-pan",
            "0.035",
            "--element-scale-ratio",
            "0.25",
            "--element-anchor-padding",
            "4",
            "--element-mask-mode",
            "text-alpha",
            "--experiment-label",
            "c25-alpha-r025",
            "--min-ocr-similarity",
            "0.35",
        ],
    ),
    Experiment(
        label="c25-alpha-moderate-r010",
        notes="Check whether text-alpha only fails under strong stress or also moderate stress.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0",
            "--motion-mode",
            "static",
            "--motion-strength",
            "0",
            "--video-layout-mode",
            "element-frame-scale",
            "--layout-transform-strength",
            "0.08",
            "--layout-transform-pan",
            "0.015",
            "--element-scale-ratio",
            "0.10",
            "--element-anchor-padding",
            "4",
            "--element-mask-mode",
            "text-alpha",
            "--experiment-label",
            "c25-alpha-moderate-r010",
            "--min-ocr-similarity",
            "0.50",
        ],
    ),
    Experiment(
        label="c25-rectangle-r010",
        notes="Rectangle anchor ratio 0.10 control to separate alpha-mask failure from scale-ratio behavior.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0",
            "--motion-mode",
            "static",
            "--motion-strength",
            "0",
            "--video-layout-mode",
            "element-frame-scale",
            "--layout-transform-strength",
            "0.18",
            "--layout-transform-pan",
            "0.035",
            "--element-scale-ratio",
            "0.10",
            "--element-anchor-padding",
            "4",
            "--element-mask-mode",
            "rectangle",
            "--experiment-label",
            "c25-rectangle-r010",
            "--min-ocr-similarity",
            "0.35",
        ],
    ),
    Experiment(
        label="c25-responsive-strong",
        notes="Stronger responsive-squeeze boundary after the first responsive-squeeze pass.",
        args=[
            *BASE_ARGS,
            "--flow-scale",
            "0.16",
            "--motion-mode",
            "responsive-squeeze",
            "--motion-strength",
            "0.16",
            "--video-viewport-mode",
            "zoom-pulse",
            "--viewport-zoom",
            "0.12",
            "--viewport-pan",
            "0.025",
            "--experiment-label",
            "c25-responsive-strong",
            "--min-ocr-similarity",
            "0.25",
        ],
    ),
]


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    LOOP_LOG.parent.mkdir(parents=True, exist_ok=True)
    with LOOP_LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"[{stamp}] {message}\n")
    print(message, flush=True)


def tmux_sessions() -> set[str]:
    result = subprocess.run(["tmux", "list-sessions", "-F", "#{session_name}"], text=True, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if result.returncode != 0:
        return set()
    return {line.strip() for line in result.stdout.splitlines() if line.strip()}


def log_done(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    if "FileExistsError" in text:
        return False
    return "DONE " in text or "Traceback" in text or "Invalid value" in text


def launch(exp: Experiment) -> None:
    command = " ".join(
        [
            "cd /Users/dennisonbertram/Develop/flipbook-research",
            "&&",
            f"FLIPBOOK_COMMIT={COMMIT}",
            "modal",
            "run",
            "scripts/track_c/modal_canvas_c2_lite.py",
            *exp.args,
            ">",
            str(exp.log_path),
            "2>&1",
        ]
    )
    subprocess.run(["tmux", "new-session", "-d", "-s", exp.session, command], check=True)
    log(f"launched {exp.label}: {exp.notes}")


def evaluate() -> None:
    result = subprocess.run(
        ["python3", "scripts/track_c/evaluate_run.py"],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    for line in result.stdout.splitlines():
        log(f"eval {line}")


def summarize() -> None:
    state = {
        "updated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "active_sessions": sorted(tmux_sessions()),
        "experiments": [
            {
                "label": exp.label,
                "session": exp.session,
                "log": str(exp.log_path.relative_to(ROOT)),
                "done": log_done(exp.log_path),
                "notes": exp.notes,
            }
            for exp in EXPERIMENTS
        ],
    }
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Track C Autoresearch Status",
        "",
        f"Updated UTC: `{state['updated_utc']}`",
        "",
        "## Active Sessions",
        "",
    ]
    if state["active_sessions"]:
        lines.extend(f"- `{name}`" for name in state["active_sessions"])
    else:
        lines.append("- none")
    lines.extend(["", "## Queue", ""])
    for item in state["experiments"]:
        status = "done" if item["done"] else "pending/running"
        lines.append(f"- `{item['label']}`: {status} - {item['notes']}")
    STATUS_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log("autoresearch loop started")
    while True:
        sessions = tmux_sessions()
        active_owned = {name for name in sessions if name.startswith("track-c-") and name != "track-c-autoresearch"}
        for exp in EXPERIMENTS:
            if len(active_owned) >= MAX_PARALLEL:
                break
            if exp.session in sessions or log_done(exp.log_path):
                continue
            launch(exp)
            active_owned.add(exp.session)
        evaluate()
        summarize()
        time.sleep(300)


if __name__ == "__main__":
    main()
