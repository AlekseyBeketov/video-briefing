import json

from video_briefing.llm import _parse_json_object


def test_parse_fenced_provider_json_with_bare_citation_ids_only():
    parsed = _parse_json_object('```json\n{"gist":"s00042 remains text","evidence":[s00001, s00002]}\n```')
    assert parsed == {"gist": "s00042 remains text", "evidence": ["s00001", "s00002"]}


def test_parse_provider_latex_backslash_without_corrupting_json_escapes():
    source = {"text": r"30 GB \approx 30 GB", "evidence": ["s00001"]}
    valid_escaped = json.dumps(source)
    invalid_single_slash = valid_escaped.replace(r"\\approx", r"\approx").replace('"s00001"', "s00001")
    assert _parse_json_object(invalid_single_slash) == source
    assert _parse_json_object(valid_escaped) == source
