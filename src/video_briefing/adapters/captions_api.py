from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from importlib.metadata import version

import requests
from youtube_transcript_api._errors import CookieError, IpBlocked, NoTranscriptFound, RequestBlocked, TranscriptsDisabled
from youtube_transcript_api import YouTubeTranscriptApi

from ..models import EvidenceBundle, TranscriptSegment
from ..validation import parse_video_url, validate_bundle


class CaptionSourceUnavailable(RuntimeError):
    """Safe-to-report error when the requested caption track is unavailable."""


class CaptionSourceBlocked(RuntimeError):
    """Safe-to-report error when YouTube blocks the anonymous network request."""


class CaptionAuthenticationRequired(RuntimeError):
    """Safe-to-report error when YouTube requires cookies or authentication."""


class _TimeoutSession(requests.Session):
    def request(self, *args, **kwargs):
        kwargs.setdefault("timeout", (10, 30))
        return super().request(*args, **kwargs)


def extract(url: str, *, language: str = "ru") -> EvidenceBundle:
    platform, video_id, canonical_url = parse_video_url(url)
    session = _TimeoutSession()
    # Do not inherit proxy/netrc settings or cookies from the user's environment.
    session.trust_env = False
    session.cookies.clear()
    try:
        try:
            fetched = YouTubeTranscriptApi(http_client=session).fetch(video_id, languages=[language])
        except (NoTranscriptFound, TranscriptsDisabled) as exc:
            raise CaptionSourceUnavailable(f"No captions are available for video {video_id!r} in language {language!r}; description-only fallback is forbidden") from exc
        except (IpBlocked, RequestBlocked) as exc:
            raise CaptionSourceBlocked("YouTube blocked this network/IP request; retry later or stop—proxy/cookie bypass is not supported") from exc
        except CookieError as exc:
            raise CaptionAuthenticationRequired("YouTube requires authentication/cookies for this source; this workflow does not read or use cookies") from exc
    finally:
        session.close()

    raw_segments = fetched.to_raw_data()
    if fetched.language_code.lower().split("-")[0] != language.lower().split("-")[0]:
        raise ValueError(
            f"Caption track language {fetched.language_code!r} does not match requested {language!r}"
        )
    raw_text = json.dumps(raw_segments, ensure_ascii=False, separators=(",", ":"))
    segments = [
        TranscriptSegment(
            id=f"s{index:05d}",
            text=str(item["text"]),
            start_seconds=float(item["start"]),
            duration_seconds=float(item["duration"]),
        )
        for index, item in enumerate(raw_segments, 1)
    ]
    extracted_version = version("youtube-transcript-api")
    source_type = "auto-captions" if fetched.is_generated else "manual-captions"
    bundle = EvidenceBundle(
        platform=platform,
        video_id=video_id,
        url=canonical_url,
        language=fetched.language_code,
        variant="captions_api",
        source_type=source_type,
        extractor_version=f"youtube-transcript-api-{extracted_version}",
        segments=segments,
        raw_sha256=hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
        fetched_at=datetime.now(timezone.utc).isoformat(),
        metadata={
            "transcript_language": fetched.language,
            "language_code": fetched.language_code,
            "is_generated": fetched.is_generated,
            "segment_count": len(segments),
            "timeout_seconds": {"connect": 10, "read": 30},
            "proxy_enabled": False,
            "browser_cookies_used": False,
        },
        raw_text=raw_text,
    )
    validate_bundle(bundle)
    return bundle
