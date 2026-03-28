# backend/voice.py
# Offline speech-to-text using faster-whisper (OpenAI weights, no API key).
# Install: pip install faster-whisper
# For WebM/MP3 decoding, FFmpeg should be on PATH (https://ffmpeg.org/download.html).

from __future__ import annotations

import logging
import os
import tempfile

_log = logging.getLogger(__name__)

_model = None
_MODEL_NAME = os.getenv("ARTHA_WHISPER_MODEL", "tiny")

_LANG_NAMES = {
    "en": "english",
    "hi": "hindi",
    "ta": "tamil",
    "te": "telugu",
    "bn": "bengali",
    "mr": "marathi",
    "kn": "kannada",
    "ml": "malayalam",
    "gu": "gujarati",
    "pa": "punjabi",
}


def _get_model():
    global _model
    if _model is not None:
        return _model
    from faster_whisper import WhisperModel

    device = "cpu"
    compute = "int8"
    try:
        import torch

        if torch.cuda.is_available():
            device = "cuda"
            compute = "float16"
    except ImportError:
        pass

    _model = WhisperModel(_MODEL_NAME, device=device, compute_type=compute)
    return _model


def _suffix_for_audio(file_extension: str) -> str:
    ext = (file_extension or "webm").lower().lstrip(".")
    if ext in ("webm", "wav", "mp3", "mp4", "m4a", "ogg", "flac"):
        return f".{ext}"
    return ".webm"


def transcribe_audio(audio_bytes: bytes, file_extension: str = "webm") -> dict:
    """
    Transcribe recorded audio bytes. Returns:
    text, language, language_name, success, error (optional).
    """
    if not audio_bytes:
        return {
            "text": "",
            "language": "en",
            "language_name": "english",
            "success": False,
            "error": "No audio data.",
        }

    try:
        model = _get_model()
    except ImportError:
        return {
            "text": "",
            "language": "en",
            "language_name": "english",
            "success": False,
            "error": "Install faster-whisper: pip install faster-whisper",
        }
    except Exception as e:
        _log.exception("Whisper load failed")
        return {
            "text": "",
            "language": "en",
            "language_name": "english",
            "success": False,
            "error": str(e),
        }

    suffix = _suffix_for_audio(file_extension)
    path = None
    try:
        fd, path = tempfile.mkstemp(suffix=suffix)
        os.close(fd)
        with open(path, "wb") as f:
            f.write(audio_bytes)

        segments, info = model.transcribe(
            path,
            beam_size=5,
            vad_filter=True,
        )
        parts = [s.text for s in segments]
        text = " ".join(p.strip() for p in parts).strip()
        lang = (info.language or "en").lower()
        lang_name = _LANG_NAMES.get(lang[:2], lang)

        return {
            "text": text,
            "language": lang,
            "language_name": lang_name,
            "success": bool(text),
            "error": None if text else "No speech detected. Try again or type your answer.",
        }
    except Exception as e:
        _log.exception("Transcribe failed")
        hint = ""
        if "ffmpeg" in str(e).lower() or "av" in str(e).lower():
            hint = " Install FFmpeg and add it to PATH for browser recordings (often WebM)."
        return {
            "text": "",
            "language": "en",
            "language_name": "english",
            "success": False,
            "error": str(e) + hint,
        }
    finally:
        if path and os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass


def get_whisper_model():
    try:
        return _get_model()
    except Exception:
        return None
