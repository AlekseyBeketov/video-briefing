from __future__ import annotations

import hashlib
import json
import os
from contextlib import contextmanager
import tempfile
import time
from pathlib import Path
from typing import Iterator

from .models import EvidenceBundle
from .validation import validate_bundle


class ArtifactStore:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()

    @staticmethod
    def key(platform: str, video_id: str, language: str, variant: str) -> str:
        identity = json.dumps([platform, video_id, language, variant], separators=(",", ":"))
        return hashlib.sha256(identity.encode()).hexdigest()

    def bundle_path(self, key: str) -> Path:
        return self.root / key[:2] / key / "bundle.json"

    @contextmanager
    def _identity_lock(self, key: str, timeout: float = 30.0) -> Iterator[None]:
        lock = self.root / ".locks" / f"{key}.lock"
        lock.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            lock.parent.chmod(0o700)
        except OSError:
            pass
        deadline = time.monotonic() + timeout
        while True:
            try:
                lock.mkdir(mode=0o700)
                (lock / "owner").write_text(f"pid={os.getpid()}\\n", encoding="ascii")
                break
            except FileExistsError:
                if time.monotonic() >= deadline:
                    raise TimeoutError("timed out waiting for evidence cache identity lock")
                time.sleep(0.05)
        try:
            yield
        finally:
            try:
                (lock / "owner").unlink(missing_ok=True)
                lock.rmdir()
            except OSError:
                pass

    def save(self, bundle: EvidenceBundle) -> EvidenceBundle:
        validate_bundle(bundle)
        if bundle.raw_text is None:
            raise ValueError("immutable cache requires the complete serialized raw source")
        self.root.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            self.root.chmod(0o700)
        except OSError:
            pass
        key = self.key(bundle.platform, bundle.video_id, bundle.language, bundle.variant)
        bundle_path = self.bundle_path(key)
        with self._identity_lock(key):
            existing = self.load(bundle.platform, bundle.video_id, bundle.language, bundle.variant)
            if existing is not None:
                if existing.raw_sha256 != bundle.raw_sha256:
                    raise ValueError("immutable cache identity conflict: source hash changed; choose an explicit new identity")
                return existing
            if bundle_path.exists():
                raise ValueError("immutable cache identity conflict: existing bundle is invalid; refusing overwrite")
            raw_path = bundle_path.with_name("source.raw")
            if raw_path.exists() and hashlib.sha256(raw_path.read_bytes()).hexdigest() != bundle.raw_sha256:
                raise ValueError("immutable cache identity conflict: existing raw source hash differs")
            self._atomic_bytes(raw_path, bundle.raw_text.encode("utf-8"))
            document = bundle.to_dict()
            canonical = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            document["store_sha256"] = hashlib.sha256(canonical).hexdigest()
            payload = json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
            self._atomic_bytes(bundle_path, payload)
            return bundle

    def find(self, video_id: str, variant: str, *, language: str | None = None) -> EvidenceBundle | None:
        """Load a matching saved bundle without invoking an extractor."""
        for path in self.root.glob("*/*/bundle.json"):
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                bundle = EvidenceBundle.from_dict(value)
                if bundle.video_id == video_id and bundle.variant == variant and (
                    language is None or bundle.language == language
                ):
                    loaded = self.load(bundle.platform, video_id, bundle.language, variant)
                    if loaded is not None:
                        return loaded
            except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
                continue
        return None

    def load(self, platform: str, video_id: str, language: str, variant: str) -> EvidenceBundle | None:
        key = self.key(platform, video_id, language, variant)
        path = self.bundle_path(key)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            stored_hash = value.pop("store_sha256", None)
            canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            if not stored_hash or hashlib.sha256(canonical).hexdigest() != stored_hash:
                return None
            bundle = EvidenceBundle.from_dict(value)
            validate_bundle(bundle)
            if bundle.raw_text is not None:
                raw_path = path.with_name("source.raw")
                raw = raw_path.read_bytes()
                if hashlib.sha256(raw).hexdigest() != bundle.raw_sha256 or raw.decode("utf-8") != bundle.raw_text:
                    return None
            return bundle
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            return None

    @staticmethod
    def _atomic_bytes(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        try:
            path.parent.chmod(0o700)
        except OSError:
            pass
        fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_name, path)
        finally:
            if os.path.exists(temp_name):
                os.unlink(temp_name)
