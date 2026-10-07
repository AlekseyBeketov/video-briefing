import hashlib

from video_briefing import cli
from video_briefing.models import EvidenceBundle, TranscriptSegment
from video_briefing.store import ArtifactStore


def test_cached_question_lookup_never_invokes_extractor(tmp_path, monkeypatch):
    store = ArtifactStore(tmp_path)
    raw = "Текст сохранённого источника"
    bundle = EvidenceBundle("youtube", "DvSwvJVens8", "https://www.youtube.com/watch?v=DvSwvJVens8", "ru", "baoyu", "auto-captions", "1", [TranscriptSegment("s00001", raw, 0, 2)], hashlib.sha256(raw.encode()).hexdigest(), raw_text=raw)
    store.save(bundle)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("cached Q&A must not re-fetch or invoke an extractor")

    monkeypatch.setattr(cli, "_run_extractor", fail_if_called)
    loaded = cli._get_bundle("https://www.youtube.com/watch?v=DvSwvJVens8", "baoyu", "ru", store, extract_if_missing=False)
    assert loaded.raw_sha256 == bundle.raw_sha256
