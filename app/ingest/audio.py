from __future__ import annotations  # allow forward-referenced type hints on older Python

from typing import Optional  # optional injected transcript


def transcribe_voice_note(
    audio_ref: str,
    transcript: Optional[str] = None,
) -> str:
    """Convert a voice note into text for the classifier prompt.

    Blueprint specifies `faster-whisper` for local, offline transcription. This scaffold accepts
    an injected transcript instead so the pipeline stays testable without an audio dependency;
    wire a `faster-whisper` call in place of the `transcript` fallback to complete Phase 2.
    """

    if transcript and transcript.strip():
        return transcript.strip()  # best case: transcription already ran
    if audio_ref.strip():
        return f"Voice note provided: {audio_ref}"  # last resort: at least note that one existed
    return ""  # no voice note at all
