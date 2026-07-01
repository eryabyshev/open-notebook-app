# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Open Notebook surreal-commands worker.

Build:
    ./desktop/build_worker.sh
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_submodules, copy_metadata

block_cipher = None

ROOT = Path(SPECPATH).parent
ENTRY = ROOT / "desktop" / "entry_worker.py"

import sys

sys.path.insert(0, str(ROOT))
from desktop.pyinstaller_binaries import collect_ffmpeg_binaries
from desktop.pyinstaller_datas import collect_docling_parse_datas

datas = [
    (str(ROOT / "open_notebook" / "database" / "migrations"), "open_notebook/database/migrations"),
    (str(ROOT / "open_notebook" / "ai" / "assets"), "open_notebook/ai/assets"),
    (str(ROOT / "pyproject.toml"), "."),
    (str(ROOT / "prompts"), "prompts"),
]

for package in (
    "ai_prompter",
    "podcast_creator",
    "tiktoken_ext",
    "langgraph",
    "langchain",
    "content_core",
    "docling",
    "docling_core",
    "docling_parse",
    "ocrmac",
):
    try:
        datas += collect_data_files(package, include_py_files=True)
    except Exception:
        pass

# docling-parse C++ layer needs pdf_resources (see docling#1714)
try:
    datas += collect_data_files("docling_parse", includes=["pdf_resources_v2/**"])
    datas += collect_data_files("docling_parse", includes=["pdf_resources/**"])
except Exception:
    pass

datas += collect_docling_parse_datas()

for dist_name in (
    "imageio",
    "imageio-ffmpeg",
    "moviepy",
    "podcast-creator",
    "content-core",
    "open-notebook",
    "surreal-commands",
    "pymupdf",
    "docling",
    "docling-core",
    "ocrmac",
    "docling-ibm-models",
    "docling-parse",
    "easyocr",
    "torch",
    "torchvision",
    "transformers",
    "decorator",
    "proglog",
    "numpy",
    "pillow",
    "tqdm",
    "typer",
    "rich",
):
    try:
        datas += copy_metadata(dist_name)
    except Exception:
        pass

hiddenimports = [
    "surreal_commands",
    "surreal_commands.cli",
    "surreal_commands.cli.worker",
    "surreal_commands.core.worker",
    "surreal_commands.core.registry",
    "surreal_commands.core.service",
    "typer",
    "rich",
    "rich.console",
    "rich.panel",
    "rich.json",
    "click",
    "commands",
    "commands.embedding_commands",
    "commands.source_commands",
    "commands.podcast_commands",
    "commands.example_commands",
    "desktop.runtime_bootstrap",
    "open_notebook",
    "open_notebook.utils.frozen",
    "surrealdb",
    "tiktoken",
    "tiktoken_ext",
    "tiktoken_ext.openai_public",
    "langchain",
    "langchain_core",
    "langchain_community",
    "langchain_openai",
    "langchain_anthropic",
    "langchain_ollama",
    "langchain_google_genai",
    "langchain_groq",
    "langchain_mistralai",
    "langchain_deepseek",
    "langgraph",
    "langgraph.checkpoint",
    "langgraph.checkpoint.sqlite",
    "langgraph.checkpoint.sqlite.aio",
    "esperanto",
    "content_core",
    "docling",
    "docling_core",
    "ocrmac",
    "docling_ibm_models",
    "docling_parse",
    "easyocr",
    "pymupdf",
    "fitz",
    "ai_prompter",
    "podcast_creator",
    "imageio",
    "imageio_ffmpeg",
    "moviepy",
    "decorator",
    "proglog",
    "numpy",
    "httpx",
    "httpcore",
    "anyio",
    "sniffio",
    "loguru",
    "pydantic",
    "pydantic_core",
    "cryptography",
]

for pkg in (
    "open_notebook.graphs",
    "open_notebook.domain",
    "open_notebook.ai",
    "open_notebook.database",
    "commands",
):
    hiddenimports += collect_submodules(pkg)

for pkg in (
    "imageio",
    "moviepy",
    "podcast_creator",
    "content_core",
    "pymupdf",
    "docling",
    "docling_core",
    "ocrmac",
    "docling_ibm_models",
    "easyocr",
):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

binaries = collect_ffmpeg_binaries()
for pkg in ("pymupdf", "torch", "torchvision", "imageio_ffmpeg"):
    try:
        binaries += collect_dynamic_libs(pkg)
    except Exception:
        pass

a = Analysis(
    [str(ENTRY)],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "IPython", "matplotlib", "tkinter", "api", "uvicorn", "fastapi"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="open-notebook-worker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="open-notebook-worker",
)
