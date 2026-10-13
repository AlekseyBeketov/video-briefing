import json

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
