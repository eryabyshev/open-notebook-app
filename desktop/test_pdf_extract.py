#!/usr/bin/env python3
"""Quick PDF extraction test (dev or frozen worker env)."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path


async def main() -> int:
    default_pdf = Path.home() / "Library/Application Support/open-notebook-desktop/data/uploads/test.pdf"
    pdf_path = Path(sys.argv[1] if len(sys.argv) > 1 else default_pdf)

    if not pdf_path.is_file():
        print(f"PDF not found: {pdf_path}")
        return 1

    print(f"Testing extract_content on: {pdf_path}")
    print(f"frozen={getattr(sys, 'frozen', False)}")

    try:
        import fitz  # pymupdf

        print(f"pymupdf version: {fitz.__doc__[:40] if fitz.__doc__ else 'ok'}")
        doc = fitz.open(pdf_path)
        text = "".join(page.get_text() for page in doc)
        doc.close()
        print(f"pymupdf direct text length: {len(text.strip())}")
    except Exception as exc:
        print(f"pymupdf direct FAILED: {exc}")

    from content_core import extract_content

    result = await extract_content({"file_path": str(pdf_path), "document_engine": "auto"})
    content = (result.content or "").strip()
    print(f"content_core title: {result.title!r}")
    print(f"content_core text length: {len(content)}")
    if content:
        print(f"preview: {content[:300]!r}")
        return 0

    print("content_core returned EMPTY content")
    return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
