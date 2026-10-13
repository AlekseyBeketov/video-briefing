import json
from copy import deepcopy

import pytest

from video_briefing.briefing import COVERAGE_SECTIONS, _normalize_inline_gist_citations, _repair_citations, brief_bundle, render_brief
from video_briefing.models import EvidenceBundle, TranscriptSegment
from video_briefing.validation import validate_citations


class FakeLLM:
    model = "fake-model"
    last_response = {"model": "fake-model", "prompt_eval_count": 7, "eval_count": 11}

    def generate_json(self, **kwargs):
        if "checks" in kwargs["schema"]["properties"]:
            rows = json.loads(kwargs["prompt"].split("\n", 1)[1])
            return {"checks": [{"index": row["index"], "support": "explicit"} for row in rows]}
        return {
            "gist": "Автор объясняет, почему важна большая общая память.",
            "gist_evidence": ["s00001"],
            "topics": [{"text": "Объём памяти важен для крупных моделей.", "evidence": ["s00001"]}],
            "useful_ideas": [{"text": "Сверяйте требования модели с доступной памятью.", "evidence": ["s00001"], "kind": "inference"}],
            "emphases": [{"text": "Говорящий подчёркивает роль памяти.", "evidence": ["s00001"]}],
            "caveats": [],
            "coverage": {facet: [] for facet in COVERAGE_SECTIONS},
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
            if self.calls == 2:
                return {"citation_repairs": [{"claim_index": 1, "evidence": ["s00001"]}]}
            result = super().generate_json(**kwargs)
            if self.calls == 1:
                result["topics"][0]["evidence"] = ["s99999"]
            return result

    bundle = EvidenceBundle("youtube", "DvSwvJVens8", "https://youtube.com/watch?v=DvSwvJVens8", "ru", "fixture", "captions", "1", [TranscriptSegment("s00001", "Объединённая память помогает вместить крупную модель", 12.5, 4)], "a" * 64)
    llm = RepairingLLM()
    result, _ = brief_bundle(bundle, llm)
    assert llm.calls == 3
    assert result["topics"][0]["evidence"][0]["id"] == "s00001"


def test_gist_evidence_ids_are_validated():
    bundle = EvidenceBundle("youtube", "DvSwvJVens8", "https://youtube.com/watch?v=DvSwvJVens8", "ru", "fixture", "captions", "1", [TranscriptSegment("s00001", "Текст", 0, 1)], "a" * 64)
    assert validate_citations({"gist_evidence": ["s99999"]}, bundle) == ["s99999"]


def citation_repair_fixture(monkeypatch):
    bundle = EvidenceBundle("youtube", "DvSwvJVens8", "https://youtube.com/watch?v=DvSwvJVens8", "ru", "fixture", "captions", "1", [
        TranscriptSegment("s00001", "Alpha source.", 0, 1),
        TranscriptSegment("s00002", "Beta source.", 5, 1),
    ], "a" * 64)
    monkeypatch.setattr("video_briefing.briefing.retrieve", lambda bundle, text, limit: [
        bundle.segments[0 if text == "Alpha" else 1]
    ])
    result = {"gist": "Summary", "gist_evidence": ["s00001"], "topics": [
        {"text": "Alpha", "evidence": ["s99998"]},
        {"text": "Beta", "evidence": ["s99999"]},
    ]}
    return bundle, result


def test_citation_repair_retries_cross_claim_ids_with_original_source(monkeypatch):
    bundle, result = citation_repair_fixture(monkeypatch)

    class RepairLLM(FakeLLM):
        def __init__(self):
            self.requests = []

        def generate_json(self, **kwargs):
            self.requests.append(kwargs)
            # The first response borrows a known ID from another claim's context.
            return {"citation_repairs": [
                {"claim_index": 1, "evidence": ["s00002" if len(self.requests) == 1 else "s00001"]},
                {"claim_index": 2, "evidence": ["s00002"]},
            ]}

    llm = RepairLLM()
    _repair_citations(result, bundle, llm)
    assert len(llm.requests) == 2
    assert result["topics"][0] == {"text": "Alpha", "evidence": ["s00001"]}
    assert result["topics"][1] == {"text": "Beta", "evidence": ["s00002"]}
    assert llm.requests[1]["prompt"].endswith(llm.requests[0]["prompt"])
    alternatives = llm.requests[0]["schema"]["properties"]["citation_repairs"]["items"]["anyOf"]
    assert {row["properties"]["claim_index"]["enum"][0]: row["properties"]["evidence"]["items"]["enum"] for row in alternatives} == {
        1: ["s00001"], 2: ["s00002"],
    }


@pytest.mark.parametrize("invalid_row", [
    {"claim_index": 2, "evidence": ["s00001"]},
    {"claim_index": 2, "evidence": [{"id": "s00002"}]},
    {"claim_index": True, "evidence": ["s00002"]},
    {"claim_index": [2], "evidence": ["s00002"]},
    {"claim_index": 1, "evidence": ["s00001"]},
])
def test_citation_repair_fails_closed_atomically_after_two_attempts(monkeypatch, invalid_row):
    bundle, result = citation_repair_fixture(monkeypatch)
    before = deepcopy(result)

    class RepairLLM(FakeLLM):
        calls = 0

        def generate_json(self, **kwargs):
            self.calls += 1
            return {"citation_repairs": [{"claim_index": 1, "evidence": ["s00001"]}, invalid_row]}

    llm = RepairLLM()
    with pytest.raises(ValueError):
        _repair_citations(result, bundle, llm)
    assert llm.calls == 2
    assert result == before


def test_citation_repair_does_not_retry_provider_failure(monkeypatch):
    bundle, result = citation_repair_fixture(monkeypatch)
    before = deepcopy(result)

    class RepairLLM(FakeLLM):
        calls = 0

        def generate_json(self, **kwargs):
            self.calls += 1
            raise RuntimeError("Provider unavailable")

    llm = RepairLLM()
    with pytest.raises(RuntimeError, match="Provider unavailable"):
        _repair_citations(result, bundle, llm)
    assert llm.calls == 1
    assert result == before


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
