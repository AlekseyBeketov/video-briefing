from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from pathlib import Path
from typing import Iterable

from .llm import JsonLLM
from .models import EvidenceBundle
from .retrieval import retrieve
from .validation import validate_briefing, validate_citations

SYSTEM = Path(__file__).resolve().parents[2] / "prompts" / "brief.md"
MAX_CHARS = 22000
BRIEF_SCHEMA = {
    "type": "object",
    "properties": {
        "gist": {"type": "string"},
        "gist_evidence": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "topics": {"type": "array", "items": {"type": "object", "properties": {"text": {"type": "string"}, "evidence": {"type": "array", "items": {"type": "string"}, "minItems": 1}}, "required": ["text", "evidence"], "additionalProperties": False}},
        "useful_ideas": {"type": "array", "items": {"type": "object", "properties": {"text": {"type": "string"}, "evidence": {"type": "array", "items": {"type": "string"}, "minItems": 1}, "kind": {"type": "string", "enum": ["source", "inference"]}}, "required": ["text", "evidence", "kind"], "additionalProperties": False}},
        "emphases": {"type": "array", "items": {"type": "object", "properties": {"text": {"type": "string"}, "evidence": {"type": "array", "items": {"type": "string"}, "minItems": 1}}, "required": ["text", "evidence"], "additionalProperties": False}},
        "caveats": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["gist", "gist_evidence", "topics", "useful_ideas", "emphases", "caveats"],
    "additionalProperties": False,
}


def _normalize_inline_gist_citations(result: dict) -> None:
    if result.get("gist_evidence") or not isinstance(result.get("gist"), str):
        return
    cited: list[str] = []

    def move_inline_citation(match: re.Match[str]) -> str:
        cited.extend(re.findall(r"[A-Za-z][A-Za-z0-9_-]*\d+", match.group(1)))
        return ""

    result["gist"] = re.sub(r"\[([^\]]+)\]", move_inline_citation, result["gist"]).strip()
    result["gist_evidence"] = list(dict.fromkeys(cited))


def _schema_for_ids(identifiers: list[str]) -> dict:
    schema = deepcopy(BRIEF_SCHEMA)
    allowed = sorted(set(identifiers))
    schema["properties"]["gist_evidence"]["items"]["enum"] = allowed
    for section in ("topics", "useful_ideas", "emphases"):
        schema["properties"][section]["items"]["properties"]["evidence"]["items"]["enum"] = allowed
    return schema


def chunk_segments(bundle: EvidenceBundle, max_chars: int = MAX_CHARS) -> list[list]:
    chunks, current, size = [], [], 0
    for segment in bundle.segments:
        cost = len(segment.text) + 80
        if current and size + cost > max_chars:
            chunks.append(current)
            current = [current[-1]]
            size = len(current[0].text) + 80
        current.append(segment)
        size += cost
    if current:
        chunks.append(current)
    return chunks


def brief_bundle(bundle: EvidenceBundle, llm: JsonLLM) -> tuple[dict, dict]:
    prompt_system = SYSTEM.read_text(encoding="utf-8")
    prompt_hash = hashlib.sha256(prompt_system.encode()).hexdigest()
    source_segments = {segment.id: segment for segment in bundle.segments}
    parts = []
    for index, chunk in enumerate(chunk_segments(bundle)):
        lines = "\n".join(f"[{s.id}] {s.start_seconds:.2f}+{s.duration_seconds:.2f}s {s.text}" for s in chunk)
        parts.append(llm.generate_json(system=prompt_system, prompt=f"Transcript part {index + 1}/{len(chunk_segments(bundle))}, source language {bundle.language}. Use only this part.\n{lines}", schema=BRIEF_SCHEMA))
    if len(parts) == 1:
        result = parts[0]
    else:
        result = llm.generate_json(system=prompt_system, prompt="Synthesize this complete-video outline into the required concise Russian JSON briefing. Retain only supported evidence IDs and do not add claims.\n" + json.dumps(parts, ensure_ascii=False), schema=BRIEF_SCHEMA)
    _normalize_inline_gist_citations(result)
    unknown = validate_citations(result, bundle)
    if unknown:
        claims = [{"text": result.get("gist", ""), "evidence": result.get("gist_evidence", [])}]
        for section in ("topics", "useful_ideas", "emphases"):
            claims.extend(result.get(section, []))
        contexts: dict[str, str] = {}
        claim_candidates = []
        for claim in claims:
            claim_text = str(claim.get("text", "")).strip()
            matches = retrieve(bundle, claim_text, limit=3)
            candidate_ids = [segment.id for segment in matches]
            claim_candidates.append({"claim": claim_text, "candidate_ids": candidate_ids})
            for segment in matches:
                contexts[segment.id] = f"[{segment.id}] {segment.start_seconds:.2f}+{segment.duration_seconds:.2f}s: {segment.text}"
        allowed_ids = list(contexts)
        if not allowed_ids:
            raise ValueError(f"Brief cites unknown IDs and no source context could be retrieved: {', '.join(unknown)}")
        repair_prompt = (
            "Repair this draft against the supplied original transcript snippets. Some IDs are invented. "
            "Return the required concise Russian briefing, cite only IDs shown in the snippets, and omit unsupported claims. "
            "Do not add facts. Draft claims/candidates:\n" + json.dumps(claim_candidates, ensure_ascii=False) +
            "\nOriginal source snippets:\n" + "\n".join(contexts.values())
        )
        result = llm.generate_json(system=prompt_system, prompt=repair_prompt, schema=_schema_for_ids(allowed_ids))
        _normalize_inline_gist_citations(result)
    gist_citations_derived = False
    if not result.get("gist_evidence"):
        result["gist_evidence"] = list(dict.fromkeys(
            identifier
            for topic in result.get("topics", [])
            for identifier in topic.get("evidence", [])
        ))
        gist_citations_derived = bool(result["gist_evidence"])
    validate_briefing(result, bundle)
    # Every reference is rendered to exact original segment times; IDs from unprovided source fail closed.
    result["gist_evidence_resolved"] = [
        {"id": identifier, "start_seconds": source_segments[identifier].start_seconds,
         "duration_seconds": source_segments[identifier].duration_seconds}
        for identifier in result["gist_evidence"]
    ]
    for section in ("topics", "useful_ideas", "emphases"):
        for claim in result.get(section, []):
            claim["evidence"] = [
                {"id": identifier, "start_seconds": source_segments[identifier].start_seconds,
                 "duration_seconds": source_segments[identifier].duration_seconds}
                for identifier in claim.get("evidence", [])
            ]
    result.setdefault("caveats", [])
    result["source_language"] = bundle.language
    result["source_sha256"] = bundle.raw_sha256
    model_info = {
        "requested_model": getattr(llm, "model", "unknown"),
        "actual_model": getattr(llm, "last_response", {}).get("model"),
        "prompt_sha256": prompt_hash,
        "source_sha256": bundle.raw_sha256,
        "prompt_tokens": getattr(llm, "last_response", {}).get("prompt_eval_count"),
        "completion_tokens": getattr(llm, "last_response", {}).get("eval_count"),
        "cloud_backed": True,
        "gist_citations_derived_from_topics": gist_citations_derived,
    }
    return result, model_info


def render_brief(result: dict) -> str:
    gist_refs = ", ".join(
        f"{source_segments_id} @{float(seconds):.0f}с"
        for source_segments_id, seconds in ((item.get("id"), item.get("start_seconds", 0)) for item in result.get("gist_evidence_resolved", []))
    )
    lines = ["Суть", str(result.get("gist", "")) + (f" [{gist_refs}]" if gist_refs else ""), "", "Темы"]
    for item in result.get("topics", []):
        citations = ", ".join(f"{e['id']} @{e['start_seconds']:.0f}с" if isinstance(e, dict) else str(e) for e in item.get("evidence", []))
        lines.append(f"- {item.get('text', '')}" + (f" [{citations}]" if citations else ""))
    lines.extend(["", "Полезные идеи"])
    for item in result.get("useful_ideas", []):
        citations = ", ".join(f"{e['id']} @{e['start_seconds']:.0f}с" if isinstance(e, dict) else str(e) for e in item.get("evidence", []))
        lines.append(f"- {item.get('text', '')}" + (f" [{citations}]" if citations else ""))
    lines.extend(["", "Акценты участников"])
    for item in result.get("emphases", []):
        citations = ", ".join(f"{e['id']} @{e['start_seconds']:.0f}с" if isinstance(e, dict) else str(e) for e in item.get("evidence", []))
        lines.append(f"- {item.get('text', '')}" + (f" [{citations}]" if citations else ""))
    if result.get("caveats"):
        lines.extend(["", "Оговорки"])
        lines.extend(f"- {item}" for item in result["caveats"])
    return "\n".join(lines).strip() + "\n"
