"""Shared PyInstaller binary collection helpers for desktop bundles."""


def collect_ffmpeg_binaries() -> list[tuple[str, str]]:
    """Bundle imageio-ffmpeg's platform ffmpeg executable."""
    try:
        import imageio_ffmpeg

        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return []

    if not ffmpeg_exe:
        return []

    # Place next to the PyInstaller exe; imageio_ffmpeg resolves it at runtime.
    return [(ffmpeg_exe, ".")]
