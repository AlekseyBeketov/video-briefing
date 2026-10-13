"""Small synthetic passages exercise window boundaries, not a copied target transcript."""
import pytest

from video_briefing.models import EvidenceBundle, TranscriptSegment
from video_briefing import retrieval


def bundle_for(segments):
    return EvidenceBundle("youtube", "DvSwvJVens8", "https://youtube.com/watch?v=DvSwvJVens8", "en", "fixture", "captions", "test", segments, "a" * 64)


def test_selected_passage_finishes_later_qualifying_sentence(monkeypatch):
    monkeypatch.setattr(retrieval, "PASSAGE_CHARS", 40)
    segments = [
        TranscriptSegment("a", "Service routing exposes a consistent interface", 0, 2),
        TranscriptSegment("b", "to clients even when requests traverse", 2, 2),
        TranscriptSegment("c", "multiple nodes; there are additional latency costs.", 4, 2),
        TranscriptSegment("d", "Its capacity grows when another node joins.", 6, 2),
    ]
    found = retrieval.retrieve(bundle_for(segments), "Service routing interface", limit=1, context_radius=1)
    assert {s.id for s in found} == {"a", "b", "c", "d"}


def test_source_time_gap_does_not_get_unconditionally_padded():
    segments = [
        TranscriptSegment("a", "Relevant routing interface.", 0, 2),
        TranscriptSegment("b", "This is unrelated material.", 60, 2),
    ]
    found = retrieval.retrieve(bundle_for(segments), "routing interface", context_radius=100)
    assert [s.id for s in found] == ["a"]
    assert retrieval._passage_ranges(segments, radius=2) == [(0, 1), (1, 2)]


def test_missing_punctuation_has_a_bounded_fallback(monkeypatch):
    monkeypatch.setattr(retrieval, "PASSAGE_CHARS", 40)
    monkeypatch.setattr(retrieval, "MAX_PASSAGE_SEGMENTS", 4)
    segments = [TranscriptSegment(str(i), "routing interface node", i * 2, 2) for i in range(40)]
    ranges = retrieval._passage_ranges(segments, radius=100)
    assert set(range(len(segments))) == {i for lo, hi in ranges for i in range(lo, hi)}
    assert all(0 <= lo < hi <= len(segments) and hi - lo <= 12 for lo, hi in ranges)


def test_incidental_matches_do_not_fill_passage_limit():
    segments = [TranscriptSegment(str(i), "memory", i * 60, 2) for i in range(12)]
    segments[9] = TranscriptSegment("9", "memory routing virtualization coherence bottleneck", 540, 2)
    found = retrieval.retrieve(bundle_for(segments), "memory routing virtualization coherence bottleneck")
    assert [s.id for s in found] == ["9"]


def test_context_budget_and_source_order_are_hard_bounds(monkeypatch):
    monkeypatch.setattr(retrieval, "MAX_CONTEXT_CHARS", 50)
    segments = [TranscriptSegment(str(i), "routing interface.", i * 60, 2) for i in range(20)]
    found = retrieval.retrieve(bundle_for(segments), "routing", limit=100)
    assert sum(len(s.text) + 1 for s in found) <= 50
    assert found == [s for s in segments if s.id in {s.id for s in found}]
    assert len({s.id for s in found}) == len(found)


@pytest.mark.parametrize("question,limit", [("the and what", 12), ("routing", 0), ("routing", -1), ("nonexistent", 12)])
def test_empty_irrelevant_or_disabled_retrieval_does_not_pad(question, limit):
    segments = [TranscriptSegment("a", "routing interface.", 0, 2)]
    assert retrieval.retrieve(bundle_for(segments), question, limit=limit) == []


def test_negative_radius_is_rejected():
    segments = [TranscriptSegment("a", "routing interface.", 0, 2)]
    with pytest.raises(ValueError, match="nonnegative"):
        retrieval.retrieve(bundle_for(segments), "routing", context_radius=-1)
