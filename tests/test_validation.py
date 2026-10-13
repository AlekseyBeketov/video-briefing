import hashlib
import math

import pytest

from video_briefing.models import EvidenceBundle, TranscriptSegment
from video_briefing.validation import parse_video_url, validate_bundle, validate_citations


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


@pytest.mark.parametrize("url", [
    "http://youtube.com/watch?v=DvSwvJVens8",
    "https://youtube.com.evil.example/watch?v=DvSwvJVens8",
    "https://user:pass@youtube.com/watch?v=DvSwvJVens8",
    "https://youtube.com:443/watch?v=DvSwvJVens8",
    "https://127.0.0.1/watch?v=DvSwvJVens8",
    "file:///etc/passwd",
])
def test_rejects_noncanonical_urls_and_ssrf_inputs(url):
    with pytest.raises(ValueError):
        parse_video_url(url)


def test_keeps_literal_youtube_url_identity_and_allows_local_sha_identity():
    assert parse_video_url("https://www.youtube.com/watch?v=DvSwvJVens8&list=WL&index=27")[1] == "DvSwvJVens8"
    local_hash = "b" * 64
    local = EvidenceBundle("local-file", local_hash, f"local-file://sha256/{local_hash}", "ru", "local_asr",
                           "local-asr-chunk-transcript", "external", [TranscriptSegment("a1", "text", 0, 24)],
                           "a" * 64, raw_text="text")
    local.raw_sha256 = hashlib.sha256(b"text").hexdigest()
    validate_bundle(local)
