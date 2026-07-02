"""Gemini TTS via OpenAI-compatible APIs: PCM-only output → MP3 for podcast-creator."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any, Union

from loguru import logger

_GEMINI_TTS_PATCHED = False
_PODCAST_CLIP_FIXUP_PATCHED = False

# Gemini flash TTS preview models return raw PCM (s16le, 24 kHz, mono).
_GEMINI_PCM_SAMPLE_RATE = 24000

# Preset speaker profiles ship with OpenAI voice IDs; map them for Gemini TTS.
_OPENAI_TO_GEMINI_VOICE: dict[str, str] = {
    "alloy": "Zephyr",
    "ash": "Charon",
    "ballad": "Leda",
    "coral": "Aoede",
    "echo": "Charon",
    "fable": "Puck",
    "nova": "Kore",
    "onyx": "Fenrir",
    "sage": "Orus",
    "shimmer": "Aoede",
    "verse": "Puck",
}

_GEMINI_VOICES = frozenset(
    {
        "Zephyr",
        "Puck",
        "Charon",
        "Kore",
        "Fenrir",
        "Leda",
        "Orus",
        "Aoede",
        "Callirrhoe",
        "Autonoe",
        "Enceladus",
        "Iapetus",
        "Umbriel",
        "Algieba",
        "Despina",
        "Erinome",
        "Algenib",
        "Rasalgethi",
        "Laomedeia",
        "Achernar",
        "Alnilam",
        "Schedar",
        "Gacrux",
        "Pulcherrima",
        "Achird",
        "Zubenelgenubi",
        "Vindemiatrix",
        "Sadachbia",
        "Sadaltager",
        "Sulafat",
    }
)


def map_voice_for_gemini_tts(voice: str) -> str:
    """Map OpenAI-style voice IDs to Gemini TTS voice names."""
    if not voice:
        return "Zephyr"
    if voice in _GEMINI_VOICES:
        return voice
    mapped = _OPENAI_TO_GEMINI_VOICE.get(voice.lower())
    if mapped:
        return mapped
    # Case-insensitive match for Gemini names typed in UI
    for gemini_voice in _GEMINI_VOICES:
        if gemini_voice.lower() == voice.lower():
            return gemini_voice
    logger.warning(
        f"Unknown voice {voice!r} for Gemini TTS; falling back to Zephyr"
    )
    return "Zephyr"


def is_gemini_tts_model(model_name: str) -> bool:
    name = (model_name or "").lower()
    return "gemini" in name and "tts" in name


def podcast_tts_config(model_name: str, config: dict | None) -> dict:
    """Merge provider config for podcast TTS (Gemini requires PCM from the API)."""
    merged = dict(config or {})
    if is_gemini_tts_model(model_name):
        merged["response_format"] = "pcm"
    return merged


def pcm_bytes_to_mp3(pcm_bytes: bytes, sample_rate: int = _GEMINI_PCM_SAMPLE_RATE) -> bytes:
    """Convert raw PCM16 mono audio to MP3 using bundled/system ffmpeg."""
    if not pcm_bytes:
        raise ValueError("Empty PCM audio payload")

    try:
        import imageio_ffmpeg
    except ImportError as exc:
        raise RuntimeError(
            "imageio-ffmpeg is required to convert Gemini TTS PCM to MP3"
        ) from exc

    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    proc = subprocess.run(
        [
            ffmpeg_exe,
            "-y",
            "-f",
            "s16le",
            "-ar",
            str(sample_rate),
            "-ac",
            "1",
            "-i",
            "pipe:0",
            "-f",
            "mp3",
            "pipe:1",
        ],
        input=pcm_bytes,
        capture_output=True,
        timeout=120,
        check=False,
    )
    if proc.returncode != 0:
        stderr = (proc.stderr or b"").decode("utf-8", errors="replace")[:500]
        raise RuntimeError(f"ffmpeg PCM→MP3 conversion failed: {stderr}")

    if not proc.stdout:
        raise RuntimeError("ffmpeg PCM→MP3 conversion produced empty output")

    return proc.stdout


def _set_response_format_on_model(model: Any, response_format: str) -> None:
    for attr in ("config", "_config"):
        cfg = getattr(model, attr, None)
        if isinstance(cfg, dict):
            cfg["response_format"] = response_format


def is_valid_mp3(audio: bytes) -> bool:
    """Return True if bytes look like a real MP3 stream."""
    if len(audio) < 4:
        return False
    if audio[:3] == b"ID3":
        return True
    return audio[0] == 0xFF and (audio[1] & 0xE0) == 0xE0


def _extract_audio_bytes(result: Any) -> tuple[Any, bytes | None]:
    if isinstance(result, (bytes, bytearray)):
        return result, bytes(result)
    audio_data = getattr(result, "audio_data", None)
    if isinstance(audio_data, (bytes, bytearray)):
        return result, bytes(audio_data)
    content = getattr(result, "content", None)
    if isinstance(content, (bytes, bytearray)):
        return result, bytes(content)
    return result, None


def _store_audio_bytes(result: Any, audio: bytes) -> Any:
    if isinstance(result, (bytes, bytearray)):
        return audio
    if hasattr(result, "model_copy"):
        updates: dict[str, Any] = {"audio_data": audio}
        if is_valid_mp3(audio):
            updates["content_type"] = "audio/mp3"
        return result.model_copy(update=updates)
    if hasattr(result, "content"):
        result.content = audio
        return result
    return audio


def ensure_mp3_clip_file(clip_path: Union[str, Path]) -> Path:
    """Rewrite Gemini PCM clips saved with a .mp3 extension as real MP3."""
    path = Path(clip_path)
    data = path.read_bytes()
    if not data:
        raise ValueError(f"Empty podcast clip: {path}")
    if is_valid_mp3(data):
        return path

    logger.info(f"Converting podcast clip PCM→MP3 in place: {path.name}")
    path.write_bytes(pcm_bytes_to_mp3(data))
    return path


def apply_gemini_tts_patch() -> None:
    """Patch esperanto OpenAI-compatible TTS for Gemini PCM models."""
    global _GEMINI_TTS_PATCHED
    if _GEMINI_TTS_PATCHED:
        return

    try:
        from esperanto.providers.tts.openai_compatible import (
            OpenAICompatibleTextToSpeechModel,
        )
    except ImportError:
        logger.debug("esperanto OpenAI-compatible TTS not available; skip Gemini patch")
        return

    original = OpenAICompatibleTextToSpeechModel.agenerate_speech

    async def agenerate_speech_patched(self, text: str, voice: str, **kwargs: Any) -> Any:
        model_name = str(getattr(self, "model_name", "") or "")
        if not is_gemini_tts_model(model_name):
            return await original(self, text, voice, **kwargs)

        kwargs = {**kwargs, "response_format": "pcm"}
        _set_response_format_on_model(self, "pcm")

        gemini_voice = map_voice_for_gemini_tts(voice)
        if gemini_voice != voice:
            logger.info(
                f"Mapped TTS voice {voice!r} → {gemini_voice!r} for Gemini model {model_name}"
            )

        # esperanto writes output_file before returning; keep raw PCM in memory only.
        output_file = kwargs.pop("output_file", None)

        result = await original(self, text, gemini_voice, **kwargs)
        wrapper, audio = _extract_audio_bytes(result)
        if audio is None:
            return result

        logger.info(
            f"Converting Gemini TTS PCM ({len(audio)} bytes) to MP3 for {model_name}"
        )
        mp3 = pcm_bytes_to_mp3(audio)

        if output_file is not None:
            out = Path(output_file)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(mp3)

        return _store_audio_bytes(wrapper, mp3)

    OpenAICompatibleTextToSpeechModel.agenerate_speech = agenerate_speech_patched  # type: ignore[method-assign]
    _GEMINI_TTS_PATCHED = True
    logger.debug("Applied Gemini TTS PCM→MP3 patch for OpenAI-compatible provider")


def apply_podcast_clip_fixup_patch() -> None:
    """Normalize mislabeled PCM clips before moviepy combines them."""
    global _PODCAST_CLIP_FIXUP_PATCHED
    if _PODCAST_CLIP_FIXUP_PATCHED:
        return

    try:
        from podcast_creator.core import combine_audio_files
    except ImportError:
        logger.debug("podcast-creator not available; skip clip fixup patch")
        return

    original = combine_audio_files

    async def combine_audio_files_patched(
        audio_dir: Union[Path, str],
        final_filename: str,
        final_output_dir: Union[Path, str],
    ) -> dict:
        clips_dir = Path(audio_dir)
        for clip_path in sorted(clips_dir.glob("*.mp3")):
            try:
                ensure_mp3_clip_file(clip_path)
            except Exception as exc:
                logger.warning(f"Could not normalize clip {clip_path.name}: {exc}")
        return await original(audio_dir, final_filename, final_output_dir)

    import podcast_creator.core as podcast_core

    podcast_core.combine_audio_files = combine_audio_files_patched
    _PODCAST_CLIP_FIXUP_PATCHED = True
    logger.debug("Applied podcast PCM clip fixup before audio combine")
