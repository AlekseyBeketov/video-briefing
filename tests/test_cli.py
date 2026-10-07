from video_briefing.cli import build_parser


def test_cli_exposes_workflow_commands():
    parser = build_parser()
    assert set(parser._subparsers._group_actions[0].choices) == {"doctor", "extract", "brief", "ask", "benchmark"}
