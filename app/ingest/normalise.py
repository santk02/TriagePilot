from __future__ import annotations  # allow forward-referenced type hints on older Python

from ..models import NormalizedTicket, TicketInput  # raw input -> unified text blob
from .audio import transcribe_voice_note  # voice note -> transcript
from .text import clean_text  # text -> whitespace-normalized text
from .vision import describe_screenshot  # screenshot -> description


def normalise_ticket(ticket: TicketInput) -> NormalizedTicket:
    """Merge whichever modalities a ticket carries (text/screenshot/voice) into one tagged text
    blob (`[TEXT]` / `[SCREENSHOT]` / `[VOICE]`), so the classifier only ever needs one input
    shape regardless of how the customer actually submitted the ticket."""
    text_block = clean_text(ticket.text)
    screenshot_block = describe_screenshot(ticket.screenshot_text, ocr_text=ticket.metadata.get("ocr_text"))
    voice_block = transcribe_voice_note(ticket.voice_transcript, transcript=ticket.metadata.get("voice_transcript"))

    chunks = []
    if text_block:
        chunks.append(f"[TEXT]\n{text_block}")
    if screenshot_block:
        chunks.append(f"[SCREENSHOT]\n{screenshot_block}")
    if voice_block:
        chunks.append(f"[VOICE]\n{voice_block}")

    content = "\n\n".join(chunks).strip()
    return NormalizedTicket(
        ticket_id=ticket.ticket_id,
        content=content,
        text=text_block,
        screenshot_text=screenshot_block,
        voice_transcript=voice_block,
        metadata=dict(ticket.metadata),  # copy so callers can't mutate the ticket's metadata via us
    )
