from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
RESOURCE_PAIRS = (
    ("skills/video-briefing/SKILL.md", "SKILL.md"),
    ("prompts/brief.md", "brief.md"),
    ("prompts/qa.md", "qa.md"),
)


@pytest.mark.parametrize(("source_path", "resource_name"), RESOURCE_PAIRS)
def test_packaged_resource_matches_repository_copy(source_path: str, resource_name: str) -> None:
    source = (REPOSITORY_ROOT / source_path).read_bytes()
    packaged = files("video_briefing.resources").joinpath(resource_name).read_bytes()

    assert packaged == source
