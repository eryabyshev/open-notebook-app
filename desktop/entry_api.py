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

from desktop.runtime_bootstrap import bootstrap

bootstrap()

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
