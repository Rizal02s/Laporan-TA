# Revisi anotasi berdasarkan review AI

Perubahan telah diterapkan pada file anotasi aktif atas permintaan pengguna.
Ini merupakan revisi kerja berdasarkan interpretasi tracking, bukan sertifikasi kebenaran seluruh label oleh ahli sepak bola. Anotasi lain belum dinyatakan valid hanya karena tidak diubah.

Tiga sampel diubah dari 1 menjadi 0: **#16, #109, #259**. Keyakinan diset sedang (2), karena tidak menggunakan video.

Sepuluh sampel diubah menjadi ragu (-1), dengan keyakinan rendah (1): **#1, #31, #51, #72, #85, #188, #193, #219, #228, #251**. Alasannya meliputi tekanan terhadap opsi operan yang belum jelas, konteks bola mati/restart/FairPlay, dan ketidaksesuaian waktu event dengan tracking.

Audit awal menyebut enam kemungkinan negatif. Pada penerapan, #31, #85, dan #188 dipertahankan sebagai ragu karena belum cukup bukti untuk menolak tekanan terhadap opsi operan. Sampel #154 tetap negatif. Delapan belas label ragu awal tetap ragu.

| Label | Sebelum | Sesudah |
| --- | ---: | ---: |
| Gegenpressing (1) | 217 | 208 |
| Bukan gegenpressing (0) | 29 | 28 |
| Ragu (-1) | 18 | 28 |
| Total | 264 | 264 |

Sampel yang dapat digunakan untuk klasifikasi biner berjumlah **236**, sedangkan 28 ragu dikecualikan. Jumlah negatif turun meskipun ada tiga negatif baru, karena empat negatif lama dipindahkan ke ragu.

Identitas reviewer pada 13 baris yang diubah adalah `codex_ai_review`; nama anotator asli, waktu, label, confidence, dan catatan lama tersimpan dalam log dan cadangan. Catatan lama juga dipertahankan di dalam catatan aktif. Tidak ada perubahan kandidat, fitur, data graph, outcome, ataupun pembagian pertandingan.

File manifest model, ringkasan pembagian pertandingan, dan laporan audit aktif telah diperbarui agar menggunakan label revisi. Artefak model smoke dan artikel sebelumnya tetap merupakan hasil historis, bukan hasil dengan label revisi ini. Tidak ada pelatihan model yang dijalankan.

Pemeriksaan `run_final_training.py --check-only` setelah revisi selesai dengan status **READY** dan seluruh 10 pemeriksaan bernilai True. Ini memeriksa syarat operasional dan integritas data, bukan kebenaran taktis label. Pembagian biner terbaru: latih 164 (147 positif, 17 negatif), validasi 36 (30 positif, 6 negatif), dan uji 36 (31 positif, 5 negatif).

Jika notebook anotasi sedang terbuka, muat ulang data anotasinya sebelum menyimpan label berikutnya, karena notebook menyimpan salinan tabel dalam memori.

## Berkas

- [Log setiap perubahan](perubahan_anotasi.csv).
- [Ringkasan per pertandingan](ringkasan_setelah_revisi.csv).
- [Metadata revisi dan lokasi cadangan](provenance.json).
- [Cadangan lengkap anotasi asli](backups/00_gegenpressing_annotation_manifest.csv).

Keputusan yang masih ragu perlu ditinjau manusia menggunakan rubrik yang sama di seluruh pembagian data. Review ini bukan anotator manusia kedua dan tidak dapat dipakai sebagai bukti inter-rater reliability.
