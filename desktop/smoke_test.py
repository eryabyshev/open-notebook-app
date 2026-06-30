#!/usr/bin/env python3
"""
Smoke tests for the Open Notebook API (dev or PyInstaller build).

Prerequisites:
  - SurrealDB running (default ws://127.0.0.1:8000/rpc)
  - API running on API_URL (default http://127.0.0.1:5055)
  - OPEN_NOTEBOOK_ENCRYPTION_KEY set in environment or .env

Usage:
  uv run python desktop/smoke_test.py
  API_URL=http://127.0.0.1:5055 uv run python desktop/smoke_test.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def _load_dotenv() -> None:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


def request(
    method: str,
    url: str,
    *,
    data: dict | None = None,
    headers: dict | None = None,
    timeout: float = 30.0,
) -> tuple[int, dict | str]:
    body = None
    req_headers = dict(headers or {})
    if data is not None:
        body = json.dumps(data).encode("utf-8")
        req_headers.setdefault("Content-Type", "application/json")

    req = urllib.request.Request(url, data=body, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8")
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, raw


def auth_headers() -> dict[str, str]:
    password = os.environ.get("OPEN_NOTEBOOK_PASSWORD", "").strip()
    if not password:
        return {}
    return {"Authorization": f"Bearer {password}"}


def main() -> int:
    _load_dotenv()
    base = os.environ.get("API_URL", "http://127.0.0.1:5055").rstrip("/")
    headers = auth_headers()
    failures: list[str] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))
        if not ok:
            failures.append(name)

    print(f"Smoke test against {base}\n")

    # 1. Config
    code, payload = request("GET", f"{base}/api/config", headers=headers)
    check(
        "GET /api/config",
        code == 200 and isinstance(payload, dict) and "version" in payload,
        f"HTTP {code}, version={payload.get('version') if isinstance(payload, dict) else payload}",
    )
    if isinstance(payload, dict):
        db_status = payload.get("dbStatus")
        check("Database online", db_status == "online", f"dbStatus={db_status}")

    # 2. OpenAPI docs
    code, _ = request("GET", f"{base}/docs", headers=headers, timeout=10)
    check("GET /docs", code == 200, f"HTTP {code}")

    # 3. Create notebook
    code, payload = request(
        "POST",
        f"{base}/api/notebooks",
        data={"name": "PyInstaller Spike", "description": "desktop smoke test"},
        headers=headers,
    )
    notebook_id = None
    if code == 200 and isinstance(payload, dict):
        notebook_id = payload.get("id") or payload.get("data", {}).get("id")
    check("POST /api/notebooks", code in (200, 201) and bool(notebook_id), f"HTTP {code}")

    # 4. List notebooks
    code, payload = request("GET", f"{base}/api/notebooks", headers=headers)
    has_notebooks = (
        code == 200
        and isinstance(payload, list)
        and len(payload) > 0
    ) or (
        code == 200
        and isinstance(payload, dict)
        and len(payload.get("data", payload.get("notebooks", []))) > 0
    )
    check("GET /api/notebooks", has_notebooks, f"HTTP {code}")

    # 5. Cleanup notebook
    if notebook_id:
        del_code, _ = request("DELETE", f"{base}/api/notebooks/{notebook_id}", headers=headers)
        check("DELETE /api/notebooks/{id}", del_code in (200, 204), f"HTTP {del_code}")

    print()
    if failures:
        print(f"FAILED ({len(failures)}): {', '.join(failures)}")
        return 1

    print("All smoke checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
