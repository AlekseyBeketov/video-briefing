from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..models import EvidenceBundle, TranscriptSegment
from ..validation import parse_video_url, validate_bundle


def _timed_segments(payload: Any) -> list[dict]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    extracted = payload.get("extracted")
    if isinstance(extracted, dict):
        for key in ("transcriptSegments", "segments", "transcript_segments"):
            value = extracted.get(key)
            if isinstance(value, list):
                return value
        metadata = extracted.get("transcriptMetadata")
        if isinstance(metadata, dict) and isinstance(metadata.get("segments"), list):
            return metadata["segments"]
    for key in ("transcriptSegments", "segments", "transcript_segments"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    transcript = payload.get("transcript")
    if isinstance(transcript, dict):
        for key in ("segments", "transcriptSegments"):
            if isinstance(transcript.get(key), list):
                return transcript[key]
    return []


def parse_summarize_output(stdout: str, video_id: str, language: str) -> EvidenceBundle:
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("summarize stdout is not JSON; diagnostics must remain on stderr") from exc
    extracted = payload.get("extracted", {}) if isinstance(payload, dict) else {}
    raw_segments = _timed_segments(payload)
    if not raw_segments:
        raise ValueError("summarize returned no timed transcript segments (metadata/description is not evidence)")
    segments = []
    for index, item in enumerate(raw_segments, 1):
        if not isinstance(item, dict):
            continue
        start_ms = item.get("startMs")
        end_ms = item.get("endMs")
        start = item.get("start", item.get("startSeconds", item.get("start_seconds")))
        end = item.get("end", item.get("endSeconds", item.get("end_seconds")))
        if start is None and start_ms is not None:
            start = float(start_ms) / 1000
        if end is None and end_ms is not None:
            end = float(end_ms) / 1000
        duration = item.get("duration", item.get("durationSeconds", item.get("duration_seconds")))
        if duration is None and start is not None and end is not None:
            duration = float(end) - float(start)
        segments.append(TranscriptSegment(str(item.get("id") or f"s{index:05d}"), str(item.get("text", "")), float(start) if start is not None else -1, float(duration) if duration is not None else -1))
    raw_text = json.dumps(raw_segments, ensure_ascii=False, separators=(",", ":"))
    source_language = str(extracted.get("language") or "und")
    metadata = {
        "title": extracted.get("title"),
        "description": extracted.get("description"),
        "transcript_source": extracted.get("transcriptSource"),
        "transcription_provider": extracted.get("transcriptionProvider"),
        "transcript_metadata": extracted.get("transcriptMetadata"),
        "requested_output_language": language,
        "source_language_reported": extracted.get("language"),
    }
    warnings = [] if source_language != "und" else ["summarize JSON did not identify the selected caption track language"]
    bundle = EvidenceBundle("youtube", video_id, f"https://www.youtube.com/watch?v={video_id}", source_language, "summarize", "captions", str(payload.get("version", "unknown")) if isinstance(payload, dict) else "unknown", segments, hashlib.sha256(raw_text.encode()).hexdigest(), datetime.now(timezone.utc).isoformat(), metadata, warnings, raw_text)
    validate_bundle(bundle)
    return bundle


def extract(url: str, *, language: str = "en", executable: str | Path | None = None) -> EvidenceBundle:
    _, video_id, canonical_url = parse_video_url(url)
    binary = Path(executable or os.environ.get("VIDEO_BRIEFING_SUMMARIZE", ".tools/summarize/summarize")).expanduser().resolve()
    if not binary.is_file():
        raise FileNotFoundError(f"Pinned project-local summarize binary missing: {binary}. Run scripts/setup-tools.sh")
    version_run = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=30, check=False)
    if version_run.returncode != 0:
        raise RuntimeError(f"summarize --version failed: {version_run.stderr.strip()}")
    command = [str(binary), canonical_url, "--youtube", "web", "--video-mode", "transcript", "--extract", "--timestamps", "--json", "--metrics", "off", "--firecrawl", "off", "--preprocess", "off"]
    run = subprocess.run(command, capture_output=True, text=True, timeout=900, check=False)
    if run.returncode != 0:
        raise RuntimeError(f"summarize failed ({run.returncode}): {run.stderr.strip() or run.stdout.strip()}")
    bundle = parse_summarize_output(run.stdout, video_id, language)
    bundle.url = canonical_url
    bundle.extractor_version = version_run.stdout.strip()
    bundle.metadata["runtime"] = {"binary": str(binary), "version": bundle.extractor_version, "stderr": run.stderr}
    return bundle
