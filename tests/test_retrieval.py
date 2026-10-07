from video_briefing.models import EvidenceBundle, TranscriptSegment
from video_briefing.retrieval import retrieve


def test_retrieval_searches_beyond_first_chunk_and_includes_context():
    segments = [TranscriptSegment(f"s{i:05d}", f"unrelated filler {i}", i * 10, 2) for i in range(1, 31)]
    segments[24] = TranscriptSegment("s00025", "The author explains retrieval augmented generation and vector indexes", 240, 5)
    source = EvidenceBundle("youtube", "DvSwvJVens8", "https://youtube.com/watch?v=DvSwvJVens8", "en", "fixture", "manual-captions", "1", segments, "a" * 64)
    found = retrieve(source, "What does the author say about vector indexes?", limit=3)
    assert any(item.id == "s00025" for item in found)
