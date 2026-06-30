#!/usr/bin/env python3
"""
Smoke test for the Open Notebook worker (dev or PyInstaller build).

Starts the worker briefly and checks that command modules register.

Usage:
  uv run python desktop/smoke_worker.py
  WORKER_BIN=desktop/dist/open-notebook-worker/open-notebook-worker uv run python desktop/smoke_worker.py
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
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
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def main() -> int:
    _load_dotenv()
    root = Path(__file__).resolve().parent.parent
    default_bin = root / "desktop" / "dist" / "open-notebook-worker" / "open-notebook-worker"
    worker_bin = os.environ.get("WORKER_BIN", str(default_bin))

    if worker_bin.endswith(".py") or worker_bin == "dev":
        cmd = [sys.executable, str(root / "desktop" / "entry_worker.py")]
        label = "dev entry_worker.py"
    else:
        path = Path(worker_bin)
        if not path.is_file():
            print(f"Worker binary not found: {path}")
            print("Build first: bash desktop/build_worker.sh")
            return 1
        cmd = [str(path)]
        label = str(path)

    print(f"Smoke test worker: {label}\n")

    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    proc = subprocess.Popen(
        cmd,
        cwd=str(root),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )

    output_lines: list[str] = []
    deadline = time.time() + 12.0
    ok = False

    try:
        while time.time() < deadline:
            if proc.stdout is None:
                break
            line = proc.stdout.readline()
            if line:
                output_lines.append(line.rstrip())
                print(line, end="")
                lower = line.lower()
                if "imported: commands" in lower or "registered commands" in lower:
                    ok = True
                    break
            elif proc.poll() is not None:
                break
            else:
                time.sleep(0.1)
    finally:
        if proc.poll() is None:
            proc.send_signal(signal.SIGINT)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    if ok:
        print("\nWorker smoke check passed (commands module registered).")
        return 0

    print("\nWorker smoke check FAILED.")
    print("Expected output containing 'Imported: commands' or 'registered commands'.")
    if proc.returncode not in (0, -2, 130, None):
        print(f"Exit code: {proc.returncode}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
