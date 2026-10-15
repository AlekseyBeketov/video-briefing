from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

from video_briefing.models import EvidenceBundle, TranscriptSegment
from video_briefing.store import ArtifactStore
from video_briefing.adapters.captions_api import (
    CaptionAuthenticationRequired,
    CaptionSourceBlocked,
    CaptionSourceUnavailable,
)
from video_briefing.local_asr import LocalASRError
import video_briefing.mcp_server as mcp_server
from video_briefing.mcp_server import _safe_call

try:
    from mcp import Client
    from mcp.client.stdio import StdioServerParameters
except ImportError:
    pytest.skip("install video-briefing[mcp] for MCP integration tests", allow_module_level=True)


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (CaptionSourceUnavailable("No captions available"), "source_unavailable"),
        (CaptionSourceBlocked("Request blocked"), "source_blocked"),
        (CaptionAuthenticationRequired("Authentication required"), "source_auth_required"),
        (LocalASRError("Invalid local audio"), "source_processing_failed"),
    ],
)
def test_safe_call_preserves_safe_source_error_categories(error, code):
    def fail():
        raise error

    result = _safe_call(fail)

    assert result == {"status": "error", "error": {"code": code, "message": str(error)}}


def test_safe_call_hides_unexpected_exception_details():
    def fail():
        raise RuntimeError("private internal detail")

    result = _safe_call(fail)

    assert result == {
        "status": "error",
        "error": {"code": "operation_failed", "message": "Operation failed; no source text was included."},
    }


def test_cli_and_mcp_use_identical_default_data_home(tmp_path, monkeypatch):
    from video_briefing.cli import _default_data_home
    from video_briefing.mcp_server import _store

    monkeypatch.delenv("VIDEO_BRIEFING_DATA_HOME", raising=False)
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: tmp_path))
    assert _store().root == _default_data_home() / "evidence"


def test_mcp_local_ingest_passes_spoken_language_to_managed_asr(tmp_path, monkeypatch):
    calls = {}
    stored = []
    bundle = SimpleNamespace(
        source_type="local-asr-chunk-transcript", video_id="media-id", variant="local_asr",
        language="en", segments=[], raw_sha256="evidence-hash", metadata={},
    )

    class Store:
        root = tmp_path / "evidence"

        def save(self, value):
            stored.append(value)

    monkeypatch.setattr(mcp_server, "_store", lambda: Store())
    monkeypatch.setattr(
        mcp_server, "ingest_local_video",
        lambda path, **kwargs: calls.update(path=path, **kwargs) or bundle,
    )
    for name in ("VIDEO_BRIEFING_TRANSCRIBE", "VIDEO_BRIEFING_ASR_MODEL"):
        monkeypatch.delenv(name, raising=False)

    report = mcp_server._ingest_local_mp4("/private/example.mp4", "en", 120)

    assert calls["language"] == "en"
    assert calls["data_home"] == tmp_path
    assert calls["timeout_seconds"] == 120
    assert stored == [bundle]
    assert report["language"] == "en"
    assert report["status"] == "ok"


def _save_fixture(root: Path) -> str:
    raw_text = json.dumps([{"text": "Evidence fixture phrase.", "start": 1.0, "duration": 2.0}])
    digest = hashlib.sha256(raw_text.encode()).hexdigest()
    bundle = EvidenceBundle(
        platform="youtube", video_id="AbCdEf12345",
        url="https://www.youtube.com/watch?v=AbCdEf12345", language="en",
        variant="captions_api", source_type="manual-captions", extractor_version="fixture",
        segments=[TranscriptSegment("s1", "Evidence fixture phrase.", 1.0, 2.0)],
        raw_sha256=digest, raw_text=raw_text,
    )
    ArtifactStore(root / "evidence").save(bundle)
    return bundle.url


@pytest.mark.anyio
async def test_mcp_stdio_exposes_bounded_evidence_tools_and_roundtrips(tmp_path, monkeypatch):
    source = _save_fixture(tmp_path)
    package_cli = shutil.which("video-briefing-mcp")
    assert package_cli, "install the MCP extra to run the stdio integration test"
    parameters = StdioServerParameters(
        command=package_cli, args=[], cwd=tmp_path,
        env={"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", ""),
             "VIDEO_BRIEFING_DATA_HOME": str(tmp_path)},
    )
    async with Client(parameters) as client:  # type: ignore[arg-type]
        tools = await client.list_tools()
        names = {tool.name for tool in tools.tools}
        assert names == {"ingest_youtube", "ingest_local_mp4", "search_video_evidence", "read_video_evidence", "validate_video_claims"}
        result = await client.call_tool("search_video_evidence", {"source": source, "query": "fixture"})
        assert not result.is_error
        content = result.structured_content
        assert content is not None
        assert content["evidence"][0]["start_seconds"] == 1.0
        assert len(content["evidence"]) == 1
        checked = await client.call_tool("validate_video_claims", {"source": source, "claims": [{
            "claim": "The fixture contains a phrase.", "segment_ids": ["s1"],
            "start_seconds": 1.0, "end_seconds": 3.0, "quote": "Evidence fixture phrase.",
        }]})
        assert checked.structured_content["status"] == "valid"
        assert checked.structured_content["semantic_support_checked"] is False


@pytest.mark.anyio
async def test_mcp_rejects_untrusted_url_input_without_network(tmp_path):
    package_cli = shutil.which("video-briefing-mcp")
    assert package_cli
    parameters = StdioServerParameters(
        command=package_cli, args=[], cwd=tmp_path,
        env={"PATH": os.environ.get("PATH", ""), "HOME": os.environ.get("HOME", ""),
             "VIDEO_BRIEFING_DATA_HOME": str(tmp_path)},
    )
    async with Client(parameters) as client:  # type: ignore[arg-type]
        result = await client.call_tool("search_video_evidence", {
            "source": "http://127.0.0.1:8080/private", "query": "fixture",
        })
        assert not result.is_error
        content = result.structured_content
        assert content is not None
        assert content["status"] == "error"
        assert content["error"]["code"] == "invalid_input"
