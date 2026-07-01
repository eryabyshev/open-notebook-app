"""Patch content-core Docling extraction to use platform OCR settings."""

from __future__ import annotations

_PATCHED = False


def apply_docling_patch() -> None:
    global _PATCHED
    if _PATCHED:
        return
    _PATCHED = True

    import content_core.processors.docling as docling_mod
    from content_core.common.state import ProcessSourceState
    from content_core.config import CONFIG

    from open_notebook.utils.docling_ocr import create_document_converter

    async def extract_with_docling(state: ProcessSourceState) -> ProcessSourceState:
        converter = create_document_converter()

        source = state.file_path or state.url or state.content
        if not source:
            raise ValueError("No input provided for Docling extraction.")

        result = converter.convert(source)
        doc = result.document

        cfg_fmt = (
            CONFIG.get("extraction", {}).get("docling", {}).get("output_format", "markdown")
        )
        fmt = state.output_format or state.metadata.get("docling_format") or cfg_fmt
        state.metadata["docling_format"] = fmt
        if fmt == "html":
            output = doc.export_to_html()
        elif fmt == "json":
            output = doc.export_to_json()
        else:
            output = doc.export_to_markdown()

        state.content = output
        return state

    docling_mod.extract_with_docling = extract_with_docling
