from video_briefing.cli import build_parser


def test_cli_exposes_workflow_commands():
    parser = build_parser()
    assert set(parser._subparsers._group_actions[0].choices) == {"doctor", "extract", "brief", "ask", "benchmark"}
    brief = parser._subparsers._group_actions[0].choices["brief"]
    assert any(action.dest == "json" for action in brief._actions)
    ask = parser._subparsers._group_actions[0].choices["ask"]
    assert any(action.dest == "languages" for action in ask._actions)
