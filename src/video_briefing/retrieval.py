from __future__ import annotations

import math

from .models import EvidenceBundle, TranscriptSegment


def _terms(text: str) -> set[str]:
    words = {word.casefold() for word in text.replace("ё", "е").split()}
    cleaned = {"".join(ch for ch in word if ch.isalnum()) for word in words}
    stop_words = {
        "а", "без", "бы", "в", "вам", "вас", "во", "вот", "все", "вы", "где", "для",
        "до", "его", "ее", "если", "же", "за", "и", "из", "или", "им", "их", "к", "как",
        "кто", "ли", "мне", "мы", "на", "над", "нам", "не", "него", "нее", "но",
        "о", "об", "однако", "он", "она", "они", "оно", "от", "по", "под", "при", "про",
        "с", "со", "так", "такой", "там", "те", "то", "тоже", "у", "уже", "что", "чем",
        "это", "этот", "я", "автор", "ведущий", "говорит", "говорил", "объясняет", "рассказывает",
        "какой", "какая", "какие", "каком", "главный", "главная", "делает", "описывает", "нового",
        "объяснении", "акцент", "при", "чем", "чём", "зависимости", "нужного", "пожалуйста",
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


def retrieve(bundle: EvidenceBundle, question: str, limit: int = 8, context_radius: int = 1) -> list[TranscriptSegment]:
    query = _terms(question)
    if not query:
        return []
    aliases = {term: _QUERY_ALIASES.get(term, set()) for term in query}
    document_terms = [_terms(segment.text) for segment in bundle.segments]
    document_frequency = {
        term: sum(term in words for words in document_terms)
        for term in query | {alias for values in aliases.values() for alias in values}
    }
    ranked = []
    for index, words in enumerate(document_terms):
        score = 0.0
        for term in query:
            df = document_frequency.get(term, 0)
            idf = math.log1p((len(document_terms) - df + 0.5) / (df + 0.5))
            if term in words:
                score += idf
            elif any(alias in words for alias in aliases[term]):
                score += 0.65 * idf
            elif len(term) > 4 and any(
                term in word or word in term or (len(word) > 5 and term[:6] == word[:6])
                for word in words
            ):
                score += 0.15 * idf
        if score > 0:
            ranked.append((score, index))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    chosen: set[int] = set()
    for _, index in ranked[:limit]:
        chosen.update(range(max(0, index - context_radius), min(len(bundle.segments), index + context_radius + 1)))
    return [segment for index, segment in enumerate(bundle.segments) if index in chosen]
