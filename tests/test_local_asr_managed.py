from __future__ import annotations

import array
import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest

import video_briefing.local_asr as local_asr
from video_briefing.asr_setup import ASRSetupError
from video_briefing.local_asr import LocalASRError, ingest_local_video


class FakePlane:
    def __init__(self, samples: int):
        pcm = array.array("f", [0.0]) * samples
        self.pcm = pcm.tobytes()

    def __bytes__(self):
        return self.pcm


class FakeFrame:
    def __init__(self, samples: int):
        self.samples = samples
        self.planes = [FakePlane(samples)]


class FakeContainer:
    def __init__(self, frames, *, has_audio=True, duration=25):
        self.frames = frames
        self.streams = SimpleNamespace(audio=[SimpleNamespace(duration=duration, time_base=1)] if has_audio else [])
        self.duration = None
        self.closed = False
        self.decode_audio_index = None

    def decode(self, *, audio):
        self.decode_audio_index = audio
        yield from self.frames

    def close(self):
        self.closed = True


class FakeResampler:
    def resample(self, frame):
        return [] if frame is None else [frame]


def configured_runtime(tmp_path, monkeypatch, *, language="en", frames=None, has_audio=True):
    source = tmp_path / "fixture.mp4"
    source.write_bytes(b"local media fixture")
    model_path = tmp_path / "model.gguf"
    model_path.write_bytes(b"verified model fixture")
    model_info = {
        "id": "fixture-model", "language": language, "revision": "a" * 40,
        "quantization": "Q8_0", "sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "license": "MIT",
    }
    monkeypatch.setattr(local_asr, "resolve_installed_model", lambda _language, _home: (model_info, model_path))
    observed = {"runs": [], "open_options": None}
    container = FakeContainer(frames or [FakeFrame(25 * 16000)], has_audio=has_audio)

    class FakeAv:
        __version__ = "18.1.0"

        @staticmethod
        def open(_path, *, mode, options):
            observed["open_options"] = (mode, options)
            return container

        @staticmethod
        def AudioResampler(**kwargs):
            assert kwargs == {"format": "flt", "layout": "mono", "rate": 16000}
            return FakeResampler()

    class FakeSession:
        def run(self, pcm, *, language, timestamps):
            observed["runs"].append({"samples": len(pcm), "language": language, "timestamps": timestamps})
            return SimpleNamespace(text=f"recognized {language} chunk")

        def close(self):
            observed["closed"] = True

    class FakeModel:
        def __init__(self, path, *, backend):
            observed["model"] = (Path(path), backend)

        def session(self, *, n_threads):
            observed["threads"] = n_threads
            return FakeSession()

    fake_cpp = SimpleNamespace(__version__="0.4.0", Model=FakeModel)
    monkeypatch.setitem(__import__("sys").modules, "av", FakeAv)
    monkeypatch.setitem(__import__("sys").modules, "transcribe_cpp", fake_cpp)
    return source, model_path, observed, container


@pytest.mark.parametrize("language", ["ru", "en"])
def test_managed_asr_resamples_chunks_routes_language_and_records_model_provenance(
    tmp_path, monkeypatch, language,
):
    source, model_path, observed, container = configured_runtime(tmp_path, monkeypatch, language=language)

    bundle = ingest_local_video(
        source, language=language, data_home=tmp_path / "data", work_root=tmp_path / "work", threads=3,
    )

    assert bundle.language == language
    assert bundle.video_id == bundle.metadata["media_sha256"]
    assert bundle.metadata["chunk_count"] == 2
    assert bundle.metadata["processed_audio_seconds"] == 25
    assert [segment.start_seconds for segment in bundle.segments] == [0, 24]
    assert [segment.duration_seconds for segment in bundle.segments] == [24, 1]
    assert bundle.metadata["asr_model"]["id"] == "fixture-model"
    assert bundle.metadata["asr_model"]["sha256"] == hashlib.sha256(model_path.read_bytes()).hexdigest()
    assert bundle.metadata["privacy"] == {
        "network_used": False, "cloud_asr": False, "cloud_llm": False, "transcript_uploaded": False,
    }
    assert observed["open_options"] == ("r", {"protocol_whitelist": "file"})
    assert [call["language"] for call in observed["runs"]] == [language, language]
    assert all(call["timestamps"] == "none" for call in observed["runs"])
    assert observed["model"] == (model_path, "auto")
    assert observed["threads"] == 3
    assert observed["closed"] is True
    assert container.closed is True


def test_managed_asr_rejects_media_without_audio_before_loading_model(tmp_path, monkeypatch):
    source, _model_path, observed, container = configured_runtime(
        tmp_path, monkeypatch, frames=[], has_audio=False,
    )

    with pytest.raises(LocalASRError, match="no audio stream"):
        ingest_local_video(source, language="en", data_home=tmp_path, work_root=tmp_path / "work")

    assert "model" not in observed
    assert container.closed is True


def test_managed_asr_rejects_unsupported_language_before_decoding(tmp_path, monkeypatch):
    source = tmp_path / "fixture.mp4"
    source.write_bytes(b"media")
    monkeypatch.setattr(
        local_asr, "resolve_installed_model",
        lambda _language, _home: (_ for _ in ()).throw(ASRSetupError("source language must be 'ru' or 'en'")),
    )

    with pytest.raises(LocalASRError, match="source language"):
        ingest_local_video(source, language="fr", data_home=tmp_path, work_root=tmp_path / "work")


def test_managed_asr_rejects_one_sided_legacy_override(tmp_path):
    with pytest.raises(LocalASRError, match="both a transcribe-cli path and a model path"):
        ingest_local_video(
            tmp_path / "fixture.mp4", transcribe_cli="/usr/bin/transcribe-cli",
            work_root=tmp_path / "work",
        )
