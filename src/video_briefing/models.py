from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class TranscriptSegment:
    id: str
    text: str
    start_seconds: float
    duration_seconds: float
    source_speaker: str | None = None
    speaker_certainty: str = "unknown"


@dataclass
class EvidenceBundle:
    platform: str
    video_id: str
    url: str
    language: str
    variant: str
    source_type: str
    extractor_version: str
    segments: list[TranscriptSegment]
    raw_sha256: str
    fetched_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    raw_text: str | None = field(default=None, repr=False)

    @property
    def key(self) -> str:
        from .store import ArtifactStore

        return ArtifactStore.key(self.platform, self.video_id, self.language, self.variant)

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "video_id": self.video_id,
            "url": self.url,
            "language": self.language,
            "variant": self.variant,
            "source_type": self.source_type,
            "extractor_version": self.extractor_version,
            "segments": [asdict(segment) for segment in self.segments],
            "raw_sha256": self.raw_sha256,
            "fetched_at": self.fetched_at,
            "metadata": self.metadata,
            "warnings": self.warnings,
            "raw_text": self.raw_text,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EvidenceBundle":
        return cls(
            **{key: value[key] for key in (
                "platform", "video_id", "url", "language", "variant", "source_type",
                "extractor_version", "raw_sha256"
            )},
            segments=[TranscriptSegment(**segment) for segment in value["segments"]],
            fetched_at=value.get("fetched_at"),
            metadata=value.get("metadata", {}),
            warnings=value.get("warnings", []),
            raw_text=value.get("raw_text"),
        )
