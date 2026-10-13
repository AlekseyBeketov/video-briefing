from __future__ import annotations

import hashlib
import math
import re
from urllib.parse import parse_qs, urlparse

from .models import EvidenceBundle, TranscriptSegment

VIDEO_ID = "DvSwvJVens8"
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


def parse_video_url(value: str) -> tuple[str, str, str]:
    parsed = urlparse(value)
    if _ID_RE.fullmatch(value):
        return "youtube", value, f"https://www.youtube.com/watch?v={value}"
    if (parsed.scheme != "https" or parsed.hostname not in {"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"}
            or parsed.username is not None or parsed.password is not None or parsed.port is not None):
        raise ValueError("Only a credential-free standard YouTube HTTPS URL or 11-character video id is supported")
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
    if bundle.platform == "youtube":
        if not _ID_RE.fullmatch(bundle.video_id):
            raise ValueError("Invalid YouTube video id")
    elif bundle.platform == "local-file":
        if not re.fullmatch(r"[0-9a-f]{64}", bundle.video_id):
            raise ValueError("Local media identity must be a lowercase SHA-256")
        if bundle.variant != "local_asr" or bundle.source_type != "local-asr-chunk-transcript":
            raise ValueError("Local media bundle must declare local ASR provenance")
    else:
        raise ValueError("Unsupported source platform")
    if bundle.language.casefold() in {"und", "unknown", ""}:
        raise ValueError("Source language must be identified before analysis")
    if not re.fullmatch(r"[0-9a-f]{64}", bundle.raw_sha256):
        raise ValueError("Source SHA-256 must be a lowercase 64-character hex digest")
    if not isinstance(bundle.segments, list) or not 1 <= len(bundle.segments) <= 100_000:
        raise ValueError("Source must contain 1..100000 transcript segments")
    if any(not isinstance(segment, TranscriptSegment) for segment in bundle.segments):
        raise ValueError("Transcript segments have an invalid schema")
    if sum(len(segment.text.encode("utf-8")) for segment in bundle.segments if isinstance(segment.text, str)) > 20_000_000:
        raise ValueError("Transcript exceeds the 20 MB text limit")
    ids: set[str] = set()
    for segment in bundle.segments:
        if not isinstance(segment.id, str) or not segment.id or len(segment.id) > 100 or segment.id in ids:
            raise ValueError("Segment ids must be non-empty unique strings of at most 100 characters")
        ids.add(segment.id)
        if not isinstance(segment.text, str) or not segment.text.strip() or len(segment.text) > 20_000:
            raise ValueError(f"Segment {segment.id} is empty or exceeds the 20000 character limit")
        if not isinstance(segment.start_seconds, (int, float)) or isinstance(segment.start_seconds, bool) or not math.isfinite(segment.start_seconds) or segment.start_seconds < 0:
            raise ValueError(f"Segment {segment.id} has invalid start time")
        if not isinstance(segment.duration_seconds, (int, float)) or isinstance(segment.duration_seconds, bool) or not math.isfinite(segment.duration_seconds) or segment.duration_seconds < 0:
            raise ValueError(f"Segment {segment.id} has invalid duration")
    if bundle.raw_text is not None and not isinstance(bundle.raw_text, str):
        raise ValueError("Raw source must be a string")
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
