"""Surreal-commands integration for Open Notebook.

Command modules are imported explicitly by API routers and services
(e.g. ``import commands.source_commands``). Avoid eager imports here so
API startup does not load heavy optional stacks (podcast/moviepy) unless needed.
"""

__all__ = [
    "embedding_commands",
    "example_commands",
    "podcast_commands",
    "source_commands",
]
