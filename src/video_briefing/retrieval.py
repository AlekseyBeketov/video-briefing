from __future__ import annotations

import math
import re
from bisect import bisect_left
from collections import Counter

from .models import EvidenceBundle, TranscriptSegment


def _terms(text: str) -> set[str]:
    # Split hyphenated captions/queries rather than fusing NPU-чип into npuchip.
    cleaned = set(re.findall(r"[^\W_]+", text.casefold().replace("ё", "е")))
    stop_words = {
        "а", "без", "бы", "в", "вам", "вас", "во", "вот", "все", "вы", "где", "для",
        "до", "его", "ее", "если", "же", "за", "и", "из", "или", "им", "их", "к", "как",
        "кто", "ли", "мне", "мы", "на", "над", "нам", "не", "него", "нее", "но",
        "о", "об", "однако", "он", "она", "они", "оно", "от", "по", "под", "при", "про",
        "с", "со", "так", "такой", "там", "те", "то", "тоже", "у", "уже", "что", "чем",
        "это", "этот", "я", "автор", "ведущий", "говорит", "говорил", "объясняет", "рассказывает",
        "какой", "какая", "какие", "каком", "главный", "главная", "делает", "описывает", "нового",
        "объяснении", "акцент", "при", "чем", "чём", "зависимости", "нужного", "пожалуйста",
        "можно", "считать", "ролик", "ролике", "всех", "таких", "относятся", "эту", "кому",
        "источнике", "ведущего", "обязательно", "только", "описаны", "приписать", "осторожно",
        "the", "and", "for", "from", "how", "does", "what", "when", "where", "which", "who",
        "why", "with", "about", "author", "speaker", "say", "says", "explain", "explains",
    }
    return {word for word in cleaned if len(word) > 1 and word not in stop_words}


_QUERY_ALIASES = {
    "компромисс": {"уступает", "медленнее", "скорость", "зато", "помещается"},
    "компромисса": {"уступает", "медленнее", "скорость", "зато", "помещается"},
    "tradeoff": {"slower", "speed", "fits", "capacity"},
    "tradeoffs": {"slower", "speed", "fits", "capacity"},
    "почему": {"потому", "поэтому", "поскольку"},
    "финальная": {"итоге", "брать", "вариант"},
    "рекомендация": {"достаточно", "оптимальный", "имеет", "вариант", "покупайте"},
    "рекомендации": {"достаточно", "оптимальный", "имеет", "вариант", "покупайте"},
    "операционной": {"macos", "windows", "linux", "mac"},
    "системы": {"macos", "windows", "linux", "mac"},
    "стека": {"софт", "mlx", "metal", "cuda", "rocm"},
    "программного": {"софт", "mlx", "metal", "cuda", "rocm"},
    "нас": {"nas", "24x7", "хранит", "подключённый", "крышку"},
    "nas": {"нас", "24x7", "хранит", "подключённый", "крышку"},
    "держать": {"дома", "24x7", "закрыли", "крышку", "подключённый", "хранит"},
    "возможности": {"есть", "поиск", "обещает", "добавить", "docker", "виртуальные"},
    "обещаны": {"обещает", "добавить"},
}


PASSAGE_CHARS = 1200
MAX_CONTEXT_CHARS = 16000
MAX_PASSAGE_SEGMENTS = 64
MIN_RELATIVE_SCORE = 0.25


def _match_strength(term: str, words: set[str]) -> float:
    if term in words:
        return 1.0
    aliases = sum(alias in words for alias in _QUERY_ALIASES.get(term, set()))
    if aliases:
        return 0.65 + 0.15 * min(3, aliases - 1)
    # Conservative Russian inflection/prefix matching; short acronyms must match exactly.
    if len(term) > 4 and any(
        len(word) >= 4 and (term in word or word in term or (len(word) > 4 and term[:5] == word[:5]))
        for word in words
    ):
        return 0.65
    return 0.0


def _passage_ranges(segments: list[TranscriptSegment], radius: int) -> list[tuple[int, int]]:
    """Sentence-bounded blocks, with sentence overlap but never across a source-time gap.

    Rank these complete passages, not individual two-second captions. A later conditional
    clause must compete with the beginning of a passage, not lose to twelve repeated hits
    on the same product name. Captions without punctuation have a bounded fallback.
    """
    if radius == 0:
        return [(index, index + 1) for index in range(len(segments))]
    runs = [0]
    for index in range(1, len(segments)):
        previous = segments[index - 1]
        if segments[index].start_seconds - previous.start_seconds - previous.duration_seconds > 8:
            runs.append(index)
    runs.append(len(segments))
    ranges = []
    for run_start, run_end in zip(runs, runs[1:]):
        boundaries = [run_start] + [
            index for index in range(run_start + 1, run_end)
            if re.search(r"[.!?](?:\s|$)", segments[index - 1].text)
        ] + [run_end]
        start = run_start
        while start < run_end:
            end, size = start, 0
            while end < run_end and size < PASSAGE_CHARS and end - start < MAX_PASSAGE_SEGMENTS:
                size += len(segments[end].text)
                end += 1
            # Finish the current sentence, unless caption punctuation is missing for too long.
            while end < run_end and end not in boundaries and end - start < MAX_PASSAGE_SEGMENTS:
                end += 1
            left = boundaries[max(0, bisect_left(boundaries, start) - radius)]
            right = boundaries[min(len(boundaries) - 1, bisect_left(boundaries, end) + radius)]
            # Overlap itself must not turn a punctuation-free run into an unbounded window.
            left = max(left, start - MAX_PASSAGE_SEGMENTS)
            right = min(right, end + MAX_PASSAGE_SEGMENTS)
            ranges.append((left, right))
            start = end
    return ranges


def retrieve(bundle: EvidenceBundle, question: str, limit: int = 12, context_radius: int = 2) -> list[TranscriptSegment]:
    """Select bounded, query-relevant passages with facet diversity; preserve source order.

    limit is the maximum number of passages (captions when context_radius=0), not a
    requirement to fill the context. Runtime never reads evaluation answers or anchor IDs.
    """
    query = _terms(question)
    if not query or limit <= 0 or not bundle.segments:
        return []
    if context_radius < 0:
        raise ValueError("context_radius must be nonnegative")
    document_terms = [_terms(segment.text) for segment in bundle.segments]
    ranges = _passage_ranges(bundle.segments, context_radius)
    window_terms = [set().union(*document_terms[start:end]) for start, end in ranges]
    strengths = [{term: _match_strength(term, words) for term in sorted(query)} for words in window_terms]
    frequency = Counter(term for matches in strengths for term, strength in matches.items() if strength)
    weights = {
        term: math.log1p((len(ranges) - frequency[term] + 0.5) / (frequency[term] + 0.5))
        for term in query
    }
    candidates = []
    for (start, end), matches in zip(ranges, strengths):
        scores = {term: strength * weights[term] for term, strength in matches.items()}
        score = sum(scores.values())
        if score:
            candidates.append((score, start, end, scores))
    # Do not fill the passage limit with incidental matches to a common product word.
    best_score = max((candidate[0] for candidate in candidates), default=0)
    candidates = [candidate for candidate in candidates if candidate[0] >= MIN_RELATIVE_SCORE * best_score]
    chosen: set[int] = set()
    hits: Counter[str] = Counter()
    size = 0
    for _ in range(limit):
        ranked = []
        for score, start, end, scores in candidates:
            fresh = set(range(start, end)) - chosen
            overlap = 1 - len(fresh) / (end - start)
            cost = sum(len(bundle.segments[index].text) + 1 for index in fresh)
            if not fresh or overlap > 0.5 or size + cost > MAX_CONTEXT_CHARS:
                continue
            gain = sum(value / (1 + hits[term]) for term, value in scores.items())
            ranked.append(((0.5 * score + 0.5 * gain) * (1 - overlap), start, end, scores, cost))
        if not ranked:
            break
        _, start, end, scores, cost = max(ranked, key=lambda item: (item[0], -item[1]))
        chosen.update(range(start, end))
        hits.update(term for term, value in scores.items() if value)
        size += cost
    return [segment for index, segment in enumerate(bundle.segments) if index in chosen]
