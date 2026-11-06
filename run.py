"""
SMOXI Service – process launcher.

Thin wrapper around ``main.main`` for scripts, packaging, and IDE run configs.
"""

from __future__ import annotations

from main import main


def run() -> int:
    """Launch SMOXI Service and return the process exit code."""
    return main()


if __name__ == "__main__":
    raise SystemExit(run())
