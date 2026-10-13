import pytest

from video_briefing.evidence_api import read_evidence, search_evidence
from video_briefing.models import EvidenceBundle, TranscriptSegment


def source():
    segments = [
        TranscriptSegment("s1", "Производительность зависит от объёма памяти и ширины канала.", 10, 3),
        TranscriptSegment("s2", "Большая модель может поместиться в общий пул памяти.", 14, 4),
        TranscriptSegment("s3", "Этот вывод не означает универсальную скорость.", 21, 3),
    ]
    return EvidenceBundle("youtube", "AbCdEf12345", "https://www.youtube.com/watch?v=AbCdEf12345",
                          "ru", "captions_api", "auto-captions", "test", segments, "a" * 64)


def test_search_returns_bounded_source_rows_and_provenance():
    result = search_evidence(source(), "общий пул памяти", limit=2)
    assert result["status"] == "ok"
    assert result["source_sha256"] == "a" * 64
    assert result["evidence"]
    assert all(set(row) == {"segment_id", "start_seconds", "end_seconds", "text"} for row in result["evidence"])


def test_search_rejects_unbounded_or_invalid_inputs():
    with pytest.raises(ValueError):
        search_evidence(source(), "x" * 2001)
    with pytest.raises(ValueError):
        search_evidence(source(), "question", limit=0)


def test_read_rejects_bool_times_and_result_is_bounded():
    with pytest.raises(ValueError):
        read_evidence(source(), True, 20)
    with pytest.raises(ValueError):
        read_evidence(source(), 0, "20")  # type: ignore[arg-type]
    long_source = EvidenceBundle("youtube", "AbCdEf12345", "https://www.youtube.com/watch?v=AbCdEf12345",
                                 "ru", "captions_api", "auto-captions", "test",
                                 [TranscriptSegment("s1", "x" * 25_000, 0, 2)], "a" * 64)
    result = read_evidence(long_source, 0, 2, max_segments=1)
    assert result["truncated"] is True
    assert len(result["evidence"][0]["text"]) == 20_000


def test_read_is_time_bounded_and_respects_segment_cap():
    result = read_evidence(source(), 13, 22, max_segments=1)
    assert len(result["evidence"]) == 1
    assert result["evidence"][0]["segment_id"] == "s1"
    assert result["truncated"] is True
    with pytest.raises(ValueError):
        read_evidence(source(), 0, 601)
    with pytest.raises(ValueError):
        read_evidence(source(), 5, 3)


def test_complete_read_is_not_marked_truncated():
    result = read_evidence(source(), 0, 30, max_segments=3)
    assert len(result["evidence"]) == 3
    assert result["truncated"] is False
