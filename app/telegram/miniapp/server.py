"""Background uvicorn host for staff Mini App."""

from __future__ import annotations

import json
import socket
import threading
import urllib.error
import urllib.request
from typing import Any

import uvicorn

from app.config.logging import get_logger
from app.core.container import ServiceContainer
from app.telegram.miniapp.app import create_miniapp

logger = get_logger("telegram.miniapp.server")

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765


class MiniAppServer:
    """Run FastAPI Mini App on a daemon thread."""

    def __init__(
        self,
        container: ServiceContainer,
        *,
        company_id: int,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
    ) -> None:
        self._container = container
        self._company_id = company_id
        self._host = host
        self._port = port
        self._thread: threading.Thread | None = None
        self._server: uvicorn.Server | None = None

    @property
    def local_url(self) -> str:
        return f"http://{self._host}:{self._port}"

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.is_running:
            return
        if _is_miniapp_alive(self._host, self._port):
            logger.info("Mini App server allaqachon ishlayapti: {}", self.local_url)
            return
        if _is_port_busy(self._host, self._port):
            raise RuntimeError(
                f"Mini App porti band: {self.local_url}. Oldin ishlayotgan jarayonni yoping."
            )
        app = create_miniapp(self._container, company_id=self._company_id)
        config = uvicorn.Config(
            app,
            host=self._host,
            port=self._port,
            log_level="warning",
            access_log=False,
        )
        self._server = uvicorn.Server(config)

        def _run() -> None:
            logger.info("Mini App server: {}", self.local_url)
            assert self._server is not None
            self._server.run()

        self._thread = threading.Thread(
            target=_run, name="telegram-miniapp", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        if self._server is not None:
            self._server.should_exit = True
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._thread = None
        self._server = None


_holder: list[MiniAppServer] = []


def _is_port_busy(host: str, port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.3)
        return sock.connect_ex((host, port)) == 0


def _is_miniapp_alive(host: str, port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://{host}:{port}/api/health", timeout=1.0) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return False
    return payload.get("status") == "ok"


def start_miniapp_server(
    container: ServiceContainer,
    company_id: int,
    *,
    holder: list[MiniAppServer] | None = None,
    port: int = DEFAULT_PORT,
) -> MiniAppServer:
    """Start (or replace) Mini App server; keep reference in *holder*."""
    target: list[MiniAppServer] = holder if holder is not None else _holder
    if target:
        target[0].stop()
        target.clear()
    server = MiniAppServer(container, company_id=company_id, port=port)
    server.start()
    target.append(server)
    return server


def stop_miniapp_servers(holder: list[Any] | None = None) -> None:
    target: list[Any] = holder if holder is not None else _holder
    for item in list(target):
        if hasattr(item, "stop"):
            item.stop()
    target.clear()
