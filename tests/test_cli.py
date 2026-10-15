import json
from importlib.metadata import PackageNotFoundError
import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest
import video_briefing.cli as cli
from video_briefing import benchmark
from video_briefing.cli import _llm, build_parser, main


def test_cli_exposes_workflow_commands():
    parser = build_parser()
    assert set(parser._subparsers._group_actions[0].choices) == {
        "doctor", "setup-asr", "extract", "ingest", "search", "read", "skill", "brief", "ask", "benchmark"
    }
    brief = parser._subparsers._group_actions[0].choices["brief"]
    assert any(action.dest == "json" for action in brief._actions)
    assert any(action.dest == "allow_cloud" for action in brief._actions)
    ask = parser._subparsers._group_actions[0].choices["ask"]
    assert any(action.dest == "languages" for action in ask._actions)
    assert any(action.dest == "allow_cloud" for action in ask._actions)
    ingest = parser._subparsers._group_actions[0].choices["ingest"]
    assert any(action.dest == "local_asr" for action in ingest._actions)


def test_cli_variant_choices_exclude_removed_summarize_adapter():
    commands = build_parser()._subparsers._group_actions[0].choices
    expected = {
        "extract": {"baoyu", "captions_api"},
        "ingest": {"baoyu", "captions_api"},
        "search": {"baoyu", "captions_api", "local_asr"},
        "read": {"baoyu", "captions_api", "local_asr"},
        "brief": {"baoyu", "captions_api"},
        "ask": {"baoyu", "captions_api"},
    }
    for command, expected_choices in expected.items():
        variant = next(action for action in commands[command]._actions if action.dest == "variant")
        assert set(variant.choices) == expected_choices


def test_errors_use_stable_json_schema_and_reject_agent_url_ssrf(capsys, tmp_path):
    code = main(["search", "http://127.0.0.1:8080/private", "q", "--store", str(tmp_path)])
    captured = capsys.readouterr()
    payload = json.loads(captured.err)
    assert code == 2
    assert set(payload) == {"error"}
    assert set(payload["error"]) == {"code", "message"}
    assert payload["error"]["code"] == "value_error"


def test_cloud_model_requires_explicit_privacy_opt_in():
    cloud = {"llm": {"provider": "ollama", "base_url": "https://ollama.example", "model": "remote", "cloud_backed": True}}
    import pytest
    with pytest.raises(PermissionError, match="--allow-cloud"):
        _llm(cloud)
    assert _llm(cloud, allow_cloud=True).model == "remote"


def test_model_endpoint_must_be_an_origin_even_with_cloud_opt_in():
    import pytest
    for base_url in ("http://127.0.0.1:11434/api?key=value", "http://127.0.0.1:99999"):
        config = {"llm": {"provider": "ollama", "base_url": base_url, "model": "m", "cloud_backed": False}}
        with pytest.raises(ValueError):
            _llm(config, allow_cloud=True)


def test_model_endpoint_credentials_are_rejected_even_with_cloud_opt_in():
    import pytest
    config = {"llm": {"provider": "ollama", "base_url": "http://user:pass@127.0.0.1:11434", "model": "m", "cloud_backed": False}}
    with pytest.raises(ValueError, match="credential-free"):
        _llm(config, allow_cloud=True)


def test_doctor_returns_nonzero_when_required_captions_dependency_is_missing(monkeypatch, capsys):
    def missing_package(_name):
        raise PackageNotFoundError

    monkeypatch.setattr(cli, "package_version", missing_package)
    monkeypatch.setattr(cli.shutil, "which", lambda _path: None)

    code = main(["doctor"])

    report = json.loads(capsys.readouterr().out)
    assert report["youtube_transcript_api"] == {"available": False}
    assert code == 1


def test_doctor_keeps_zero_status_when_only_optional_local_asr_tools_are_missing(monkeypatch, capsys):
    monkeypatch.setattr(cli, "package_version", lambda _name: "1.2.3")
    monkeypatch.setattr(cli.shutil, "which", lambda _path: None)
    monkeypatch.delenv("VIDEO_BRIEFING_FFMPEG", raising=False)
    monkeypatch.delenv("VIDEO_BRIEFING_FFPROBE", raising=False)

    code = main(["doctor"])

    report = json.loads(capsys.readouterr().out)
    assert report["youtube_transcript_api"] == {"available": True, "version": "1.2.3"}
    assert report["local_asr_tools"]["ffmpeg"]["available"] is False
    assert report["network_probes"] is False
    assert report["model_inference"] is False
    assert "ready_languages" in report["managed_asr"]
    assert code == 0


def test_setup_asr_requires_languages_in_noninteractive_use(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(cli, "_asr_runtime_available", lambda: True)
    monkeypatch.setenv("VIDEO_BRIEFING_DATA_HOME", str(tmp_path))

    code = main(["setup-asr", "--yes"])

    payload = json.loads(capsys.readouterr().err)
    assert code == 2
    assert "--languages" in payload["error"]["message"]


def test_setup_asr_installs_only_the_selected_language(tmp_path, monkeypatch, capsys):
    selected = []
    monkeypatch.setattr(cli, "_asr_runtime_available", lambda: True)
    monkeypatch.setattr(cli, "_default_data_home", lambda: tmp_path)
    monkeypatch.setattr(cli, "installed_models", lambda _root: [
        {"language": language, "installed": False} for language in ("ru", "en")
    ])
    monkeypatch.setattr(
        cli, "install_models",
        lambda languages, _root, **_kwargs: selected.extend(languages) or [{"status": "installed"}],
    )

    code = main(["setup-asr", "--languages", "en", "--yes"])

    report = json.loads(capsys.readouterr().out)
    assert code == 0
    assert selected == ["en"]
    assert report["languages"] == ["en"]


def test_benchmark_cli_allocates_and_reports_a_unique_run_directory(tmp_path, monkeypatch, capsys):
    run_directories = []
    monkeypatch.setattr(benchmark, "load_config", lambda _path: {})
    monkeypatch.setattr(
        benchmark,
        "run_benchmark",
        lambda config, *, root, artifact_root, progress_dir: run_directories.append(progress_dir)
        or {"metrics": {"status": "completed", "variant": "captions_api", "source_sha256": "a" * 64}},
    )
    monkeypatch.setattr(
        benchmark,
        "write_run",
        lambda result, output_dir: {name: output_dir / f"{name}.json" for name in ("metrics", "answers")},
    )
    args = SimpleNamespace(
        config="fixture.json", root=tmp_path, artifact_root=tmp_path / "evidence", output_dir=tmp_path / "runs",
    )

    for _ in range(2):
        assert cli._benchmark(args) == 0
        result = json.loads(capsys.readouterr().out)
        metrics_path = Path(result["paths"]["metrics"])
        assert all(Path(path).parent == metrics_path.parent for path in result["paths"].values())

    assert len(run_directories) == 2
    assert run_directories[0] != run_directories[1]
    assert all(path.parent == args.output_dir for path in run_directories)


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission bits are not portable to Windows")
def test_new_benchmark_run_directories_are_unique_and_private(tmp_path):
    first = cli._new_run_dir(tmp_path / "runs")
    second = cli._new_run_dir(tmp_path / "runs")

    assert first != second
    assert stat.S_IMODE(first.stat().st_mode) == 0o700
    assert stat.S_IMODE(second.stat().st_mode) == 0o700


def test_benchmark_cli_reports_run_directory_without_exposing_failure_details(tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(benchmark, "load_config", lambda _path: {})

    def fail_benchmark(*args, **kwargs):
        raise ValueError("private transcript-derived detail")

    monkeypatch.setattr(benchmark, "run_benchmark", fail_benchmark)
    code = main([
        "benchmark", "--config", "fixture.json", "--root", str(tmp_path),
        "--artifact-root", str(tmp_path / "evidence"), "--output-dir", str(tmp_path / "runs"),
    ])

    error = json.loads(capsys.readouterr().err)["error"]
    assert code == 2
    assert error["code"] == "benchmark_run_error"
    assert str(tmp_path / "runs" / "run-") in error["message"]
    assert "private transcript-derived detail" not in error["message"]
