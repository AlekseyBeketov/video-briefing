from types import SimpleNamespace

import pytest

from video_briefing.adapters import baoyu


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
