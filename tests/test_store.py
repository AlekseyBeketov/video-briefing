from video_briefing.models import EvidenceBundle, TranscriptSegment
from video_briefing.store import ArtifactStore


def source(title, variant="baoyu"):
    return EvidenceBundle("youtube", "DvSwvJVens8", "https://youtube.com/watch?v=DvSwvJVens8", "en", variant,
                          "manual-captions", "1", [TranscriptSegment("s00001", title, 0, 1)], "a" * 64,
                          metadata={"title": title})


def test_cache_identity_excludes_title_and_variant_isolated(tmp_path):
    store = ArtifactStore(tmp_path)
    one = store.save(source("First title"))
    assert store.load("youtube", "DvSwvJVens8", "en", "baoyu").metadata["title"] == "First title"
    assert store.save(source("Changed title")).key == one.key
    other = store.save(source("Second", "summarize"))
    assert other.key != one.key
    assert store.load("youtube", "DvSwvJVens8", "en", "baoyu").segments[0].text == "Changed title"


def test_incomplete_or_tampered_store_is_rejected(tmp_path):
    store = ArtifactStore(tmp_path)
    saved = store.save(source("immutable"))
    path = store.bundle_path(saved.key)
    data = path.read_text()
    path.write_text(data.replace('"text": "immutable"', '"text": "tampered"'))
    assert store.load("youtube", "DvSwvJVens8", "en", "baoyu") is None


def test_find_can_select_the_requested_source_language(tmp_path):
    store = ArtifactStore(tmp_path)
    store.save(source("English", "captions_api"))
    russian = source("Русский", "captions_api")
    russian.language = "ru"
    store.save(russian)

    assert store.find("DvSwvJVens8", "captions_api", language="ru").segments[0].text == "Русский"
