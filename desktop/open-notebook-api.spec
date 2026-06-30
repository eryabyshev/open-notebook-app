# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for Open Notebook API (desktop spike).

Build:
    ./desktop/build_api.sh
"""

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

block_cipher = None

ROOT = Path(SPECPATH).parent
ENTRY = ROOT / "desktop" / "entry_api.py"

# Bundled read-only assets
datas = [
    (str(ROOT / "open_notebook" / "database" / "migrations"), "open_notebook/database/migrations"),
    (str(ROOT / "open_notebook" / "ai" / "assets"), "open_notebook/ai/assets"),
    (str(ROOT / "pyproject.toml"), "."),
]

for package in (
    "ai_prompter",
    "podcast_creator",
    "tiktoken_ext",
    "langgraph",
    "langchain",
    "content_core",
):
    try:
        datas += collect_data_files(package, include_py_files=True)
    except Exception:
        pass

# importlib.metadata.version() needs dist-info folders in frozen builds
for dist_name in (
    "imageio",
    "imageio-ffmpeg",
    "moviepy",
    "podcast-creator",
    "content-core",
    "open-notebook",
    "decorator",
    "proglog",
    "numpy",
    "pillow",
    "tqdm",
):
    try:
        datas += copy_metadata(dist_name)
    except Exception:
        pass

hiddenimports = [
    # uvicorn / ASGI stack
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "uvicorn.lifespan.off",
    "h11",
    "httptools",
    "websockets",
    "watchfiles",
    # FastAPI / Starlette
    "fastapi",
    "starlette",
    "starlette.middleware",
    "starlette.routing",
    "pydantic",
    "pydantic_core",
    "pydantic.deprecated.decorator",
    "email_validator",
    "multipart",
    "python_multipart",
    # App packages
    "api",
    "api.main",
    "open_notebook",
    "open_notebook.utils.frozen",
    # Database / jobs
    "surrealdb",
    "surreal_commands",
    # AI stack (extend as build errors appear)
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
    "cryptography",
    "bcrypt",
]

# Collect router and graph submodules dynamically
for pkg in (
    "api.routers",
    "open_notebook.graphs",
    "open_notebook.domain",
    "open_notebook.ai",
    "open_notebook.database",
):
    hiddenimports += collect_submodules(pkg)

for pkg in ("imageio", "moviepy", "podcast_creator", "content_core", "commands"):
    try:
        hiddenimports += collect_submodules(pkg)
    except Exception:
        pass

a = Analysis(
    [str(ENTRY)],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "IPython", "matplotlib", "tkinter"],
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
    name="open-notebook-api",
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
    name="open-notebook-api",
)
