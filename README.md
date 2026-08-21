# Gas Test Log Generator

Web app Python untuk mengubah PDF scan Oil Content Measurement, Moisture Content Measurement, dan Airborne Particle Measurement menjadi Excel log serta grafik.

## Cara Menjalankan

1. Jalankan DeepSeek-OCR di Kaggle dan buat ngrok endpoint dengan server yang telah Anda siapkan.
2. Jalankan `START_MAC.sh` pada macOS atau `START_WINDOWS.bat` pada Windows.
3. Browser akan membuka `http://127.0.0.1:5001`.
4. Pilih jenis pengukuran, masukkan URL ngrok, lalu unggah satu atau beberapa PDF yang sejenis.
5. Tinjau dan koreksi hasil ekstraksi sebelum memilih **Buat Excel dan Grafik**.

## Data dan Privasi

- PDF dirender di komputer lokal, kemudian setiap halaman dikirim ke endpoint DeepSeek-OCR Kaggle/ngrok yang Anda masukkan.
- Hasil pengukuran tersimpan secara lokal pada `data/gas_test_logs.sqlite3` agar input semester baru digabungkan dengan log sebelumnya.
- File hasil sementara berada di `outputs/`.
- Untuk menghapus riwayat lokal, hapus file `data/gas_test_logs.sqlite3` saat aplikasi tidak berjalan.

## Output

- **Oil:** `데이터`, `간소화된 데이터`, `피벗 차트`
- **Moisture:** `데이터`, `간소화된 데이터`, `피벗 차트`
- **Airborne:** `데이터`, `Pivot 0.5`, `Pivot 5.0`

Selain workbook Excel, aplikasi menyediakan PNG untuk setiap grafik dan PDF gabungan grafik.

## Dependensi Sistem

PDF scan membutuhkan Poppler agar `pdf2image` dapat merender halaman PDF.

- macOS: `brew install poppler`
- Ubuntu/Debian: `sudo apt install poppler-utils`
- Windows: pasang Poppler dan tambahkan folder `Library\\bin` ke `PATH`.
