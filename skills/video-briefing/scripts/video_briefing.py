#!/usr/bin/env python3
"""Run the checked-in video-briefing CLI from a canonical skill entrypoint."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys

DEFAULT_PROJECT = Path("/Users/alexbeketov/video-briefing")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the video-briefing project's pinned CLI")
    parser.add_argument("action", choices=("brief", "ask"))
    parser.add_argument("url", help="YouTube video URL")
    parser.add_argument("--question", help="Question to answer from cached transcript evidence")
    parser.add_argument("--language", default="ru", help="Caption language (default: ru)")
    parser.add_argument("--variant", default="captions_api", choices=("captions_api", "baoyu", "summarize"))
    parser.add_argument("--project", type=Path, help="Project checkout; defaults to VIDEO_BRIEFING_PROJECT or the configured checkout")
    args = parser.parse_args()

    if args.action == "ask" and not args.question:
        parser.error("ask requires --question")

    project = args.project or Path(os.environ.get("VIDEO_BRIEFING_PROJECT", DEFAULT_PROJECT))
    project = project.expanduser().resolve()
    if not (project / "pyproject.toml").is_file():
        print(f"Project checkout not found at {project}; set VIDEO_BRIEFING_PROJECT or pass --project", file=sys.stderr)
        return 2
    uv = shutil.which("uv")
    if not uv:
        print("uv is not on PATH; install uv and run `uv sync --frozen` in the project", file=sys.stderr)
        return 2

    command = [uv, "run", "--frozen", "video-briefing", args.action, args.url,
               "--variant", args.variant, "--languages", args.language]
    if args.question:
        command.append(args.question)
    if args.action == "brief":
        command.append("--json")
    return subprocess.run(command, cwd=project, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
