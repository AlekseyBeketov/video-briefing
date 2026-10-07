from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

from .briefing import brief_bundle, render_brief
from .llm import OllamaClient
from .qa import answer_question
from .store import ArtifactStore
from . import __version__

EXPECTED_URL = "https://www.youtube.com/watch?v=DvSwvJVens8"
EXPECTED_ID = "DvSwvJVens8"


def load_config(path: str | Path) -> dict:
    config_path = Path(path).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    from .validation import parse_video_url
    _, video_id, canonical = parse_video_url(config.get("video_url", ""))
    if video_id != config.get("video_id") or video_id != EXPECTED_ID:
        raise ValueError(f"Benchmark target must be exactly {EXPECTED_ID}")
    if canonical != EXPECTED_URL:
        raise ValueError(f"Benchmark URL must be exactly {EXPECTED_URL}")
    if config.get("variant") not in {"baoyu", "summarize", "captions_api"}:
        raise ValueError("Benchmark variant must be baoyu, summarize, or captions_api")
    if not config.get("questions_file"):
        raise ValueError("Committed fixed questions_file is required; no synthetic fallback")
    config["_config_dir"] = str(config_path.parent)
    return config


def _questions(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    questions = payload.get("questions", payload.get("root", {}).get("questions")) if isinstance(payload, dict) else payload
    if not isinstance(questions, list) or not questions:
        raise ValueError("Evaluation question file must contain a non-empty questions list")
    if any(not isinstance(item, dict) or not item.get("question") for item in questions):
        raise ValueError("Every fixed evaluation item needs a question")
    return questions


def run_benchmark(config: dict, *, root: Path, artifact_root: Path) -> dict:
    variant = config["variant"]
    store = ArtifactStore(artifact_root)
    requested_language = config.get("languages", config.get("language", "ru")).split(",")[0].strip()
    bundle = store.find(EXPECTED_ID, variant, language=requested_language)
    extract_seconds = 0.0
    extractor_calls = 0
    if bundle is None:
        started = time.perf_counter()
        if variant == "baoyu":
            from .adapters.baoyu import extract
            bundle = extract(config["video_url"], languages=config.get("languages", "en,ru"), output_dir=root / ".tools/baoyu-cache")
        elif variant == "summarize":
            from .adapters.summarize import extract
            bundle = extract(config["video_url"], language=config.get("languages", config.get("language", "ru")).split(",")[0])
        else:
            from .adapters.captions_api import extract
            bundle = extract(config["video_url"], language=config.get("languages", "ru").split(",")[0])
        extract_seconds = time.perf_counter() - started
        store.save(bundle)
        extractor_calls += 1
    llm_settings = config["llm"]
    llm = OllamaClient(llm_settings["base_url"], llm_settings["model"], float(llm_settings["temperature"]), float(llm_settings.get("timeout_seconds", 300)))
    started = time.perf_counter()
    brief, llm_metadata = brief_bundle(bundle, llm)
    brief_seconds = time.perf_counter() - started
    configured_questions = Path(config["questions_file"])
    questions_path = configured_questions if configured_questions.is_absolute() else root / configured_questions
    if not questions_path.is_file():
        questions_path = Path(config["_config_dir"]) / configured_questions
    qa_results, qa_seconds = [], []
    for item in _questions(questions_path):
        started = time.perf_counter()
        answer = answer_question(bundle, item["question"], llm)
        qa_seconds.append(time.perf_counter() - started)
        qa_results.append({"id": item.get("id"), "question": item["question"], **answer})
    same_hash = store.find(EXPECTED_ID, variant, language=bundle.language)
    if same_hash is None or same_hash.raw_sha256 != bundle.raw_sha256:
        raise RuntimeError("Warm artifact reuse did not preserve the exact source hash")
    metrics = {
        "status": "completed", "target": EXPECTED_URL, "video_id": EXPECTED_ID, "variant": variant,
        "extractor_calls": extractor_calls, "source_type": bundle.source_type, "source_language": bundle.language,
        "source_sha256": bundle.raw_sha256, "timed_segments": len(bundle.segments),
        "measured_seconds": {"extract_cold": extract_seconds, "brief": brief_seconds, "qa_each": qa_seconds,
                             "total": extract_seconds + brief_seconds + sum(qa_seconds)},
        "warm_source_reuse": {"cache_hit": True, "same_source_hash": True, "extractor_calls": 0},
        "model": llm_metadata, "runtime": {"python": __import__("sys").version, "package": __version__},
        "questions_n": len(qa_results), "usage": {"prompt_tokens": llm_metadata.get("prompt_tokens"), "completion_tokens": llm_metadata.get("completion_tokens")},
    }
    return {"metrics": metrics, "briefing": brief, "briefing_markdown": render_brief(brief), "answers": qa_results}


def write_run(result: dict, output_dir: Path) -> dict[str, Path]:
    """Persist the machine-readable result and human-readable output atomically."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "metrics": output_dir / "metrics.json",
        "briefing": output_dir / "briefing.md",
        "answers": output_dir / "answers.json",
    }
    payloads = {
        "metrics": json.dumps(result["metrics"], ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        "briefing": result["briefing_markdown"],
        "answers": json.dumps(result["answers"], ensure_ascii=False, sort_keys=True, indent=2) + "\n",
    }
    for name, path in paths.items():
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(payloads[name], encoding="utf-8")
        temporary.replace(path)
    return paths
