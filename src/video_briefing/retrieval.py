from __future__ import annotations

from .models import EvidenceBundle, TranscriptSegment


def _terms(text: str) -> set[str]:
    words = {word.casefold() for word in text.replace("ё", "е").split()}
    cleaned = {"".join(ch for ch in word if ch.isalnum()) for word in words}
    return {word for word in cleaned if len(word) > 1}


def retrieve(bundle: EvidenceBundle, question: str, limit: int = 8, context_radius: int = 1) -> list[TranscriptSegment]:
    query = _terms(question)
    if not query:
        return []
    ranked = []
    for index, segment in enumerate(bundle.segments):
        words = _terms(segment.text)
        score = len(query & words) / max(1, len(query))
        # Also reward the rare case where the question is phrased in a different morphology.
        if score == 0:
            score = 0.15 * sum(1 for q in query for word in words if len(q) > 4 and len(word) > 4 and (q in word or word in q)) / len(query)
        if score > 0:
            ranked.append((score, index))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    chosen: set[int] = set()
    for _, index in ranked[:limit]:
        chosen.update(range(max(0, index - context_radius), min(len(bundle.segments), index + context_radius + 1)))
    return [segment for index, segment in enumerate(bundle.segments) if index in chosen]
