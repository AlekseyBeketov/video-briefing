from video_briefing import cli
from video_briefing.models import EvidenceBundle, TranscriptSegment
from video_briefing.store import ArtifactStore


def test_cached_question_lookup_never_invokes_extractor(tmp_path, monkeypatch):
    store = ArtifactStore(tmp_path)
    bundle = EvidenceBundle("youtube", "DvSwvJVens8", "https://youtube.com/watch?v=DvSwvJVens8", "ru", "baoyu", "auto-captions", "1", [TranscriptSegment("s00001", "Текст сохранённого источника", 0, 2)], "a" * 64)
    store.save(bundle)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("cached Q&A must not re-fetch or invoke an extractor")

    monkeypatch.setattr(cli, "_run_extractor", fail_if_called)
    loaded = cli._get_bundle("https://www.youtube.com/watch?v=DvSwvJVens8", "baoyu", "ru", store, extract_if_missing=False)
    assert loaded.raw_sha256 == bundle.raw_sha256
