# VAEP Track Training Pipeline

## Status

Pipeline baseline, temporal GNN, dan evaluasi match-level sudah tersedia. Hasil
yang berada di direktori `artifacts/*_smoke` hanya membuktikan integrasi kode.
Hasil tersebut tidak boleh digunakan sebagai hasil penelitian karena anotasi
manual belum lengkap.

## Urutan kerja

1. Selesaikan seluruh queue pada `08_full_gegenpressing_annotation.ipynb`.
2. Jalankan cell quality gate dan pastikan `all_264_completed` bernilai `True`.
3. Jalankan `13_annotation_quality_audit.ipynb`, lalu audit ulang label ragu dan
   confidence rendah tanpa melihat quick regain.
4. Jalankan pemeriksaan kesiapan:

   ```powershell
   .\venv\Scripts\python.exe scripts\run_final_training.py --check-only
   ```

5. Hanya jika output menunjukkan `READY`, jalankan training final:

   ```powershell
   .\venv\Scripts\python.exe scripts\run_final_training.py
   ```

## Artefak final

Runner membuat direktori bertimestamp `artifacts/final_training_<UTC>` yang
berisi:

- snapshot anotasi dan model manifest;
- ringkasan audit anotasi dan blinded review queue;
- model logistic regression dan XGBoost;
- checkpoint temporal GNN;
- prediksi untuk train, validation, dan test;
- metrik per split dan per pertandingan;
- riwayat training GNN;
- checksum input dan metadata reproduksibilitas.
- hasil audit integritas artefak sebelum direktori diberi status final.

Runner mula-mula menulis ke `artifacts/final_training_incomplete_<UTC>`. Nama
tersebut hanya diubah menjadi `final_training_<UTC>` setelah seluruh file,
metadata final, quality gate, model, dan checksum lulus audit.

## Aturan metodologis

- Split dilakukan berdasarkan pertandingan dan tidak boleh diacak per episode.
- Threshold klasifikasi dipilih dari validation, bukan test.
- Fitur kontinu GNN (`x`, `y`, dan `speed`) dinormalisasi memakai statistik
  train saja; indikator jenis node dan tim tetap biner.
- Label `Ragu` tidak boleh dikonversi menjadi kelas negatif.
- Outcome quick regain tidak digunakan sebagai fitur atau target deteksi
  gegenpressing.
- Artefak smoke test tidak boleh dipindahkan atau dinamai sebagai hasil final.
- Evaluasi menolak kandidat, ground truth, match/split, atau threshold yang tidak
  konsisten di antara model pembanding.
