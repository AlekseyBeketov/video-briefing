from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from importlib.metadata import PackageNotFoundError, version as package_version
from importlib.resources import files
from pathlib import Path

from . import __version__
from .briefing import brief_bundle, render_brief
from .evidence_api import read_evidence, search_evidence
from .llm import OllamaClient
from .qa import answer_question
from .store import ArtifactStore
from .validation import parse_video_url

def _default_data_home() -> Path:
    override = os.environ.get("VIDEO_BRIEFING_DATA_HOME")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "VideoBriefing"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/VideoBriefing"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "video-briefing"


DEFAULT_STORE = _default_data_home() / "evidence"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="video-briefing", description="Evidence-first video briefing and cached Q&A")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check local package and optional extractor availability without network probes")
    doctor.add_argument("--config", default="config/experiment.json", help=argparse.SUPPRESS)
    doctor.set_defaults(handler=_doctor)

    extract = subparsers.add_parser("extract", help="Fetch timed YouTube captions and persist source evidence")
    extract.add_argument("url")
    extract.add_argument("--variant", choices=("baoyu", "captions_api"), default="captions_api")
    extract.add_argument("--languages", default="ru")
    extract.add_argument("--store", type=Path, default=DEFAULT_STORE)
    extract.set_defaults(handler=_extract_command)

    ingest = subparsers.add_parser("ingest", help="Ingest YouTube captions or a local MP4 using explicit local ASR")
    ingest.add_argument("source", help="YouTube URL/ID or local MP4 path")
    ingest.add_argument("--variant", choices=("baoyu", "captions_api"), default="captions_api")
    ingest.add_argument("--languages", default="ru")
    ingest.add_argument("--local-asr", action="store_true", help="Allow local-only ASR for an MP4 path")
    ingest.add_argument("--ffmpeg", default=os.environ.get("VIDEO_BRIEFING_FFMPEG", "ffmpeg"))
    ingest.add_argument("--ffprobe", default=os.environ.get("VIDEO_BRIEFING_FFPROBE", "ffprobe"))
    ingest.add_argument("--transcribe-cli", default=os.environ.get("VIDEO_BRIEFING_TRANSCRIBE", ""))
    ingest.add_argument("--model", default=os.environ.get("VIDEO_BRIEFING_ASR_MODEL", ""))
    ingest.add_argument("--timeout-seconds", type=float, default=21600)
    ingest.add_argument("--threads", type=int)
    ingest.add_argument("--store", type=Path, default=DEFAULT_STORE)
    ingest.set_defaults(handler=_ingest)

    search = subparsers.add_parser("search", help="Return bounded timed evidence; synthesis is the caller agent's task")
    search.add_argument("source", help="Cached YouTube URL/ID or local media SHA-256")
    search.add_argument("query")
    search.add_argument("--variant", choices=("baoyu", "captions_api", "local_asr"), default="captions_api")
    search.add_argument("--language", default="ru")
    search.add_argument("--limit", type=int, default=12)
    search.add_argument("--store", type=Path, default=DEFAULT_STORE)
    search.set_defaults(handler=_search)

    read = subparsers.add_parser("read", help="Read cached source evidence in a bounded time interval")
    read.add_argument("source", help="Cached YouTube URL/ID or local media SHA-256")
    read.add_argument("start_seconds", type=float)
    read.add_argument("end_seconds", type=float)
    read.add_argument("--variant", choices=("baoyu", "captions_api", "local_asr"), default="captions_api")
    read.add_argument("--language", default="ru")
    read.add_argument("--limit", type=int, default=50)
    read.add_argument("--store", type=Path, default=DEFAULT_STORE)
    read.set_defaults(handler=_read)

    skill = subparsers.add_parser("skill", help="Print the packaged portable agent skill")
    skill.set_defaults(handler=_skill)

    brief = subparsers.add_parser("brief", help="Optional model-generated brief (requires explicit privacy opt-in)")
    _add_video_options(brief)
    brief.add_argument("--allow-cloud", action="store_true", help="Explicitly allow sending source excerpts to a configured cloud model")
    brief.add_argument("--json", action="store_true", help="Emit structured JSON including citations and model metadata")
    brief.set_defaults(handler=_brief)

    ask = subparsers.add_parser("ask", help="Optional model-generated Q&A (requires explicit privacy opt-in)")
    ask.add_argument("url")
    ask.add_argument("question")
    ask.add_argument("--variant", choices=("baoyu", "captions_api"), default="captions_api")
    ask.add_argument("--languages", default="ru", help="Source language required for cache lookup (default: ru)")
    ask.add_argument("--store", type=Path, default=DEFAULT_STORE)
    ask.add_argument("--config", default="config/experiment.json")
    ask.add_argument("--allow-cloud", action="store_true", help="Explicitly allow sending question/excerpts to a configured cloud model")
    ask.set_defaults(handler=_ask)

    benchmark = subparsers.add_parser("benchmark", help="Run the committed fixed-target cold/warm workflow")
    benchmark.add_argument("--config", default="config/experiment.json")
    benchmark.add_argument("--root", type=Path, default=Path.cwd())
    benchmark.add_argument("--artifact-root", type=Path, default=DEFAULT_STORE)
    benchmark.add_argument("--output-dir", type=Path, default=_default_data_home() / "runs")
    benchmark.set_defaults(handler=_benchmark)
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def _add_video_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("url")
    parser.add_argument("--variant", choices=("baoyu", "captions_api"), required=True)
    parser.add_argument("--languages", default="ru")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--config", default="config/experiment.json")


def _load_config(path: str | Path) -> tuple[dict, Path]:
    config_path = Path(path).expanduser().resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    return config, config_path.parent


def _llm(config: dict, *, allow_cloud: bool = False) -> OllamaClient:
    from urllib.parse import urlsplit
    from ipaddress import ip_address

    settings = config.get("llm", {})
    if settings.get("provider", "ollama") != "ollama":
        raise ValueError("Only explicitly configured Ollama is supported")
    base_url = settings.get("base_url", "http://127.0.0.1:11434")
    parsed = urlsplit(base_url)
    try:
        _ = parsed.port
    except ValueError as exc:
        raise ValueError("Model endpoint must have a valid port") from exc
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password
            or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
        raise ValueError("Model endpoint must be a credential-free HTTP(S) origin")
    try:
        local = parsed.hostname.casefold() == "localhost" or ip_address(parsed.hostname).is_loopback
    except ValueError:
        local = False
    cloud_backed = bool(settings.get("cloud_backed", not local)) or not local
    if cloud_backed and not allow_cloud:
        raise PermissionError("Configured model may be cloud-backed; pass --allow-cloud only after approving transcript disclosure")
    if not local and not allow_cloud:
        raise PermissionError("Non-loopback model endpoint requires explicit --allow-cloud privacy approval")
    return OllamaClient(base_url, settings.get("model", ""), float(settings.get("temperature", 0)),
                        float(settings.get("timeout_seconds", 300)))


def _tool_version(path: Path) -> dict:
    if not path.is_file():
        return {"available": False, "path": str(path)}
    try:
        result = subprocess.run([str(path), "--version"], capture_output=True, text=True, timeout=15, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"available": False, "path": str(path), "error": f"{type(exc).__name__}: {exc}"}
    return {"available": result.returncode == 0, "path": str(path),
            "version": (result.stdout.strip() or result.stderr.strip()), "exit_code": result.returncode}


def _run_extractor(url: str, variant: str, languages: str, store: ArtifactStore):
    platform, video_id, _ = parse_video_url(url)
    if variant == "baoyu":
        from .adapters.baoyu import extract as extract_baoyu
        bundle = extract_baoyu(url, languages=languages, output_dir=_default_data_home() / "extractor-cache" / "baoyu")
    elif variant == "captions_api":
        from .adapters.captions_api import extract as extract_captions
        bundle = extract_captions(url, language=languages.split(",")[0])
    else:
        raise ValueError(f"Unsupported extractor variant: {variant}")
    if bundle.platform != platform or bundle.video_id != video_id:
        raise ValueError("Extractor output identity does not match requested video")
    return store.save(bundle)


def _get_bundle(url: str, variant: str, languages: str, store: ArtifactStore, *, extract_if_missing: bool):
    _, video_id, _ = parse_video_url(url)
    requested_language = languages.split(",")[0].strip()
    bundle = store.find(video_id, variant, language=requested_language)
    if bundle is None:
        if not extract_if_missing:
            raise FileNotFoundError("No saved evidence bundle; run `video-briefing extract` first")
        bundle = _run_extractor(url, variant, languages, store)
    return bundle


def _doctor(args: argparse.Namespace) -> int:
    del args
    report = {"version": __version__, "python": sys.version.split()[0],
              "data_home": str(_default_data_home()), "store": str(DEFAULT_STORE),
              "network_probes": False, "model_inference": False,
              "youtube_transcript_api": None, "local_asr_tools": {}}
    try:
        report["youtube_transcript_api"] = {"available": True, "version": package_version("youtube-transcript-api")}
    except PackageNotFoundError:
        report["youtube_transcript_api"] = {"available": False}
    for name in ("ffmpeg", "ffprobe"):
        path = os.environ.get("VIDEO_BRIEFING_FFMPEG" if name == "ffmpeg" else "VIDEO_BRIEFING_FFPROBE", name)
        try:
            available = subprocess.run([path, "-version"], capture_output=True, timeout=10).returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            available = False
        report["local_asr_tools"][name] = {"available": available}
    for name, variable in (("transcribe_cli", "VIDEO_BRIEFING_TRANSCRIBE"), ("model", "VIDEO_BRIEFING_ASR_MODEL")):
        path = os.environ.get(variable, "")
        report["local_asr_tools"][name] = {"configured": bool(path), "available": bool(path and Path(path).is_file())}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _extract_command(args: argparse.Namespace) -> int:
    bundle = _run_extractor(args.url, args.variant, args.languages, ArtifactStore(args.store))
    print(json.dumps({"status": "saved", "video_id": bundle.video_id, "language": bundle.language, "variant": bundle.variant, "source_type": bundle.source_type, "segments": len(bundle.segments), "source_sha256": bundle.raw_sha256}, ensure_ascii=False, indent=2))
    return 0


def _ingest(args: argparse.Namespace) -> int:
    store = ArtifactStore(args.store)
    source = args.source.strip()
    if "://" in source or re.fullmatch(r"[A-Za-z0-9_-]{11}", source):
        platform, _, _ = parse_video_url(source)
        bundle = _run_extractor(source, args.variant, args.languages, store)
        report = {"status": "saved", "platform": platform, "video_id": bundle.video_id,
                  "language": bundle.language, "variant": bundle.variant,
                  "source_type": bundle.source_type, "segments": len(bundle.segments),
                  "source_sha256": bundle.raw_sha256, "provenance": bundle.extractor_version}
    else:
        if not args.local_asr:
            raise PermissionError("local MP4 ingestion requires explicit --local-asr opt-in")
        if not args.transcribe_cli or not args.model:
            raise ValueError("local ASR requires --transcribe-cli and --model local file paths")
        from .local_asr import ingest_local_video
        bundle = ingest_local_video(source, ffmpeg=args.ffmpeg, ffprobe=args.ffprobe,
                                    transcribe_cli=args.transcribe_cli, model_path=args.model,
                                    work_root=_default_data_home() / "work",
                                    timeout_seconds=args.timeout_seconds, threads=args.threads)
        bundle = store.save(bundle)
        report = {"status": "saved", "platform": bundle.platform, "video_id": bundle.video_id,
                  "variant": bundle.variant, "source_type": bundle.source_type,
                  "source_sha256": bundle.raw_sha256, "media_sha256": bundle.metadata["media_sha256"],
                  "audio_duration_seconds": bundle.metadata["audio_duration_seconds"],
                  "processed_audio_seconds": bundle.metadata["processed_audio_seconds"],
                  "chunk_count": bundle.metadata["chunk_count"],
                  "nonempty_transcript_chunks": bundle.metadata["nonempty_transcript_chunks"],
                  "timing_precision": bundle.metadata["timing_precision"],
                  "privacy": bundle.metadata["privacy"]}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def _load_saved(source: str, variant: str, language: str, store: ArtifactStore):
    if re.fullmatch(r"[0-9a-f]{64}", source):
        video_id = source
        if variant == "captions_api":
            variant = "local_asr"
    else:
        _, video_id, _ = parse_video_url(source)
    bundle = store.find(video_id, variant, language=language)
    if bundle is None:
        raise FileNotFoundError("No saved evidence for this source; run `video-briefing ingest` first")
    return bundle


def _search(args: argparse.Namespace) -> int:
    bundle = _load_saved(args.source, args.variant, args.language, ArtifactStore(args.store))
    print(json.dumps(search_evidence(bundle, args.query, args.limit), ensure_ascii=False, indent=2))
    return 0


def _read(args: argparse.Namespace) -> int:
    bundle = _load_saved(args.source, args.variant, args.language, ArtifactStore(args.store))
    result = read_evidence(bundle, args.start_seconds, args.end_seconds, max_segments=args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _skill(args: argparse.Namespace) -> int:
    del args
    print(files("video_briefing.resources").joinpath("SKILL.md").read_text(encoding="utf-8"), end="")
    return 0


def _brief(args: argparse.Namespace) -> int:
    config, _ = _load_config(args.config)
    bundle = _get_bundle(args.url, args.variant, args.languages, ArtifactStore(args.store), extract_if_missing=True)
    llm = _llm(config, allow_cloud=args.allow_cloud)
    started = time.perf_counter()
    result, metadata = brief_bundle(bundle, llm)
    metadata["elapsed_seconds"] = time.perf_counter() - started
    metadata["inference_calls"] = list(llm.responses)
    metadata["usage_complete"] = all(call.get("prompt_tokens") is not None and call.get("completion_tokens") is not None for call in llm.responses)
    result["model"] = metadata
    if args.json:
        print(json.dumps({"briefing": result, "model": metadata, "markdown": render_brief(result)}, ensure_ascii=False, indent=2))
    else:
        print(render_brief(result))
    return 0


def _ask(args: argparse.Namespace) -> int:
    config, _ = _load_config(args.config)
    bundle = _get_bundle(args.url, args.variant, args.languages, ArtifactStore(args.store), extract_if_missing=False)
    llm = _llm(config, allow_cloud=args.allow_cloud)
    started = time.perf_counter()
    result = answer_question(bundle, args.question, llm)
    result.update({
        "source": {"video_id": bundle.video_id, "language": bundle.language, "variant": bundle.variant,
                   "source_sha256": bundle.raw_sha256, "segments": len(bundle.segments),
                   "extractor_version": bundle.extractor_version},
        "model": {"requested_model": llm.model, "returned_model": llm.last_response.get("model"),
                  "cloud_backed": llm.model.endswith("-cloud"), "inference_calls": llm.responses,
                  "usage_complete": all(call.get("prompt_tokens") is not None and call.get("completion_tokens") is not None for call in llm.responses)},
        "elapsed_seconds": time.perf_counter() - started,
    })
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _benchmark(args: argparse.Namespace) -> int:
    from .benchmark import load_config, run_benchmark, write_run
    config = load_config(args.config)
    output_dir = args.output_dir.resolve()
    result = run_benchmark(config, root=args.root.resolve(), artifact_root=args.artifact_root.resolve(), progress_dir=output_dir)
    paths = write_run(result, output_dir)
    print(json.dumps({"status": result["metrics"]["status"], "variant": result["metrics"]["variant"], "source_sha256": result["metrics"]["source_sha256"], "paths": {name: str(path) for name, path in paths.items()}}, ensure_ascii=False, indent=2))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.handler(args)
    except Exception as exc:
        safe_types = (ValueError, PermissionError, FileNotFoundError, TimeoutError, RuntimeError)
        message = str(exc)[:500] if isinstance(exc, safe_types) else "The operation failed; see local diagnostics."
        code = re.sub(r"(?<!^)(?=[A-Z])", "_", type(exc).__name__).lower()
        print(json.dumps({"error": {"code": code, "message": message}}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
