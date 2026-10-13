from __future__ import annotations

import json
import hashlib
import re
import time
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener


class JsonLLM(Protocol):
    model: str

    def generate_json(self, *, system: str, prompt: str, timeout: float = 180, schema: dict[str, Any] | None = None) -> dict[str, Any]: ...


def _parse_json_object(message: Any) -> dict[str, Any]:
    candidate = message.strip() if isinstance(message, str) else message
    if isinstance(candidate, str):
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", candidate, flags=re.DOTALL)
        if fenced:
            candidate = fenced.group(1)

        def quote_bare_ids(match: re.Match[str]) -> str:
            body = re.sub(r"(?<![\w\"])([A-Za-z][A-Za-z0-9_-]*\d+)(?![\w\"])", r'"\1"', match.group(2))
            return match.group(1) + body + match.group(3)

        candidate = re.sub(r'("(?:gist_evidence|evidence)"\s*:\s*\[)([^\]]*)(\])', quote_bare_ids, candidate)
        # Some providers emit LaTeX-like text such as ``\approx`` inside JSON strings.
        # Escape only backslashes that cannot begin a JSON escape; preserve valid JSON escapes.
        candidate = re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', candidate)
    value = json.loads(candidate)
    if not isinstance(value, dict):
        raise ValueError("Ollama response JSON must be an object")
    return value


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class OllamaClient:
    def __init__(self, base_url: str, model: str, temperature: float = 0.0, timeout: float = 180):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout
        self.last_response: dict[str, Any] = {}
        self.responses: list[dict[str, Any]] = []
        self._opener = build_opener(ProxyHandler({}), _NoRedirect())

    def generate_json(self, *, system: str, prompt: str, timeout: float | None = None, schema: dict[str, Any] | None = None) -> dict[str, Any]:
        request_body = {
            "model": self.model,
            "stream": False,
            "format": schema or "json",
            "options": {"temperature": self.temperature},
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
        }
        request = Request(f"{self.base_url}/api/chat", data=json.dumps(request_body).encode(),
                          headers={"Content-Type": "application/json"}, method="POST")
        started = time.perf_counter()
        try:
            with self._opener.open(request, timeout=timeout or self.timeout) as response:
                self.last_response = json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc
        self.responses.append({
            "requested_model": self.model,
            "returned_model": self.last_response.get("model"),
            "prompt_sha256": hashlib.sha256((system + "\0" + prompt).encode("utf-8")).hexdigest(),
            "system_sha256": hashlib.sha256(system.encode("utf-8")).hexdigest(),
            "schema_sha256": hashlib.sha256(json.dumps(schema, sort_keys=True).encode("utf-8")).hexdigest() if schema else None,
            "prompt_tokens": self.last_response.get("prompt_eval_count"),
            "completion_tokens": self.last_response.get("eval_count"),
            "elapsed_seconds": time.perf_counter() - started,
            "cloud_backed": self.model.endswith("-cloud"),
        })
        message = self.last_response.get("message", {}).get("content", "")
        try:
            return _parse_json_object(message)
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            preview = repr(message)[:2000]
            actual_model = self.last_response.get("model")
            parse_detail = f"{exc.msg} at line {exc.lineno}, column {exc.colno}" if isinstance(exc, json.JSONDecodeError) else str(exc)
            raise RuntimeError(f"Ollama returned non-JSON content despite JSON mode; model={actual_model!r}, parse={parse_detail}, content_chars={len(message) if isinstance(message, str) else 'n/a'}, content={preview}") from exc
