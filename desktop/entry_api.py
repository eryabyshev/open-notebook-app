#!/usr/bin/env python3
"""
PyInstaller entry point for the Open Notebook API server.

Usage (dev):
    uv run python desktop/entry_api.py

Usage (frozen):
    ./open-notebook-api/open-notebook-api
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _bootstrap() -> None:
    if getattr(sys, "frozen", False):
        os.chdir(Path(sys.executable).resolve().parent)
        return

    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    os.chdir(root)


_bootstrap()

from dotenv import load_dotenv

load_dotenv()

import uvicorn


def main() -> None:
    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "5055"))
    log_level = os.getenv("LOG_LEVEL", "info").lower()

    print(f"Starting Open Notebook API on {host}:{port} (frozen={getattr(sys, 'frozen', False)})")

    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=False,
        log_level=log_level,
    )


if __name__ == "__main__":
    main()
