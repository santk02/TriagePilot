from __future__ import annotations

from typing import Optional


def describe_screenshot(
    image_ref: str,
    ocr_text: Optional[str] = None,
    alt_text: Optional[str] = None,
) -> str:
    """Convert screenshot input into a text description.

    The scaffold keeps this dependency-free by preferring supplied OCR text.
    """

    if ocr_text and ocr_text.strip():
        return ocr_text.strip()
    if alt_text and alt_text.strip():
        return alt_text.strip()
    if image_ref.strip():
        return f"Screenshot provided: {image_ref}"
    return ""

