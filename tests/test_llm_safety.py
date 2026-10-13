import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from video_briefing.llm import OllamaClient


def test_llm_client_ignores_proxy_environment_and_refuses_redirect(monkeypatch):
    hits = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length", "0")))
            hits.append(self.path)
            if self.path == "/api/chat":
                self.send_response(302)
                self.send_header("Location", "/collect")
                self.end_headers()
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'{"message":{"content":"{}"}}')

        def log_message(self, format, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:1")
        monkeypatch.setenv("http_proxy", "http://127.0.0.1:1")
        client = OllamaClient(f"http://127.0.0.1:{server.server_port}", "local")
        with pytest.raises(RuntimeError, match="request failed"):
            client.generate_json(system="private", prompt="transcript sentinel")
        assert hits == ["/api/chat"]
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()
