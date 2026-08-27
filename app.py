import json
import shutil
import uuid
from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename

from config import MAX_UPLOAD_BYTES, OUTPUT_DIR, TEST_TYPES, UPLOAD_DIR
from deepseek_client import ocr_pdf
from excel_generator import generate_workbook
from online_client import ocr_pdf as online_ocr_pdf
from parsers import parse_document
from storage import save_and_load

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_BYTES
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


@app.get("/")
def index():
    return redirect(url_for("online"))


@app.get("/online")
def online():
    return render_template("index.html", test_types=TEST_TYPES, ocr_mode="online")


@app.get("/offline")
def offline():
    return render_template("index.html", test_types=TEST_TYPES, ocr_mode="offline")


@app.post("/extract")
def extract():
    test_type = request.form.get("test_type")
    ocr_mode = request.form.get("ocr_mode", "offline")
    endpoint = request.form.get("endpoint", "").strip()
    files = request.files.getlist("pdf_files")
    if test_type not in TEST_TYPES:
        return jsonify(error="Jenis pengukuran tidak valid."), 400
    if ocr_mode not in ("online", "offline"):
        return jsonify(error="Mode OCR tidak valid."), 400
    if ocr_mode == "offline" and not endpoint:
        return jsonify(error="URL endpoint DeepSeek-OCR diperlukan."), 400
    if not files or all(not file.filename for file in files):
        return jsonify(error="Pilih minimal satu PDF."), 400

    records, errors = [], []
    job_dir = UPLOAD_DIR / uuid.uuid4().hex
    job_dir.mkdir()
    try:
        for upload in files:
            if not upload.filename:
                continue
            if Path(upload.filename).suffix.lower() != ".pdf":
                errors.append(f"{upload.filename}: bukan PDF.")
                continue
            path = job_dir / secure_filename(upload.filename)
            upload.save(path)
            try:
                pages = online_ocr_pdf(path, test_type) if ocr_mode == "online" else ocr_pdf(path, endpoint)
                parsed = parse_document(test_type, pages, upload.filename)
                if not parsed:
                    errors.append(f"{upload.filename}: OCR berhasil, tetapi format tabel tidak dikenali parser.")
                records.extend(parsed)
            except Exception as error:
                errors.append(f"{upload.filename}: {error}")
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)

    if not records:
        return jsonify(error="Tidak ada data yang berhasil diekstrak.", details=errors), 422
    return jsonify(records=records, warnings=errors)


@app.post("/generate")
def generate():
    payload = request.get_json(silent=True) or {}
    test_type = payload.get("test_type")
    records = payload.get("records")
    if test_type not in TEST_TYPES or not isinstance(records, list) or not records:
        return jsonify(error="Data untuk pembuatan Excel tidak valid."), 400

    job_id = uuid.uuid4().hex
    save_and_load(test_type, records)
    result = generate_workbook(test_type, records, OUTPUT_DIR, job_id)
    return jsonify(
        excel_url=f"/download/{result['excel'].name}",
        charts=[
            {"label": chart.stem, "png_url": f"/download/{chart.name}"}
            for chart in result["charts"]
        ],
        pdf_url=f"/download/{result['pdf'].name}",
        total_records=len(records),
    )


@app.get("/download/<path:filename>")
def download(filename):
    name = Path(filename).name
    job_id, separator, export_name = name.partition("_")
    download_name = export_name if separator and len(job_id) == 32 and all(character in "0123456789abcdef" for character in job_id) else name
    return send_from_directory(OUTPUT_DIR, filename, as_attachment=True, download_name=download_name)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5005, debug=False)
