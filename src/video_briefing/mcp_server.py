"""Optional MCP stdio interface; evidence stays local and no LLM is invoked."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from typing import Any

from .evidence_api import read_evidence as _read_evidence, search_evidence as _search_evidence
from .citation_validation import validate_citations
from .local_asr import ingest_local_video
from .models import EvidenceBundle
from .store import ArtifactStore
from .validation import parse_video_url


def _store() -> ArtifactStore:
    override = os.environ.get("VIDEO_BRIEFING_DATA_HOME")
    if override:
        root = Path(override).expanduser()
    elif os.name == "nt":
        root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "VideoBriefing"
    elif os.uname().sysname == "Darwin":
        root = Path.home() / "Library/Application Support/VideoBriefing"
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "video-briefing"
    return ArtifactStore(root / "evidence")


def _bundle(bundle: EvidenceBundle) -> dict[str, Any]:
    return {"status": "ok", "source_type": bundle.source_type, "video_id": bundle.video_id,
            "variant": bundle.variant, "language": bundle.language,
            "segment_count": len(bundle.segments), "raw_sha256": bundle.raw_sha256,
            "time_range_seconds": [min((s.start_seconds for s in bundle.segments), default=0),
                                   max((s.start_seconds + s.duration_seconds for s in bundle.segments), default=0)]}


def _load(source: str, variant: str | None = None, language: str | None = None) -> EvidenceBundle:
    if re.fullmatch(r"[0-9a-f]{64}", source):
        source_type, video_id = "local-file", source
        variant = variant or "local_asr"
    else:
        source_type, video_id, _ = parse_video_url(source)
        variant = variant or "captions_api"
    bundle = _store().find(video_id, variant, language=language)
    if bundle is None or bundle.platform != source_type:
        raise ValueError("no matching evidence is cached; ingest the source first")
    return bundle


def _safe_call(operation):
    try:
        return operation()
    except ValueError as exc:
        return {"status": "error", "error": {"code": "invalid_input", "message": str(exc)}}
    except (FileNotFoundError, TimeoutError) as exc:
        return {"status": "error", "error": {"code": "source_unavailable", "message": str(exc)}}
    except Exception:
        return {"status": "error", "error": {"code": "operation_failed", "message": "Operation failed; no source text was included."}}


def create_server():
    """Build an MCPServer instance. Importing this module does not require the optional SDK."""
    try:
        from mcp.server import MCPServer
    except ImportError as exc:
        raise RuntimeError("MCP support is optional; install video-briefing[mcp]") from exc

    server = MCPServer("Video Briefing")

    @server.tool()
    def ingest_youtube(url: str, language: str = "ru") -> dict[str, Any]:
        """Fetch public YouTube caption evidence using youtube-transcript-api; never generates an answer."""
        def operation():
            _, _, canonical = parse_video_url(url)
            from .adapters.captions_api import extract
            bundle = extract(canonical, language=language)
            _store().save(bundle)
            return _bundle(bundle)
        return _safe_call(operation)

    @server.tool()
    def ingest_local_mp4(path: str, language: str = "ru", timeout_seconds: int = 21600) -> dict[str, Any]:
        """Run local-only ASR for an explicit MP4 path. Audio and transcript are not uploaded."""
        def operation():
            if language.casefold() != "ru":
                raise ValueError("the configured local ASR model supports Russian only")
            transcribe_cli = os.environ.get("VIDEO_BRIEFING_TRANSCRIBE")
            model_path = os.environ.get("VIDEO_BRIEFING_ASR_MODEL")
            if not transcribe_cli or not model_path:
                raise ValueError("configure VIDEO_BRIEFING_TRANSCRIBE and VIDEO_BRIEFING_ASR_MODEL before local ASR")
            store = _store()
            bundle = ingest_local_video(
                Path(path), ffmpeg=os.environ.get("VIDEO_BRIEFING_FFMPEG", "ffmpeg"),
                ffprobe=os.environ.get("VIDEO_BRIEFING_FFPROBE", "ffprobe"),
                transcribe_cli=transcribe_cli, model_path=Path(model_path),
                work_root=store.root.parent / "work", timeout_seconds=timeout_seconds,
            )
            store.save(bundle)
            return _bundle(bundle)
        return _safe_call(operation)

    @server.tool()
    def search_video_evidence(source: str, query: str, language: str | None = None,
                              variant: str | None = None, limit: int = 12) -> dict[str, Any]:
        """Search stored caption/ASR segments and return bounded verbatim evidence with times."""
        return _safe_call(lambda: _search_evidence(_load(source, variant, language), query, limit))

    @server.tool()
    def read_video_evidence(source: str, start_seconds: float, end_seconds: float,
                            language: str | None = None, variant: str | None = None,
                            max_segments: int = 20) -> dict[str, Any]:
        """Read bounded verbatim evidence for a time range; no model synthesis is performed."""
        return _safe_call(lambda: _read_evidence(_load(source, variant, language), start_seconds,
                                                 end_seconds, max_segments=max_segments))

    @server.tool()
    def validate_video_claims(source: str, claims: list[dict], language: str | None = None,
                              variant: str | None = None) -> dict[str, Any]:
        """Check literal quotes, source/segment IDs and exact bounds; NOT semantic truth or entailment."""
        return _safe_call(lambda: validate_citations(_load(source, variant, language), claims))

    return server


def main() -> int:
    try:
        server = create_server()
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    server.run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
