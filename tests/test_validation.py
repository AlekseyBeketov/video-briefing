import math

import pytest

from video_briefing.models import EvidenceBundle, TranscriptSegment
from video_briefing.validation import validate_bundle, validate_citations


def bundle(segments=None):
    return EvidenceBundle(
        platform="youtube",
        video_id="DvSwvJVens8",
        url="https://www.youtube.com/watch?v=DvSwvJVens8",
        language="en",
        variant="fixture",
        source_type="manual-captions",
        extractor_version="test",
        segments=segments if segments is not None else [TranscriptSegment("s00001", "Source words", 0, 2)],
        raw_sha256="a" * 64,
    )


def test_valid_timed_source_and_resolved_citation():
    source = bundle()
    validate_bundle(source)
    assert validate_citations({"claims": [{"text": "Claim", "evidence": ["s00001"]}]}, source) == []


@pytest.mark.parametrize("segments", [[], [TranscriptSegment("s1", "", 0, 1)]])
def test_rejects_empty_or_description_only_source(segments):
    with pytest.raises(ValueError):
        validate_bundle(bundle(segments))


@pytest.mark.parametrize("start,duration", [(-1, 1), (0, -1), (math.nan, 1), (0, math.inf)])
def test_rejects_invalid_times(start, duration):
    with pytest.raises(ValueError):
        validate_bundle(bundle([TranscriptSegment("s1", "text", start, duration)]))


def test_rejects_duplicate_ids_and_unknown_citations():
    with pytest.raises(ValueError):
        validate_bundle(bundle([TranscriptSegment("s1", "a", 0, 1), TranscriptSegment("s1", "b", 1, 1)]))
    assert validate_citations({"claims": [{"text": "Claim", "evidence": ["not-real"]}]}, bundle()) == ["not-real"]
