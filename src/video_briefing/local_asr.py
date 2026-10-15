"""Explicit local-only MP4 ingestion through user-provided FFmpeg/transcribe.cpp."""
from __future__ import annotations

import hashlib
import json
import math
import os
import sys
import subprocess
import tempfile
import time
import array
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .file_permissions import set_private_file_mode
from .models import EvidenceBundle, TranscriptSegment
from .validation import validate_bundle
from .asr_setup import ASRSetupError, default_data_home, resolve_installed_model, sha256_file

MAX_MEDIA_BYTES = 2 * 1024 * 1024 * 1024
MAX_DURATION_SECONDS = 4 * 60 * 60
MAX_ASR_SECONDS = 6 * 60 * 60
CHUNK_SECONDS = 24
MAX_SEGMENTS = 10_000


class LocalASRError(RuntimeError):
    """Safe-to-report local extraction error; never embeds transcript text."""


def _local_environment() -> dict[str, str]:
    """Pass only runtime essentials to local binaries; strip credentials and proxy settings."""
    allowed = ("PATH", "HOME", "TMPDIR", "TMP", "TEMP", "LANG", "LC_ALL")
    environment = {key: os.environ[key] for key in allowed if key in os.environ}
    environment.setdefault("PATH", os.defpath)
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        environment[name] = ""
    environment["NO_PROXY"] = environment["no_proxy"] = "*"
    return environment


def _run(command: list[str], *, timeout: float, capture: bool = True) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(command, check=False, capture_output=capture, text=True, timeout=timeout,
                              env=_local_environment())
    except subprocess.TimeoutExpired as exc:
        raise LocalASRError(f"local ASR process timed out after {timeout:g}s") from exc
    except OSError as exc:
        raise LocalASRError(f"cannot start local dependency ({Path(command[0]).name}): {type(exc).__name__}") from exc


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _duration(ffprobe: str, source: Path) -> tuple[float, dict[str, Any]]:
    run = _run([ffprobe, "-protocol_whitelist", "file", "-v", "error", "-select_streams", "a", "-show_entries",
                "stream=codec_type,duration:format=duration", "-of", "json", str(source)], timeout=30)
    if run.returncode:
        raise LocalASRError(f"ffprobe failed with exit code {run.returncode}")
    try:
        report = json.loads(run.stdout)
        streams = report.get("streams", [])
        duration = float((streams[0].get("duration") if streams else None) or report.get("format", {}).get("duration"))
    except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError) as exc:
        raise LocalASRError("ffprobe returned malformed media metadata") from exc
    if not streams:
        raise LocalASRError("input has no audio stream")
    if not math.isfinite(duration) or duration <= 0 or duration > MAX_DURATION_SECONDS:
        raise LocalASRError(f"audio duration must be between 0 and {MAX_DURATION_SECONDS} seconds")
    return duration, {"audio_stream_count": len(streams)}


def _persist_asr_run(root: Path, media_hash: str, command: list[str], stdout_path: Path,
                     stderr: str | bytes, exit_code: int | None, elapsed_seconds: float) -> dict[str, Any]:
    log_dir = root / "runs" / media_hash / f"{time.time_ns()}-{os.getpid()}"
    log_dir.mkdir(parents=True, exist_ok=False, mode=0o700)
    for directory in (log_dir.parent.parent, log_dir.parent, log_dir):
        try:
            directory.chmod(0o700)
        except OSError:
            pass
    stdout = stdout_path.read_bytes() if stdout_path.exists() else b""
    stderr_bytes = stderr.encode("utf-8", errors="replace") if isinstance(stderr, str) else stderr or b""
    files = {"stdout.jsonl": stdout, "stderr.txt": stderr_bytes}
    for name, content in files.items():
        path = log_dir / name
        fd, temporary = tempfile.mkstemp(prefix=f".{name}.", dir=log_dir)
        try:
            with os.fdopen(fd, "wb") as handle:
                set_private_file_mode(handle.fileno(), path)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    manifest = {"command": command, "exit_code": exit_code, "elapsed_seconds": elapsed_seconds,
                "stdout_sha256": hashlib.sha256(stdout).hexdigest(), "stdout_bytes": len(stdout),
                "stderr_sha256": hashlib.sha256(stderr_bytes).hexdigest(), "stderr_bytes": len(stderr_bytes)}
    manifest_bytes = json.dumps(manifest, sort_keys=True, indent=2).encode("utf-8")
    fd, temporary = tempfile.mkstemp(prefix=".manifest.", dir=log_dir)
    try:
        with os.fdopen(fd, "wb") as handle:
            set_private_file_mode(handle.fileno(), Path(temporary))
            handle.write(manifest_bytes)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, log_dir / "manifest.json")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return {**manifest, "directory": str(log_dir)}


def _ingest_external_cli(
    source_path: str | Path,
    *,
    ffmpeg: str | Path,
    ffprobe: str | Path,
    transcribe_cli: str | Path,
    model_path: str | Path,
    work_root: str | Path,
    language: str,
    timeout_seconds: float = MAX_ASR_SECONDS,
    threads: int | None = None,
) -> EvidenceBundle:
    """Transcribe the complete local MP4; no URL/network/cloud calls are made here."""
    source = Path(source_path).expanduser().resolve(strict=True)
    if not source.is_file() or source.suffix.casefold() != ".mp4":
        raise LocalASRError("local source must be an existing MP4 file")
    if source.stat().st_size <= 0 or source.stat().st_size > MAX_MEDIA_BYTES:
        raise LocalASRError(f"MP4 size must be between 1 byte and {MAX_MEDIA_BYTES} bytes")
    if language not in {"ru", "en"}:
        raise LocalASRError("source language must be 'ru' or 'en'")
    ffmpeg_path, ffprobe_path = str(Path(ffmpeg).expanduser()), str(Path(ffprobe).expanduser())
    cli_path, model = Path(transcribe_cli).expanduser().resolve(), Path(model_path).expanduser().resolve()
    if not cli_path.is_file() or not model.is_file():
        raise LocalASRError("local transcribe-cli or model file is missing")
    if timeout_seconds <= 0 or timeout_seconds > MAX_ASR_SECONDS:
        raise LocalASRError(f"timeout_seconds must be in (0, {MAX_ASR_SECONDS}]")
    worker_threads = threads or max(1, min(os.cpu_count() or 1, 12))
    if not 1 <= worker_threads <= 64:
        raise LocalASRError("threads must be between 1 and 64")

    duration, media_info = _duration(ffprobe_path, source)
    media_hash = _sha256_file(source)
    video_id = media_hash
    root = Path(work_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        root.chmod(0o700)
    except OSError:
        pass
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="video-briefing-asr-", dir=root) as temporary:
        work = Path(temporary)
        pattern = work / "chunk_%05d.wav"
        split = _run([ffmpeg_path, "-protocol_whitelist", "file", "-nostdin", "-hide_banner", "-loglevel", "error", "-i", str(source),
                      "-map", "0:a:0", "-vn", "-ac", "1", "-ar", "16000", "-c:a", "pcm_s16le",
                      "-f", "segment", "-segment_time", str(CHUNK_SECONDS), "-reset_timestamps", "1", str(pattern)],
                     timeout=min(timeout_seconds, max(60.0, duration * 0.3)))
        if split.returncode:
            raise LocalASRError(f"ffmpeg audio segmentation failed with exit code {split.returncode}")
        chunks = sorted(work.glob("chunk_*.wav"))
        expected = math.ceil(duration / CHUNK_SECONDS)
        if not chunks or len(chunks) != expected or len(chunks) > MAX_SEGMENTS:
            raise LocalASRError(f"incomplete segmentation: expected {expected} chunks, got {len(chunks)}")
        batch_file = work / "batch.list"
        batch_file.write_text("".join(str(chunk) + "\n" for chunk in chunks), encoding="utf-8")
        jsonl_path = work / "asr.jsonl"
        asr_command = [str(cli_path), "-m", str(model), "--language", language, "--backend", "cpu",
                       "--threads", str(worker_threads), "--timestamps", "none", "--batch",
                       str(batch_file), "--batch-size", "1", "--batch-jsonl"]
        run_log: dict[str, Any]
        try:
            with jsonl_path.open("w", encoding="utf-8") as output:
                run = subprocess.run(asr_command, stdout=output, stderr=subprocess.PIPE, text=True,
                                     timeout=max(1.0, timeout_seconds - (time.monotonic() - started)),
                                     env=_local_environment())
        except subprocess.TimeoutExpired as exc:
            run_log = _persist_asr_run(root, media_hash, asr_command, jsonl_path,
                                       exc.stderr or b"", None, time.monotonic() - started)
            raise LocalASRError(f"full-source local ASR timed out after {timeout_seconds:g}s") from exc
        except OSError as exc:
            run_log = _persist_asr_run(root, media_hash, asr_command, jsonl_path,
                                       type(exc).__name__, None, time.monotonic() - started)
            raise LocalASRError(f"cannot start local dependency ({cli_path.name}): {type(exc).__name__}") from exc
        run_log = _persist_asr_run(root, media_hash, asr_command, jsonl_path,
                                   run.stderr, run.returncode, time.monotonic() - started)
        if run.returncode != 0:
            raise LocalASRError(f"transcribe-cli failed with exit code {run.returncode}; diagnostic bytes={len(run.stderr.encode())}")
        try:
            rows = [json.loads(line) for line in jsonl_path.read_text(encoding="utf-8").splitlines() if line.strip()]
        except (OSError, json.JSONDecodeError) as exc:
            raise LocalASRError("transcribe-cli returned malformed JSONL") from exc
        entries = [row for row in rows if isinstance(row, dict) and row.get("type") != "batch_header"]
        if len(entries) != len(chunks) or any(not isinstance(row.get("text"), str) for row in entries):
            raise LocalASRError(f"incomplete ASR output: expected {len(chunks)} rows, got {len(entries)}")
        # Row count alone cannot establish correspondence: a duplicated, reordered,
        # or truncated batch result would otherwise receive plausible timestamps.
        for index, (row, chunk) in enumerate(zip(entries, chunks)):
            reported_file = row.get("file")
            if not isinstance(reported_file, str) or Path(reported_file).resolve() != chunk.resolve():
                raise LocalASRError(f"ASR output row {index + 1} does not match the submitted chunk order")
            if any(row.get(flag) is True for flag in ("truncated", "is_truncated", "output_truncated")):
                raise LocalASRError(f"ASR output row {index + 1} reports truncated output")
        segments = []
        for index, row in enumerate(entries):
            text = row["text"].strip()
            if not text:
                continue
            # transcribe.cpp's text-only CLI does not expose word alignment for this
            # model family; timestamps are intentionally conservative 24s chunk bounds.
            start = index * CHUNK_SECONDS
            segments.append(TranscriptSegment(f"a{index + 1:06d}", text, float(start), min(CHUNK_SECONDS, duration - start)))
        if not segments:
            raise LocalASRError("local ASR returned no text for the full source")
        if _sha256_file(source) != media_hash:
            raise LocalASRError("input MP4 changed during local ASR; refusing to cache unverified provenance")
        raw_text = json.dumps([{"id": s.id, "text": s.text, "start_seconds": s.start_seconds,
                               "duration_seconds": s.duration_seconds} for s in segments],
                              ensure_ascii=False, separators=(",", ":"))
        bundle = EvidenceBundle(
            platform="local-file", video_id=video_id, url=f"local-file://sha256/{media_hash}",
            language=language, variant="local_asr", source_type="local-asr-chunk-transcript",
            extractor_version="transcribe.cpp-user-provided-binary",
            segments=segments, raw_sha256=hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
            fetched_at=datetime.now(timezone.utc).isoformat(),
            metadata={"media_sha256": media_hash, "media_bytes": source.stat().st_size,
                      "audio_duration_seconds": duration, "processed_audio_seconds": duration,
                      "chunk_seconds": CHUNK_SECONDS, "chunk_count": len(chunks),
                      "nonempty_transcript_chunks": len(segments),
                      "timing_precision": "24-second chunk bounds; not word alignment",
                      "binary_sha256": _sha256_file(cli_path), "model_sha256": _sha256_file(model),
                      "asr_model": {"id": model.stem, "language": language,
                                    "sha256": _sha256_file(model), "source": "user-configured"},
                      "ffmpeg": Path(ffmpeg_path).name, **media_info,
                      "privacy": {"network_used": False, "cloud_asr": False, "cloud_llm": False,
                                  "transcript_uploaded": False},
                      "elapsed_seconds": time.monotonic() - started, "execution_logs": run_log},
            warnings=["Local ASR word-level alignment unavailable; citation times identify 24-second chunks.",
                      "ASR transcript is not a verbatim/independently verified transcript."], raw_text=raw_text)
        validate_bundle(bundle)
        return bundle


def _ingest_managed_model(
    source_path: str | Path,
    *,
    work_root: str | Path,
    language: str | None,
    timeout_seconds: float,
    threads: int | None,
    data_home: str | Path,
) -> EvidenceBundle:
    try:
        model_info, model_path = resolve_installed_model(language, data_home)
    except ASRSetupError as exc:
        raise LocalASRError(str(exc)) from exc
    language = model_info["language"]
    source = Path(source_path).expanduser().resolve(strict=True)
    if not source.is_file() or source.suffix.casefold() != ".mp4":
        raise LocalASRError("local source must be an existing MP4 file")
    if source.stat().st_size <= 0 or source.stat().st_size > MAX_MEDIA_BYTES:
        raise LocalASRError(f"MP4 size must be between 1 byte and {MAX_MEDIA_BYTES} bytes")
    if timeout_seconds <= 0 or timeout_seconds > MAX_ASR_SECONDS:
        raise LocalASRError(f"timeout_seconds must be in (0, {MAX_ASR_SECONDS}]")
    worker_threads = threads or max(1, min(os.cpu_count() or 1, 12))
    if not 1 <= worker_threads <= 64:
        raise LocalASRError("threads must be between 1 and 64")
    try:
        import av
        import transcribe_cpp
    except (ImportError, OSError) as exc:
        raise LocalASRError("managed local ASR runtime is missing; install the project with its 'asr' extra") from exc

    media_hash = _sha256_file(source)
    root = Path(work_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        root.chmod(0o700)
    except OSError:
        pass
    started = time.monotonic()
    try:
        container = av.open(str(source), mode="r", options={"protocol_whitelist": "file"})
    except Exception as exc:
        raise LocalASRError(f"cannot open local MP4 audio ({type(exc).__name__})") from exc

    session = None
    try:
        audio_streams = list(container.streams.audio)
        if not audio_streams:
            raise LocalASRError("input has no audio stream")
        audio_stream = audio_streams[0]
        reported_duration: float | None = None
        if audio_stream.duration is not None and audio_stream.time_base is not None:
            reported_duration = float(audio_stream.duration * audio_stream.time_base)
        elif container.duration is not None:
            reported_duration = float(container.duration) / 1_000_000
        if reported_duration is not None and (
            not math.isfinite(reported_duration) or reported_duration <= 0
            or reported_duration > MAX_DURATION_SECONDS
        ):
            raise LocalASRError(f"audio duration must be between 0 and {MAX_DURATION_SECONDS} seconds")

        try:
            asr_model = transcribe_cpp.Model(model_path, backend="auto")
            session = asr_model.session(n_threads=worker_threads)
            resampler = av.AudioResampler(format="flt", layout="mono", rate=16000)
        except Exception as exc:
            raise LocalASRError(f"cannot initialize local ASR runtime ({type(exc).__name__})") from exc

        samples_per_chunk = CHUNK_SECONDS * 16000
        bytes_per_chunk = samples_per_chunk * 4
        pending = bytearray()
        decoded_samples = 0
        transcribed_samples = 0
        chunk_index = 0
        segments: list[TranscriptSegment] = []

        def transcribe_chunk(raw_pcm: bytes) -> None:
            nonlocal transcribed_samples, chunk_index
            chunk = array.array("f")
            chunk.frombytes(raw_pcm)
            if sys.byteorder != "little":
                chunk.byteswap()
            if len(chunk) == 0:
                return
            if chunk_index >= MAX_SEGMENTS:
                raise LocalASRError(f"local audio exceeds the {MAX_SEGMENTS}-chunk processing limit")
            if time.monotonic() - started >= timeout_seconds:
                raise LocalASRError(f"local ASR timed out after {timeout_seconds:g}s")
            start = transcribed_samples / 16000
            try:
                result = session.run(chunk, language=language, timestamps="none")
            except Exception as exc:
                raise LocalASRError(f"local ASR inference failed ({type(exc).__name__})") from exc
            text = getattr(result, "text", None)
            if not isinstance(text, str):
                raise LocalASRError("local ASR returned malformed transcript output")
            text = text.strip()
            duration = len(chunk) / 16000
            if text:
                segments.append(TranscriptSegment(
                    f"a{chunk_index + 1:06d}", text, start, duration,
                ))
            chunk_index += 1
            transcribed_samples += len(chunk)
            if time.monotonic() - started > timeout_seconds:
                raise LocalASRError(f"local ASR timed out after {timeout_seconds:g}s")

        def append_frame(frame: Any) -> None:
            nonlocal decoded_samples
            expected_bytes = frame.samples * 4
            try:
                frame_bytes = bytes(frame.planes[0])[:expected_bytes]
            except (IndexError, TypeError, ValueError) as exc:
                raise LocalASRError("audio decoder returned an unsupported PCM frame") from exc
            if len(frame_bytes) != expected_bytes:
                raise LocalASRError("audio decoder returned an incomplete PCM frame")
            decoded_samples += frame.samples
            if decoded_samples > MAX_DURATION_SECONDS * 16000:
                raise LocalASRError(f"audio duration exceeds {MAX_DURATION_SECONDS} seconds")
            pending.extend(frame_bytes)
            while len(pending) >= bytes_per_chunk:
                transcribe_chunk(bytes(pending[:bytes_per_chunk]))
                del pending[:bytes_per_chunk]

        try:
            for frame in container.decode(audio=0):
                for converted in resampler.resample(frame):
                    append_frame(converted)
                if time.monotonic() - started > timeout_seconds:
                    raise LocalASRError(f"local ASR timed out after {timeout_seconds:g}s")
            for converted in resampler.resample(None):
                append_frame(converted)
        except LocalASRError:
            raise
        except Exception as exc:
            raise LocalASRError(f"cannot decode local MP4 audio ({type(exc).__name__})") from exc

        if pending:
            transcribe_chunk(bytes(pending))
        if decoded_samples == 0 or chunk_index == 0:
            raise LocalASRError("local MP4 contains no decodable audio samples")
        if not segments:
            raise LocalASRError("local ASR returned no text for the full source")
        if _sha256_file(source) != media_hash:
            raise LocalASRError("input MP4 changed during local ASR; refusing to cache unverified provenance")
        if sha256_file(model_path) != model_info["sha256"]:
            raise LocalASRError("the selected local ASR model changed during transcription")

        duration = decoded_samples / 16000
        raw_text = json.dumps([{"id": segment.id, "text": segment.text,
                                "start_seconds": segment.start_seconds,
                                "duration_seconds": segment.duration_seconds} for segment in segments],
                              ensure_ascii=False, separators=(",", ":"))
        runtime_version = transcribe_cpp.__version__
        bundle = EvidenceBundle(
            platform="local-file", video_id=media_hash, url=f"local-file://sha256/{media_hash}",
            language=language, variant="local_asr", source_type="local-asr-chunk-transcript",
            extractor_version=f"transcribe.cpp-python/{runtime_version}", segments=segments,
            raw_sha256=hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
            fetched_at=datetime.now(timezone.utc).isoformat(),
            metadata={
                "media_sha256": media_hash, "media_bytes": source.stat().st_size,
                "audio_duration_seconds": duration, "processed_audio_seconds": duration,
                "audio_stream_count": len(audio_streams), "selected_audio_stream": 0,
                "chunk_seconds": CHUNK_SECONDS, "chunk_count": chunk_index,
                "nonempty_transcript_chunks": len(segments),
                "timing_precision": "24-second chunk bounds; not word alignment",
                "asr_model": {
                    "id": model_info["id"], "language": language,
                    "revision": model_info["revision"], "quantization": model_info["quantization"],
                    "sha256": model_info["sha256"], "license": model_info["license"],
                },
                "decoder": {"name": "PyAV", "version": av.__version__},
                "runtime": {"name": "transcribe.cpp Python binding", "version": runtime_version,
                            "backend": "auto", "threads": worker_threads},
                "privacy": {"network_used": False, "cloud_asr": False, "cloud_llm": False,
                            "transcript_uploaded": False},
                "elapsed_seconds": time.monotonic() - started,
            },
            warnings=["Local ASR word-level alignment unavailable; citation times identify 24-second chunks.",
                      "ASR transcript is not a verbatim/independently verified transcript."],
            raw_text=raw_text,
        )
        validate_bundle(bundle)
        return bundle
    finally:
        if session is not None:
            try:
                session.close()
            except Exception:
                pass
        container.close()


def ingest_local_video(
    source_path: str | Path,
    *,
    work_root: str | Path,
    language: str | None = None,
    data_home: str | Path | None = None,
    ffmpeg: str | Path = "ffmpeg",
    ffprobe: str | Path = "ffprobe",
    transcribe_cli: str | Path | None = None,
    model_path: str | Path | None = None,
    timeout_seconds: float = MAX_ASR_SECONDS,
    threads: int | None = None,
) -> EvidenceBundle:
    """Transcribe an explicitly selected local language with managed ASR or a legacy CLI."""
    if bool(transcribe_cli) != bool(model_path):
        raise LocalASRError("legacy ASR mode requires both a transcribe-cli path and a model path")
    if transcribe_cli and model_path:
        return _ingest_external_cli(
            source_path, ffmpeg=ffmpeg, ffprobe=ffprobe, transcribe_cli=transcribe_cli,
            model_path=model_path, work_root=work_root, language=language or "ru",
            timeout_seconds=timeout_seconds, threads=threads,
        )
    return _ingest_managed_model(
        source_path, work_root=work_root, language=language, timeout_seconds=timeout_seconds,
        threads=threads, data_home=data_home or default_data_home(),
    )
