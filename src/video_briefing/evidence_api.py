"""Bounded, source-first transcript search/read API for humans and agents."""
from __future__ import annotations

import math
from .models import EvidenceBundle
from .retrieval import retrieve

MAX_QUERY_CHARS = 2_000
MAX_READ_SECONDS = 600
MAX_RESULTS = 50
MAX_RESULT_CHARS = 20_000


def _validate_query(query: str, limit: int) -> None:
    if not isinstance(query, str) or not query.strip() or len(query) > MAX_QUERY_CHARS:
        raise ValueError(f"query must contain 1..{MAX_QUERY_CHARS} characters")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= MAX_RESULTS:
        raise ValueError(f"limit must be between 1 and {MAX_RESULTS}")


def search_evidence(bundle: EvidenceBundle, query: str, limit: int = 12) -> dict:
    """Return transcript excerpts only; an agent performs final synthesis and citations."""
    _validate_query(query, limit)
    segments = retrieve(bundle, query, limit=limit)
    output = []
    size = 0
    truncated = False
    for item in segments:
        remaining = MAX_RESULT_CHARS - size
        if remaining <= 0:
            truncated = True
            break
        if len(item.text) > remaining:
            text = item.text[:remaining]
            truncated = True
        else:
            text = item.text
        size += len(text)
        output.append({"segment_id": item.id, "start_seconds": item.start_seconds,
                       "end_seconds": item.start_seconds + item.duration_seconds, "text": text})
        if truncated:
            break
    return {"status": "ok" if output else "no_evidence", "video_id": bundle.video_id,
            "source_sha256": bundle.raw_sha256, "source_type": bundle.source_type,
            "language": bundle.language, "query": query, "evidence": output, "truncated": truncated,
            "limitations": ["Relevance retrieval is not semantic entailment.",
                            "Citations identify source intervals; an agent must verify each claim against the quoted text."]}


def read_evidence(bundle: EvidenceBundle, start_seconds: float, end_seconds: float,
                  *, max_segments: int = MAX_RESULTS) -> dict:
    if (isinstance(start_seconds, bool) or not isinstance(start_seconds, (int, float))
            or isinstance(end_seconds, bool) or not isinstance(end_seconds, (int, float))
            or not math.isfinite(start_seconds) or not math.isfinite(end_seconds)):
        raise ValueError("time bounds must be finite numbers")
    if start_seconds < 0 or end_seconds <= start_seconds or end_seconds - start_seconds > MAX_READ_SECONDS:
        raise ValueError(f"time range must be positive and no longer than {MAX_READ_SECONDS} seconds")
    _validate_query("time range", max_segments)
    matching = [s for s in bundle.segments if s.start_seconds < end_seconds
                and s.start_seconds + s.duration_seconds >= start_seconds]
    selected = matching[:max_segments]
    evidence = []
    size = 0
    truncated = len(matching) > max_segments
    for segment in selected:
        text = segment.text
        remaining = MAX_RESULT_CHARS - size
        if len(text) > remaining:
            if remaining > 0:
                evidence.append({"segment_id": segment.id, "start_seconds": segment.start_seconds,
                                 "end_seconds": segment.start_seconds + segment.duration_seconds,
                                 "text": text[:remaining], "truncated": True})
            truncated = True
            break
        evidence.append({"segment_id": segment.id, "start_seconds": segment.start_seconds,
                         "end_seconds": segment.start_seconds + segment.duration_seconds, "text": text})
        size += len(text)
    return {"status": "ok" if evidence else "no_evidence", "video_id": bundle.video_id,
            "source_sha256": bundle.raw_sha256, "source_type": bundle.source_type,
            "language": bundle.language, "requested_range_seconds": [start_seconds, end_seconds],
            "evidence": evidence, "truncated": truncated}
