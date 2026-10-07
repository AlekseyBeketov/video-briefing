from video_briefing.briefing import _normalize_inline_gist_citations, brief_bundle, render_brief
from video_briefing.models import EvidenceBundle, TranscriptSegment
from video_briefing.validation import validate_citations


class FakeLLM:
    model = "fake-model"
    last_response = {"model": "fake-model", "prompt_eval_count": 7, "eval_count": 11}

    def generate_json(self, **kwargs):
        return {
            "gist": "Автор объясняет, почему важна большая общая память.",
            "gist_evidence": ["s00001"],
            "topics": [{"text": "Объём памяти важен для крупных моделей.", "evidence": ["s00001"]}],
            "useful_ideas": [{"text": "Сверяйте требования модели с доступной памятью.", "evidence": ["s00001"], "kind": "inference"}],
            "emphases": [{"text": "Говорящий подчёркивает роль памяти.", "evidence": ["s00001"]}],
            "caveats": [],
        }


def test_brief_citations_are_resolved_to_real_times():
    bundle = EvidenceBundle("youtube", "DvSwvJVens8", "https://youtube.com/watch?v=DvSwvJVens8", "ru", "fixture", "captions", "1", [TranscriptSegment("s00001", "Объём памяти важен для моделей", 12.5, 4)], "a" * 64)
    result, metadata = brief_bundle(bundle, FakeLLM())
    assert result["gist_evidence_resolved"] == [{"id": "s00001", "start_seconds": 12.5, "duration_seconds": 4}]
    assert "s00001 @12с" in render_brief(result)
    assert metadata["actual_model"] == "fake-model"


def test_brief_repairs_model_citations_using_only_retrieved_source_ids():
    class RepairingLLM(FakeLLM):
        def __init__(self):
            self.calls = 0

        def generate_json(self, **kwargs):
            self.calls += 1
            result = super().generate_json(**kwargs)
            if self.calls == 1:
                result["topics"][0]["evidence"] = ["s99999"]
            return result

    bundle = EvidenceBundle("youtube", "DvSwvJVens8", "https://youtube.com/watch?v=DvSwvJVens8", "ru", "fixture", "captions", "1", [TranscriptSegment("s00001", "Объединённая память помогает вместить крупную модель", 12.5, 4)], "a" * 64)
    llm = RepairingLLM()
    result, _ = brief_bundle(bundle, llm)
    assert llm.calls == 2
    assert result["topics"][0]["evidence"][0]["id"] == "s00001"


def test_gist_evidence_ids_are_validated():
    bundle = EvidenceBundle("youtube", "DvSwvJVens8", "https://youtube.com/watch?v=DvSwvJVens8", "ru", "fixture", "captions", "1", [TranscriptSegment("s00001", "Текст", 0, 1)], "a" * 64)
    assert validate_citations({"gist_evidence": ["s99999"]}, bundle) == ["s99999"]


def test_inline_citations_are_normalized_for_each_claim_type():
    result = {
        "gist": "Summary [s00001]", "gist_evidence": [],
        "topics": [{"text": "Topic [s00001]", "evidence": []}],
        "useful_ideas": [{"text": "Idea [s00001]", "evidence": [], "kind": "source"}],
        "emphases": [{"text": "Emphasis [s00001]", "evidence": []}],
        "caveats": [{"text": "Caveat [s00001]", "evidence": []}],
    }
    _normalize_inline_gist_citations(result)
    assert result["gist"] == "Summary"
    assert result["gist_evidence"] == ["s00001"]
    for section in ("topics", "useful_ideas", "emphases", "caveats"):
        assert "[" not in result[section][0]["text"]
        assert result[section][0]["evidence"] == ["s00001"]
