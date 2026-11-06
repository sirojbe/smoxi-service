"""Start Mini App server + auto HTTPS tunnel and persist URL."""

from __future__ import annotations

import json
import ssl
import threading
import time
import urllib.error
import urllib.request

from app.config.logging import get_logger
from app.core.container import ServiceContainer
from app.modules.settings.services.settings_service import SettingsService
from app.telegram.client import TelegramClient, TelegramClientError
from app.telegram.miniapp.server import MiniAppServer, start_miniapp_server
from app.telegram.miniapp.tunnel import CloudflareTunnel
from app.telegram.runtime_status import (
    get_telegram_runtime_status,
    set_bot_status,
    set_tunnel_reachable,
    set_tunnel_status,
)
from app.telegram.staff_bot import sync_staff_menu_button

logger = get_logger("telegram.bootstrap")

_tunnels: list[CloudflareTunnel] = []
_ctx_lock = threading.Lock()
_health_lock = threading.Lock()
_ctx: dict[str, object] = {}

_TUNNEL_GRACE_SECONDS = 60.0
_TUNNEL_PROBE_ATTEMPTS = 4
_TUNNEL_PROBE_DELAY_SECONDS = 6.0
_MIN_RESTART_INTERVAL_SECONDS = 180.0
_MAX_FAILURES_BEFORE_RESTART = 6

_tunnel_meta = {
    "url_created_at": 0.0,
    "last_restart_at": 0.0,
    "consecutive_failures": 0,
}


def probe_local_health(local_url: str = "http://127.0.0.1:8765", *, timeout: float = 3.0) -> bool:
    """Return True when the local Mini App responds."""
    url = f"{local_url.rstrip('/')}/api/health"
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
            if resp.status != 200:
                return False
            payload = json.loads(resp.read().decode("utf-8"))
    except (OSError, ValueError, urllib.error.URLError):
        return False
    return payload.get("status") == "ok"


def probe_tunnel_health(
    public_url: str,
    *,
    timeout: float = 12.0,
    attempts: int = _TUNNEL_PROBE_ATTEMPTS,
    delay: float = _TUNNEL_PROBE_DELAY_SECONDS,
) -> bool:
    """Return True when the public Mini App health endpoint responds."""
    url = f"{public_url.rstrip('/')}/api/health"
    ctx = ssl.create_default_context()
    tries = max(attempts, 1)
    for attempt in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SMOXI-Service"})
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:  # noqa: S310
                if resp.status != 200:
                    logger.debug("Tunnel probe HTTP {}: {}", resp.status, url)
                else:
                    payload = json.loads(resp.read().decode("utf-8"))
                    if payload.get("status") == "ok":
                        return True
        except urllib.error.HTTPError as exc:
            logger.debug("Tunnel probe HTTPError {}: {}", exc.code, url)
        except (OSError, ValueError, urllib.error.URLError) as exc:
            logger.debug("Tunnel probe {}: {}", type(exc).__name__, url)
        if attempt < tries - 1:
            time.sleep(delay)
    return False


def check_bot_token(container: ServiceContainer, company_id: int) -> None:
    """Update runtime bot status via getMe."""
    db = container.create_session()
    try:
        company = SettingsService(db).get_company(company_id)
        from app.security.secrets import company_bot_token

        token = company_bot_token(company)
        if not token:
            set_bot_status("no_token", "")
            return
        try:
            body = TelegramClient(token).get_me()
            result = body.get("result") if isinstance(body, dict) else {}
            username = ""
            if isinstance(result, dict):
                username = str(result.get("username") or "")
            set_bot_status("ok", username)
        except TelegramClientError as exc:
            set_bot_status("fail", str(exc))
    except Exception as exc:  # noqa: BLE001
        set_bot_status("fail", str(exc))
    finally:
        db.close()


def _remember_ctx(
    container: ServiceContainer,
    company_id: int,
    *,
    server_holder: list[MiniAppServer],
    tunnel_holder: list[CloudflareTunnel],
) -> None:
    with _ctx_lock:
        _ctx.clear()
        _ctx.update(
            {
                "container": container,
                "company_id": company_id,
                "server_holder": server_holder,
                "tunnel_holder": tunnel_holder,
            }
        )


def _mark_url_created() -> None:
    _tunnel_meta["url_created_at"] = time.time()
    _tunnel_meta["consecutive_failures"] = 0


def _sync_menu_when_online(container: ServiceContainer, company_id: int, url: str) -> None:
    db = container.create_session()
    try:
        company = SettingsService(db).get_company(company_id)
        company.telegram_mini_app_url = url.rstrip("/")
        from app.security.secrets import company_bot_token

        token = company_bot_token(company)
        if token:
            sync_staff_menu_button(TelegramClient(token), company)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Menu button yangilanmadi: {}", exc)
    finally:
        db.close()


def _verify_tunnel_later(container: ServiceContainer, company_id: int, url: str) -> None:
    """Wait for Cloudflare DNS, then verify public reachability."""
    time.sleep(15.0)
    if probe_tunnel_health(url, attempts=3, delay=5.0):
        set_tunnel_status("ok", url, "")
        set_tunnel_reachable(True)
        _tunnel_meta["consecutive_failures"] = 0
        _sync_menu_when_online(container, company_id, url)
        logger.info("Mini App tunnel tasdiqlandi: {}", url)
        return
    set_tunnel_reachable(False)
    set_tunnel_status("ok", url, tr_public_unreachable())
    logger.warning("Tunnel URL hali tashqidan ochilmadi: {}", url)


def _persist_tunnel_url(container: ServiceContainer, company_id: int, url: str) -> None:
    _mark_url_created()
    set_tunnel_status("ok", url, tr_checking())
    set_tunnel_reachable(False)
    db = container.create_session()
    try:
        SettingsService(db).set_mini_app_url(company_id, url)
        db.commit()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.error("Mini App URL saqlanmadi: {}", exc)
    finally:
        db.close()
    threading.Thread(
        target=_verify_tunnel_later,
        args=(container, company_id, url),
        name="tunnel-verify",
        daemon=True,
    ).start()


def _start_tunnel(
    container: ServiceContainer,
    company_id: int,
    local_url: str,
    tunnel_holder: list[CloudflareTunnel],
    *,
    restarting: bool = False,
) -> CloudflareTunnel:
    for old in list(tunnel_holder):
        old.stop()
    tunnel_holder.clear()
    if restarting:
        _tunnel_meta["last_restart_at"] = time.time()
        set_tunnel_status("starting", detail=tr_restart_detail())
        set_tunnel_reachable(False)

    company_url = None
    company_token = None
    db = container.create_session()
    try:
        company = SettingsService(db).get_company(company_id)
        company_url = company.telegram_mini_app_url
        company_token = company.cloudflare_tunnel_token
    except Exception as exc:  # noqa: BLE001
        logger.warning("Tunnel sozlamalari o‘qilmadi: {}", exc)
    finally:
        db.close()

    from app.telegram.miniapp.tunnel_plan import resolve_tunnel_plan

    plan = resolve_tunnel_plan(
        company_public_url=company_url,
        company_tunnel_token=company_token,
    )
    tunnel = CloudflareTunnel(
        local_url,
        mode=plan.mode,
        tunnel_token=plan.tunnel_token,
        public_url=plan.public_url,
    )
    tunnel_holder.append(tunnel)
    logger.info("Mini App tunnel rejimi: {}", plan.mode)

    def _on_ready(url: str | None, error: str | None) -> None:
        if not url:
            set_tunnel_status("fail", detail=error or "")
            set_tunnel_reachable(False)
            logger.warning("Tunnel URL olinmadi: {}", error)
            return
        _persist_tunnel_url(container, company_id, url)

    def _on_stopped() -> None:
        if plan.mode == "external":
            return
        set_tunnel_status("fail", detail="cloudflared to‘xtadi")
        set_tunnel_reachable(False)
        ensure_tunnel_health()

    tunnel.start_async(_on_ready, on_stopped=_on_stopped)
    return tunnel


def start_miniapp_with_tunnel(
    container: ServiceContainer,
    company_id: int,
    *,
    server_holder: list[MiniAppServer],
    tunnel_holder: list[CloudflareTunnel] | None = None,
) -> MiniAppServer:
    """Start local Mini App and auto-open Cloudflare tunnel; write URL to DB."""
    tunnels = tunnel_holder if tunnel_holder is not None else _tunnels
    _remember_ctx(container, company_id, server_holder=server_holder, tunnel_holder=tunnels)
    set_tunnel_status("starting", detail="")
    set_tunnel_reachable(False)
    server = start_miniapp_server(container, company_id, holder=server_holder)
    _start_tunnel(container, company_id, server.local_url, tunnels)
    return server


def ensure_tunnel_health() -> None:
    """Verify tunnel process + public URL; restart only after repeated failures."""
    if not _health_lock.acquire(blocking=False):
        return
    try:
        with _ctx_lock:
            if not _ctx:
                return
            container = _ctx["container"]
            company_id = int(_ctx["company_id"])
            server_holder = _ctx["server_holder"]
            tunnel_holder = _ctx["tunnel_holder"]

        status = get_telegram_runtime_status()
        tunnels: list[CloudflareTunnel] = tunnel_holder  # type: ignore[assignment]
        servers: list[MiniAppServer] = server_holder  # type: ignore[assignment]
        local_url = servers[0].local_url if servers else "http://127.0.0.1:8765"

        if status.tunnel == "starting":
            tunnel = tunnels[0] if tunnels else None
            if tunnel and tunnel.is_running and tunnel.public_url:
                age = time.time() - _tunnel_meta["url_created_at"]
                if age > _TUNNEL_GRACE_SECONDS:
                    set_tunnel_status("ok", tunnel.public_url, tr_checking())
            return

        if not probe_local_health(local_url):
            set_tunnel_status("fail", detail="Lokal Mini App server ishlamayapti")
            set_tunnel_reachable(False)
            return

        if not tunnels or not tunnels[0].is_running:
            if time.time() - _tunnel_meta["last_restart_at"] < _MIN_RESTART_INTERVAL_SECONDS:
                return
            logger.info("cloudflared ishlamayapti, qayta ishga tushirilmoqda…")
            _start_tunnel(
                container,
                company_id,
                local_url,
                tunnels,
                restarting=True,
            )  # type: ignore[arg-type]
            return

        public_url = (tunnels[0].public_url or status.mini_url or "").strip()
        if not public_url:
            return

        age = time.time() - _tunnel_meta["url_created_at"]
        if age < _TUNNEL_GRACE_SECONDS:
            return

        if probe_tunnel_health(public_url, attempts=2, delay=4.0):
            set_tunnel_status("ok", public_url, "")
            set_tunnel_reachable(True)
            _tunnel_meta["consecutive_failures"] = 0
            _sync_menu_when_online(container, company_id, public_url)
            return

        _tunnel_meta["consecutive_failures"] += 1
        set_tunnel_reachable(False)
        set_tunnel_status("ok", public_url, tr_public_unreachable())
        logger.warning(
            "Tunnel tashqidan ochilmadi ({} marta): {}",
            _tunnel_meta["consecutive_failures"],
            public_url,
        )

        if (
            _tunnel_meta["consecutive_failures"] >= _MAX_FAILURES_BEFORE_RESTART
            and time.time() - _tunnel_meta["last_restart_at"] >= _MIN_RESTART_INTERVAL_SECONDS
        ):
            logger.warning("Tunnel qayta ishga tushiriladi: {}", public_url)
            _start_tunnel(
                container,
                company_id,
                local_url,
                tunnels,
                restarting=True,
            )  # type: ignore[arg-type]
    finally:
        _health_lock.release()


def tr_restart_detail() -> str:
    from app.localization.translator import tr

    return tr("settings.mini_app_restarting")


def tr_checking() -> str:
    from app.localization.translator import tr

    return tr("settings.mini_app_checking")


def tr_public_unreachable() -> str:
    from app.localization.translator import tr

    return tr("settings.mini_app_public_unreachable")


def shutdown_miniapp_tunnel(container: ServiceContainer, company_id: int) -> None:
    """Stop tunnel and clear stale public URL from Telegram menu."""
    for item in list(_tunnels):
        item.stop()
    _tunnels.clear()
    with _ctx_lock:
        tunnel_holder = _ctx.get("tunnel_holder")
        if isinstance(tunnel_holder, list):
            for item in list(tunnel_holder):
                if hasattr(item, "stop"):
                    item.stop()
            tunnel_holder.clear()
        _ctx.clear()

    _tunnel_meta["url_created_at"] = 0.0
    _tunnel_meta["consecutive_failures"] = 0
    set_tunnel_status("idle", url="", detail="")
    set_tunnel_reachable(False)
    db = container.create_session()
    try:
        company = SettingsService(db).get_company(company_id)
        current = (company.telegram_mini_app_url or "").strip()
        # Doimiy/named URL ni o‘chirmaymiz — faqat ephemeral trycloudflare.
        if current and "trycloudflare.com" in current.lower():
            company = SettingsService(db).set_mini_app_url(company_id, None)
            db.commit()
        else:
            db.commit()
        from app.security.secrets import company_bot_token

        token = company_bot_token(company)
        if token and current and "trycloudflare.com" in current.lower():
            try:
                TelegramClient(token).clear_chat_menu_button()
            except TelegramClientError as exc:
                logger.warning("Menu button tozalanmadi: {}", exc)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.warning("Mini App URL tozalanmadi: {}", exc)
    finally:
        db.close()


def stop_tunnels(holder: list[CloudflareTunnel] | None = None) -> None:
    target = holder if holder is not None else _tunnels
    for item in list(target):
        item.stop()
    target.clear()


__all__ = [
    "check_bot_token",
    "ensure_tunnel_health",
    "probe_local_health",
    "probe_tunnel_health",
    "shutdown_miniapp_tunnel",
    "start_miniapp_with_tunnel",
    "stop_tunnels",
]
