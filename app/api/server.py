"""
Run SMOXI HTTP API (uvicorn).

Usage:
  python -m app.api.server
  # or
  python scripts/run_api.py
"""

from __future__ import annotations

import uvicorn

from app.api.app import create_api_app
from app.config.settings import get_settings


def main() -> None:
    settings = get_settings()
    app = create_api_app()
    host = "127.0.0.1"
    port = 8787
    print(f"SMOXI API {settings.app_version} → http://{host}:{port}/api/docs")
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
