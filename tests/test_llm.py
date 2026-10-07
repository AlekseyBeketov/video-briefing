from video_briefing.llm import _parse_json_object


def test_parse_fenced_provider_json_with_bare_citation_ids_only():
    parsed = _parse_json_object('```json\n{"gist":"s00042 remains text","evidence":[s00001, s00002]}\n```')
    assert parsed == {"gist": "s00042 remains text", "evidence": ["s00001", "s00002"]}
