"""Docling / docling-parse configuration for PyInstaller (frozen) desktop builds."""

from __future__ import annotations

import os
from pathlib import Path


def resolve_docling_artifacts_path() -> Path | None:
    """
    Return the directory of prefetched Docling models, if available.

    Resolution order:
    1. ``DOCLING_ARTIFACTS_PATH`` env var
    2. Bundled ``docling/models`` inside a PyInstaller onedir worker
    """
    env = os.environ.get("DOCLING_ARTIFACTS_PATH", "").strip()
    if env:
        path = Path(env)
        if path.is_dir():
            return path

    import sys

    if not getattr(sys, "frozen", False):
        return None

    from open_notebook.utils.frozen import bundle_root

    for rel in ("docling/models", "docling-models"):
        candidate = bundle_root() / rel
        if candidate.is_dir() and any(candidate.iterdir()):
            return candidate
    return None


def register_docling_plugins() -> None:
    """
    Register built-in docling pipeline plugins in PyInstaller frozen workers.

    ``load_from_plugins()`` relies on setuptools entry points, which are empty in
    frozen bundles → ``No class found with the name 'picture_description_vlm_engine'``.
    """
    import sys

    if not getattr(sys, "frozen", False):
        return

    from loguru import logger

    try:
        from docling.models.factories import (
            get_layout_factory,
            get_ocr_factory,
            get_picture_description_factory,
            get_table_structure_factory,
        )
        from docling.models.factories.base_factory import BaseFactory
        from docling.models.plugins import defaults as plugin_defaults
    except ImportError as exc:
        logger.warning("Docling factories unavailable for plugin registration: {}", exc)
        return

    if getattr(BaseFactory.load_from_plugins, "_open_notebook_patched", False):
        return

    _DEFAULT_LOADERS = {
        "ocr_engines": plugin_defaults.ocr_engines,
        "picture_description": plugin_defaults.picture_description,
        "layout_engines": plugin_defaults.layout_engines,
        "table_structure_engines": plugin_defaults.table_structure_engines,
    }

    _original_load = BaseFactory.load_from_plugins

    def _load_from_plugins(
        self,
        plugin_name=None,
        allow_external_plugins: bool = False,
    ):
        _original_load(self, plugin_name, allow_external_plugins)
        loader = _DEFAULT_LOADERS.get(self.plugin_attr_name)
        if not loader:
            return
        try:
            config = loader()
            self.process_plugin(
                config, "docling", "docling.models.plugins.defaults"
            )
        except ValueError:
            # Class already registered via entry points (dev) or duplicate register.
            pass

    _load_from_plugins._open_notebook_patched = True  # type: ignore[attr-defined]
    BaseFactory.load_from_plugins = _load_from_plugins  # type: ignore[method-assign]

    for getter in (
        get_ocr_factory,
        get_picture_description_factory,
        get_layout_factory,
        get_table_structure_factory,
    ):
        getter.cache_clear()

    logger.debug("Patched docling BaseFactory.load_from_plugins for frozen worker")


def configure_docling_for_frozen() -> None:
    """
    Configure docling-parse PDF resources and offline model artifacts for frozen builds.

    Without pdf_resources, frozen workers log::
      resources-dir does not exist
      Input document ... is not valid

    Without bundled models, docling tries to download on first use and often fails
    inside PyInstaller (no write access to bundle, flaky network from worker).
    """
    import sys

    if not getattr(sys, "frozen", False):
        return

    if not os.environ.get("DOC_PARSER_PDF_RESOURCES_DIR"):
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
                break

    artifacts = resolve_docling_artifacts_path()
    if artifacts and not os.environ.get("DOCLING_ARTIFACTS_PATH"):
        os.environ["DOCLING_ARTIFACTS_PATH"] = str(artifacts)

    register_docling_plugins()
