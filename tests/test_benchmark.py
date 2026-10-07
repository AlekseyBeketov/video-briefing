import json
import hashlib

import pytest

from video_briefing import benchmark
from video_briefing.benchmark import load_config
from video_briefing.models import EvidenceBundle, TranscriptSegment
from video_briefing.store import ArtifactStore


def test_benchmark_requires_fixed_target_and_question_file(tmp_path):
    config = {"video_url": "https://www.youtube.com/watch?v=DvSwvJVens8", "video_id": "DvSwvJVens8", "variant": "baoyu", "questions_file": "questions.json"}
    path = tmp_path / "experiment.json"
    path.write_text(json.dumps(config))
    assert load_config(path)["video_id"] == "DvSwvJVens8"
    config["video_id"] = "other"
    path.write_text(json.dumps(config))
    try:
        load_config(path)
    except ValueError:
        pass
    else:
        raise AssertionError("mismatched fixed target must fail")


def test_failed_benchmark_persists_phase_and_failure_without_losing_source(tmp_path, monkeypatch):
    source_text = "\n".join(f"synthetic fixture segment {index} " + "x" * 120 for index in range(1, 301))
    segments = [TranscriptSegment(f"s{index:05d}", f"synthetic fixture segment {index} " + "x" * 120, index, 2) for index in range(1, 301)]
    bundle = EvidenceBundle("youtube", "DvSwvJVens8", "https://www.youtube.com/watch?v=DvSwvJVens8", "ru", "captions_api", "fixture", "test", segments, hashlib.sha256(source_text.encode()).hexdigest(), raw_text=source_text)
    store = ArtifactStore(tmp_path / "evidence")
    store.save(bundle)
    question_path = tmp_path / "questions.json"
    question_path.write_text(json.dumps({"questions": [{"id": "q-test", "question": "Fixture question"}]}))
    config = {"variant": "captions_api", "languages": "ru", "questions_file": str(question_path), "_config_dir": str(tmp_path), "llm": {"base_url": "http://127.0.0.1:11434", "model": "gemma4:31b-cloud", "temperature": 0, "timeout_seconds": 1}}

    class BrokenLLM:
        model = "gemma4:31b-cloud"
        responses = []
        calls = 0

        def __init__(self, *args):
            pass

        def generate_json(self, **kwargs):
            self.calls += 1
            if self.calls > 1:
                raise ValueError("intentional synthetic late-chunk failure")
            return {"gist": "Synthetic test claim", "gist_evidence": ["s00001"], "topics": [], "useful_ideas": [], "emphases": [], "caveats": []}

    monkeypatch.setattr(benchmark, "OllamaClient", BrokenLLM)
    progress_dir = tmp_path / "run"
    with pytest.raises(ValueError, match="intentional synthetic late-chunk"):
        benchmark.run_benchmark(config, root=tmp_path, artifact_root=tmp_path / "evidence", progress_dir=progress_dir)
    progress = json.loads((progress_dir / "progress.json").read_text())
    assert progress["status"] == "failed"
    assert progress["phase"] == "brief_chunk"
    assert progress["chunk"] == 1
    assert len(progress["partial_brief_parts"]) == 1
    assert progress["source_sha256"] == bundle.raw_sha256
    assert progress["error"]["type"] == "ValueError"
