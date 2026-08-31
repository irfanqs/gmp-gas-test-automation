"""Anthropic-backed OCR for the /online workflow."""

import base64
import os
from io import BytesIO

import requests
from pdf2image import convert_from_path
from dotenv import load_dotenv
from PIL import ImageEnhance, ImageFilter

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
load_dotenv()

PROMPTS = {
    "oil": (
        "Oil Content Measurement",
        "no, management_number, location, result_text, photo_attached, judgement, criteria_text, performed_date",
    ),
    "moisture": (
        "Moisture Content Measurement",
        "no, management_number, location, result_text, photo_attached, judgement, criteria_text, performed_date",
    ),
    "airborne": (
        "Airborne Particle Measurement",
        "no, management_number, location, grade, particle_05, particle_50, judgement, criteria_text, performed_date",
    ),
}


def _base64_png(image):
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def ocr_pdf(pdf_path, test_type, dpi=200):
    """Return structured OCR text for all scanned PDF pages."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not configured in .env.")
    images = convert_from_path(pdf_path, dpi=dpi)
    content = []
    for page_number, image in enumerate(images, start=1):
        content.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": _base64_png(image)},
        })
        width, height = image.size
        table_detail = image.crop((int(width * 0.02), int(height * 0.07), int(width * 0.98), int(height * 0.48)))
        table_detail = ImageEnhance.Contrast(table_detail).enhance(1.35).filter(ImageFilter.SHARPEN)
        content.extend([
            {
                "type": "text",
                "text": (
                    f"The next image is an enhanced close-up of the measurement table on page {page_number}. "
                    "Use it only to verify handwritten values; it does not contain additional records."
                ),
            },
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": _base64_png(table_detail)},
            },
        ])
    if images:
        width, height = images[-1].size
        date_detail = images[-1].crop((0, int(height * 0.68), width, height))
        content.extend([
            {"type": "text", "text": "The next image is a close-up of the signature and date area from the final page."},
            {
                "type": "image",
                "source": {"type": "base64", "media_type": "image/png", "data": _base64_png(date_detail)},
            },
        ])
    document_name, fields = PROMPTS[test_type]
    content.append(
        {
            "type": "text",
            "text": (
                f"Extract this scanned Korean GMP document ({document_name}) into JSON. "
                f"Return only one valid JSON object with this shape: {{\"records\": [...]}}. "
                f"Every record must contain these keys: {fields}. "
                "Create exactly one record per numbered measurement row. Preserve Korean text exactly. "
                "Keep result_text limited to the handwritten measurement result; do not include photo or checkbox text. "
                "Every measurement-result cell contains a numeric value, never a punctuation symbol. "
                "For oil and moisture, normalize result_text as '<number> mg/m³ 이하' or '<number> mg/m³ 이상'. "
                "A handwritten vertical stroke in a decimal value is the digit 1, never |, I, l, or !; "
                "for example, read 0.|, 0.I, and 0.l as 0.1. Cross-check the value against the printed criterion and repeated rows. "
                "For airborne measurements, particle_05 and particle_50 are handwritten integer counts. "
                "Use each enhanced table close-up as the primary source for those digits and explicitly distinguish ambiguous "
                "pairs such as 3/4, 1/7, 0/6, and 6/8 by their pen strokes. Never infer a measured value from the limit. "
                "Before returning JSON, compare each count with its Grade limit and checked row judgement. If they conflict, "
                "re-inspect the close-up and transcribe the visible digits; do not change a clearly written value merely to fit the limit. "
                "Set photo_attached to exactly Yes or No and judgement to exactly 적합 or 부적합. "
                "Use performed_date from the handwritten Performed by date in YYYY.MM.DD format. "
                "Cross-check repeated dates in the close-up and carefully distinguish handwritten 08 from 06. "
                "Repeat the document-level criterion, judgement, and performed date in every record. "
                "Use JSON numbers for particle_05 and particle_50. Do not return Markdown or explanatory text."
            ),
        }
    )
    response = requests.post(
        ANTHROPIC_URL,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        json={"model": ANTHROPIC_MODEL, "max_tokens": 8192, "messages": [{"role": "user", "content": content}]},
        timeout=300,
    )
    if response.status_code != 200:
        raise RuntimeError(f"Anthropic API returned {response.status_code}: {response.text}")
    text = "".join(block.get("text", "") for block in response.json().get("content", []) if block.get("type") == "text")
    return [text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()]
