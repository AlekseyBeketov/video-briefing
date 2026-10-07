from video_briefing.adapters import captions_api
import hashlib


class FakeTranscript:
    language = "Russian (auto-generated)"
    language_code = "ru"
    is_generated = True

    def to_raw_data(self):
        return [{"text": "Пример исходных субтитров", "start": 1.25, "duration": 2.5}]


class FakeApi:
    def __init__(self, *, http_client):
        assert http_client.trust_env is False
        assert not http_client.cookies

    def fetch(self, video_id, *, languages):
        assert video_id == "DvSwvJVens8"
        assert languages == ["ru"]
        return FakeTranscript()


def test_captions_api_preserves_language_times_and_is_anonymous(monkeypatch):
    monkeypatch.setattr(captions_api, "YouTubeTranscriptApi", FakeApi)
    monkeypatch.setattr(captions_api, "version", lambda package: "1.2.4")
    bundle = captions_api.extract("https://www.youtube.com/watch?v=DvSwvJVens8", language="ru")
    assert bundle.language == "ru"
    assert bundle.source_type == "auto-captions"
    assert bundle.segments[0].start_seconds == 1.25
    assert bundle.segments[0].duration_seconds == 2.5
    assert bundle.raw_text is not None
    assert bundle.raw_sha256 == hashlib.sha256(bundle.raw_text.encode()).hexdigest()
