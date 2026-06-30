#!/usr/bin/env python3
"""
Smoke test for the Next.js standalone frontend on port 8502.

Assumes API is on :5055 and standalone server is already running.

Usage:
  uv run python desktop/smoke_standalone.py
  FRONTEND_URL=http://127.0.0.1:8502 uv run python desktop/smoke_standalone.py
"""

from __future__ import annotations

import os
import sys
import urllib.error
import urllib.request


def check(name: str, url: str, expect_status: int = 200) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            ok = response.status == expect_status
            print(f"  [{'PASS' if ok else 'FAIL'}] {name} — HTTP {response.status}")
            return ok
    except urllib.error.HTTPError as exc:
        print(f"  [FAIL] {name} — HTTP {exc.code}")
        return False
    except Exception as exc:
        print(f"  [FAIL] {name} — {exc}")
        return False


def main() -> int:
    base = os.environ.get("FRONTEND_URL", "http://127.0.0.1:8502").rstrip("/")
    print(f"Smoke test standalone frontend at {base}\n")

    checks = [
        ("GET /", f"{base}/"),
        ("GET /login", f"{base}/login"),
        ("GET /api/config (proxy)", f"{base}/api/config"),
    ]

    ok = all(check(name, url) for name, url in checks)
    if ok:
        print("\nStandalone frontend smoke checks passed.")
        return 0

    print("\nStandalone frontend smoke checks FAILED.")
    print("Start stack first, e.g. OPEN_NOTEBOOK_FRONTEND_MODE=standalone npm run dev")
    return 1


if __name__ == "__main__":
    sys.exit(main())
