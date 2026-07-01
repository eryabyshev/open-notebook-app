"""Docling / docling-parse configuration for PyInstaller (frozen) desktop builds."""

from __future__ import annotations

import os
from pathlib import Path


def configure_docling_for_frozen() -> None:
    """
    Point docling-parse at bundled pdf_resources_v2 when running from PyInstaller.

    Without this, frozen workers log:
      resources-dir does not exist
      Input document ... is not valid
    """
    import sys

    if not getattr(sys, "frozen", False):
        return

    if os.environ.get("DOC_PARSER_PDF_RESOURCES_DIR"):
        return

    from open_notebook.utils.frozen import bundle_root

    candidates = (
        "docling_parse/pdf_resources_v2",
        "docling_parse/pdf_resources",
        "pdf_resources_v2",
        "pdf_resources",
    )
    for rel in candidates:
        candidate = bundle_root() / rel
        if candidate.is_dir():
            os.environ["DOC_PARSER_PDF_RESOURCES_DIR"] = str(candidate)
            return
