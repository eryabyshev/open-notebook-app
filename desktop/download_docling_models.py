#!/usr/bin/env python3
"""Prefetch Docling models into desktop/cache/docling-models for PyInstaller bundles."""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    out = Path(
        sys.argv[1] if len(sys.argv) > 1 else root / "desktop" / "cache" / "docling-models"
    ).resolve()
    out.mkdir(parents=True, exist_ok=True)

    if any(out.iterdir()):
        print(f"Docling models already present at {out}")
        return 0

    print(f"Downloading Docling models to {out} …")
    try:
        from docling.utils.model_downloader import download_models

        download_models(output_dir=out, progress=True)
    except ImportError:
        import subprocess

        print("Falling back to docling-tools CLI …")
        subprocess.run(
            ["docling-tools", "models", "download", "-o", str(out)],
            check=True,
        )

    if not any(out.iterdir()):
        print(f"ERROR: download produced an empty directory: {out}", file=sys.stderr)
        return 1

    print(f"Done: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
