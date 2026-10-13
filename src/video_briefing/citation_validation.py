"""Deterministic citation integrity checks, deliberately not semantic entailment."""
from __future__ import annotations

import math
import re

from .models import EvidenceBundle

MAX_CLAIMS = 50
MAX_CLAIM_CHARS = 2000
MAX_QUOTE_CHARS = 2000


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def validate_citations(bundle: EvidenceBundle, claims: list[dict]) -> dict:
    """Reject wrong source IDs, invented segments, wrong times and unsupported literal quotes.

    This check does NOT establish that the quoted text entails the claim's meaning.
    Invalid submissions remain invalid; canonical time bounds are suggestions only.
    """
    if not isinstance(claims, list) or not 1 <= len(claims) <= MAX_CLAIMS:
        raise ValueError(f"claims must be a list containing 1..{MAX_CLAIMS} items")
    source = {segment.id: (index, segment) for index, segment in enumerate(bundle.segments)}
    results = []
    for index, claim in enumerate(claims):
        if not isinstance(claim, dict):
            raise ValueError("every claim must be an object")
        text, quote = claim.get("claim"), claim.get("quote")
        if not isinstance(text, str) or not 1 <= len(text.strip()) <= MAX_CLAIM_CHARS:
            raise ValueError("claim text is missing or exceeds the size limit")
        if not isinstance(quote, str) or not 1 <= len(quote.strip()) <= MAX_QUOTE_CHARS:
            raise ValueError("literal quote is missing or exceeds the size limit")
        ids = claim.get("segment_ids")
        if not isinstance(ids, list) or not 1 <= len(ids) <= 50 or any(not isinstance(s, str) for s in ids):
            raise ValueError("segment_ids must contain 1..50 string identifiers")
        errors = []
        if claim.get("source_id", bundle.video_id) != bundle.video_id:
            errors.append("source_identity_mismatch")
        if claim.get("source_sha256", bundle.raw_sha256) != bundle.raw_sha256:
            errors.append("source_hash_mismatch")
        if len(set(ids)) != len(ids):
            errors.append("duplicate_segment_id")
        if any(sid not in source for sid in ids):
            errors.append("unknown_segment_id")
        start, end = claim.get("start_seconds"), claim.get("end_seconds")
        valid_times = all(isinstance(v, (int, float)) and not isinstance(v, bool)
                          and math.isfinite(v) for v in (start, end))
        if not valid_times:
            errors.append("invalid_time_bounds")
        canonical = None
        if all(sid in source for sid in ids):
            selected = [source[sid] for sid in ids]
            selected.sort(key=lambda item: item[0])
            segments = [item[1] for item in selected]
            canonical = [min(s.start_seconds for s in segments),
                         max(s.start_seconds + s.duration_seconds for s in segments)]
            if valid_times and isinstance(start, (int, float)) and isinstance(end, (int, float)):
                if abs(start - canonical[0]) > 1e-6 or abs(end - canonical[1]) > 1e-6:
                    errors.append("time_bounds_mismatch")
            # A quotation cannot bridge uncited source segments.
            passages = []
            last = None
            for position, segment in selected:
                if last is not None and position == last + 1:
                    passages[-1] += " " + segment.text
                else:
                    passages.append(segment.text)
                last = position
            if not any(_normalize(quote) in _normalize(passage) for passage in passages):
                errors.append("quote_not_in_cited_segments")
        results.append({"index": index, "valid": not errors, "errors": errors,
                        "canonical_range_seconds": canonical})
    return {"status": "valid" if all(item["valid"] for item in results) else "invalid",
            "video_id": bundle.video_id, "source_sha256": bundle.raw_sha256,
            "semantic_support_checked": False, "citations": results,
            "limitations": ["Literal citation integrity is not proof of semantic support.",
                            "An agent must verify every assertion and condition against the source."]}
