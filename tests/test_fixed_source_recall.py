"""Evaluator-only recall checks on the supplied immutable cache; no transcript fixture copies.

Missing private evidence is an explicit skip on other machines, never a synthetic pass.
All cases run against the actual bundle in the corrective repair workspace.
"""
import hashlib
import json
import os
from pathlib import Path

import pytest

from video_briefing.retrieval import MAX_CONTEXT_CHARS, retrieve
from video_briefing.store import ArtifactStore
from video_briefing.source_guards import (
    coordinated_quantity_conflicts, preserve_example_quantities, quantities,
    repair_coordinated_quantities, software_interpretation_context,
    preserve_source_uncertainty,
)

ROOT = Path(__file__).resolve().parents[1]
SOURCE_SHA = "940d5b89a1d24b30f256d352f97d3d6624a5f296a1707780b777dbdb17d1e3af"
EVALUATION_SHA = "7abd485c1549e336497346a7cf571098a7ca18c8662ddf8f81ad781a0c94d1a1"
# Minimum complete supporting ranges, not a substitute for the frozen answer/rubric.
# q05 attribution may remain neutral without retrieving the self-introduction; its
# complete final recommendation is mandatory. Additional reference ranges are reported
# by the smoke evaluator, not silently labelled as 100% coverage here.
CORE_RANGES = {
    "q01": [(36, 41), (78, 87), (117, 137)],
    "q02": [(138, 147)],
    "q03": [(167, 194), (199, 201), (217, 226)],
    "q04": [(266, 273), (277, 289), (334, 345)],
    "q05": [(526, 563)],
    "q06": [(202, 208), (460, 463), (475, 487)],
    "q07": [(503, 525)],
    "q08": [(334, 345)],
}


@pytest.fixture(scope="module")
def actual_source():
    store = ArtifactStore(os.environ.get("VIDEO_BRIEFING_EVIDENCE_STORE", ROOT / "artifacts/private/evidence"))
    bundle = store.find("DvSwvJVens8", "captions_api", language="ru")
    if bundle is None:
        pytest.skip("Supplied private source cache unavailable; no extraction or fixture substitution")
    assert bundle.raw_sha256 == SOURCE_SHA
    assert len(bundle.segments) == 566
    raw_path = store.bundle_path(bundle.key).with_name("source.raw")
    assert hashlib.sha256(raw_path.read_bytes()).hexdigest() == SOURCE_SHA
    evaluation_path = ROOT / "docs/research/evaluation.json"
    assert hashlib.sha256(evaluation_path.read_bytes()).hexdigest() == EVALUATION_SHA
    evaluation = json.loads(evaluation_path.read_text())
    # Verify reference namespace mapping before using rNNNN offsets as candidate indices.
    reference_path = ROOT / evaluation["reference"]["segments_path"]
    if not reference_path.is_file():
        pytest.skip("Private reference mapping unavailable; offsets cannot be assumed")
    reference = json.loads(reference_path.read_text())
    assert hashlib.sha256(reference_path.read_bytes()).hexdigest() == evaluation["reference"]["segments_sha256"]
    assert len(reference) == len(bundle.segments)
    for index, (ref, actual) in enumerate(zip(reference, bundle.segments)):
        assert ref["id"] == f"r{index:04d}"
        assert (ref["text"], ref["start_seconds"], ref["duration_seconds"]) == (
            actual.text, actual.start_seconds, actual.duration_seconds
        )
    return bundle, {q["id"]: q for q in evaluation["questions"]}, raw_path


@pytest.mark.parametrize("query_id", list(CORE_RANGES))
def test_all_eight_fixed_questions_have_complete_core_source_windows(actual_source, query_id):
    bundle, questions, raw_path = actual_source
    before = raw_path.read_bytes()
    result = retrieve(bundle, questions[query_id]["question"])
    found = {segment.id for segment in result}
    for low, high in CORE_RANGES[query_id]:
        expected = {segment.id for segment in bundle.segments[low:high + 1]}
        assert expected <= found, f"{query_id}: missing {sorted(expected - found)}"
    assert result == retrieve(bundle, questions[query_id]["question"])
    assert result == [segment for segment in bundle.segments if segment.id in found]
    assert len(result) == len(found) < len(bundle.segments)
    assert sum(len(segment.text) + 1 for segment in result) <= MAX_CONTEXT_CHARS
    assert raw_path.read_bytes() == before


@pytest.mark.parametrize("query_id,low,high", [
    ("q04", 277, 289), ("q04", 334, 345), ("q05", 526, 563),
    ("q06", 460, 463), ("q06", 475, 487),
])
def test_each_reported_recall_defect_requires_every_original_caption(actual_source, query_id, low, high):
    bundle, questions, _ = actual_source
    found = {segment.id for segment in retrieve(bundle, questions[query_id]["question"])}
    expected = {segment.id for segment in bundle.segments[low:high + 1]}
    assert found & expected == expected


def test_frozen_evaluation_is_byte_identical():
    assert hashlib.sha256((ROOT / "docs/research/evaluation.json").read_bytes()).hexdigest() == EVALUATION_SHA


def test_actual_numeric_example_cannot_lose_its_active_parameter_clause(actual_source):
    bundle, _, _ = actual_source
    # Deliberately reproduce the omission. Values are evaluator-only and this test
    # never invokes generation or substitutes a transcript fixture.
    example = {"text": "GPT OSS 120B: 117 млрд параметров, MXFP4 на 80 ГБ памяти.",
               "evidence": [bundle.segments[i].id for i in (138, 139, 142, 143)],
               "kind": "source", "quantities": []}
    repairs = preserve_example_quantities({"coverage": {"worked_examples": [example]}}, bundle, bundle.segments)
    assert any(("5.1", "billion") in repair["quantities"] for repair in repairs)
    active = next(item for item in example["quantities"] if ("5.1", "billion") in quantities(item["text"]))
    assert bundle.segments[141].text.split(". И")[0] in active["text"]
    assert bundle.segments[141].id in active["evidence"]


def test_actual_multisystem_example_preserves_numeric_clauses_in_bounded_cited_clusters(actual_source):
    bundle, _, _ = actual_source
    example = {"text": "GPT OSS 120B: 117 млрд параметров, MXFP4 на 80 ГБ; сравнение нескольких систем.",
               "evidence": [bundle.segments[i].id for i in (138, 139, 142, 143, 267, 268, 385, 386, 387)],
               "kind": "source", "quantities": []}
    repairs = preserve_example_quantities({"coverage": {"worked_examples": [example]}}, bundle, bundle.segments)
    active = next(repair for repair in repairs if ("5.1", "billion") in repair["quantities"])
    assert bundle.segments[141].id in active["evidence"]
    assert all(len(repair["evidence"]) <= 32 for repair in repairs)
    assert not any(bundle.segments[200].id in repair["evidence"] for repair in repairs)


def test_actual_dgx_ceiling_cannot_transfer_to_rtx_even_with_both_names_cited(actual_source):
    bundle, _, _ = actual_source
    claim = {"text": "Для разработки и инференса моделей до 200 млрд параметров: NVIDIA DJX Spark или RTX Spark.",
             "evidence": [bundle.segments[i].id for i in (279, 280, 281, 282, 299)], "kind": "source"}
    assert coordinated_quantity_conflicts(claim, bundle, bundle.segments)
    repair_coordinated_quantities([claim], bundle, bundle.segments)
    assert "RTX" not in claim["text"] and "DJX Spark" in claim["text"]
    assert bundle.segments[281].id in claim["evidence"]


def test_actual_q05_interpretation_requires_earlier_software_source_context(actual_source):
    bundle, questions, _ = actual_source
    excerpts = retrieve(bundle, questions["q05"]["question"])
    claim = {"text": "Если нужна CUDA, покупать RTX Spark или DGX Spark под нейронки.",
             "evidence": [bundle.segments[i].id for i in range(555, 560)]}
    context = software_interpretation_context(claim, bundle, excerpts)
    assert context and set(context) <= {segment.id for segment in excerpts}
    assert all(int(identifier[1:]) < 555 for identifier in context)
    text = " ".join(segment.text for segment in excerpts if segment.id in context)
    assert "Nvidia" in text and "программная платформа" in text


def test_actual_vendor_omission_keeps_software_context_and_exact_product_bridge(actual_source):
    bundle, questions, _ = actual_source
    excerpts = retrieve(bundle, questions['q05']['question'])
    claim = {'text': 'Если нужна CUDA, выбирать RTX Spark или DGX Spark.',
             'evidence': [bundle.segments[i].id for i in (557, 558)]}
    ids = software_interpretation_context(claim, bundle, excerpts)
    text = ' '.join(segment.text for segment in bundle.segments if segment.id in ids)
    assert 'программная платформа' in text and 'Nvidia' in text
    assert 'RTX' in text and 'Spark' in text
    assert set(ids) <= {segment.id for segment in excerpts}


def test_actual_brief_cannot_silently_drop_source_testing_uncertainty(actual_source):
    bundle, _, _ = actual_source
    value = {'topics': [{'text': 'RTX Spark PC объявлены.', 'evidence': [bundle.segments[341].id]}]}
    repairs = preserve_source_uncertainty(value, bundle, bundle.segments)
    assert len(repairs) == 1
    assert 'нет полноценной картины' in repairs[0]['source_text']
    assert all(bundle.segments[i].id in repairs[0]['evidence'] for i in range(341, 346))
