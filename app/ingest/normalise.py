from __future__ import annotations

from ..models import NormalizedTicket, TicketInput
from .audio import transcribe_voice_note
from .text import clean_text
from .vision import describe_screenshot


def normalise_ticket(ticket: TicketInput) -> NormalizedTicket:
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
        metadata=dict(ticket.metadata),
    )

