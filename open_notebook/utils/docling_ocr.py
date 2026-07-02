"""Platform-specific Docling OCR configuration for Open Notebook."""

from __future__ import annotations

import os
import shutil
import sys
from typing import TYPE_CHECKING, Optional

from loguru import logger

if TYPE_CHECKING:
    from docling.datamodel.pipeline_options import PdfPipelineOptions


def describe_ocr_engine() -> str:
    """Human-readable OCR backend for the current platform."""
    if sys.platform == "darwin":
        try:
            import ocrmac  # noqa: F401

            return "ocrmac (macOS Vision, ru-RU/en-US)"
        except ImportError:
            return "docling default (ocrmac not installed)"
    tesseract_cmd = os.environ.get("OPEN_NOTEBOOK_TESSERACT_CMD", "tesseract")
    if shutil.which(tesseract_cmd) or os.path.isfile(tesseract_cmd):
        return f"tesseract CLI ({tesseract_cmd}, rus+eng)"
    return "docling default (tesseract not on PATH)"


def build_pdf_pipeline_options() -> Optional["PdfPipelineOptions"]:
    from docling.datamodel.pipeline_options import (
        OcrMacOptions,
        PdfPipelineOptions,
        TesseractCliOcrOptions,
    )

    from open_notebook.utils.docling_frozen import resolve_docling_artifacts_path

    pipeline_kwargs: dict = {
        "do_ocr": True,
        # VLM / enrichment plugins are not bundled in the desktop worker — text+OCR only.
        "do_picture_description": False,
        "do_chart_extraction": False,
        "do_formula_enrichment": False,
        "do_code_enrichment": False,
        "generate_picture_images": False,
    }

    # Docling 2.64+ may still resolve picture-description stage unless options are set.
    try:
        from docling.datamodel.pipeline_options import PictureDescriptionApiOptions

        pipeline_kwargs["picture_description_options"] = PictureDescriptionApiOptions()
    except ImportError:
        pass

    pipeline_options = PdfPipelineOptions(**pipeline_kwargs)

    artifacts = resolve_docling_artifacts_path()
    if artifacts:
        pipeline_options.artifacts_path = str(artifacts)
        logger.debug("Docling artifacts_path={}", artifacts)

    if sys.platform == "darwin":
        try:
            import ocrmac  # noqa: F401
        except ImportError:
            logger.warning(
                "ocrmac is not installed; Docling will use its default OCR on macOS. "
                "Install with: uv sync"
            )
            return None

        pipeline_options.ocr_options = OcrMacOptions(
            lang=["ru-RU", "en-US"],
            recognition="accurate",
        )
        logger.debug("Docling OCR engine: ocrmac (macOS Vision)")
        return pipeline_options

    tesseract_cmd = os.environ.get("OPEN_NOTEBOOK_TESSERACT_CMD", "tesseract")
    if not (shutil.which(tesseract_cmd) or os.path.isfile(tesseract_cmd)):
        logger.warning(
            "Tesseract not found on PATH ({}). Docling will use its default OCR. "
            "On Windows/Linux install tesseract and the rus language pack.",
            tesseract_cmd,
        )
        return None

    tessdata = os.environ.get("TESSDATA_PREFIX")
    pipeline_options.ocr_options = TesseractCliOcrOptions(
        lang=["rus", "eng"],
        tesseract_cmd=tesseract_cmd,
        path=tessdata or None,
    )
    logger.debug("Docling OCR engine: tesseract CLI ({})", tesseract_cmd)
    return pipeline_options


def create_document_converter():
    from docling.datamodel.base_models import InputFormat
    from docling.document_converter import DocumentConverter, PdfFormatOption

    pipeline_options = build_pdf_pipeline_options()
    if pipeline_options is None:
        return DocumentConverter()

    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        }
    )
