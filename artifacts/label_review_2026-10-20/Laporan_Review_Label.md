# Audit awal label gegenpressing — 20 Oktober 2026

Audit ini membantu adjudikasi anotasi, bukan penetapan ground truth otomatis. Seluruh 264 sampel diperiksa kembali secara numerik dari tracking; 65 sampel prioritas diperiksa melalui ringkasan lintasan 0–2 detik, termasuk seluruh 29 negatif, 18 ragu, dan 18 positif dengan cue nol atau singkat. Sepuluh sampel diperiksa lagi dengan panel lima waktu. Sampel lain belum divalidasi visual satu per satu. Tidak ada label sumber yang diubah.

## Dasar penilaian

Dalam definisi Bauer dan Anzer (2021), tekanan balik dapat dilakukan oleh sedikitnya satu pemain terhadap pembawa bola atau lawan dekat bola selama transisi bertahan. Menutup opsi operan juga dapat menjadi tekanan. Karena itu, bek yang tetap di belakang, hanya satu pemain yang mengejar, atau kegagalan merebut bola kembali bukan alasan tunggal untuk memberi label 0.

Sumber: [Bauer & Anzer, bagian 2.1.2–2.2.1](https://link.springer.com/article/10.1007/s10618-021-00763-7).

Cue program mengukur jarak ke bola (bukan identitas pembawa bola terverifikasi): jarak ≤4,572 m atau jarak ≤10 m yang berkurang ≥1 m/s. Cue nol hanya alasan untuk meninjau, bukan definisi negatif. Penurunan jarak dipengaruhi gerakan bola. Batas 0,4 detik digunakan untuk memilih prioritas audit sesuai konfigurasi, bukan syarat ilmiah universal bahwa pressing yang lebih singkat pasti bukan gegenpressing.

## Enam label positif yang paling perlu ditinjau sebagai kemungkinan negatif

Semua rekomendasi di bawah bersifat sementara berdasarkan tracking dan visualisasi. Ketidakadaan tekanan langsung tidak meniadakan kemungkinan tekanan terhadap opsi operan; keputusan akhir perlu mengikuti rubrik yang konsisten.

| Nomor sampel | ID kandidat | Label awal | Jarak minimum ke bola (m) | Panel |
| --- | --- | --- | --- | --- |
| 16 | J03WMX_P1_F11238 | 1 | 14.76 | [Bukti](panels/016.png) |
| 31 | J03WMX_P2_F104384 | 1 | 12.66 | [Bukti](panels/031.png) |
| 85 | J03WOH_P1_F50920 | 1 | 14.21 | [Bukti](panels/085.png) |
| 109 | J03WOY_P1_F48730 | 1 | 16.33 | [Bukti](panels/109.png) |
| 188 | J03WQQ_P1_F71233 | 1 | 11.61 | [Bukti](panels/188.png) |
| 259 | J03WR9_P1_F16153 | 1 | 18.05 | [Bukti](panels/259.png) |

- **#16:** Lawan berada dekat bola di sisi kiri; pemain merah terdekat tetap 14,76–19,13 m. Tidak tampak penutupan langsung terhadap pemain dekat bola sepanjang panel. Penjagaan lawan yang jauh dari bola belum membuktikan counterpress.
- **#31:** Bola berada di sisi kiri dengan ruang antara pemain dekat bola dan tim merah. Jarak terdekat tidak pernah kurang dari 12,66 m. Penjagaan beberapa lawan jauh dari bola terlihat, tetapi tekanan segera di sekitar bola tidak jelas.
- **#85:** Bola berpindah di antara pemain biru; jarak pemain merah terdekat terhadap bola naik dari 14,21 menjadi 17,23 m. Tidak tampak penutupan langsung terhadap bola. Perlu memastikan apakah penjagaan penerima lain merupakan tekanan terhadap opsi operan.
- **#109:** Bola bergerak menjauh dari kelompok merah; jarak terdekat bertambah dari 16,33 menjadi 29,36 m. Tidak terlihat pemain merah menutup pemain dekat bola. Panel lebih mendukung tidak adanya tekanan langsung dalam jendela ini.
- **#188:** Pemain biru di sisi bawah kiri memiliki ruang; jarak terdekat tim merah naik dari 11,61 menjadi 19,53 m. Pergerakan merah tidak memperlihatkan pengejaran langsung yang menutup jarak. Penjagaan opsi operan tetap perlu dipertimbangkan.
- **#259:** Bola berada di sisi kanan, sedangkan pemain merah tetap di luar radius 10 m. Jarak terdekat 18,05–19,36 m; lintasan merah umumnya menjauh dari sisi bola. Lebih mendukung tidak adanya tekanan langsung.

## Kasus yang perlu dipisahkan dari dugaan negatif biasa

- **#51 — review_konteks_bola_mati:** Label awal 1 tidak didukung cue dekat bola. Tracking berubah menjadi dead pada t=0,72 s dan tetap dead selama 33 frame. Perlu menilai bagian permainan hidup dan kesesuaian event; jangan otomatis memasukkan kejadian di luar permainan sebagai negatif biasa. [Bukti](panels/051.png).
- **#228 — review_konteks_fairplay:** Semua pemain merah berjarak sekurangnya 22,52 m dari bola. Event GENERIC:FairPlay tercatat pada t=+0,308 s. Panel tidak mendukung tekanan langsung, tetapi arti event dan kelayakan kandidat perlu dipastikan sebelum memutuskan 0 atau pengecualian. [Bukti](panels/228.png).
- **#251 — belum_pasti_review_0_atau_ragu:** Jarak bola terhadap pemain merah terdekat meningkat 6,32 menjadi 19,99 m setelah bola bergerak ke sisi kanan. Tidak ada cue berbasis jarak bola, tetapi lintasan pemain dekat lokasi awal perlu diperiksa: operan cepat dapat membuat tekanan yang sebenarnya tidak tertangkap cue. [Bukti](panels/251.png).
- **#219 — review_label_0_dan_konteks:** Tidak ada cue dekat bola, tetapi bola kemudian mati. Event BALL_OUT berada pada +0,606 s, sedangkan tracking pertama dead pada +1,64 s. Perbedaan waktu ini perlu dicek; jangan menyamakan seluruh jendela sebagai permainan aktif. [Bukti](panels/219.png).
- **#72 — review_konteks_restart:** Catatan pengguna menyebut throw-in. Lintasan memang dekat garis samping, dan event BALL_OUT tercatat -1,535 s. Tracking dua detik sebelumnya tidak mencatat dead, sehingga jenis kejadian dan sinkronisasi harus dipastikan sebelum menyimpulkan. [Bukti](panels/sheet_03.png).
- **#193 — review_kelayakan_transisi:** Frame tepat sebelum loss berstatus dead, sedangkan frame loss alive. Kandidat mungkin menangkap restart, bukan kehilangan bola dalam permainan terbuka; evaluasi kelayakannya terpisah dari label perilaku. [Bukti](panels/sheet_09.png).

## Contoh negatif yang didukung dan alasan yang perlu ditinjau

- **#154:** Label awal 0 didukung panel: pemain biru memiliki ruang, tidak ada pemain merah dalam radius 10 m; jarak minimum 14,51 m. Tidak terlihat tekanan segera terhadap bola. Tetap merupakan interpretasi tracking. [Bukti](panels/154.png).
- **#1:** Catatan bek terlalu ke belakang tidak cukup untuk menetapkan 0. Lintasan menunjukkan satu pemain merah mengikuti area bola dan terdapat cue singkat; nilai respons pemain lokal, bukan posisi seluruh garis pertahanan. [Lintasan](panels/sheet_01.png).
- **#73:** Pemain merah mengikuti area pemain biru dengan jarak sekitar 5–6 m sebelum bola menjauh. Cue hanya muncul singkat (run terpanjang 0,08 s). Ini belum cukup untuk memastikan negatif karena tekanan terhadap ruang dapat terjadi di luar ambang jarak. [Panel](panels/073.png).

Untuk 29 sampel berlabel 0, audit ini tidak menyatakan semuanya benar. Sampel berkerumun dekat gawang, rebound, dan duel memerlukan pemeriksaan urutan kepemilikan serta arah respons. Hasil cue yang besar tidak otomatis berarti label 0 salah.

## Cakupan dan temuan integritas

- Label sumber: 217 positif, 29 negatif, 18 ragu. Total 264.
- 9 positif tidak mempunyai cue dekat bola sama sekali; 9 positif lain memiliki run cue terpanjang kurang dari 0,4 detik.
- 27 jendela mengandung setidaknya satu frame dead setelah loss. Ini tidak otomatis membatalkan pressing sebelum bola mati; hanya bagian saat permainan aktif yang relevan untuk menilai perilaku.
- 14 kandidat memiliki frame dead dalam dua detik sebelum loss; pada #193, frame tepat sebelum loss adalah dead. Perlu membedakan restart dan pergantian penguasaan saat permainan terbuka.
- Hasil perhitungan ulang jumlah cue maksimum, durasi cue, dan jarak minimum cocok dengan fitur yang tersimpan. Jadi, temuan bukan akibat membaca hitungan anotasi lama.
- Hasil READY sebelumnya adalah pemeriksaan kelengkapan dan syarat program, bukan pengesahan kebenaran taktis label.
- Angka durasi dari kode dihitung jumlah frame/25; run 51 frame ditulis 2,04 s meskipun rentang waktu sampel adalah 0–2,00 s. Ini merupakan konvensi hitungan kode, bukan perpanjangan observasi.
- Dimensi lapangan 105 × 68 m mengikuti konfigurasi proyek. Tidak ada rekaman video yang digunakan dalam audit ini. Panel menyembunyikan label dan hasil perebutan kembali, tetapi reviewer telah membaca label untuk memilih sampel; ini bukan penilaian manusia independen atau uji inter-rater reliability.

## Tindak lanjut yang disarankan

1. Buka nomor sampel di notebook anotasi dan nilai apakah tim merah benar tim yang kehilangan bola, apakah permainan aktif, serta apakah ada tekanan segera terhadap pembawa bola atau opsi operan.
2. Tinjau enam kandidat di atas dan kasus konteks khusus lebih dulu. Bila tetap tidak jelas, pertahankan status ragu; jangan memaksakan negatif untuk menyeimbangkan kelas.
3. Catat keputusan akhir, alasan, reviewer, tanggal, dan versi anotasi. Label di kelompok uji tidak boleh diubah karena ingin memperbaiki skor model; audit harus mengikuti aturan yang sama pada semua kelompok.
4. Setelah adjudikasi selesai, buat ulang laporan audit dan periksa kesiapan pelatihan.

## Berkas pendukung

- [Hasil screening dan rekomendasi 264 sampel](hasil_review_264.csv): `belum_diputuskan` tidak berarti label sudah benar.
- [29 label negatif asli](29_label_negatif_asli.csv).
- [27 jendela yang mengandung bola mati](27_jendela_mengandung_bola_mati.csv).
- [Konteks event](event_context.csv) dan [status permainan sekitar transisi](transition_context.csv).

Semua label asli tetap berada pada `data/processed/gegenpressing_annotation_manifest.csv`. Tidak ada pelatihan model atau perubahan artikel dalam audit ini.
