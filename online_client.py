"""Anthropic-backed OCR for the /online workflow."""

import base64
import os
from io import BytesIO

import requests
from pdf2image import convert_from_path
from dotenv import load_dotenv

ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_MODEL = "claude-sonnet-4-5-20250929"
load_dotenv()

PROMPTS = {
    "oil": "유분 측정 기록서 (Oil Content Measurement)",
    "moisture": "수분 측정 기록서 (Moisture Content Measurement)",
    "airborne": "부유입자 측정 기록서 (Airborne Particle Measurement)",
}


def _base64_png(image):
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def ocr_pdf(pdf_path, test_type, dpi=200):
    """Return an HTML transcription for every scanned PDF page."""
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not configured in .env.")
    images = convert_from_path(pdf_path, dpi=dpi)
    content = [
        {
            "type": "image",
            "source": {"type": "base64", "media_type": "image/png", "data": _base64_png(image)},
        }
        for image in images
    ]
    content.append(
        {
            "type": "text",
            "text": (
                f"Transcribe this scanned Korean GMP document ({PROMPTS[test_type]}) exactly. "
                "Return only valid HTML. Preserve every table, row, column, Korean text, handwritten "
                "measurement, checkbox state, acceptance criterion, final judgement, and performed date. "
                "Use <table>, <tr>, <th>, and <td>; use checked checkboxes as the character ☑."
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
    return [text.removeprefix("```html").removeprefix("```").removesuffix("```").strip()]
