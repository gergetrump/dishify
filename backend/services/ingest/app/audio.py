from __future__ import annotations

import base64
import os
import shutil
import subprocess
import tempfile

# MIME types Gemini's audio understanding accepts directly.
GEMINI_AUDIO_MIME_TYPES = {
    "audio/wav",
    "audio/x-wav",
    "audio/mp3",
    "audio/mpeg",
    "audio/aiff",
    "audio/aac",
    "audio/ogg",
    "audio/flac",
}


class AudioTranscodeError(RuntimeError):
    pass


def _base_mime(mime_type: str) -> str:
    return mime_type.split(";")[0].strip().lower()


def ensure_supported_audio(audio_base64: str, mime_type: str) -> tuple[str, str]:
    """Return (base64, mime_type) Gemini can read.

    Browsers (Chrome) record ``audio/webm;codecs=opus``, which Gemini does not
    accept. When the input format is unsupported and ``ffmpeg`` is available, we
    transcode to 16 kHz mono WAV. If ``ffmpeg`` is missing we pass the audio
    through unchanged and let Gemini decide (best effort).
    """
    base = _base_mime(mime_type)
    if base in GEMINI_AUDIO_MIME_TYPES:
        return audio_base64, base

    if not shutil.which("ffmpeg"):
        return audio_base64, mime_type

    raw = base64.b64decode(audio_base64)
    out_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            out_path = tmp.name
        result = subprocess.run(
            ["ffmpeg", "-y", "-i", "pipe:0", "-ac", "1", "-ar", "16000", out_path],
            input=raw,
            capture_output=True,
            timeout=60,
        )
        if result.returncode != 0:
            raise AudioTranscodeError(
                f"ffmpeg failed (code {result.returncode}): "
                f"{result.stderr.decode('utf-8', 'ignore')[:500]}"
            )
        with open(out_path, "rb") as handle:
            transcoded = handle.read()
        if not transcoded:
            raise AudioTranscodeError("ffmpeg produced empty output")
        return base64.b64encode(transcoded).decode("ascii"), "audio/wav"
    finally:
        if out_path and os.path.exists(out_path):
            os.remove(out_path)
