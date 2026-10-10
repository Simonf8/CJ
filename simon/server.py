from __future__ import annotations

import json
import logging
import mimetypes
import os
import queue
import secrets
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, Optional
from urllib.parse import urlparse

from .config import HUD_DIR
from .events import EventBus

log = logging.getLogger(__name__)

mimetypes.add_type("font/woff2", ".woff2")
mimetypes.add_type("text/javascript", ".js")

Api = Dict[str, Callable[[Dict[str, Any]], Any]]


class HudServer:
    def __init__(self, bus: EventBus, api: Api, host: str = "127.0.0.1", port: int = 47800):
        self.bus = bus
        self.api = api
        self.host = host
        self.port = port
        self.token = secrets.token_urlsafe(24)
        self._httpd: Optional[ThreadingHTTPServer] = None

    @property
    def url(self) -> str:
        return f"http://{self.host}:{self.port}/"

    def start(self) -> None:
        handler = type("Handler", (_Handler,), {"server_ref": self})
        for _ in range(10):
            try:
                self._httpd = ThreadingHTTPServer((self.host, self.port), handler)
                break
            except OSError:
                self.port += 1
        else:
            raise RuntimeError("No free port for the HUD server")
        self._httpd.daemon_threads = True
        threading.Thread(target=self._httpd.serve_forever, name="hud-server", daemon=True).start()
        log.info("HUD online at %s", self.url)

    def stop(self) -> None:
        if self._httpd:
            self._httpd.shutdown()


class _Handler(BaseHTTPRequestHandler):
    server_ref: HudServer
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: Any) -> None:
        log.debug("http " + fmt, *args)

    def _host_ok(self) -> bool:
        host = (self.headers.get("Host") or "").split(":")[0]
        return host in {"127.0.0.1", "localhost"}

    def _send(self, status: int, body: bytes, ctype: str, extra: Optional[Dict[str, str]] = None) -> None:
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: int, payload: Any) -> None:
        self._send(status, json.dumps(payload).encode(), "application/json")

    def do_GET(self) -> None:
        if not self._host_ok():
            return self._json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})
        path = urlparse(self.path).path
        if path == "/events":
            return self._stream()
        if path in ("/", "/index.html"):
            return self._index()
        return self._static(path)

    def _index(self) -> None:
        with open(os.path.join(HUD_DIR, "index.html"), "rb") as f:
            html = f.read().replace(b"__SIMON_TOKEN__", self.server_ref.token.encode())
        self._send(HTTPStatus.OK, html, "text/html; charset=utf-8",
                   {"Content-Security-Policy": "default-src 'self'; style-src 'self' 'unsafe-inline'; "
                                               "img-src 'self' data:; connect-src 'self'"})

    def _static(self, path: str) -> None:
        root = os.path.realpath(HUD_DIR)
        full = os.path.realpath(os.path.join(root, path.lstrip("/")))
        if not full.startswith(root + os.sep) or not os.path.isfile(full):
            return self._json(HTTPStatus.NOT_FOUND, {"error": "not found"})
        ctype = mimetypes.guess_type(full)[0] or "application/octet-stream"
        with open(full, "rb") as f:
            self._send(HTTPStatus.OK, f.read(), ctype)

    def _stream(self) -> None:
        bus = self.server_ref.bus
        q = bus.subscribe_queue()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        try:
            self.wfile.write(b"retry: 1500\n\n")
            while True:
                try:
                    event = q.get(timeout=15)
                    self.wfile.write(b"data: " + json.dumps(event).encode() + b"\n\n")
                except queue.Empty:
                    self.wfile.write(b": keepalive\n\n")
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            bus.unsubscribe_queue(q)

    def do_POST(self) -> None:
        if not self._host_ok() or self.headers.get("X-Simon-Token") != self.server_ref.token:
            return self._json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})
        name = urlparse(self.path).path.removeprefix("/api/")
        handler = self.server_ref.api.get(name)
        if handler is None:
            return self._json(HTTPStatus.NOT_FOUND, {"error": "unknown endpoint"})
        try:
            length = min(int(self.headers.get("Content-Length") or 0), 64 * 1024)
            body = json.loads(self.rfile.read(length) or b"{}") if length else {}
            result = handler(body if isinstance(body, dict) else {})
        except Exception as exc:
            log.exception("API %s failed", name)
            return self._json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": str(exc)})
        self._json(HTTPStatus.OK, {"ok": True, "result": result})
