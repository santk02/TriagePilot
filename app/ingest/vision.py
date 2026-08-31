from __future__ import annotations  # allow forward-referenced type hints on older Python

from typing import Optional  # optional OCR/alt-text inputs


def describe_screenshot(
    image_ref: str,
    ocr_text: Optional[str] = None,
    alt_text: Optional[str] = None,
) -> str:
    """Convert screenshot input into a text description for the classifier prompt.

    Blueprint calls for a vision-model description that extracts visible error messages, status
    codes, and UI state verbatim — that call site is here. This scaffold stays dependency-free by
    preferring supplied OCR text over invoking a real vision model; wire a vision-capable model
    call in place of the `ocr_text`/`alt_text` fallback chain to complete Phase 2 of the blueprint.
    """

    if ocr_text and ocr_text.strip():
        return ocr_text.strip()  # best case: OCR already ran and gave us the on-screen text
    if alt_text and alt_text.strip():
        return alt_text.strip()  # fallback: a caller-supplied description of the image
    if image_ref.strip():
        return f"Screenshot provided: {image_ref}"  # last resort: at least note that one existed
    return ""  # no screenshot at all
