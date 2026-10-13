"""Deterministic structured generation tests; tiny synthetic source, no target answer fixtures."""
from copy import deepcopy
import json

import pytest

from video_briefing import briefing, qa
from video_briefing.grounding import audit_claims
from video_briefing.models import EvidenceBundle, TranscriptSegment


def source():
    return EvidenceBundle("youtube", "DvSwvJVens8", "https://youtube.com/watch?v=DvSwvJVens8", "en", "fixture", "captions", "test", [
        TranscriptSegment("a", "Protocol ABC supports routing. Capacity is 9 units.", 0, 2),
        TranscriptSegment("b", "If your requirement is, choose this service.", 2, 2),
        TranscriptSegment("c", "The planned release is next quarter.", 4, 2),
        TranscriptSegment("d", "Unrelated material.", 60, 2),
    ], "a" * 64)


def draft():
    return {"gist": "A service exposes routing.", "gist_evidence": ["a"], "topics": [], "useful_ideas": [], "emphases": [], "caveats": [], "coverage": {facet: [] for facet in briefing.COVERAGE_SECTIONS}}


class SequenceLLM:
    model = "synthetic-model"

    def __init__(self, responses):
        self.responses_to_return = list(responses)
        self.requests = []

    def generate_json(self, **kwargs):
        self.requests.append(kwargs)
        response = self.responses_to_return.pop(0)
        if isinstance(response, Exception):
            raise response
        return deepcopy(response)


def explicit_checks(count):
    return {"checks": [{"index": index, "support": "explicit"} for index in range(count)]}


def test_coverage_inventory_preserves_quantities_kind_and_promised_status():
    value = draft()
    value["coverage"]["worked_examples"] = [{"text": "Capacity example", "evidence": ["a"], "kind": "source", "quantities": [{"text": "9 units of capacity", "evidence": ["a"]}, {"text": "3 active units per request", "evidence": ["b"]}]}]
    value["coverage"]["conditional_recommendations"] = [{"text": "Interpretation of the incomplete condition", "evidence": ["a", "b"], "kind": "inference"}]
    value["coverage"]["available_vs_promised"] = [{"text": "A planned release", "evidence": ["c"], "kind": "source", "status": "promised_in_source"}]
    briefing._validate_generation_shape(value)
    briefing._fold_coverage(value)
    assert len(value["useful_ideas"]) == 2
    example = value["useful_ideas"][0]
    assert "9 units" in example["text"] and "3 active units" in example["text"]
    assert example["evidence"] == ["a", "b"]
    assert value["useful_ideas"][1]["kind"] == "inference"
    assert value["caveats"][0]["text"].startswith("Обещание в источнике:")
    assert "coverage" not in value


@pytest.mark.parametrize("field,bad", [("topics", ["heading only"]), ("coverage", {}), ("gist_evidence", []), ("gist", "")])
def test_malformed_generated_shape_is_rejected(field, bad):
    value = draft()
    value[field] = bad
    with pytest.raises(ValueError):
        briefing._validate_generation_shape(value)


def test_structural_retry_keeps_original_source_and_is_bounded():
    broken = draft()
    broken["topics"] = ["heading only"]
    model = SequenceLLM([broken, draft(), explicit_checks(1)])
    result, _ = briefing.brief_bundle(source(), model)
    assert result["gist_evidence_resolved"][0]["id"] == "a"
    assert len(model.requests) == 3
    for request in model.requests[:2]:
        assert "[a]" in request["prompt"] and "[d]" in request["prompt"]
        assert source().segments[0].text in request["prompt"]
    always_broken = SequenceLLM([broken, broken])
    with pytest.raises(ValueError, match="structured"):
        briefing.brief_bundle(source(), always_broken)
    assert len(always_broken.requests) == 2


def test_network_failure_is_not_retried_as_a_shape_failure():
    model = SequenceLLM([RuntimeError("Ollama request failed: timeout")])
    with pytest.raises(RuntimeError, match="request failed"):
        briefing.brief_bundle(source(), model)
    assert len(model.requests) == 1


def test_map_inventory_cannot_launder_another_parts_ids():
    with pytest.raises(ValueError, match="supplied part IDs"):
        briefing._validate_inventory({"carry_forward": [{"text": "Wrong part", "evidence": ["b"], "kind": "source"}]}, source().segments[:1])
    with pytest.raises(ValueError, match="source/inference"):
        briefing._validate_inventory({"carry_forward": [{"text": "Claim", "evidence": ["a"]}]}, source().segments[:1])


def test_synthesis_uses_only_inventory_ids_and_repairs_against_actual_source(monkeypatch):
    bundle = source()
    monkeypatch.setattr(briefing, "chunk_segments", lambda bundle: [bundle.segments[:2], bundle.segments[2:]])
    inventories = [{"carry_forward": [{"text": "Routing", "evidence": ["a"], "kind": "source"}]}, {"carry_forward": [{"text": "Planned release", "evidence": ["c"], "kind": "source"}]}]
    value = draft()
    value["topics"] = [{"text": "Capacity is 9 units.", "evidence": ["b"]}]
    model = SequenceLLM([*inventories, value, {"citation_repairs": [{"claim_index": 1, "evidence": ["a"]}]}, explicit_checks(2)])
    result, metadata = briefing.brief_bundle(bundle, model)
    assert metadata["source_parts"] == 2 and metadata["carry_forward_details"] == 2
    assert model.requests[2]["schema"]["properties"]["gist_evidence"]["items"]["enum"] == ["a", "c"]
    assert result["topics"][0]["text"] == "Capacity is 9 units."
    assert result["topics"][0]["evidence"][0]["id"] == "a"
    assert "source" in json.loads(model.requests[3]["prompt"])[0]


@pytest.mark.parametrize("checks", [[], [{"index": 0, "support": "explicit"}] * 2, [{"index": True, "support": "explicit"}], [{"index": 1, "support": "explicit"}], [{"index": 0, "support": "guess"}]])
def test_grounding_audit_fails_closed_on_missing_duplicate_or_invalid_checks(checks):
    model = SequenceLLM([{"checks": checks}])
    with pytest.raises(ValueError):
        audit_claims(source(), [{"text": "Routing", "evidence": ["a"]}], model)
    assert len(model.requests) == 1


def test_missing_literal_acronym_is_not_promoted_to_explicit_and_context_is_minimal():
    bundle = source()
    model = SequenceLLM([{"checks": [{"index": 0, "support": "explicit", "evidence": ["b", "a"]}]}])
    labels, ids = audit_claims(bundle, [{"text": "If ABC is needed, choose this service.", "evidence": ["b"]}], model, context=bundle.segments[:2])
    assert labels == ["inference"] and ids == [["b", "a"]]
    rows = json.loads(model.requests[0]["prompt"].split("\n", 1)[1])
    assert [s["id"] for s in rows[0]["source"]] == ["b"]
    assert [s["id"] for s in rows[0]["context_for_interpretation_only"]] == ["a"]
    limited = SequenceLLM([explicit_checks(1)])
    assert audit_claims(bundle, [{"text": "If ABC is needed", "evidence": ["b"]}], limited, context=bundle.segments[1:2]) == (["inference"], [["b"]])


def qa_draft():
    return {"answer": "Unused uncited prose", "answer_supported": True, "claims": [{"text": "Routing is supported", "evidence": ["a"], "kind": "author_statement"}], "qualifications": {facet: [] for facet in qa.QUALIFICATION_FACETS}}


def test_qa_renders_all_qualifications_and_never_uncited_prose():
    value = qa_draft()
    value["qualifications"]["limitations"] = [{"text": "Capacity is limited", "evidence": ["a"], "kind": "author_statement"}]
    value["qualifications"]["source_uncertainty"] = [{"text": "A condition is incomplete", "evidence": ["b"], "kind": "inference"}]
    model = SequenceLLM([value, explicit_checks(3)])
    result = qa.answer_question(source(), "routing", model)
    assert len(result["claims"]) == 3
    assert "Capacity is limited" in result["answer"] and "Интерпретация" in result["answer"]
    assert "Unused uncited prose" not in result["answer"]


def test_cited_unavailability_explanation_still_abstains_from_requested_measurement():
    value = qa_draft()
    value["answer_supported"] = False
    value["claims"][0]["text"] = "The requested measurements are not established by these captions"
    result = qa.answer_question(source(), "routing measurements", SequenceLLM([value, explicit_checks(1)]))
    assert result["abstained"] is True and result["claims"]
    assert result["answer"] == value["claims"][0]["text"]


def test_unsupported_claims_are_removed_but_inference_is_not_called_author_statement():
    value = qa_draft()
    value["claims"].append({"text": "Speculative condition", "evidence": ["b"], "kind": "author_statement"})
    checks = {"checks": [{"index": 0, "support": "unsupported"}, {"index": 1, "support": "inference"}]}
    result = qa.answer_question(source(), "routing", SequenceLLM([value, checks]))
    assert len(result["claims"]) == 1 and result["claims"][0]["kind"] == "inference"
    assert result["answer"].startswith("Интерпретация")


def test_phrase_repair_cannot_join_adjacent_ids_across_a_time_gap():
    bundle = source()
    bundle.segments = [TranscriptSegment("left", "Example product", 0, 2), TranscriptSegment("right", "suffix", 60, 2)]
    assert qa._complete_phrase_citations("Example product suffix", ["right"], bundle, bundle.segments) == ["right"]


def test_duplicate_coverage_merges_evidence_and_preserves_inference_status():
    value = draft()
    value["useful_ideas"] = [{"text": "A conclusion", "evidence": ["a"], "kind": "source"}]
    value["coverage"]["conditional_recommendations"] = [{"text": "A conclusion", "evidence": ["b"], "kind": "inference"}]
    value["caveats"] = [{"text": "A planned release", "evidence": ["c"]}]
    value["coverage"]["available_vs_promised"] = [{"text": "A planned release", "evidence": ["c"], "kind": "source", "status": "promised_in_source"}]
    briefing._fold_coverage(value)
    assert value["useful_ideas"] == [{"text": "A conclusion", "evidence": ["a", "b"], "kind": "inference"}]
    assert any(claim["text"].startswith("Обещание в источнике:") for claim in value["caveats"])


def test_audit_cannot_cite_an_unprovided_context_row_even_if_its_id_is_valid():
    model = SequenceLLM([{"checks": [{"index": 0, "support": "explicit", "evidence": ["d"]}]}])
    with pytest.raises(ValueError, match="outside this claim"):
        audit_claims(source(), [{"text": "ABC supports routing", "evidence": ["a"]}], model)


def test_unverified_identity_metadata_produces_caveat_without_an_expected_answer_fixture():
    value = qa_draft()
    value["claims"][0]["text"] = "Говорящий представился по имени"
    result = qa.answer_question(source(), "routing", SequenceLLM([value, explicit_checks(1)]))
    assert len(result["claims"]) == 2
    assert result["claims"][-1]["kind"] == "inference"
    assert "не подтверждают точную личность" in result["answer"]
    assert result["claims"][-1]["evidence"][0]["id"] == "a"


def test_audit_can_supply_missing_compound_name_row_and_brief_completes_the_phrase():
    bundle = source()
    bundle.segments = [TranscriptSegment("a", "Widget N8", 0, 2), TranscriptSegment("b", "Max serves clients", 2, 2), TranscriptSegment("c", "It runs all day", 4, 2)]
    value = draft()
    value["gist_evidence"] = ["c"]
    value["topics"] = [{"text": "Widget N8 Max serves clients", "evidence": ["b"]}]
    audit = {"checks": [{"index": 0, "support": "explicit", "evidence": ["c"]}, {"index": 1, "support": "explicit", "evidence": ["a", "b"]}]}
    result, _ = briefing.brief_bundle(bundle, SequenceLLM([value, audit]))
    assert [e["id"] for e in result["topics"][0]["evidence"]] == ["a", "b"]


def test_positive_identity_assertion_is_not_laundered_as_an_inference():
    value = qa_draft()
    value['claims'][0].update(text='Точная личность говорящего установлена по представлению.', kind='inference')
    result = qa.answer_question(source(), 'routing', SequenceLLM([value, explicit_checks(1)]))
    assert 'точная личность и фамилия не подтверждены' in result['answer']
    assert 'личность говорящего установлена' not in result['answer']
    assert all(claim['kind'] == 'inference' for claim in result['claims'])


def test_mechanism_qualifiers_extensions_and_existing_features_survive_folding():
    value = draft()
    value["coverage"]["mechanism_limits"] = [{"text": "Transfer has a delay", "evidence": ["a"], "kind": "source"}]
    value["coverage"]["mechanism_extensions"] = [{"text": "Add another node", "evidence": ["b"], "kind": "source"}]
    value["coverage"]["available_vs_promised"] = [{"text": "Current capability", "evidence": ["a"], "kind": "source", "status": "available_in_source"}, {"text": "Future capability", "evidence": ["c"], "kind": "source", "status": "promised_in_source"}]
    briefing._validate_generation_shape(value)
    briefing._fold_coverage(value)
    assert value["useful_ideas"][0]["text"] == "Add another node"
    assert [claim["text"] for claim in value["caveats"]] == ["Transfer has a delay", "Описано как имеющееся в источнике: Current capability", "Обещание в источнике: Future capability"]
