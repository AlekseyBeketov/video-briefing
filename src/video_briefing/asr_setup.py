"""Pinned, local installation of the optional speech-recognition models."""
from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import time
from importlib.resources import files
from pathlib import Path
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .file_permissions import set_private_file_mode

DOWNLOAD_TIMEOUT_SECONDS = 60
DOWNLOAD_TOTAL_TIMEOUT_SECONDS = 2 * 60 * 60
DOWNLOAD_BLOCK_BYTES = 1024 * 1024
LANGUAGES = ("ru", "en")
_ALLOWED_DOWNLOAD_SUFFIXES = (".huggingface.co", ".hf.co")


class ASRSetupError(RuntimeError):
    """A safe-to-display model setup or selection error."""


def default_data_home() -> Path:
    override = os.environ.get("VIDEO_BRIEFING_DATA_HOME")
    if override:
        return Path(override).expanduser()
    if os.name == "nt":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "VideoBriefing"
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/VideoBriefing"
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "video-briefing"


def load_model_manifest() -> dict[str, Any]:
    resource = files("video_briefing.resources").joinpath("asr-models.json")
    try:
        manifest = json.loads(resource.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ASRSetupError("packaged ASR model manifest is unavailable or invalid") from exc
    if manifest.get("schema_version") != 1 or not isinstance(manifest.get("models"), list):
        raise ASRSetupError("packaged ASR model manifest has an unsupported schema")
    return manifest


def parse_languages(value: str) -> list[str]:
    languages = [item.strip().casefold() for item in value.split(",") if item.strip()]
    if not languages or len(languages) != len(set(languages)):
        raise ASRSetupError("choose one or both languages: ru, en, or ru,en")
    unsupported = sorted(set(languages) - set(LANGUAGES))
    if unsupported:
        raise ASRSetupError(f"unsupported source language: {', '.join(unsupported)}; choose ru or en")
    return [language for language in LANGUAGES if language in languages]


def model_for_language(language: str) -> dict[str, Any]:
    normalized = language.casefold()
    if normalized not in LANGUAGES:
        raise ASRSetupError("source language must be 'ru' or 'en'")
    for model in load_model_manifest()["models"]:
        if model.get("language") == normalized:
            return model
    raise ASRSetupError(f"no packaged ASR model is configured for source language '{normalized}'")


def model_path(model: dict[str, Any], data_home: str | Path) -> Path:
    filename = model.get("filename")
    if not isinstance(filename, str) or Path(filename).name != filename:
        raise ASRSetupError("model manifest contains an unsafe filename")
    return Path(data_home).expanduser() / "asr" / "models" / filename


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(DOWNLOAD_BLOCK_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_model_file(path: Path, model: dict[str, Any]) -> tuple[bool, str | None]:
    if not path.is_file():
        return False, "missing"
    try:
        if path.stat().st_size != model["size_bytes"]:
            return False, "size_mismatch"
        if sha256_file(path) != model["sha256"]:
            return False, "sha256_mismatch"
    except OSError:
        return False, "unreadable"
    return True, None


def installed_models(data_home: str | Path) -> list[dict[str, Any]]:
    result = []
    for model in load_model_manifest()["models"]:
        path = model_path(model, data_home)
        valid, problem = verify_model_file(path, model)
        result.append({
            "id": model["id"], "language": model["language"], "display_name": model["display_name"],
            "path": str(path), "size_bytes": model["size_bytes"], "quantization": model["quantization"],
            "license": model["license"], "installed": valid, "problem": problem,
        })
    return result


def resolve_installed_model(language: str | None, data_home: str | Path) -> tuple[dict[str, Any], Path]:
    if language is None:
        installed = [item for item in installed_models(data_home) if item["installed"]]
        if len(installed) == 1:
            language = installed[0]["language"]
        elif not installed:
            raise ASRSetupError("no verified local ASR model is installed; run `video-briefing setup-asr`")
        else:
            raise ASRSetupError("source language is required when both Russian and English models are installed")
    model = model_for_language(language)
    path = model_path(model, data_home)
    valid, problem = verify_model_file(path, model)
    if not valid:
        if problem == "missing":
            raise ASRSetupError(f"the {language} ASR model is not installed; run `video-briefing setup-asr --languages {language}`")
        raise ASRSetupError(f"the installed {language} ASR model failed {problem} verification; move it aside and run setup again")
    return model, path


class _PinnedHTTPSRedirectHandler(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        parsed = urlsplit(newurl)
        host = (parsed.hostname or "").casefold()
        allowed = host == "huggingface.co" or any(host.endswith(suffix) for suffix in _ALLOWED_DOWNLOAD_SUFFIXES)
        if parsed.scheme != "https" or not allowed or parsed.username or parsed.password:
            raise ASRSetupError("model download redirected outside the trusted HTTPS model hosts")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _download_url(model: dict[str, Any]) -> str:
    repository = model["repository"]
    revision = model["revision"]
    filename = model["filename"]
    if not isinstance(repository, str) or "/" not in repository or not isinstance(revision, str):
        raise ASRSetupError("model manifest contains an invalid upstream reference")
    if len(revision) != 40 or any(character not in "0123456789abcdef" for character in revision):
        raise ASRSetupError("model manifest revision must be an immutable commit hash")
    return f"https://huggingface.co/{repository}/resolve/{revision}/{filename}?download=true"


def _download_model(
    model: dict[str, Any],
    destination: Path,
    progress: Callable[[int, int], None] | None = None,
) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        destination.parent.chmod(0o700)
    except OSError:
        pass
    if destination.exists():
        valid, problem = verify_model_file(destination, model)
        if valid:
            return
        raise ASRSetupError(
            f"existing model path is not a verified managed model ({problem}); it was left untouched: {destination}"
        )

    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".part", dir=destination.parent)
    temporary = Path(temporary_name)
    digest = hashlib.sha256()
    downloaded = 0
    try:
        request = Request(_download_url(model), headers={"User-Agent": "video-briefing/0.2"})
        opener = build_opener(_PinnedHTTPSRedirectHandler())
        deadline = time.monotonic() + DOWNLOAD_TOTAL_TIMEOUT_SECONDS
        with os.fdopen(descriptor, "wb") as output:
            set_private_file_mode(output.fileno(), temporary)
            try:
                response = opener.open(request, timeout=DOWNLOAD_TIMEOUT_SECONDS)
            except HTTPError as exc:
                raise ASRSetupError(f"model download failed with HTTP {exc.code}") from exc
            except URLError as exc:
                raise ASRSetupError(f"model download failed ({type(exc.reason).__name__})") from exc
            with response:
                if time.monotonic() > deadline:
                    raise ASRSetupError("model download exceeded its total time limit")
                final = urlsplit(response.geturl())
                final_host = (final.hostname or "").casefold()
                if final.scheme != "https" or not (
                    final_host == "huggingface.co"
                    or any(final_host.endswith(suffix) for suffix in _ALLOWED_DOWNLOAD_SUFFIXES)
                ):
                    raise ASRSetupError("model download resolved outside the trusted HTTPS model hosts")
                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) != model["size_bytes"]:
                    raise ASRSetupError("model server returned a size that differs from the pinned manifest")
                while True:
                    if time.monotonic() > deadline:
                        raise ASRSetupError("model download exceeded its total time limit")
                    block = response.read(DOWNLOAD_BLOCK_BYTES)
                    if time.monotonic() > deadline:
                        raise ASRSetupError("model download exceeded its total time limit")
                    if not block:
                        break
                    downloaded += len(block)
                    if downloaded > model["size_bytes"]:
                        raise ASRSetupError("model download exceeded the pinned size limit")
                    output.write(block)
                    digest.update(block)
                    if progress is not None:
                        progress(downloaded, model["size_bytes"])
            output.flush()
            os.fsync(output.fileno())
        if downloaded != model["size_bytes"]:
            raise ASRSetupError(f"model download was incomplete ({downloaded} of {model['size_bytes']} bytes)")
        if digest.hexdigest() != model["sha256"]:
            raise ASRSetupError("model SHA-256 did not match the pinned manifest")
        try:
            os.link(temporary, destination)
        except FileExistsError as exc:
            raise ASRSetupError(f"model path appeared during setup and was left untouched: {destination}") from exc
        except OSError as exc:
            raise ASRSetupError(f"cannot atomically install verified model ({type(exc).__name__})") from exc
    except ASRSetupError:
        raise
    except (OSError, ValueError) as exc:
        raise ASRSetupError(f"model download failed ({type(exc).__name__})") from exc
    finally:
        try:
            temporary.unlink(missing_ok=True)
        except OSError:
            pass


def install_models(
    languages: list[str],
    data_home: str | Path,
    *,
    progress: Callable[[dict[str, Any], int, int], None] | None = None,
) -> list[dict[str, Any]]:
    requested = parse_languages(",".join(languages))
    results = []
    for language in requested:
        model = model_for_language(language)
        destination = model_path(model, data_home)
        was_present = destination.exists()
        callback = (lambda done, total, entry=model: progress(entry, done, total)) if progress else None
        _download_model(model, destination, callback)
        results.append({
            "id": model["id"], "language": language, "display_name": model["display_name"],
            "path": str(destination), "size_bytes": model["size_bytes"],
            "quantization": model["quantization"], "license": model["license"],
            "status": "already_installed" if was_present else "installed",
        })
    return results
