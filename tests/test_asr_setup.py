from __future__ import annotations

import hashlib
import io
import stat
from pathlib import Path

import pytest

import video_briefing.asr_setup as asr_setup


PAYLOAD = b"pinned fake model payload"
MODEL = {
    "id": "test-en-model",
    "display_name": "Test English model",
    "language": "en",
    "language_name": "English",
    "repository": "handy-computer/test-model",
    "revision": "0123456789abcdef0123456789abcdef01234567",
    "filename": "test-en.gguf",
    "size_bytes": len(PAYLOAD),
    "sha256": hashlib.sha256(PAYLOAD).hexdigest(),
    "quantization": "Q8_0",
    "license": "CC-BY-4.0",
}


class FakeResponse:
    def __init__(self, body: bytes, *, url: str, content_length: bool = True):
        self.body = io.BytesIO(body)
        self.url = url
        self.headers = {"Content-Length": str(len(body))} if content_length else {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.body.close()

    def read(self, size: int = -1) -> bytes:
        return self.body.read(size)

    def geturl(self) -> str:
        return self.url


class FakeOpener:
    def __init__(self, response: FakeResponse):
        self.response = response
        self.calls = 0
        self.request_url = None

    def open(self, request, *, timeout: int):
        self.calls += 1
        self.request_url = request.full_url
        assert timeout == asr_setup.DOWNLOAD_TIMEOUT_SECONDS
        return self.response


def configure_fake_download(monkeypatch, model=MODEL, *, body=PAYLOAD, url=None, content_length=True):
    monkeypatch.setattr(asr_setup, "load_model_manifest", lambda: {"schema_version": 1, "models": [model]})
    monkeypatch.setattr(asr_setup, "model_for_language", lambda _language: model)
    final_url = url or f"https://huggingface.co/{model['repository']}/resolve/{model['revision']}/{model['filename']}"
    opener = FakeOpener(FakeResponse(body, url=final_url, content_length=content_length))
    monkeypatch.setattr(asr_setup, "build_opener", lambda _handler: opener)
    return opener


def test_manifest_pins_supported_languages_models_and_hashes():
    manifest = asr_setup.load_model_manifest()

    assert {model["language"] for model in manifest["models"]} == {"ru", "en"}
    assert all(len(model["revision"]) == 40 for model in manifest["models"])
    assert all(len(model["sha256"]) == 64 for model in manifest["models"])
    assert asr_setup.model_for_language("en")["id"] == "parakeet-tdt-ctc-110m-q8-0"


@pytest.mark.parametrize(("value", "expected"), [
    ("ru", ["ru"]), ("en", ["en"]), ("en,ru", ["ru", "en"]),
])
def test_parse_languages_normalizes_language_selection(value, expected):
    assert asr_setup.parse_languages(value) == expected


@pytest.mark.parametrize("value", ["", "ru,ru", "fr", "ru,en,fr"])
def test_parse_languages_rejects_empty_duplicate_and_unsupported_values(value):
    with pytest.raises(asr_setup.ASRSetupError):
        asr_setup.parse_languages(value)


def test_install_is_verified_private_and_idempotent(tmp_path, monkeypatch):
    opener = configure_fake_download(monkeypatch)

    first = asr_setup.install_models(["en"], tmp_path)
    second = asr_setup.install_models(["en"], tmp_path)
    destination = Path(first[0]["path"])

    assert first[0]["status"] == "installed"
    assert second[0]["status"] == "already_installed"
    assert destination.read_bytes() == PAYLOAD
    assert stat.S_IMODE(destination.stat().st_mode) == 0o600
    assert opener.calls == 1
    assert "/resolve/0123456789abcdef0123456789abcdef01234567/" in opener.request_url
    assert not list(destination.parent.glob("*.part"))


@pytest.mark.parametrize(("payload", "content_length"), [(b"short", False), (PAYLOAD + b"extra", False)])
def test_download_failure_never_installs_a_partial_or_oversized_file(
    tmp_path, monkeypatch, payload, content_length,
):
    configure_fake_download(monkeypatch, body=payload, content_length=content_length)

    with pytest.raises(asr_setup.ASRSetupError):
        asr_setup.install_models(["en"], tmp_path)

    model_directory = tmp_path / "asr" / "models"
    assert not (model_directory / MODEL["filename"]).exists()
    assert list(model_directory.iterdir()) == []


def test_hash_mismatch_never_installs_a_model(tmp_path, monkeypatch):
    wrong_model = {**MODEL, "sha256": "0" * 64}
    configure_fake_download(monkeypatch, model=wrong_model)

    with pytest.raises(asr_setup.ASRSetupError, match="SHA-256"):
        asr_setup.install_models(["en"], tmp_path)

    assert list((tmp_path / "asr" / "models").iterdir()) == []


def test_download_total_timeout_removes_the_temporary_file(tmp_path, monkeypatch):
    now = [0.0]
    configure_fake_download(monkeypatch)
    monkeypatch.setattr(asr_setup.time, "monotonic", lambda: now[0])
    response = asr_setup.build_opener(None).response
    original_read = response.read

    def slow_read(size: int = -1) -> bytes:
        block = original_read(size)
        now[0] = asr_setup.DOWNLOAD_TOTAL_TIMEOUT_SECONDS + 1
        return block

    response.read = slow_read

    with pytest.raises(asr_setup.ASRSetupError, match="total time limit"):
        asr_setup.install_models(["en"], tmp_path)

    model_directory = tmp_path / "asr" / "models"
    assert not (model_directory / MODEL["filename"]).exists()
    assert list(model_directory.iterdir()) == []


def test_untrusted_download_redirect_is_rejected(tmp_path, monkeypatch):
    configure_fake_download(monkeypatch, url="https://downloads.example.invalid/model.gguf")

    with pytest.raises(asr_setup.ASRSetupError, match="trusted HTTPS"):
        asr_setup.install_models(["en"], tmp_path)

    assert list((tmp_path / "asr" / "models").iterdir()) == []


def test_existing_user_file_is_never_replaced(tmp_path, monkeypatch):
    model_directory = tmp_path / "asr" / "models"
    model_directory.mkdir(parents=True)
    destination = model_directory / MODEL["filename"]
    destination.write_bytes(b"existing user data")
    monkeypatch.setattr(asr_setup, "load_model_manifest", lambda: {"schema_version": 1, "models": [MODEL]})
    monkeypatch.setattr(asr_setup, "model_for_language", lambda _language: MODEL)
    monkeypatch.setattr(asr_setup, "build_opener", lambda _handler: pytest.fail("must not download"))

    with pytest.raises(asr_setup.ASRSetupError, match="left untouched"):
        asr_setup.install_models(["en"], tmp_path)

    assert destination.read_bytes() == b"existing user data"


def test_no_language_is_ambiguous_when_both_models_are_installed(tmp_path, monkeypatch):
    monkeypatch.setattr(asr_setup, "installed_models", lambda _root: [
        {"language": "ru", "installed": True}, {"language": "en", "installed": True},
    ])

    with pytest.raises(asr_setup.ASRSetupError, match="source language is required"):
        asr_setup.resolve_installed_model(None, tmp_path)
