# Laporan hasil VAEP-Track

Sumber: `final_training_20261027T152829Z`. Status: `final_training_complete`. Seed: 42.

Penelitian menggunakan 1,873 episode beranotasi, dengan 1,355 episode latih, 195 episode validasi, dan 323 episode uji. Pembagian dilakukan berdasarkan pertandingan. Pada data uji dari 1 pertandingan, Temporal GNN memperoleh accuracy 86.69%, precision kelas positif 89.01%, recall kelas positif 94.92%, dan F1 kelas positif 91.87%. XGBoost memperoleh accuracy 80.80% dan F1 kelas positif 88.60%. Selisih accuracy GNN terhadap XGBoost adalah 5.88 poin persentase. GNN memiliki macro F1 77.56%, balanced accuracy 75.07%, ROC-AUC 0.8764, dan AP 0.9533. Recall kelas bukan gegenpressing sebesar 55.22% menunjukkan keterbatasan pengenalan kelas negatif. Terdapat 30 false positive dan 13 false negative. Hasil mendukung kinerja deteksi GNN yang lebih tinggi pada split ini, namun belum membuktikan generalisasi lintas pertandingan yang luas, signifikansi perbedaan, atau efektivitas kausal gegenpressing.

## Batas interpretasi

- Test berisi 323 episode dari 1 pertandingan; belum evaluasi silang antarpertandingan.
- Episode dalam pertandingan dapat saling berkaitan; jangan menganggap semuanya sampel independen untuk uji statistik.
- Label positif dominan. Laporkan kelas negatif, macro F1, dan balanced accuracy bersama accuracy/F1 positif.
- Ada 6 label confidence 1 dalam manifest; pemeriksaan berkas tidak menilai kebenaran taktis label.
- Belum ada pengukuran kesepakatan penilai independen dalam laporan ini.
- Perbedaan model bersifat deskriptif pada satu run/split; belum membuktikan keunggulan umum atau signifikansi statistik.
- Prediksi mendeteksi anotasi gegenpressing menggunakan jendela observasi; bukan deteksi seketika tepat saat kehilangan bola.
- Hasil ini belum mengukur efek kausal taktik, nilai VAEP, atau keberhasilan merebut bola kembali sebagai target klasifikasi.

## Tabel uji (%)

```text
                              accuracy  precision_1  recall_1   f1_1  recall_0  macro_f1  balanced_accuracy
model                                                                                                      
Logistic Regression              77.71        82.86     90.62  86.57     28.36     60.56              59.49
XGBoost                          80.80        83.68     94.14  88.60     29.85     63.91              62.00
Temporal GNN                     86.69        89.01     94.92  91.87     55.22     77.56              75.07
Selalu kelas mayoritas latih     79.26        79.26    100.00  88.43      0.00     44.21              50.00
```

AP dihitung dengan average_precision_score; F1 kelas 1 bukan accuracy.
