"""Client for the DeepSeek-OCR server running on Kaggle through ngrok."""

import base64
from io import BytesIO

import requests
from pdf2image import convert_from_path

TIMEOUT_SECONDS = 300


def _image_to_base64(image):
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def ocr_pdf(pdf_path, endpoint_url, dpi=200, resolution="gundam"):
    """Return one DeepSeek-OCR markdown/HTML response for every PDF page."""
    url = endpoint_url.rstrip("/") + "/ocr"
    pages = convert_from_path(pdf_path, dpi=dpi)
    results = []

    for page_number, image in enumerate(pages, start=1):
        response = requests.post(
            url,
            json={
                "image_b64": _image_to_base64(image),
                "mode": "markdown",
                "resolution": resolution,
            },
            timeout=TIMEOUT_SECONDS,
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"OCR server returned {response.status_code} for page {page_number}: "
                f"{response.text}"
            )
        results.append(response.json().get("text", ""))

    return results
