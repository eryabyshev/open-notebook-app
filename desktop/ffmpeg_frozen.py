"""Configure bundled ffmpeg for PyInstaller worker/API (podcast audio combine)."""

from __future__ import annotations

import os
import sys
from pathlib import Path


def configure_ffmpeg_for_frozen() -> None:
    """Point imageio-ffmpeg / moviepy at the PyInstaller-bundled ffmpeg binary."""
    if not getattr(sys, "frozen", False):
        return

    exe_dir = Path(sys.executable).resolve().parent
    candidates = [
        exe_dir / "ffmpeg",
        exe_dir / "_internal" / "ffmpeg",
        exe_dir / "imageio_ffmpeg" / "binaries" / "ffmpeg-macos-aarch64-v7.1",  # arm64
        exe_dir / "imageio_ffmpeg" / "binaries" / "ffmpeg-macos-x86_64-v7.1",  # x86_64
    ]

    for path in candidates:
        if path.is_file():
            os.environ["IMAGEIO_FFMPEG_EXE"] = str(path)
            return

    try:
        import imageio_ffmpeg

        bundled = imageio_ffmpeg.get_ffmpeg_exe()
        if bundled and Path(bundled).is_file():
            os.environ["IMAGEIO_FFMPEG_EXE"] = bundled
    except Exception:
        pass
