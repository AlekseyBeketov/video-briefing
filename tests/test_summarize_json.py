import json

from video_briefing.adapters.summarize import parse_summarize_output


def test_summarize_extract_json_nested_segments_preserves_ms_and_unknown_source_language():
    payload = {
        "input": {"language": {"tag": "ru"}},
        "extracted": {
            "title": "Fixture title",
            "transcriptSource": "captionTracks",
            "transcriptSegments": [{"startMs": 1500, "endMs": 2750, "text": "Actual timed caption"}],
        },
    }
    bundle = parse_summarize_output(json.dumps(payload), "DvSwvJVens8", "ru")
    assert bundle.language == "und"
    assert bundle.segments[0].start_seconds == 1.5
    assert bundle.segments[0].duration_seconds == 1.25
    assert bundle.metadata["transcript_source"] == "captionTracks"
    assert bundle.warnings
