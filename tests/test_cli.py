import json
from importlib.metadata import PackageNotFoundError
from types import SimpleNamespace

import video_briefing.cli as cli
from video_briefing.cli import _llm, build_parser, main


def test_cli_exposes_workflow_commands():
    parser = build_parser()
    assert set(parser._subparsers._group_actions[0].choices) == {
        "doctor", "extract", "ingest", "search", "read", "skill", "brief", "ask", "benchmark"
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
    monkeypatch.setattr(cli.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0))

    code = main(["doctor"])

    report = json.loads(capsys.readouterr().out)
    assert report["youtube_transcript_api"] == {"available": False}
    assert code == 1


def test_doctor_keeps_zero_status_when_only_optional_local_asr_tools_are_missing(monkeypatch, capsys):
    monkeypatch.setattr(cli, "package_version", lambda _name: "1.2.3")
    monkeypatch.setattr(cli.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=1))

    code = main(["doctor"])

    report = json.loads(capsys.readouterr().out)
    assert report["youtube_transcript_api"] == {"available": True, "version": "1.2.3"}
    assert report["local_asr_tools"]["ffmpeg"]["available"] is False
    assert code == 0
