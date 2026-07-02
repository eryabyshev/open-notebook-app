"""
Eager-import optional esperanto provider modules for PyInstaller frozen builds.

Esperanto loads TTS/STT providers lazily; without these imports PyInstaller omits
modules like ``esperanto.providers.tts.openai_compatible`` and podcast TTS fails.
"""

from __future__ import annotations

import importlib
import logging

logger = logging.getLogger(__name__)

# Keep in sync with providers exposed in Settings → API Keys.
_OPTIONAL_PROVIDER_MODULES = (
    # TTS
    "esperanto.providers.tts.openai_compatible",
    "esperanto.providers.tts.openai",
    "esperanto.providers.tts.google",
    "esperanto.providers.tts.elevenlabs",
    "esperanto.providers.tts.azure",
    "esperanto.providers.tts.deepgram",
    "esperanto.providers.tts.mistral",
    "esperanto.providers.tts.vertex",
    "esperanto.providers.tts.xai",
    # Legacy layout (older esperanto releases)
    "esperanto.providers.text_to_speech.openai_compatible",
    "esperanto.providers.text_to_speech.openai",
    # STT (audio sources / podcasts)
    "esperanto.providers.stt.openai_compatible",
    "esperanto.providers.stt.openai",
    "esperanto.providers.speech_to_text.openai_compatible",
    "esperanto.providers.speech_to_text.openai",
)


def preload_esperanto_providers() -> None:
    for module_name in _OPTIONAL_PROVIDER_MODULES:
        try:
            importlib.import_module(module_name)
        except ImportError:
            logger.debug("Optional esperanto provider not installed: %s", module_name)
