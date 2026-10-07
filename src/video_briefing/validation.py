from __future__ import annotations

import hashlib
import math
import re
from urllib.parse import parse_qs, urlparse

from .models import EvidenceBundle

VIDEO_ID = "DvSwvJVens8"
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def parse_video_url(value: str) -> tuple[str, str, str]:
    parsed = urlparse(value)
    if _ID_RE.fullmatch(value):
        return "youtube", value, f"https://www.youtube.com/watch?v={value}"
    if parsed.scheme != "https" or parsed.hostname not in {"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"}:
        raise ValueError("Only a YouTube URL or 11-character video id is supported")
    if parsed.hostname == "youtu.be":
        video_id = parsed.path.strip("/").split("/")[0]
    elif parsed.path == "/watch":
        video_id = parse_qs(parsed.query).get("v", [""])[0]
    else:
        pieces = [piece for piece in parsed.path.split("/") if piece]
        video_id = pieces[1] if len(pieces) >= 2 and pieces[0] in {"shorts", "embed", "live"} else ""
    if not _ID_RE.fullmatch(video_id):
        raise ValueError("YouTube URL does not contain a valid video id")
    return "youtube", video_id, f"https://www.youtube.com/watch?v={video_id}"


def validate_bundle(bundle: EvidenceBundle) -> None:
    if not bundle.platform or not bundle.video_id or not bundle.language or not bundle.variant:
        raise ValueError("Bundle identity, source language, and extractor variant are required")
    if not _ID_RE.fullmatch(bundle.video_id):
        raise ValueError("Invalid YouTube video id")
    if bundle.language.casefold() in {"und", "unknown", ""}:
        raise ValueError("Source language must be identified before analysis")
    if not re.fullmatch(r"[0-9a-f]{64}", bundle.raw_sha256):
        raise ValueError("Source SHA-256 must be a lowercase 64-character hex digest")
    if not bundle.segments or not any(segment.text.strip() for segment in bundle.segments):
        raise ValueError("Source has no transcript text; descriptions/metadata are not evidence")
    ids: set[str] = set()
    for segment in bundle.segments:
        if not segment.id or segment.id in ids:
            raise ValueError("Segment ids must be non-empty and unique")
        ids.add(segment.id)
        if not segment.text.strip():
            raise ValueError(f"Segment {segment.id} is empty")
        if not math.isfinite(segment.start_seconds) or segment.start_seconds < 0:
            raise ValueError(f"Segment {segment.id} has invalid start time")
        if not math.isfinite(segment.duration_seconds) or segment.duration_seconds < 0:
            raise ValueError(f"Segment {segment.id} has invalid duration")
    if bundle.raw_text is not None and hashlib.sha256(bundle.raw_text.encode("utf-8")).hexdigest() != bundle.raw_sha256:
        raise ValueError("Raw source hash does not match immutable source text")


def validate_citations(payload: dict, bundle: EvidenceBundle) -> list[str]:
    known = {segment.id for segment in bundle.segments}
    unknown: list[str] = []
    def scan(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key in {"evidence", "segment_ids", "gist_evidence"} and isinstance(child, list):
                    unknown.extend(str(item) for item in child if str(item) not in known)
                else:
                    scan(child)
        elif isinstance(value, list):
            for child in value:
                scan(child)
    scan(payload)
    return unknown


def validate_briefing(payload: dict, bundle: EvidenceBundle) -> None:
    if not isinstance(payload.get("gist"), str) or not payload["gist"].strip():
        raise ValueError("Brief must contain a non-empty gist")
    sections = [payload.get("gist_evidence", [])]
    for name in ("topics", "useful_ideas", "emphases"):
        items = payload.get(name, [])
        if not isinstance(items, list):
            raise ValueError(f"Brief section {name} must be a list")
        for item in items:
            if not isinstance(item, dict) or not str(item.get("text", "")).strip():
                raise ValueError(f"Brief section {name} contains an invalid claim")
            sections.append(item.get("evidence", []))
    caveats = payload.get("caveats", [])
    if not isinstance(caveats, list):
        raise ValueError("Brief caveats must be a list")
    for caveat in caveats:
        if not isinstance(caveat, dict) or not str(caveat.get("text", "")).strip():
            raise ValueError("Brief contains an invalid caveat")
        sections.append(caveat.get("evidence", []))
    if any(not isinstance(evidence, list) or not evidence for evidence in sections):
        raise ValueError("Every briefing claim, including gist, needs evidence segment ids")
    unknown = validate_citations(payload, bundle)
    if unknown:
        raise ValueError(f"Brief contains unknown evidence ids: {', '.join(unknown)}")
