"""Surreal-commands integration for Open Notebook.

Command modules are imported explicitly by API routers and services
(e.g. ``import commands.source_commands``). Avoid eager imports here so
API startup does not load heavy optional stacks (podcast/moviepy) unless needed.

Workers must call ``register_commands()`` before starting surreal-commands.
"""

from __future__ import annotations

from importlib import import_module

__all__ = [
    "embedding_commands",
    "example_commands",
    "podcast_commands",
    "source_commands",
]


def register_commands() -> None:
    """Import all command modules so @command handlers register with surreal-commands."""
    for module_name in __all__:
        import_module(f"{__name__}.{module_name}")
