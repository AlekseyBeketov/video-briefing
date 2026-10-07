import json

import pytest

from video_briefing.adapters.summarize import parse_summarize_output


def test_summarize_requires_actual_timed_transcript():
    payload = {"title": "T", "transcriptSegments": [{"text": "Hi", "start": 1.5, "duration": 2}]}
    assert parse_summarize_output(json.dumps(payload), "DvSwvJVens8", "en").segments[0].start_seconds == 1.5


@pytest.mark.parametrize("payload", [
    '{"title":"T","description":"only metadata"}',
    '{"transcript":"untimed prose"}',
    '{"transcriptSegments":[{"text":"no time"}]}',
])
def test_summarize_rejects_description_or_untimed_output(payload):
    with pytest.raises(ValueError):
        parse_summarize_output(payload, "DvSwvJVens8", "en")
