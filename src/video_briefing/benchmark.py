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
SUPPORTED_VARIANTS = frozenset({"baoyu", "captions_api"})


def load_config(path: str | Path) -> dict:
    config_path = Path(path).resolve()
    config = json.loads(config_path.read_text(encoding="utf-8"))
    from .validation import parse_video_url
    _, video_id, canonical = parse_video_url(config.get("video_url", ""))
    if video_id != config.get("video_id") or video_id != EXPECTED_ID:
        raise ValueError(f"Benchmark target must be exactly {EXPECTED_ID}")
    if canonical != EXPECTED_URL:
        raise ValueError(f"Benchmark URL must be exactly {EXPECTED_URL}")
    if config.get("variant") not in SUPPORTED_VARIANTS:
        raise ValueError("Benchmark variant must be baoyu or captions_api")
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


def _save_progress(output_dir: Path | None, progress: dict) -> None:
    if output_dir is None:
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    temporary = output_dir / ".progress.json.tmp"
    temporary.write_text(json.dumps(progress, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    temporary.replace(output_dir / "progress.json")


def run_benchmark(config: dict, *, root: Path, artifact_root: Path, progress_dir: Path | None = None) -> dict:
    overall_started = time.perf_counter()
    variant = config["variant"]
    if variant not in SUPPORTED_VARIANTS:
        raise ValueError(f"Unsupported benchmark variant: {variant}")
    store = ArtifactStore(artifact_root)
    requested_language = config.get("languages", config.get("language", "ru")).split(",")[0].strip()
    llm_settings = config["llm"]
    effective_config = {
        "variant": variant, "source_language": requested_language,
        "provider": llm_settings.get("provider", "ollama"), "requested_model": llm_settings["model"],
        "temperature": float(llm_settings["temperature"]), "timeout_seconds": float(llm_settings.get("timeout_seconds", 300)),
        "cloud_backed": bool(llm_settings.get("cloud_backed", str(llm_settings["model"]).endswith("-cloud"))),
        "questions_file": config["questions_file"],
    }
    config_hash = hashlib.sha256(json.dumps(effective_config, sort_keys=True).encode("utf-8")).hexdigest()
    progress = {"status": "running", "target": EXPECTED_URL, "variant": variant, "phase": "cache_lookup", "answers": [],
                "effective_config": effective_config, "effective_config_sha256": config_hash}
    llm = None
    _save_progress(progress_dir, progress)
    try:
        started = time.perf_counter()
        bundle = store.find(EXPECTED_ID, variant, language=requested_language)
        artifact_read_seconds = time.perf_counter() - started
        extractor_calls = 0
        extractor_wrapper_seconds = None
        if bundle is None:
            progress["phase"] = "extract"
            _save_progress(progress_dir, progress)
            started = time.perf_counter()
            if variant == "baoyu":
                from .adapters.baoyu import extract
                bundle = extract(config["video_url"], languages=config.get("languages", "en,ru"), output_dir=root / ".tools/baoyu-cache")
            elif variant == "captions_api":
                from .adapters.captions_api import extract
                bundle = extract(config["video_url"], language=requested_language)
            else:
                raise ValueError(f"Unsupported benchmark variant: {variant}")
            extractor_wrapper_seconds = time.perf_counter() - started
            store.save(bundle)
            extractor_calls = 1
        progress.update({"phase": "brief", "source_sha256": bundle.raw_sha256, "source_language": bundle.language})
        _save_progress(progress_dir, progress)
        llm = OllamaClient(llm_settings["base_url"], llm_settings["model"], float(llm_settings["temperature"]), float(llm_settings.get("timeout_seconds", 300)))
        started = time.perf_counter()
        def save_brief_progress(update: dict) -> None:
            progress.update(update)
            _save_progress(progress_dir, progress)

        brief, llm_metadata = brief_bundle(bundle, llm, progress=save_brief_progress)
        brief_seconds = time.perf_counter() - started
        progress.update({"phase": "questions", "briefing": brief, "model_calls": list(llm.responses)})
        _save_progress(progress_dir, progress)
        configured_questions = Path(config["questions_file"])
        questions_path = configured_questions if configured_questions.is_absolute() else root / configured_questions
        if not questions_path.is_file():
            questions_path = Path(config["_config_dir"]) / configured_questions
        qa_results, qa_seconds = [], []
        for item in _questions(questions_path):
            progress["question_id"] = item.get("id")
            _save_progress(progress_dir, progress)
            started = time.perf_counter()
            answer = answer_question(bundle, item["question"], llm)
            elapsed = time.perf_counter() - started
            qa_seconds.append(elapsed)
            qa_results.append({"id": item.get("id"), "question": item["question"], **answer})
            progress.update({"answers": qa_results, "model_calls": list(llm.responses)})
            _save_progress(progress_dir, progress)
        started = time.perf_counter()
        same_hash = store.find(EXPECTED_ID, variant, language=bundle.language)
        warm_read_seconds = time.perf_counter() - started
        if same_hash is None or same_hash.raw_sha256 != bundle.raw_sha256:
            raise RuntimeError("Warm artifact reuse did not preserve the exact source hash")
        llm_metadata["inference_calls"] = list(llm.responses)
        llm_metadata["usage_complete"] = all(call.get("prompt_tokens") is not None and call.get("completion_tokens") is not None for call in llm.responses)
        metrics = {
            "status": "completed", "target": EXPECTED_URL, "video_id": EXPECTED_ID, "variant": variant,
            "extractor_calls": extractor_calls, "source_type": bundle.source_type, "source_language": bundle.language,
            "source_sha256": bundle.raw_sha256, "timed_segments": len(bundle.segments),
            "measured_seconds": {"artifact_lookup": artifact_read_seconds, "extractor_wrapper": extractor_wrapper_seconds,
                                 "brief": brief_seconds, "qa_each": qa_seconds, "warm_artifact_read": warm_read_seconds,
                                 "end_to_end": time.perf_counter() - overall_started},
            "measurement_notes": {"extractor_wrapper": "None means cache hit; non-null is wrapper wall time, not proof of upstream cold cache.",
                                  "usage_cost": "provider usage may be incomplete; cost is not measured"},
            "effective_config": effective_config, "effective_config_sha256": config_hash,
            "warm_source_reuse": {"cache_hit": True, "same_source_hash": True, "extractor_calls": 0},
            "model": llm_metadata, "runtime": {"python": __import__("sys").version, "package": __version__},
            "questions_n": len(qa_results), "usage": {"prompt_tokens": sum(call["prompt_tokens"] for call in llm.responses if call.get("prompt_tokens") is not None) if llm_metadata["usage_complete"] else None,
                                                          "completion_tokens": sum(call["completion_tokens"] for call in llm.responses if call.get("completion_tokens") is not None) if llm_metadata["usage_complete"] else None,
                                                          "complete": llm_metadata["usage_complete"], "cost": "not measured"},
        }
        result = {"metrics": metrics, "briefing": brief, "briefing_markdown": render_brief(brief), "answers": qa_results}
        progress.update({"status": "completed", "phase": "complete", "metrics": metrics, "model_calls": list(llm.responses)})
        _save_progress(progress_dir, progress)
        return result
    except Exception as exc:
        if llm is not None:
            progress["model_calls"] = list(getattr(llm, "responses", []))
        progress.update({"status": "failed", "error": {"type": type(exc).__name__, "message": str(exc)}})
        _save_progress(progress_dir, progress)
        raise


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
