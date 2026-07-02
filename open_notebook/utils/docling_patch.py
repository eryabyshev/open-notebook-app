"""Patch content-core Docling extraction to use platform OCR settings."""

from __future__ import annotations

import asyncio

from loguru import logger

_PATCHED = False


async def _convert_with_platform_ocr(source: str) -> tuple[str, str]:
    """Run Docling convert with ocrmac/tesseract + bundled artifacts."""
    from open_notebook.utils.docling_ocr import create_document_converter

    converter = create_document_converter()
    logger.info("Docling convert starting: {}", source)
    try:
        result = await asyncio.to_thread(converter.convert, source)
    except Exception as exc:
        logger.error("Docling convert failed for {}: {}", source, exc)
        raise ValueError(f"Could not extract content with Docling: {exc}") from exc

    doc = result.document
    return doc.export_to_markdown(), "markdown"


def _patch_document_docling() -> bool:
    """content-core >= 1.14: processors.document.docling.extract_docling."""
    try:
        import content_core.processors.document.docling as docling_mod
    except ImportError:
        return False

    if not getattr(docling_mod, "DOCLING_AVAILABLE", False):
        logger.warning("Docling not available in content-core document processor")
        return False

    from content_core.common.state import ExtractionOutput
    from content_core.config import ContentCoreConfig

    async def extract_docling(source: str, config: ContentCoreConfig) -> ExtractionOutput:
        fmt = config.docling_output_format or "markdown"
        converter = None
        from open_notebook.utils.docling_ocr import create_document_converter

        converter = create_document_converter()
        logger.info("Docling convert starting: {}", source)
        try:
            result = await asyncio.to_thread(converter.convert, source)
        except Exception as exc:
            logger.error("Docling convert failed for {}: {}", source, exc)
            raise ValueError(f"Could not extract content with Docling: {exc}") from exc

        doc = result.document
        if fmt == "html":
            output = doc.export_to_html()
        elif fmt == "json":
            output = doc.export_to_json()
        else:
            output = doc.export_to_markdown()
            fmt = "markdown"

        return ExtractionOutput(
            content=output,
            source_type="file",
            identified_type="",
            metadata={"docling_format": fmt},
        )

    docling_mod.extract_docling = extract_docling
    logger.debug("Patched content_core.processors.document.docling.extract_docling")
    return True


def _patch_legacy_docling() -> bool:
    """content-core < 1.14: processors.docling.extract_with_docling."""
    try:
        import content_core.processors.docling as docling_mod
    except ImportError:
        return False

    from content_core.common.state import ProcessSourceState
    from content_core.config import CONFIG

    async def extract_with_docling(state: ProcessSourceState) -> ProcessSourceState:
        source = state.file_path or state.url or state.content
        if not source:
            raise ValueError("No input provided for Docling extraction.")

        output, fmt = await _convert_with_platform_ocr(source)
        state.metadata["docling_format"] = (
            state.output_format or state.metadata.get("docling_format")
            or CONFIG.get("extraction", {}).get("docling", {}).get("output_format", "markdown")
            or fmt
        )
        state.content = output
        return state

    docling_mod.extract_with_docling = extract_with_docling
    logger.debug("Patched content_core.processors.docling.extract_with_docling")
    return True


def apply_docling_patch() -> None:
    global _PATCHED
    if _PATCHED:
        return
    _PATCHED = True

    from open_notebook.utils.docling_frozen import configure_docling_for_frozen

    configure_docling_for_frozen()

    if _patch_document_docling() or _patch_legacy_docling():
        return

    logger.warning(
        "Could not patch content-core Docling processor — OCR/artifacts may not apply"
    )
