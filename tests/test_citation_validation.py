import pytest

from video_briefing.citation_validation import validate_citations
from video_briefing.models import EvidenceBundle, TranscriptSegment


def source():
    return EvidenceBundle(
        'youtube', 'AbCdEf12345', 'https://www.youtube.com/watch?v=AbCdEf12345',
        'ru', 'captions_api', 'manual-captions', 'test',
        [TranscriptSegment('s1', 'Цена низкая.', 1, 2),
         TranscriptSegment('s2', 'Полного привода нет.', 4, 3)], 'a' * 64,
    )


def claim(**overrides):
    return {'claim': 'В записи сказано, что полного привода нет.',
            'segment_ids': ['s2'], 'start_seconds': 4, 'end_seconds': 7,
            'quote': 'Полного привода нет.', **overrides}


def test_valid_citation_is_not_a_semantic_entailment_guarantee():
    result = validate_citations(source(), [claim()])
    assert result['status'] == 'valid'
    assert result['semantic_support_checked'] is False
    assert result['citations'][0]['errors'] == []


@pytest.mark.parametrize('overrides,reason', [
    ({'end_seconds': 6}, 'time_bounds_mismatch'),
    ({'quote': 'Цена низкая. Полного привода нет.'}, 'quote_not_in_cited_segments'),
    ({'segment_ids': ['invented']}, 'unknown_segment_id'),
    ({'source_id': 'OtherVid123'}, 'source_identity_mismatch'),
    ({'source_sha256': 'b' * 64}, 'source_hash_mismatch'),
    ({'start_seconds': True}, 'invalid_time_bounds'),
    ({'end_seconds': float('nan')}, 'invalid_time_bounds'),
    ({'segment_ids': ['s2', 's2']}, 'duplicate_segment_id'),
])
def test_rejects_structurally_unverifiable_citations(overrides, reason):
    result = validate_citations(source(), [claim(**overrides)])
    assert result['status'] == 'invalid'
    assert reason in result['citations'][0]['errors']


def test_canonical_bounds_are_returned_without_silently_correcting_claim():
    result = validate_citations(source(), [claim(end_seconds=6)])
    assert result['citations'][0]['canonical_range_seconds'] == [4, 7]
    assert result['citations'][0]['valid'] is False


def test_validation_is_bounded():
    with pytest.raises(ValueError):
        validate_citations(source(), [claim()] * 51)
    with pytest.raises(ValueError):
        validate_citations(source(), 'not a list')
