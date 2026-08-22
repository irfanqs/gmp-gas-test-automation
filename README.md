# Gas Test Log Generator

Python web application that converts scanned Oil Content Measurement, Moisture Content Measurement, and Airborne Particle Measurement PDFs into Excel logs and charts.

## Running the Application

1. For `/offline`, run DeepSeek-OCR on Kaggle and create an ngrok endpoint with the provided server. For `/online`, prepare an Anthropic API key.
2. Run `START_MAC.sh` on macOS or `START_WINDOWS.bat` on Windows.
3. Your browser will open `http://127.0.0.1:5001`.
4. Open `/offline` for a DeepSeek ngrok URL or `/online` for an Anthropic API key, select a measurement type, and upload one or more PDFs of the same type.
5. Review and correct extracted data before selecting **Generate Excel and Charts**.

## Data and Privacy

- PDFs are rendered locally, then each page is sent to the DeepSeek-OCR Kaggle/ngrok endpoint you provide.
- Measurement results are stored locally in `data/gas_test_logs.sqlite3`, allowing later semesters to be combined with existing logs.
- Temporary output files are stored in `outputs/`.
- To clear local history, delete `data/gas_test_logs.sqlite3` while the application is not running.

## Output

- **Oil:** `데이터`, `간소화된 데이터`, `피벗 차트`
- **Moisture:** `데이터`, `간소화된 데이터`, `피벗 차트`
- **Airborne:** `데이터`, `Pivot 0.5`, `Pivot 5.0`

In addition to the Excel workbook, the application generates a PNG for every chart and a combined chart PDF.

## System Dependencies

Scanned PDFs require Poppler so that `pdf2image` can render their pages.

- macOS: `brew install poppler`
- Ubuntu/Debian: `sudo apt install poppler-utils`
- Windows: install Poppler and add its `Library\bin` directory to `PATH`.
