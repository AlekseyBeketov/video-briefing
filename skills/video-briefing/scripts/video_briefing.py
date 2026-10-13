#!/usr/bin/env python3
"""Portable compatibility launcher for an installed video-briefing command."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys


def main() -> int:
    executable = shutil.which("video-briefing")
    if not executable:
        print(json.dumps({"error": {"code": "not_installed", "message": "Install the video-briefing wheel and retry."}}), file=sys.stderr)
        return 2
    return subprocess.run([executable, *sys.argv[1:]], check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
