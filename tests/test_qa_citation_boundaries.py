"""Boundary regression with a small excerpt, not a full private transcript fixture."""

import pytest
import json

from video_briefing.models import EvidenceBundle, TranscriptSegment
from video_briefing.qa import QUALIFICATION_FACETS, _complete_phrase_citations, answer_question


LIVE_SOURCE_SHA256 = "940d5b89a1d24b30f256d352f97d3d6624a5f296a1707780b777dbdb17d1e3af"
QUESTION = "Что автор говорит о NAS и какие функции Mini Scloud уже доступны или обещаны?"
CLAIM = "Mini Sform N5 Max: пять отсеков под HDD, пять под SSD, до 200 ТБ хранения и два десятигигабитных Ethernet."


@pytest.fixture
def nas_source():
    # Exact caption IDs, text and times from the saved 566-segment source above.
    # The hash identifies that complete source; this fixture contains only its boundary excerpt.
    return EvidenceBundle(
        "youtube", "DvSwvJVens8", "https://www.youtube.com/watch?v=DvSwvJVens8",
        "ru", "captions_api", "auto-captions", "youtube-transcript-api-1.2.4",
        [
            TranscriptSegment("s00496", "Что если вообще убрать AI из вашего", 1257.08, 6.429),
            TranscriptSegment("s00497", "основного компьютера? Вот Mini Sform N5", 1260.559, 5.721),
            TranscriptSegment("s00498", "[музыка] Max. Снаружи нас пять отсеков", 1263.509, 7.691),
            TranscriptSegment("s00499", "под HDD, ещё пять под SSD до 200 ТБ", 1266.28, 7.709),
            TranscriptSegment("s00500", "хранения, два десятигибитных Eernet.", 1271.2, 5.16),
            TranscriptSegment("s00501", "[музыка] Внутри стоит всё тот же Ryzen", 1273.989, 8.371),
        ],
        LIVE_SOURCE_SHA256,
    )


class BoundaryLLM:
    model = "boundary-fixture"

    def __init__(self, evidence):
        self.evidence = evidence

    def generate_json(self, **kwargs):
        if "checks" in kwargs["schema"]["properties"]:
            rows = json.loads(kwargs["prompt"].split("\n", 1)[1])
            return {"checks": [{"index": row["index"], "support": "explicit"} for row in rows]}
        assert "[s00497]" in kwargs["prompt"]
        return {
            "answer": CLAIM,
            "answer_supported": True,
            "qualifications": {facet: [] for facet in QUALIFICATION_FACETS},
            "claims": [{"text": CLAIM, "evidence": self.evidence, "kind": "author_statement"}],
        }


def test_fixed_source_nas_identity_extends_only_needed_caption(nas_source):
    result = answer_question(nas_source, QUESTION, BoundaryLLM(["s00498", "s00499", "s00500"]))
    evidence = result["claims"][0]["evidence"]
    assert [item["id"] for item in evidence] == ["s00497", "s00498", "s00499", "s00500"]
    assert evidence[0] == {"id": "s00497", "start_seconds": 1260.559, "duration_seconds": 5.721}
    assert result["answer"] == CLAIM
    assert result["abstained"] is False
    assert nas_source.raw_sha256 == LIVE_SOURCE_SHA256


def test_complete_citations_are_idempotent_and_not_padded(nas_source):
    ids = ["s00497", "s00498", "s00499", "s00500"]
    assert _complete_phrase_citations(CLAIM, ids, nas_source, nas_source.segments) == ids
    assert _complete_phrase_citations("До 200 ТБ хранения", ["s00499"], nas_source, nas_source.segments) == ["s00499", "s00500"]
    assert _complete_phrase_citations("Пять отсеков", ["s00498"], nas_source, nas_source.segments) == ["s00498"]


def test_phrase_completion_never_joins_separate_retrieval_windows(nas_source):
    # s00498 is missing: s00497 and s00499 must not form a synthetic spoken phrase.
    excerpts = [nas_source.segments[1], nas_source.segments[3]]
    assert _complete_phrase_citations("N5 под HDD", ["s00499"], nas_source, excerpts) == ["s00499"]
    # A neighbouring identity segment outside the model context must not be pulled in.
    excerpts = nas_source.segments[2:5]
    assert _complete_phrase_citations(CLAIM, ["s00498", "s00499", "s00500"], nas_source, excerpts) == ["s00498", "s00499", "s00500"]


def test_phrase_can_span_three_segments_in_both_directions(nas_source):
    nas_source.segments = [
        TranscriptSegment("left", "Unrelated introductory text", 0, 1),
        TranscriptSegment("name", "Mini Sform", 1, 1),
        TranscriptSegment("number", "N5", 2, 1),
        TranscriptSegment("suffix", "[music] Max", 3, 1),
        TranscriptSegment("right", "Unrelated ending", 4, 1),
    ]
    for cited in (["name"], ["number"], ["suffix"]):
        assert _complete_phrase_citations("Mini Sform N5 Max", cited, nas_source, nas_source.segments) == ["name", "number", "suffix"]


def test_repeated_phrase_does_not_expand_an_already_supported_occurrence(nas_source):
    nas_source.segments = [
        TranscriptSegment("first", "Mini Sform N5 Max", 0, 1),
        TranscriptSegment("second", "Mini Sform N5", 1, 1),
        TranscriptSegment("third", "Max", 2, 1),
    ]
    assert _complete_phrase_citations("Mini Sform N5 Max", ["first", "third"], nas_source, nas_source.segments) == ["first", "third"]


@pytest.mark.parametrize("ids", [[], ["unknown-id"]])
def test_boundary_repair_does_not_make_invalid_citations_valid(nas_source, ids):
    with pytest.raises(ValueError, match="must cite evidence|unknown evidence ids"):
        answer_question(nas_source, QUESTION, BoundaryLLM(ids))


def test_boundary_repair_still_rejects_model_citations_outside_context(nas_source, monkeypatch):
    from video_briefing import qa

    monkeypatch.setattr(qa, "retrieve", lambda *args, **kwargs: nas_source.segments[1:5])
    with pytest.raises(ValueError, match="outside the supplied retrieval context"):
        answer_question(nas_source, QUESTION, BoundaryLLM(["s00501"]))
