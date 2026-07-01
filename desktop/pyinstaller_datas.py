"""PyInstaller data collection helpers for desktop bundles."""


def collect_docling_parse_datas() -> list[tuple[str, str]]:
    """
    Bundle docling-parse PDF resource folders for frozen workers.

    C++ layer looks for ``docling_parse/pdf_resources/``; newer wheels ship
    ``pdf_resources_v2/`` only — include both names when needed.
    """
    try:
        import docling_parse
    except ImportError:
        return []

    root = __import__("pathlib").Path(docling_parse.__file__).parent
    datas: list[tuple[str, str]] = []

    v2 = root / "pdf_resources_v2"
    v1 = root / "pdf_resources"

    if v2.is_dir():
        datas.append((str(v2), "docling_parse/pdf_resources_v2"))
        if not v1.is_dir():
            # Alias v2 resources under the legacy path expected by docling-parse C++.
            datas.append((str(v2), "docling_parse/pdf_resources"))

    if v1.is_dir():
        datas.append((str(v1), "docling_parse/pdf_resources"))

    return datas
