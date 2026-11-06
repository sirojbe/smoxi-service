"""Tunnel resolution helpers for staff Mini App HTTPS."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.config.settings import Settings, get_settings
from app.security.secrets import decrypt_secret

TunnelMode = Literal["named", "quick", "external"]


@dataclass(frozen=True, slots=True)
class TunnelPlan:
    """Resolved how to expose the local Mini App."""

    mode: TunnelMode
    public_url: str | None
    tunnel_token: str | None


def _clean(value: str | None) -> str:
    return (value or "").strip().rstrip("/")


def resolve_tunnel_plan(
    *,
    company_public_url: str | None = None,
    company_tunnel_token: str | None = None,
    settings: Settings | None = None,
) -> TunnelPlan:
    """
    Decide tunnel strategy from env + company settings.

    Priority (auto): named (token+URL) → external (fixed URL, non-trycloudflare) → quick.
    """
    cfg = settings or get_settings()
    env_url = _clean(cfg.miniapp_public_url)
    env_token = _clean(cfg.cloudflare_tunnel_token)
    company_url = _clean(company_public_url)
    company_token = decrypt_secret(company_tunnel_token) if company_tunnel_token else ""
    company_token = _clean(company_token)

    public_url = env_url or company_url or None
    token = env_token or company_token or None
    forced = cfg.miniapp_tunnel_mode

    if forced == "quick":
        return TunnelPlan(mode="quick", public_url=None, tunnel_token=None)
    if forced == "named":
        return TunnelPlan(mode="named", public_url=public_url, tunnel_token=token)
    if forced == "external":
        return TunnelPlan(mode="external", public_url=public_url, tunnel_token=None)

    # auto
    if token and public_url:
        return TunnelPlan(mode="named", public_url=public_url, tunnel_token=token)
    if public_url and "trycloudflare.com" not in public_url.lower():
        return TunnelPlan(mode="external", public_url=public_url, tunnel_token=None)
    return TunnelPlan(mode="quick", public_url=None, tunnel_token=None)
