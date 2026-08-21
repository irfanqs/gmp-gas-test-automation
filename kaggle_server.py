"""Run this file in Kaggle to expose DeepSeek-OCR as an ngrok HTTP service."""

import base64
import contextlib
import io
import os
import shutil
import tempfile
import uuid

import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoModel, AutoTokenizer

MODEL_NAME = "deepseek-ai/DeepSeek-OCR"
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME, trust_remote_code=True)
model = AutoModel.from_pretrained(
    MODEL_NAME,
    _attn_implementation="eager",
    trust_remote_code=True,
    use_safetensors=True,
).eval().cuda().to(torch.bfloat16)

app = FastAPI(title="DeepSeek-OCR GMP Backend")
DOC_TO_MARKDOWN_PROMPT = "<image>\n<|grounding|>Convert the document to markdown. "
RESOLUTION_PRESETS = {
    "tiny": dict(base_size=512, image_size=512, crop_mode=False),
    "small": dict(base_size=640, image_size=640, crop_mode=False),
    "base": dict(base_size=1024, image_size=1024, crop_mode=False),
    "large": dict(base_size=1280, image_size=1280, crop_mode=False),
    "gundam": dict(base_size=1024, image_size=640, crop_mode=True),
}


class OcrRequest(BaseModel):
    image_b64: str
    mode: str = "markdown"
    resolution: str = "gundam"


@app.get("/health")
def health():
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/ocr")
def ocr(request: OcrRequest):
    if request.resolution not in RESOLUTION_PRESETS:
        raise HTTPException(400, "Unknown resolution preset")

    work_dir = tempfile.mkdtemp(prefix="deepseek_ocr_")
    image_path = os.path.join(work_dir, f"{uuid.uuid4().hex}.png")
    try:
        with open(image_path, "wb") as image_file:
            image_file.write(base64.b64decode(request.image_b64))

        preset = RESOLUTION_PRESETS[request.resolution]
        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            result = model.infer(
                tokenizer,
                prompt=DOC_TO_MARKDOWN_PROMPT,
                image_file=image_path,
                output_path=work_dir,
                base_size=preset["base_size"],
                image_size=preset["image_size"],
                crop_mode=preset["crop_mode"],
                save_results=True,
            )

        if not isinstance(result, str) or not result.strip():
            output = captured.getvalue().split("=====================")
            result = output[-1].strip() if len(output) > 1 else ""
        if not result:
            saved = []
            for name in sorted(os.listdir(work_dir)):
                if name.endswith((".mmd", ".md", ".txt")):
                    with open(os.path.join(work_dir, name), encoding="utf-8") as file:
                        saved.append(file.read())
            result = "\n".join(saved)
        return {"text": result}
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
