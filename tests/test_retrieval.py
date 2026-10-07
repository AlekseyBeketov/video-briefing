from video_briefing.models import EvidenceBundle, TranscriptSegment
from video_briefing.retrieval import retrieve


def test_retrieval_searches_beyond_first_chunk_and_includes_context():
    segments = [TranscriptSegment(f"s{i:05d}", f"unrelated filler {i}", i * 10, 2) for i in range(1, 31)]
    segments[24] = TranscriptSegment("s00025", "The author explains retrieval augmented generation and vector indexes", 240, 5)
    source = EvidenceBundle("youtube", "DvSwvJVens8", "https://youtube.com/watch?v=DvSwvJVens8", "en", "fixture", "manual-captions", "1", segments, "a" * 64)
    found = retrieve(source, "What does the author say about vector indexes?", limit=3)
    assert any(item.id == "s00025" for item in found)


def test_russian_query_retrieves_explanation_not_generic_memory_mentions():
    segments = [
        TranscriptSegment(f"s{index:05d}", "Устройство имеет объём объединённой памяти", index * 5, 3)
        for index in range(1, 20)
    ]
    segments[9] = TranscriptSegment(
        "s00010", "Объединённая память уступает GDDR7 по скорости, зато модель помещается целиком", 45, 5
    )
    source = EvidenceBundle("youtube", "DvSwvJVens8", "https://youtube.com/watch?v=DvSwvJVens8", "ru", "fixture", "auto-captions", "1", segments, "a" * 64)
    found = retrieve(source, "Какой компромисс у объединённой памяти?", limit=1, context_radius=0)
    assert found[0].id == "s00010"


def test_fixed_question_synonyms_retrieve_late_recommendation_and_nas_passages():
    segments = [
        TranscriptSegment(f"s{index:05d}", f"Устройство имеет большой объём памяти {index}", index * 5, 3)
        for index in range(1, 50)
    ]
    segments[44] = TranscriptSegment("s00045", "Если модель помещается в 32 ГБ VRAM, достаточно классического ПК с RTX 5090", 220, 5)
    segments[45] = TranscriptSegment("s00046", "На Mac имеет смысл смотреть, если устраивает macOS и нужный софт работает через MLX", 225, 5)
    segments[46] = TranscriptSegment("s00047", "Если нужна Windows или Linux, интересный вариант у AMD", 230, 5)
    segments[47] = TranscriptSegment("s00048", "NAS хранит данные, работает дома 24x7 и подключён к сети", 235, 5)
    segments[48] = TranscriptSegment("s00049", "Ноутбук закрыли и ушли; локальный ассистент принимает запросы с телефона", 240, 5)
    source = EvidenceBundle("youtube", "DvSwvJVens8", "https://youtube.com/watch?v=DvSwvJVens8", "ru", "fixture", "auto-captions", "1", segments, "a" * 64)

    recommendation = retrieve(source, "Как меняется финальная рекомендация ведущего в зависимости от размера модели, операционной системы и нужного программного стека?")
    nas = retrieve(source, "Почему ролик предлагает держать локального AI-ассистента на NAS, а не обязательно в ноутбуке?")

    recommendation_ids = {item.id for item in recommendation}
    nas_ids = {item.id for item in nas}
    assert {"s00045", "s00046", "s00047"} <= recommendation_ids
    assert {"s00048", "s00049"} <= nas_ids
