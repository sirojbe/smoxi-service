"""Auto Cloudflare tunnel for staff Mini App HTTPS URL (quick or named)."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import threading
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path

from app.config.logging import get_logger
from app.config.settings import PROJECT_ROOT

logger = get_logger("telegram.tunnel")

_CLOUDFLARED_URL = (
    "https://github.com/cloudflare/cloudflared/releases/latest/download/"
    "cloudflared-windows-amd64.exe"
)
_URL_RE = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")


class CloudflareTunnel:
    """Spawn cloudflared (quick or named token) and expose a public HTTPS URL."""

    def __init__(
        self,
        local_url: str = "http://127.0.0.1:8765",
        *,
        mode: str = "quick",
        tunnel_token: str | None = None,
        public_url: str | None = None,
    ) -> None:
        self._local_url = local_url
        self._mode = mode
        self._tunnel_token = (tunnel_token or "").strip() or None
        self._configured_public = (public_url or "").strip().rstrip("/") or None
        self._proc: subprocess.Popen[str] | None = None
        self._public_url: str | None = None
        self._error: str | None = None
        self._last_output: str = ""
        self._thread: threading.Thread | None = None
        self._generation = 0
        self._on_stopped: Callable[[], None] | None = None

    @property
    def public_url(self) -> str | None:
        return self._public_url

    @property
    def error(self) -> str | None:
        return self._error

    @property
    def is_running(self) -> bool:
        if self._mode == "external":
            return True
        return self._proc is not None and self._proc.poll() is None

    def start_async(
        self,
        on_ready: Callable[[str | None, str | None], None] | None = None,
        *,
        on_stopped: Callable[[], None] | None = None,
    ) -> None:
        self._on_stopped = on_stopped

        def _run() -> None:
            try:
                url = self.start_blocking(timeout=90.0)
                if on_ready:
                    on_ready(url, None if url else self._error)
            except Exception as exc:  # noqa: BLE001
                self._error = str(exc)
                logger.error("Tunnel xatosi: {}", exc)
                if on_ready:
                    on_ready(None, self._error)

        self._thread = threading.Thread(target=_run, name="cloudflared-tunnel", daemon=True)
        self._thread.start()

    def start_blocking(self, *, timeout: float = 90.0) -> str | None:
        """Start tunnel (or bind external URL) and wait until ready."""
        if self._mode == "external":
            if not self._configured_public:
                self._error = "Doimiy Mini App URL sozlanmagan"
                return None
            self._public_url = self._configured_public
            logger.info("Mini App tashqi HTTPS: {}", self._public_url)
            return self._public_url

        if self._mode == "named":
            return self._start_named(timeout=timeout)
        return self._start_quick(timeout=timeout)

    def _start_named(self, *, timeout: float) -> str | None:
        if not self._tunnel_token:
            self._error = "Cloudflare tunnel token sozlanmagan"
            return None
        if not self._configured_public:
            self._error = "Named tunnel uchun doimiy HTTPS URL majburiy"
            return None
        binary = ensure_cloudflared()
        if binary is None:
            self._error = "cloudflared topilmadi"
            return None
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self._proc = subprocess.Popen(
            [str(binary), "tunnel", "run", "--token", self._tunnel_token],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
        assert self._proc.stdout is not None
        # Named tunnels do not print trycloudflare URLs; wait briefly for process survival.
        deadline = time.time() + min(timeout, 25.0)
        while time.time() < deadline:
            if self._proc.poll() is not None:
                exit_code = self._proc.returncode
                detail = f": {self._last_output}" if self._last_output else ""
                self._error = f"named tunnel yopildi (kod={exit_code}){detail}"
                return None
            line = self._proc.stdout.readline()
            if line:
                line = line.strip()
                if line:
                    self._last_output = line
                    logger.debug("cloudflared named: {}", line)
                    lower = line.lower()
                    if "registered" in lower or "connIndex" in line or "connected" in lower:
                        break
            else:
                time.sleep(0.15)
        if self._proc.poll() is not None:
            exit_code = self._proc.returncode
            detail = f": {self._last_output}" if self._last_output else ""
            self._error = f"named tunnel yopildi (kod={exit_code}){detail}"
            return None
        self._public_url = self._configured_public
        logger.info("Mini App named HTTPS: {}", self._public_url)
        generation = self._generation
        threading.Thread(
            target=self._drain_stdout, name="cloudflared-drain", daemon=True
        ).start()
        if self._on_stopped is not None:
            threading.Thread(
                target=self._watch_process,
                args=(generation, self._on_stopped),
                name="cloudflared-watch",
                daemon=True,
            ).start()
        return self._public_url

    def _start_quick(self, *, timeout: float) -> str | None:
        binary = ensure_cloudflared()
        if binary is None:
            self._error = "cloudflared topilmadi"
            return None
        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        self._proc = subprocess.Popen(
            [str(binary), "tunnel", "--url", self._local_url],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
        )
        assert self._proc.stdout is not None
        deadline_chunks = int(timeout * 10)
        for _ in range(max(deadline_chunks, 1)):
            if self._proc.poll() is not None:
                exit_code = self._proc.returncode
                detail = f": {self._last_output}" if self._last_output else ""
                self._error = f"cloudflared jarayoni yopildi (kod={exit_code}){detail}"
                break
            line = self._proc.stdout.readline()
            if not line:
                time.sleep(0.1)
                continue
            line = line.strip()
            if line:
                self._last_output = line
                logger.debug("cloudflared: {}", line)
            match = _URL_RE.search(line)
            if match:
                self._public_url = match.group(0)
                logger.info("Mini App HTTPS: {}", self._public_url)
                generation = self._generation
                threading.Thread(
                    target=self._drain_stdout, name="cloudflared-drain", daemon=True
                ).start()
                if self._on_stopped is not None:
                    threading.Thread(
                        target=self._watch_process,
                        args=(generation, self._on_stopped),
                        name="cloudflared-watch",
                        daemon=True,
                    ).start()
                return self._public_url
        if self._public_url is None and self._error is None:
            detail = f": {self._last_output}" if self._last_output else ""
            self._error = f"HTTPS manzil olinmadi (timeout){detail}"
        return self._public_url

    def _watch_process(self, generation: int, on_stopped: Callable[[], None]) -> None:
        proc = self._proc
        if proc is None:
            return
        proc.wait()
        if generation != self._generation:
            return
        if self._error is None:
            exit_code = proc.returncode
            detail = f": {self._last_output}" if self._last_output else ""
            self._error = f"cloudflared jarayoni yopildi (kod={exit_code}){detail}"
        logger.warning("cloudflared to‘xtadi: {}", self._error)
        on_stopped()

    def _drain_stdout(self) -> None:
        if self._proc is None or self._proc.stdout is None:
            return
        try:
            for _line in self._proc.stdout:
                pass
        except Exception:  # noqa: BLE001
            pass

    def stop(self) -> None:
        self._generation += 1
        if self._mode == "external":
            self._public_url = None
            return
        if self._proc is None:
            return
        try:
            self._proc.terminate()
            self._proc.wait(timeout=5)
        except Exception:  # noqa: BLE001
            try:
                self._proc.kill()
            except Exception:  # noqa: BLE001
                pass
        self._proc = None


def ensure_cloudflared() -> Path | None:
    """Return path to cloudflared binary; download into tools/ if needed."""
    found = shutil.which("cloudflared")
    if found:
        return Path(found)
    tools = PROJECT_ROOT / "tools"
    tools.mkdir(parents=True, exist_ok=True)
    local = tools / "cloudflared.exe"
    if local.is_file() and local.stat().st_size > 1_000_000:
        return local
    logger.info("cloudflared yuklanmoqda…")
    try:
        urllib.request.urlretrieve(_CLOUDFLARED_URL, local)  # noqa: S310 — fixed vendor URL
    except Exception as exc:  # noqa: BLE001
        logger.error("cloudflared yuklanmadi: {}", exc)
        if local.exists():
            try:
                local.unlink()
            except OSError:
                pass
        return None
    if not local.is_file():
        return None
    return local
