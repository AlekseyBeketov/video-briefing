import json
from types import SimpleNamespace

import pytest

from video_briefing.adapters.summarize import parse_summarize_output
from video_briefing.adapters import baoyu


def test_summarize_requires_actual_timed_transcript():
    payload = {"extracted": {"language": "en", "transcriptSegments": [{"text": "Hi", "start": 1.5, "duration": 2}]}}
    assert parse_summarize_output(json.dumps(payload), "DvSwvJVens8", "en").segments[0].start_seconds == 1.5


def test_summarize_rejects_unknown_or_mismatched_track_language():
    with pytest.raises(ValueError, match="source language"):
        parse_summarize_output(json.dumps({"extracted": {"language": "und", "segments": [{"text": "Hi", "start": 0, "duration": 1}]}}), "DvSwvJVens8", "ru")
    with pytest.raises(ValueError, match="source language"):
        parse_summarize_output(json.dumps({"extracted": {"language": "en", "segments": [{"text": "Hi", "start": 0, "duration": 1}]}}), "DvSwvJVens8", "ru")


def test_baoyu_does_not_accept_old_output_when_invocation_writes_nothing(tmp_path, monkeypatch):
    bun = tmp_path / "bun"
    bun.write_text("test executable placeholder")
    stale_root = tmp_path / "output" / "DvSwvJVens8" / "ru"
    stale_root.mkdir(parents=True)
    (stale_root / "transcript-raw.json").write_text('[{"text":"stale","start":0,"duration":1}]')
    calls = 0

    def run(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return SimpleNamespace(returncode=0, stdout="1.4.0", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(baoyu.subprocess, "run", run)
    skill_root = tmp_path / "baoyu"
    (skill_root / "scripts").mkdir(parents=True)
    (skill_root / "scripts" / "main.ts").write_text("// fixture")
    with pytest.raises(ValueError, match="without raw transcript JSON"):
        baoyu.extract("https://www.youtube.com/watch?v=DvSwvJVens8", languages="ru", output_dir=tmp_path / "output", bun=bun, skill_dir=skill_root)
    assert calls == 2
    invocation_dirs = list(stale_root.iterdir())
    assert len(invocation_dirs) == 2
    assert not any(path.is_dir() and list(path.glob("**/transcript-raw.json")) for path in invocation_dirs)


@pytest.mark.parametrize("payload", [
    '{"title":"T","description":"only metadata"}',
    '{"transcript":"untimed prose"}',
    '{"transcriptSegments":[{"text":"no time"}]}',
])
def test_summarize_rejects_description_or_untimed_output(payload):
    with pytest.raises(ValueError):
        parse_summarize_output(payload, "DvSwvJVens8", "en")
