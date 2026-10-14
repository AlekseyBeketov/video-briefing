from __future__ import annotations

import hashlib
import json
import os
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path

from ..models import EvidenceBundle, TranscriptSegment
from ..validation import parse_video_url, validate_bundle

def extract(url: str, *, languages: str = "en,ru", output_dir: str | Path,
            bun: str | Path | None = None, skill_dir: str | Path | None = None) -> EvidenceBundle:
    configured_skill = skill_dir or os.environ.get("VIDEO_BRIEFING_BAOYU")
    if not configured_skill:
        raise FileNotFoundError("Optional Baoyu adapter requires VIDEO_BRIEFING_BAOYU to point at its installed skill")
    baoyu_dir = Path(configured_skill).expanduser().resolve()
    configured_bun = bun or os.environ.get("VIDEO_BRIEFING_BUN")
    if not configured_bun:
        raise FileNotFoundError("Optional Baoyu adapter requires an explicit Bun executable path")
    _, video_id, canonical_url = parse_video_url(url)
    bun_path = Path(configured_bun).expanduser()
    if not bun_path.is_file():
        raise FileNotFoundError("Configured Bun executable is not a file")
    if not (baoyu_dir / "scripts/main.ts").is_file():
        raise FileNotFoundError("Configured Baoyu skill is missing scripts/main.ts")
    runtime = subprocess.run([str(bun_path), "--version"], capture_output=True, text=True, timeout=30, check=False)
    if runtime.returncode != 0:
        raise RuntimeError(f"Bun --version failed: {runtime.stderr.strip()}")
    output_root = (Path(output_dir).expanduser().resolve() / video_id / languages.split(",")[0] / uuid.uuid4().hex)
    output_root.mkdir(parents=True, exist_ok=True)
    run = subprocess.run(
        [str(bun_path), str(baoyu_dir / "scripts/main.ts"), canonical_url, "--languages", languages,
         "--format", "srt", "--output-dir", str(output_root)],
        capture_output=True, text=True, timeout=300, check=False,
    )
    if run.returncode != 0:
        raise RuntimeError(f"Baoyu failed ({run.returncode}): {run.stderr.strip() or run.stdout.strip()}")
    raw_files = list(output_root.glob("**/transcript-raw.json"))
    meta_files = sorted(output_root.glob("**/meta.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not raw_files:
        raise ValueError(f"Baoyu exited successfully without raw transcript JSON; stdout={run.stdout[:500]!r}; stderr={run.stderr[:500]!r}")
    raw_text = raw_files[0].read_text(encoding="utf-8")
    raw = json.loads(raw_text)
    segments = [TranscriptSegment(f"s{index:05d}", str(item.get("text", "")), float(item.get("start", -1)), float(item.get("duration", -1))) for index, item in enumerate(raw, 1)]
    metadata = json.loads(meta_files[0].read_text(encoding="utf-8")) if meta_files else {}
    language = str(metadata.get("language", {}).get("code") or "und")
    requested = languages.split(",")[0].strip().lower()
    if language.lower().split("-")[0] != requested.split("-")[0]:
        raise ValueError(f"Baoyu selected language {language!r}, expected {requested!r}; refusing non-comparable source")
    bundle = EvidenceBundle("youtube", video_id, canonical_url, language, "baoyu", "auto-captions" if metadata.get("language", {}).get("isGenerated") else "manual-captions", f"baoyu-skill-1.1.0; bun-{runtime.stdout.strip()}", segments, hashlib.sha256(raw_text.encode()).hexdigest(), datetime.now(timezone.utc).isoformat(), {**metadata, "runtime": {"bun": runtime.stdout.strip(), "raw_path": str(raw_files[0])}}, [], raw_text)
    validate_bundle(bundle)
    return bundle
