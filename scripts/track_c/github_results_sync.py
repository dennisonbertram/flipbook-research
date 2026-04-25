#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TRACK_C_DOCS = Path("docs/experiments/track-c")
SYNC_PATHS = [
    TRACK_C_DOCS,
    Path("docs/research/track-c-clean-page-state-next.md"),
    Path("scripts/track_c/modal_canvas_c2_lite.py"),
    Path("scripts/track_c/autoresearch_loop.py"),
    Path("scripts/track_c/evaluate_run.py"),
    Path("scripts/track_c/github_results_sync.py"),
]
TERMINAL_LOG_MARKERS = ("DONE ", "Traceback", "Invalid value", "FileExistsError")


def run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def checked(cmd: list[str], cwd: Path | None = None) -> str:
    result = run(cmd, cwd)
    if result.returncode != 0:
        raise RuntimeError(f"{' '.join(cmd)} failed:\n{result.stdout}")
    return result.stdout


def log(message: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"[{stamp}] {message}", flush=True)


def ensure_clone(repo_url: str, branch: str, clone_dir: Path) -> None:
    if not (clone_dir / ".git").exists():
        clone_dir.parent.mkdir(parents=True, exist_ok=True)
        checked(["git", "clone", "--branch", branch, repo_url, str(clone_dir)])
        return
    checked(["git", "fetch", "origin", branch], clone_dir)
    checked(["git", "checkout", branch], clone_dir)
    checked(["git", "pull", "--ff-only", "origin", branch], clone_dir)


def evaluate(project_dir: Path) -> None:
    result = run(["python3", "scripts/track_c/evaluate_run.py"], project_dir)
    if result.returncode != 0:
        raise RuntimeError(result.stdout)
    for line in result.stdout.splitlines()[-8:]:
        log(f"eval {line}")


def sync_docs(project_dir: Path, clone_dir: Path) -> None:
    source = project_dir / TRACK_C_DOCS
    dest = clone_dir / TRACK_C_DOCS
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, dest)
    for log_path in dest.glob("c*.log"):
        text = log_path.read_text(encoding="utf-8", errors="replace")
        if not any(marker in text for marker in TERMINAL_LOG_MARKERS):
            log_path.unlink()
    for rel_path in SYNC_PATHS:
        if rel_path == TRACK_C_DOCS:
            continue
        source_file = project_dir / rel_path
        if not source_file.exists():
            continue
        dest_file = clone_dir / rel_path
        dest_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, dest_file)


def commit_if_needed(clone_dir: Path) -> bool:
    paths = [str(path) for path in SYNC_PATHS]
    checked(["git", "add", *paths], clone_dir)
    status = checked(["git", "status", "--porcelain", "--", *paths], clone_dir).strip()
    if not status:
        log("no Track C docs changes to publish")
        return False
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    checked(["git", "commit", "-m", f"Update Track C results {stamp}"], clone_dir)
    checked(["git", "push", "origin", "HEAD"], clone_dir)
    log(f"published Track C docs update: {stamp}")
    return True


def sync_once(args: argparse.Namespace) -> bool:
    project_dir = Path(args.project_dir).resolve()
    clone_dir = Path(args.clone_dir).resolve()
    evaluate(project_dir)
    ensure_clone(args.repo_url, args.branch, clone_dir)
    sync_docs(project_dir, clone_dir)
    return commit_if_needed(clone_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Publish Track C docs/results to GitHub when they change.")
    parser.add_argument("--project-dir", default=str(ROOT))
    parser.add_argument("--clone-dir", default="/tmp/flipbook-research-public-sync")
    parser.add_argument("--repo-url", default="https://github.com/dennisonbertram/flipbook-research.git")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--interval-sec", type=int, default=600)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    while True:
        try:
            sync_once(args)
        except Exception as exc:
            log(f"sync failed: {exc}")
        if args.once:
            return
        time.sleep(max(60, args.interval_sec))


if __name__ == "__main__":
    main()
