import json

from video_briefing.benchmark import load_config


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
