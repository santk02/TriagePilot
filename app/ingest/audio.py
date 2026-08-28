from __future__ import annotations

from typing import Optional


def transcribe_voice_note(
    audio_ref: str,
    transcript: Optional[str] = None,
) -> str:
    """Convert a voice note into text.

    The real project can wire faster-whisper here; the scaffold accepts an
    injected transcript so the pipeline stays testable offline.
    """

    if transcript and transcript.strip():
        return transcript.strip()
    if audio_ref.strip():
        return f"Voice note provided: {audio_ref}"
    return ""

