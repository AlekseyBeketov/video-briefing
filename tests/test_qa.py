from video_briefing.models import EvidenceBundle, TranscriptSegment
from video_briefing.qa import answer_question


class FakeLLM:
    def __init__(self):
        self.calls = 0

    def generate_json(self, **kwargs):
        self.calls += 1
        return {"answer": "The author favors retrieval over fine-tuning.", "claims": [{"text": "Favors retrieval", "evidence": ["s00001"], "kind": "author_statement"}]}


def test_grounded_answer_validates_evidence_and_abstains_without_hits():
    source = EvidenceBundle("youtube", "DvSwvJVens8", "https://youtube.com/watch?v=DvSwvJVens8", "en", "fixture", "manual-captions", "1", [TranscriptSegment("s00001", "I prefer retrieval augmented generation over fine-tuning.", 3, 4)], "a" * 64)
    model = FakeLLM()
    result = answer_question(source, "What approach does the author prefer?", model)
    assert result["claims"][0]["evidence"][0]["start_seconds"] == 3
    assert answer_question(source, "What is the speaker's favorite color?", model)["abstained"] is True
    assert model.calls == 1
