from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
from urllib.request import urlopen

from . import __version__
from .briefing import brief_bundle, render_brief
from .llm import OllamaClient
from .qa import answer_question
from .store import ArtifactStore
from .validation import parse_video_url

BAOYU_DIR = Path(os.environ.get("VIDEO_BRIEFING_BAOYU", Path.home() / ".hermes/skills/media/baoyu-youtube-transcript")).expanduser()

DEFAULT_STORE = Path("artifacts/private/evidence")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="video-briefing", description="Evidence-first video briefing and cached Q&A")
    subparsers = parser.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Check configured model endpoint and local extractor runtimes")
    doctor.add_argument("--config", default="config/experiment.json")
    doctor.set_defaults(handler=_doctor)

    extract = subparsers.add_parser("extract", help="Extract and persist timed source evidence")
    extract.add_argument("url")
    extract.add_argument("--variant", choices=("baoyu", "summarize", "captions_api"), required=True)
    extract.add_argument("--languages", default="ru")
    extract.add_argument("--store", type=Path, default=DEFAULT_STORE)
    extract.set_defaults(handler=_extract_command)

    brief = subparsers.add_parser("brief", help="Create a Russian briefing from cached or newly extracted evidence")
    _add_video_options(brief)
    brief.add_argument("--json", action="store_true", help="Emit structured JSON including citations and model metadata")
    brief.set_defaults(handler=_brief)

    ask = subparsers.add_parser("ask", help="Answer a question from saved transcript evidence without re-extraction")
    ask.add_argument("url")
    ask.add_argument("question")
    ask.add_argument("--variant", choices=("baoyu", "summarize", "captions_api"), required=True)
    ask.add_argument("--languages", default="ru", help="Source language required for cache lookup (default: ru)")
    ask.add_argument("--store", type=Path, default=DEFAULT_STORE)
    ask.add_argument("--config", default="config/experiment.json")
    ask.set_defaults(handler=_ask)

    benchmark = subparsers.add_parser("benchmark", help="Run the committed fixed-target cold/warm workflow")
    benchmark.add_argument("--config", default="config/experiment.json")
    benchmark.add_argument("--root", type=Path, default=Path.cwd())
    benchmark.add_argument("--artifact-root", type=Path, default=DEFAULT_STORE)
    benchmark.add_argument("--output-dir", type=Path, default=Path("artifacts/private/runs"))
    benchmark.set_defaults(handler=_benchmark)
    return parser


def _add_video_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("url")
    parser.add_argument("--variant", choices=("baoyu", "summarize", "captions_api"), required=True)
    parser.add_argument("--languages", default="ru")
    parser.add_argument("--store", type=Path, default=DEFAULT_STORE)
    parser.add_argument("--config", default="config/experiment.json")


def _load_config(path: str | Path) -> tuple[dict, Path]:
    config_path = Path(path).expanduser().resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    return config, config_path.parent


def _llm(config: dict) -> OllamaClient:
    settings = config.get("llm", {})
    if settings.get("provider", "ollama") != "ollama":
        raise ValueError("Only the explicitly configured Ollama provider is supported")
    return OllamaClient(
        settings.get("base_url", "http://127.0.0.1:11434"),
        settings.get("model", "gemma4:31b-cloud"),
        float(settings.get("temperature", 0)),
        float(settings.get("timeout_seconds", 300)),
    )


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
        bundle = extract_baoyu(url, languages=languages, output_dir=Path(".tools/baoyu-cache"))
    elif variant == "summarize":
        from .adapters.summarize import extract as extract_summarize
        bundle = extract_summarize(url, language=languages.split(",")[0])
    else:
        from .adapters.captions_api import extract as extract_captions
        bundle = extract_captions(url, language=languages.split(",")[0])
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
    config, _ = _load_config(args.config)
    settings = config.get("llm", {})
    report = {
        "version": __version__,
        "python": sys.version.split()[0],
        "ollama": {"base_url": settings.get("base_url", "http://127.0.0.1:11434"), "model": settings.get("model", "gemma4:31b-cloud"), "cloud_backed": settings.get("cloud_backed", True)},
        "extractors": {
            "baoyu_skill": {"available": (BAOYU_DIR / "scripts/main.ts").is_file(), "path": str(BAOYU_DIR / "scripts/main.ts")},
            "bun": _tool_version(Path(os.environ.get("VIDEO_BRIEFING_BUN", ".tools/bun/node_modules/.bin/bun")).expanduser()),
            "summarize": _tool_version(Path(os.environ.get("VIDEO_BRIEFING_SUMMARIZE", ".tools/summarize/summarize")).expanduser()),
        },
    }
    try:
        with urlopen(f"{report['ollama']['base_url'].rstrip('/')}/api/tags", timeout=5):
            report["ollama"]["reachable"] = True
    except Exception as exc:
        report["ollama"]["reachable"] = False
        report["ollama"]["error"] = str(exc)
    try:
        report["extractors"]["captions_api"] = {"available": True, "version": package_version("youtube-transcript-api")}
    except PackageNotFoundError:
        report["extractors"]["captions_api"] = {"available": False, "error": "Install project dependencies with `uv sync --frozen`"}
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ollama"]["reachable"] and report["extractors"]["captions_api"]["available"] else 2


def _extract_command(args: argparse.Namespace) -> int:
    bundle = _run_extractor(args.url, args.variant, args.languages, ArtifactStore(args.store))
    print(json.dumps({"status": "saved", "video_id": bundle.video_id, "language": bundle.language, "variant": bundle.variant, "source_type": bundle.source_type, "segments": len(bundle.segments), "source_sha256": bundle.raw_sha256}, ensure_ascii=False, indent=2))
    return 0


def _brief(args: argparse.Namespace) -> int:
    config, _ = _load_config(args.config)
    bundle = _get_bundle(args.url, args.variant, args.languages, ArtifactStore(args.store), extract_if_missing=True)
    llm = _llm(config)
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
    llm = _llm(config)
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
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
