"""
SMOXI Service – application entry point.

Starts the desktop application or headless bootstrap depending on mode.
"""

from __future__ import annotations

import sys

from app.config.logging import get_logger


def main() -> int:
    """
    Launch SMOXI Service desktop application.

    Returns
    -------
    int
        Process exit code.
    """
    try:
        from app.ui.application import DesktopApplication

        return DesktopApplication().run()
    except Exception:
        logger = get_logger("main")
        logger.exception("Dastur ishga tushirishda xatolik")
        import traceback

        traceback.print_exc(file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
