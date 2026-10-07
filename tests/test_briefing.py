from video_briefing.briefing import brief_bundle, render_brief
from video_briefing.models import EvidenceBundle, TranscriptSegment


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
