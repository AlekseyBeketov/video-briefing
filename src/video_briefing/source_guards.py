"""Conservative lexical guards derived from supplied captions, never evaluator answers.

These are preservation/relationship checks, not general semantic entailment. Extractive
repairs are explicitly quoted; they do not correct ASR spellings or infer hardware facts.
"""
from __future__ import annotations

import re
import math
from collections import Counter
from dataclasses import dataclass

from .models import EvidenceBundle, TranscriptSegment
from .retrieval import _match_strength, _terms

# Match quantities, not model numbers (120B, MXFP4, RTX 5090). Keep roles in the
# original quoted sentence; equal magnitudes alone do not establish an entity relation.
_QUANTITY = re.compile(
    r"(?<![\w.,])(?P<value>\d+(?:[.,]\d+)?(?:\s*[-–]\s*\d+(?:[.,]\d+)?)?)\s*"
    r"(?P<unit>млрд\b|миллиард\w*|billion\b|ГБ\b|Гб\b|GB\b|гигабайт\w*|"
    r"Гбит/с|Gbit/s|токен\w*\s+(?:в\s+секунду|/\s*с)|tokens?/s)", re.I,
)
_ENTITY = re.compile(r"\b([A-Z][A-Z0-9]{1,})\s+[A-Z][a-z]+\b")
_SOFTWARE = re.compile(r"софт|программ|экосистем|\bстек|software|ecosystem", re.I)
_UNCERTAINTY = re.compile(
    r"\bне\s+(?:\w+\s+){0,2}протест\w*|\bнет\s+(?:\w+\s+){0,2}(?:картин\w*|тест\w*)|"
    r"\b(?:not|never)\s+(?:\w+\s+){0,2}tested\b|\bno\s+(?:\w+\s+){0,2}(?:tests?|measurements?)\b", re.I,
)


@dataclass(frozen=True)
class SourceSentence:
    text: str
    ids: tuple[str, ...]
    run: int


def quantities(text: str) -> set[tuple[str, str]]:
    result = set()
    for match in _QUANTITY.finditer(text):
        value = re.sub(r"\s+", "", match['value']).replace(',', '.').replace('–', '-')
        unit = match['unit'].casefold()
        if unit == 'млрд' or unit.startswith(('миллиард', 'billion')):
            unit = 'billion'
        elif unit in {'гб', 'gb'} or unit.startswith('гигабайт'):
            unit = 'gb'
        result.add((value, unit))
    return result


def source_sentences(bundle: EvidenceBundle, context: list[TranscriptSegment]) -> list[SourceSentence]:
    """Exact caption sentences; never join absent rows or source-time gaps.

    Decimal punctuation and event markers are not sentence boundaries. IDs refer to
    every original row touched by the sentence, even if a row contains two sentences.
    """
    available = {segment.id for segment in context}
    sentences = []
    text, ids, run = '', [], 0
    previous = None

    def flush():
        nonlocal text, ids
        if text.strip():
            sentences.append(SourceSentence(text.strip(), tuple(dict.fromkeys(ids)), run))
        text, ids = '', []

    for segment in bundle.segments:
        gap = previous is not None and segment.start_seconds - previous.start_seconds - previous.duration_seconds > 8
        previous = segment
        if segment.id not in available or gap:
            flush()
            run += 1
        if segment.id not in available:
            continue
        clean = re.sub(r"\[(?:музыка|music|аплодисменты|applause)\]", '', segment.text, flags=re.I)
        # Retain the source punctuation in the quote, without splitting a decimal.
        for part in re.split(r"(?<=[.!?])(?:\s+|$)", clean):
            if not part.strip():
                continue
            text += (' ' if text else '') + part.strip()
            ids.append(segment.id)
            if re.search(r"[.!?]$", part.strip()):
                flush()
    flush()
    return sentences


def preserve_example_quantities(result: dict, bundle: EvidenceBundle, context: list[TranscriptSegment]) -> list[dict]:
    """Carry missing numeric clauses forward as source quotes, not generated facts.

    Only completed sentences inside each worked example's own evidence span compete.
    Do not scan unrelated source for additional numbers or use frozen anchor offsets.
    """
    sentences = source_sentences(bundle, context)
    positions = {segment.id: index for index, segment in enumerate(bundle.segments)}
    available = {segment.id for segment in context}
    repairs = []
    for detail in result.get('coverage', {}).get('worked_examples', []):
        evidence = detail['evidence'] + [identifier for item in detail.get('quantities', []) for identifier in item['evidence']]
        if not evidence or not set(evidence) <= positions.keys():
            continue  # The ordinary citation validator handles unknown IDs.
        low, high = min(positions[i] for i in evidence), max(positions[i] for i in evidence)
        span = bundle.segments[low:high + 1]
        if any(segment.id not in available for segment in span) or any(
            right.start_seconds - left.start_seconds - left.duration_seconds > 8
            for left, right in zip(span, span[1:])
        ):
            continue  # A sparse cross-topic ledger is not a coherent worked example.
        spans = [(low, high)]
        if high - low >= 64:
            # A folded example may compare several systems in distant passages.
            # Preserve within each bounded cited cluster, never through the large
            # intervening gap. Isolated remote IDs cannot introduce new numbers.
            clusters = []
            for position in sorted({positions[i] for i in evidence}):
                if not clusters or position - clusters[-1][0] >= 64:
                    clusters.append([position])
                else:
                    clusters[-1].append(position)
            spans = [(cluster[0], cluster[-1]) for cluster in clusters if len(cluster) >= 2]
        present = quantities(' '.join([detail['text'], *[item['text'] for item in detail.get('quantities', [])]]))
        for sentence in sentences:
            # Complete sentences intersecting an example's span, not neighbouring padding.
            if not any(left <= positions[i] <= right for left, right in spans for i in sentence.ids):
                continue
            missing = quantities(sentence.text) - present
            if not missing:
                continue
            quote = 'Деталь исходного примера (по captions): «' + sentence.text + '»'
            detail['quantities'].append({'text': quote, 'evidence': list(sentence.ids)})
            repairs.append({'kind': 'extractive_quantity_preservation', 'quantities': sorted(missing),
                            'evidence': list(sentence.ids), 'source_text': sentence.text})
            present.update(missing)
    return repairs


def validate_preserved_quantities(claims: list[dict], repairs: list[dict]) -> None:
    """Fail closed if later stochastic filtering discarded an extractive repair.

    A matching magnitude elsewhere in the brief cannot satisfy the obligation: it
    must retain the original repaired sentence and its complete source citations.
    """
    for repair in repairs:
        if repair['kind'] != 'extractive_quantity_preservation':
            continue
        required = {tuple(amount) for amount in repair['quantities']}
        if not any(required <= quantities(claim['text'])
                   and set(repair['evidence']) <= set(claim['evidence'])
                   and repair.get('source_text', '') in claim['text'] for claim in claims):
            raise ValueError('Brief dropped a preserved original example quantity')


def coordinated_quantity_conflicts(claim: dict, bundle: EvidenceBundle, context: list[TranscriptSegment]) -> list[SourceSentence]:
    """Reject shared or transferred quantities for source-named acronym subjects.

    An exact quantity and all known acronym subjects must occur in the same source
    sentence (or its preceding subject sentence), anchored to the claim's citations.
    A single claimed subject also fails when its cited quantity explicitly belongs
    to a different source-named subject. This narrow guard does not certify ASR
    name equivalence, arbitrary numbers, or general semantic entailment.
    """
    known_words = set(re.findall(r"\w+", ' '.join(segment.text for segment in context).casefold()))
    # A preservation ledger contains multiple semicolon-separated clauses. A
    # subject in its heading must not inherit every later quantity, and repairing
    # one relation must not silently erase another example's preserved numbers.
    scopes = []
    for clause in re.split(r";|(?<=[.!?])\s+", claim['text']):
        subjects = {match.casefold() for match in _ENTITY.findall(clause)} & known_words
        if subjects:
            scopes.extend((amount, subjects) for amount in sorted(quantities(clause)))
    cited = set(claim['evidence'])
    sentences = source_sentences(bundle, context)
    conflicts = []
    for amount, subjects in scopes:
        anchors = []
        for index, sentence in enumerate(sentences):
            if amount not in quantities(sentence.text) or not cited.intersection(sentence.ids):
                continue
            # Use a preceding subject only for an anaphoric quantity sentence with
            # no named subject of its own. A nearby catalogue cannot transfer a limit.
            anaphoric = re.search(r"\b(?:он|его|она|её|ее|это|it|its|they|their)\b", sentence.text, re.I)
            preceding = sentences[index - 1] if (index and anaphoric
                and not _ENTITY.search(sentence.text) and sentences[index - 1].run == sentence.run) else None
            related = ((preceding.text + ' ') if preceding else '') + sentence.text
            supported = subjects & set(re.findall(r"\w+", related.casefold()))
            source_subjects = {match.casefold() for match in _ENTITY.findall(related)} & known_words
            anchors.append((sentence, preceding, supported, source_subjects))
        if not anchors or any(subjects <= supported for _, _, supported, _ in anchors):
            continue
        # Fail only when an anchored source establishes some subjects but not the
        # shared relation. Different separately supported subjects are valid.
        union = set().union(*(supported for _, _, supported, _ in anchors))
        anchored_subjects = set().union(*(named for _, _, _, named in anchors))
        if anchored_subjects and not subjects <= union:
            for sentence, preceding, supported, named in anchors:
                if supported or named:
                    conflicts.append(SourceSentence(
                        ((preceding.text + ' ') if preceding else '') + sentence.text,
                        tuple(dict.fromkeys([*(preceding.ids if preceding else ()), *sentence.ids])), sentence.run,
                    ))
    return list(dict.fromkeys(conflicts))


def repair_coordinated_quantities(claims: list[dict], bundle: EvidenceBundle, context: list[TranscriptSegment]) -> list[dict]:
    """Replace a rejected shared relation with its exact, narrower source assertion."""
    repairs = []
    for claim in claims:
        conflicts = coordinated_quantity_conflicts(claim, bundle, context)
        if not conflicts:
            continue
        original = claim['text']
        claim['text'] = 'Утверждение источника (по captions): ' + ' '.join('«' + sentence.text + '»' for sentence in conflicts)
        claim['evidence'] = list(dict.fromkeys(identifier for sentence in conflicts for identifier in sentence.ids))
        # This is an exact extract, not a claim that the hardware was independently tested.
        if 'kind' in claim:
            claim['kind'] = 'source' if claim['kind'] in {'source', 'inference'} else 'author_statement'
        repairs.append({'kind': 'extractive_relationship_repair', 'rejected_text': original, 'evidence': claim['evidence']})
    return repairs


def software_interpretation_context(claim: dict, bundle: EvidenceBundle, context: list[TranscriptSegment]) -> list[str]:
    """Minimal earlier software/ecosystem sentence for a missing conditional acronym.

    Lexical vendor overlap must be present in the original cited rows or claim; an
    arbitrary software passage cannot establish an invented prerequisite. The result
    is context for a labelled inference only, never proof of the missing acronym.
    """
    segments = {segment.id: segment for segment in bundle.segments}
    cited = set(claim['evidence'])
    sentences = source_sentences(bundle, context)
    # A vendor's name may finish the actual cited sentence in the next caption.
    # Use that bounded source phrase, not an unrelated adjacent product catalogue.
    cited_phrases = [sentence.text for sentence in sentences if cited.intersection(sentence.ids)
                     and len(sentence.text) <= 1600 and len(sentence.ids) <= 32
                     and re.search(r"[.!?]$", sentence.text)]
    names = set(re.findall(r"\b[A-Z][A-Za-z0-9]{2,}\b", claim['text'] + ' ' + ' '.join(
        [*[segments[i].text for i in claim['evidence']], *cited_phrases])))
    names = {name.casefold() for name in names}
    positions = {segment.id: index for index, segment in enumerate(bundle.segments)}
    first = min(positions[i] for i in cited)
    # A final option may omit its vendor. Resolve only an exact source-named
    # product phrase through an earlier bounded sentence naming that vendor;
    # no external vendor table or ASR name equivalence is allowed. Retain this
    # bridge as provenance if it is needed to select the software passage.
    products = {match.group().casefold() for match in _ENTITY.finditer(claim['text'])}
    bridges = {}
    for sentence in sentences:
        if (max(positions[i] for i in sentence.ids) >= first or len(sentence.text) > 1600
                or len(sentence.ids) > 32 or not re.search(r"[.!?]$", sentence.text)):
            continue
        if not products.intersection(match.group().casefold() for match in _ENTITY.finditer(sentence.text)):
            continue
        for name in re.findall(r"\b[A-Z][a-z][A-Za-z0-9]{1,}\b", sentence.text):
            key = name.casefold()
            if key not in names:
                bridges[key] = sentence.ids
    direct_names = set(names)
    names.update(bridges)
    candidates = []
    for sentence in sentences:
        if cited.intersection(sentence.ids) or max(positions[i] for i in sentence.ids) >= first or not _SOFTWARE.search(sentence.text):
            continue
        words = set(re.findall(r"\w+", sentence.text.casefold()))
        overlap = {name for name in names if name in words or (len(name) >= 4 and any(word.startswith(name) for word in words))}
        if overlap:
            bridge_ids = [identifier for name in sorted(overlap - direct_names) for identifier in bridges[name]]
            candidates.append((len(overlap), max(positions[i] for i in sentence.ids),
                               tuple(dict.fromkeys([*sentence.ids, *bridge_ids]))))
    return list(max(candidates)[2]) if candidates else []


def preserve_source_uncertainty(result: dict, bundle: EvidenceBundle, context: list[TranscriptSegment]) -> list[dict]:
    """Carry explicit untested/unknown-measurement qualifications for named products.

    The quoted qualification must name a draft product exactly or immediately follow
    a source sentence naming it in the same continuous run. Never infer a test result
    or bind an ASR variant to a product from memory. This is source preservation,
    not an evaluation-topic table or unconditional neighbouring caption padding.
    """
    claims = [claim for section in ('topics', 'useful_ideas', 'emphases', 'caveats')
              for claim in result.get(section, [])]
    products = {match.group().casefold() for claim in claims for match in _ENTITY.finditer(claim['text'])}
    sentences = source_sentences(bundle, context)
    repairs = []
    for index, sentence in enumerate(sentences):
        if (not _UNCERTAINTY.search(sentence.text) or len(sentence.text) > 1600
                or len(sentence.ids) > 32 or not re.search(r'[.!?]$', sentence.text)):
            continue
        related = [sentence]
        if not _ENTITY.search(sentence.text) and index and sentences[index - 1].run == sentence.run:
            related.insert(0, sentences[index - 1])
        if (sum(len(item.text) for item in related) > 1600
                or not products.intersection(match.group().casefold() for item in related
                                             for match in _ENTITY.finditer(item.text))):
            continue
        source_text = ' '.join(item.text for item in related)
        ids = list(dict.fromkeys(identifier for item in related for identifier in item.ids))
        if len(ids) > 32:
            continue
        if not any(source_text in claim['text'] and set(ids) <= set(claim['evidence']) for claim in claims):
            result.setdefault('caveats', []).append({
                'text': 'Оговорка источника (по captions): «' + source_text + '»', 'evidence': ids,
            })
        repairs.append({'kind': 'extractive_uncertainty_preservation', 'evidence': ids, 'source_text': source_text})
    return repairs


def validate_preserved_uncertainty(claims: list[dict], repairs: list[dict]) -> None:
    for repair in repairs:
        if repair['kind'] != 'extractive_uncertainty_preservation':
            continue
        if not any(repair['source_text'] in claim['text'] and set(repair['evidence']) <= set(claim['evidence'])
                   for claim in claims):
            raise ValueError('Brief dropped a preserved original source qualification')


def claim_source_context(claim: dict, bundle: EvidenceBundle, context: list[TranscriptSegment]) -> list[str]:
    """Bounded lexical support sentences per clause, from supplied source only.

    Audit snippets must include later clauses, not just rows containing a proper
    name. IDF downweights generic 'model/memory' matches. No evaluator/topic lookup,
    adjacent padding, gap joining, or external name correction is performed.
    """
    sentences = source_sentences(bundle, context)
    words = [_terms(sentence.text) for sentence in sentences]
    frequency = Counter(word for terms in words for word in terms)
    chosen = []
    # A folded numeric inventory has independent semicolon-separated details.
    # Ranking only its whole text can erase later quantities and client clauses.
    for clause in re.split(r";|(?<=[.!?])\s+", claim['text']):
        query = _terms(clause)
        scored = []
        for sentence, terms in zip(sentences, words):
            if (len(sentence.text) > 1600 or len(sentence.ids) > 32
                    or not re.search(r"[.!?]$", sentence.text)):
                continue
            matches = {term: _match_strength(term, terms) for term in query}
            if sum(bool(strength) for strength in matches.values()) < 2:
                continue
            score = sum(strength * math.log1p(len(sentences) / (1 + frequency[term])) for term, strength in matches.items())
            scored.append((score, sentence))
        scored.sort(key=lambda item: item[0], reverse=True)
        for score, sentence in scored[:2]:
            if score >= scored[0][0] * 0.65 and sentence not in chosen:
                chosen.append(sentence)
        if len(chosen) >= 8:
            break
    chosen = chosen[:8]
    return list(dict.fromkeys(identifier for sentence in chosen for identifier in sentence.ids))


def complete_support_sentences(text: str, evidence: list[str], bundle: EvidenceBundle, context: list[TranscriptSegment]) -> list[str]:
    """Complete only a cited, lexically anchored supporting source sentence."""
    resolved = set(evidence)
    anchored = set(evidence)
    query = _terms(text)
    for sentence in source_sentences(bundle, context):
        if (not anchored.intersection(sentence.ids) or len(sentence.text) > 1600
                or len(sentence.ids) > 32 or not re.search(r"[.!?]$", sentence.text)):
            continue
        if any(_match_strength(term, _terms(sentence.text)) for term in query):
            resolved.update(sentence.ids)
    # Preserve the auditor's explicit selections; only completed supporting phrases
    # may add rows. An unpunctuated run is not permission to join unrelated captions.
    return list(dict.fromkeys([*evidence, *[segment.id for segment in context if segment.id in resolved]]))
