from esperanto.common_types.tts import AudioResponse

from open_notebook.utils.gemini_tts import (
    _extract_audio_bytes,
    _store_audio_bytes,
    is_valid_mp3,
    map_voice_for_gemini_tts,
)


def test_map_openai_voice_to_gemini():
    assert map_voice_for_gemini_tts("echo") == "Charon"
    assert map_voice_for_gemini_tts("Kore") == "Kore"


def test_extract_audio_bytes_from_audio_response():
    response = AudioResponse(audio_data=b"\x00\x01", content_type="audio/pcm")
    wrapper, audio = _extract_audio_bytes(response)
    assert wrapper is response
    assert audio == b"\x00\x01"


def test_store_audio_bytes_updates_frozen_audio_response():
    response = AudioResponse(audio_data=b"pcm", content_type="audio/pcm")
    mp3 = b"ID3\x04\x00\x00\x00"
    updated = _store_audio_bytes(response, mp3)
    assert updated.audio_data == mp3
    assert updated.content_type == "audio/mp3"


def test_is_valid_mp3_detects_id3_header():
    assert is_valid_mp3(b"ID3\x04\x00\x00\x00")
    assert not is_valid_mp3(b"\x00\x01\x02\x03")
