# GMP Automation Gas Test - Offline OCR

Flask web application that converts scanned Korean GMP gas-test PDFs into reviewable records, Excel workbooks, and downloadable charts.

Supported measurements:

- Oil Content Measurement (`유분 측정 일지`)
- Moisture Content Measurement (`수분 측정 일지`)
- Airborne Particle Measurement (`부유입자 측정 일지`)

## Features

- Offline OCR through a DeepSeek-OCR Kaggle/ngrok endpoint.
- English and Korean interface.
- Additive multi-PDF upload for one measurement type at a time.
- Duplicate upload selections are ignored, and selected files can be removed before extraction.
- Reviewable and editable OCR results before export.
- Excel generation with XlsxWriter.
- Column charts with warning/acceptance limits rendered as line series.
- JPG chart exports and a combined chart PDF.
- Clean download names without internal job IDs.

## Offline OCR

Open `http://127.0.0.1:5006/offline`.

This branch listens on port `5006`. The companion `gmp-online` branch listens on port `5005`. To run both applications at the same time, launch each branch from a separate checkout or Git worktree.

Offline OCR renders each PDF page locally and sends it to the DeepSeek-OCR `/ocr` endpoint. Enter the active Kaggle/ngrok base URL in the interface, for example:

```text
https://example.ngrok-free.app
```

The application appends `/ocr` automatically. `kaggle_server.py` contains the FastAPI server used by the offline workflow and exposes `/health` and `/ocr` routes.

## System Requirements

- Python 3.10 or newer.
- Poppler for rendering scanned PDF pages.
- Access to the configured DeepSeek-OCR endpoint.

Install Poppler:

```bash
# macOS
brew install poppler

# Ubuntu or Debian
sudo apt install poppler-utils
```

On Windows, install Poppler and add its `Library\bin` directory to `PATH`.

## Installation

### Automatic Start

macOS:

```bash
./START_MAC.sh
```

Windows:

```bat
START_WINDOWS.bat
```

The startup scripts create `.venv`, install `requirements.txt`, open the browser, and run the application on port `5006`.

### Manual Start

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Windows activation:

```bat
.venv\Scripts\activate
```

Open `http://127.0.0.1:5006`. The root route redirects to `/offline`.

## Workflow

1. Enter the active DeepSeek-OCR Kaggle/ngrok endpoint.
2. Select Oil, Moisture, or Airborne Particle.
3. Select or drag one or more PDFs from the same measurement type.
4. Add more PDFs in later selections if needed; new files are appended to the list.
5. Remove unwanted files with the red cross button.
6. Select **Extract Data**.
7. Review and correct OCR values, especially handwritten dates and measurements.
8. Select **Generate Excel and Charts**.
9. Download the Excel workbook, combined chart PDF, or individual chart JPG files.

Generating Excel does not call the DeepSeek-OCR endpoint. Endpoint usage only occurs during **Extract Data**.

## Output

Each export contains only the records reviewed in the current upload batch. Previous local records are not appended to the generated workbook.

Oil workbook:

- `데이터`
- `간소화된 데이터`
- `피벗 차트`

Moisture workbook:

- `데이터`
- `간소화된 데이터`
- `피벗 차트`

Airborne workbook:

- `데이터`
- `Pivot 0.5`
- `Pivot 5.0`

Airborne creates separate `0.5 μm` and `5.0 μm` JPG downloads. Its charts are placed dynamically two blank rows after their source tables.

Generated files are stored in `outputs/`. Server filenames include an internal job ID to prevent collisions, but browser downloads use clean measurement-log names.

## Local Data

Reviewed records are also stored locally in:

```text
data/gas_test_logs.sqlite3
```

The database is retained as local history, but it is not merged into the current Excel export. To clear the history, stop the application and delete `data/gas_test_logs.sqlite3`.

Temporary uploaded PDFs are removed after OCR processing. The following paths are ignored by Git:

- `.env`
- `.venv/`
- `uploads/`
- `outputs/`
- `data/`

## Privacy

The application sends rendered pages to the DeepSeek-OCR endpoint entered by the user. PDF rendering, review, storage, Excel generation, JPG generation, and PDF chart generation occur locally.

## Validation

Run basic syntax checks without performing OCR:

```bash
.venv/bin/python -m py_compile app.py deepseek_client.py parsers.py storage.py excel_generator.py
node --check static/app.js
```

For an end-to-end test, upload a sample PDF through the interface, verify the review table, generate the workbook, and inspect each Excel sheet and chart.

## Troubleshooting

### `422 Unprocessable Entity`

OCR completed, but no valid measurement records were parsed. Confirm that the selected measurement type matches the PDF. Restart the Flask server after pulling code changes. Offline OCR expects table-based Markdown or HTML from DeepSeek-OCR.

### PDF rendering fails

Install Poppler and confirm `pdftoppm` is available on `PATH`.

### Offline endpoint fails

Open `<endpoint>/health` and confirm it returns a successful response. Ensure the ngrok session and Kaggle runtime are still active.

### Browser shows an older interface

Restart the Flask process and reload the page. Static JavaScript URLs include cache-busting versions, but a running process may still serve an older template until restarted.

## Main Files

- `app.py`: Flask routes for the offline page, extraction, generation, and downloads.
- `deepseek_client.py`: DeepSeek-OCR endpoint client.
- `parsers.py`: Structured JSON and HTML/Markdown table parsers.
- `excel_generator.py`: XlsxWriter workbooks plus Matplotlib JPG/PDF charts.
- `storage.py`: Local SQLite history.
- `templates/index.html`: Application interface.
- `static/app.js`: Upload management, review table, generation, and downloads.
- `kaggle_server.py`: DeepSeek-OCR FastAPI server for Kaggle.
