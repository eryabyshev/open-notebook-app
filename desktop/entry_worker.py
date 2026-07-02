#!/usr/bin/env python3
"""
PyInstaller entry point for the Open Notebook surreal-commands worker.

Usage (dev):
    uv run python desktop/entry_worker.py

Usage (frozen):
    ./open-notebook-worker/open-notebook-worker

Equivalent to:
    surreal-commands-worker --import-modules commands
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _handle_frozen_multiprocessing_child() -> None:
    """
    Torch/docling spawn worker children by re-execing the PyInstaller binary with
    ``-B -S -c "from multiprocessing.spawn import spawn_main; ..."``.

    Those children must not enter the surreal-commands typer CLI.
    """
    if not _is_frozen():
        return

    argv_text = " ".join(sys.argv)
    if not (
        "--multiprocessing-fork" in sys.argv
        or "multiprocessing.spawn" in argv_text
        or "multiprocessing.resource_tracker" in argv_text
        or "-c" in sys.argv
    ):
        return

    import multiprocessing

    multiprocessing.freeze_support()
    from multiprocessing.spawn import spawn_main

    spawn_main()
    raise SystemExit(0)


def _sanitize_frozen_argv() -> None:
    """
    Drop Python interpreter flags from sys.argv in frozen builds.

    Leftover flags (e.g. ``-B``, ``-S``) make typer fail with "No such option".
    """
    if not _is_frozen() or len(sys.argv) <= 1:
        return

    cleaned = [sys.argv[0]]
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("--"):
            cleaned.append(arg)
            i += 1
            continue
        if arg in ("-c", "-m"):
            i += 2
            continue
        if arg.startswith("-") and arg[1:2].isalpha():
            # -B, -S, -Werror, -Xutf8, etc.
            i += 1
            continue
        cleaned.append(arg)
        i += 1
    sys.argv = cleaned


def _prepend_repo_root() -> None:
    """Allow `import desktop` when running `python desktop/entry_*.py` from repo root."""
    if getattr(sys, "frozen", False):
        return
    root = Path(__file__).resolve().parent.parent
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)


_prepend_repo_root()
_handle_frozen_multiprocessing_child()
_sanitize_frozen_argv()

if _is_frozen():
    import multiprocessing

    multiprocessing.freeze_support()

from desktop.runtime_bootstrap import bootstrap

bootstrap()

from desktop.ffmpeg_frozen import configure_ffmpeg_for_frozen

configure_ffmpeg_for_frozen()

from dotenv import load_dotenv

load_dotenv()

from open_notebook.utils.docling_frozen import configure_docling_for_frozen

configure_docling_for_frozen()

from open_notebook.utils.docling_patch import apply_docling_patch

apply_docling_patch()

from commands import register_commands
from desktop.esperanto_frozen_imports import preload_esperanto_providers

preload_esperanto_providers()

from open_notebook.utils.gemini_tts import (
    apply_gemini_tts_patch,
    apply_podcast_clip_fixup_patch,
)

apply_gemini_tts_patch()
apply_podcast_clip_fixup_patch()

try:
    from surreal_commands.cli.worker import main
except ModuleNotFoundError as exc:
    if exc.name == "typer":
        raise SystemExit(
            "Missing Python dependency 'typer'. From repo root run:\n"
            "  uv sync\n"
            "or:\n"
            "  bash desktop/ensure_deps.sh"
        ) from exc
    raise


def _default_argv() -> None:
    """Match supervisord / Makefile: import commands from the app package."""
    if len(sys.argv) == 1:
        sys.argv.extend(["--import-modules", "commands"])

    # Optional env override (comma-separated module names)
    env_modules = os.environ.get("SURREAL_COMMANDS_MODULES", "").strip()
    if env_modules and "--import-modules" not in sys.argv:
        sys.argv.extend(["--import-modules", env_modules])


def run() -> None:
    _default_argv()
    register_commands()
    frozen = getattr(sys, "frozen", False)
    print(f"Starting Open Notebook worker (frozen={frozen})")
    if frozen:
        from open_notebook.utils.docling_frozen import resolve_docling_artifacts_path

        artifacts = resolve_docling_artifacts_path()
        if artifacts:
            print(f"Docling artifacts: {artifacts}")
        else:
            print("WARNING: Docling artifacts not found in bundle — OCR may fail offline")
    main()


if __name__ == "__main__":
    run()
