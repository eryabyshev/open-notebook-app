#!/usr/bin/env python3
"""Quick PDF extraction test (dev or frozen worker env)."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path


async def try_engine(pdf_path: Path, engine: str) -> int:
    from content_core import extract_content

    print(f"\n--- document_engine={engine!r} ---")
    result = await extract_content(
        {"file_path": str(pdf_path), "document_engine": engine, "output_format": "markdown"}
    )
    content = (result.content or "").strip()
    print(f"title: {result.title!r}")
    print(f"text length: {len(content)}")
    if content:
        print(f"preview: {content[:300]!r}")
        return len(content)
    print("EMPTY content")
    return 0


DEFAULT_UPLOADS = (
    Path.home() / "Library/Application Support/open-notebook-desktop/data/uploads"
)


def resolve_pdf_path() -> Path | None:
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).expanduser()

    default = DEFAULT_UPLOADS / "test.pdf"
    if default.is_file():
        return default

    if DEFAULT_UPLOADS.is_dir():
        pdfs = sorted(DEFAULT_UPLOADS.glob("*.pdf"))
        if pdfs:
            print(f"test.pdf not found; using latest upload: {pdfs[-1].name}")
            return pdfs[-1]

    return default


async def main() -> int:
    from open_notebook.utils.docling_ocr import describe_ocr_engine
    from open_notebook.utils.docling_patch import apply_docling_patch

    apply_docling_patch()

    pdf_path = resolve_pdf_path()
    assert pdf_path is not None

    if not pdf_path.is_file():
        print(f"PDF not found: {pdf_path}")
        print("\nUsage: uv run python desktop/test_pdf_extract.py [path/to/file.pdf]")
        if DEFAULT_UPLOADS.is_dir():
            files = list(DEFAULT_UPLOADS.iterdir())
            if files:
                print(f"\nFiles in {DEFAULT_UPLOADS}:")
                for f in sorted(files)[:10]:
                    print(f"  {f.name}")
            else:
                print(f"\nUploads folder is empty: {DEFAULT_UPLOADS}")
                print("Upload a PDF via the app first, or pass a path to a local PDF.")
        else:
            print(f"\nUploads folder does not exist yet: {DEFAULT_UPLOADS}")
        return 1

    print(f"Testing extract_content on: {pdf_path}")
    print(f"frozen={getattr(sys, 'frozen', False)}")
    print(f"docling OCR: {describe_ocr_engine()}")

    try:
        import docling  # noqa: F401

        print(f"docling: installed ({docling.__version__ if hasattr(docling, '__version__') else 'ok'})")
    except ImportError:
        print("docling: NOT installed — run: uv lock && uv sync")

    try:
        import fitz  # pymupdf

        doc = fitz.open(pdf_path)
        text = "".join(page.get_text() for page in doc)
        doc.close()
        print(f"pymupdf direct text length: {len(text.strip())}")
    except Exception as exc:
        print(f"pymupdf direct FAILED: {exc}")

    best = 0
    for engine in ("simple", "docling", "auto"):
        try:
            best = max(best, await try_engine(pdf_path, engine))
        except Exception as exc:
            print(f"engine {engine!r} FAILED: {exc}")

    if best > 0:
        return 0
    print("\nAll engines returned empty — PDF may be unreadable or OCR models still downloading")
    return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
