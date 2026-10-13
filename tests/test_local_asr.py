import json
import sys
from pathlib import Path

import pytest

from video_briefing.local_asr import LocalASRError, _local_environment, ingest_local_video


def executable(path: Path, body: str) -> Path:
    path.write_text(f"#!{sys.executable}\n{body}", encoding="utf-8")
    path.chmod(0o700)
    return path


def setup_fake_runtime(tmp_path: Path):
    source = tmp_path / "input.mp4"
    source.write_bytes(b"synthetic-local-fixture")
    model = tmp_path / "model.gguf"
    model.write_bytes(b"test-model-placeholder")
    probe = executable(tmp_path / "ffprobe", "import json; print(json.dumps({'streams':[{'codec_type':'audio','duration':'40.0'}]}))\n")
    ffmpeg = executable(tmp_path / "ffmpeg", """
import pathlib, sys
pattern = pathlib.Path(sys.argv[-1])
for i in range(2):
    pattern.with_name(f'chunk_{i:05d}.wav').write_bytes(b'fixture')
""")
    cli = executable(tmp_path / "transcribe-cli", """
import json, pathlib, sys
batch = pathlib.Path(sys.argv[sys.argv.index('--batch') + 1])
print(json.dumps({'type':'batch_header','load_ms':1}))
for i, line in enumerate(batch.read_text().splitlines()):
    print(json.dumps({'file':line,'text':'Speech chunk.' if i == 0 else ''}))
""")
    return source, model, probe, ffmpeg, cli


def test_local_environment_drops_credentials_and_proxy(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-pass")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "must-not-pass")
    monkeypatch.setenv("HTTP_PROXY", "http://proxy.invalid")
    monkeypatch.setenv("HTTPS_PROXY", "http://proxy.invalid")
    monkeypatch.setenv("VIDEO_BRIEFING_ASR_MODEL", "/private/model.gguf")
    env = _local_environment()
    assert "OPENAI_API_KEY" not in env
    assert "AWS_SECRET_ACCESS_KEY" not in env
    assert "VIDEO_BRIEFING_ASR_MODEL" not in env
    assert env["HTTP_PROXY"] == env["HTTPS_PROXY"] == ""
    assert env["NO_PROXY"] == "*"


def test_local_asr_records_chunk_timing_provenance_and_privacy(tmp_path):
    source, model, probe, ffmpeg, cli = setup_fake_runtime(tmp_path)
    bundle = ingest_local_video(source, ffmpeg=ffmpeg, ffprobe=probe, transcribe_cli=cli,
                                model_path=model, work_root=tmp_path / "work", threads=2)
    assert bundle.platform == "local-file"
    assert bundle.video_id == bundle.metadata["media_sha256"]
    assert len(bundle.segments) == 1
    assert bundle.segments[0].start_seconds == 0
    assert bundle.segments[0].duration_seconds == 24
    assert bundle.metadata["processed_audio_seconds"] == 40
    assert bundle.metadata["privacy"] == {
        "network_used": False, "cloud_asr": False, "cloud_llm": False, "transcript_uploaded": False
    }
    assert "chunk bounds" in bundle.metadata["timing_precision"]
    logs = bundle.metadata["execution_logs"]
    log_dir = Path(logs["directory"])
    manifest = json.loads((log_dir / "manifest.json").read_text())
    assert manifest["exit_code"] == 0
    assert "--batch-jsonl" in manifest["command"]
    assert logs["stdout_bytes"] > 0
    assert (log_dir / "stdout.jsonl").stat().st_mode & 0o777 == 0o600
    assert (log_dir / "stderr.txt").stat().st_mode & 0o777 == 0o600
    assert not list((tmp_path / "work").glob("video-briefing-asr-*"))


def test_local_ffmpeg_tools_receive_file_only_protocol_whitelist(tmp_path):
    source, model, probe, ffmpeg, cli = setup_fake_runtime(tmp_path)
    observed = tmp_path / "args.log"
    for tool in (probe, ffmpeg):
        original = tool.read_text()
        tool.write_text(original.replace("import json; print", f"import os; open({str(observed)!r}, 'a').write(os.path.basename(__file__) + ' ' + ' '.join(__import__('sys').argv[1:]) + '\\n'); import json; print")
                               if tool == probe else original.replace("import pathlib, sys", f"import pathlib, sys, os; open({str(observed)!r}, 'a').write(os.path.basename(__file__) + ' ' + ' '.join(sys.argv[1:]) + '\\n')"))
    ingest_local_video(source, ffmpeg=ffmpeg, ffprobe=probe, transcribe_cli=cli,
                       model_path=model, work_root=tmp_path / "work")
    invocations = observed.read_text().splitlines()
    assert len(invocations) == 2
    assert all("-protocol_whitelist file" in invocation for invocation in invocations)


@pytest.mark.parametrize("mode,expected", [("reorder", "chunk order"), ("truncate", "truncated")])
def test_local_asr_rejects_mismatched_or_truncated_rows(tmp_path, mode, expected):
    source, model, probe, ffmpeg, _ = setup_fake_runtime(tmp_path)
    cli = executable(tmp_path / f"{mode}-cli", f"""
import json, pathlib, sys
batch = pathlib.Path(sys.argv[sys.argv.index('--batch') + 1])
files = batch.read_text().splitlines()
if {mode!r} == 'reorder': files.reverse()
for i, file in enumerate(files):
    row = {{'file': file, 'text': 'Speech.'}}
    if {mode!r} == 'truncate' and i == 0: row['truncated'] = True
    print(json.dumps(row))
""")
    with pytest.raises(LocalASRError, match=expected):
        ingest_local_video(source, ffmpeg=ffmpeg, ffprobe=probe, transcribe_cli=cli,
                           model_path=model, work_root=tmp_path / "work")


def test_local_asr_timeout_persists_private_failure_logs(tmp_path):
    source, model, probe, ffmpeg, _ = setup_fake_runtime(tmp_path)
    cli = executable(tmp_path / "slow-transcribe-cli", "import time; time.sleep(5)")
    with pytest.raises(LocalASRError, match="timed out"):
        ingest_local_video(source, ffmpeg=ffmpeg, ffprobe=probe, transcribe_cli=cli,
                           model_path=model, work_root=tmp_path / "work", timeout_seconds=1)
    logs = list((tmp_path / "work" / "runs").glob("*/*/manifest.json"))
    assert len(logs) == 1
    manifest = json.loads(logs[0].read_text())
    assert manifest["exit_code"] is None
    assert manifest["command"][-1] == "--batch-jsonl"
    assert logs[0].with_name("stdout.jsonl").exists()
    assert logs[0].with_name("stderr.txt").exists()


def test_local_asr_rejects_unbounded_timeout_and_non_mp4(tmp_path):
    source, model, probe, ffmpeg, cli = setup_fake_runtime(tmp_path)
    with pytest.raises(LocalASRError, match="timeout_seconds"):
        ingest_local_video(source, ffmpeg=ffmpeg, ffprobe=probe, transcribe_cli=cli,
                           model_path=model, work_root=tmp_path / "work", timeout_seconds=21601)
    audio = tmp_path / "input.wav"
    audio.write_bytes(b"x")
    with pytest.raises(LocalASRError, match="MP4"):
        ingest_local_video(audio, ffmpeg=ffmpeg, ffprobe=probe, transcribe_cli=cli,
                           model_path=model, work_root=tmp_path / "work")
