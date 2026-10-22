from pathlib import Path
import json,re

BASE=Path(r'C:\VAEP-Track\docs\artikel_progres_2026-10-19')
# Reuse verified content and helpers without executing the original file-writing block.
source=(BASE/'_work'/'build_article.py').read_text(encoding='utf-8')
exec(compile(source.split('\nfull=newdoc()\n')[0],str(BASE/'_work'/'build_article.py'),'exec'))
DEST=BASE/'tahap_1'
DEST.mkdir(exist_ok=True)

intro=SECTIONS[1]
SECTIONS[1]=[
H('Latar belakang'), *intro[:4],
P('Secara operasional, situasi menekan dibaca dari perubahan hubungan pemain yang kehilangan bola terhadap bola dan lawan. Pemain yang sudah dekat pada satu frame belum tentu sedang meningkatkan tekanan, sementara pemain yang semula lebih jauh dapat bergerak cepat mendekati situasi penguasaan. Informasi waktu diperlukan untuk membedakan perubahan tersebut. Graph dipilih sebagai representasi relasional karena identitas pemain dan bola tetap dapat dipertahankan ketika hubungan kedekatannya berubah. Pemilihan representasi ini memiliki alasan konseptual, tetapi efektivitasnya tetap merupakan pertanyaan empiris.'),
H('Permasalahan dan pertanyaan penelitian'),
P('Permasalahan penelitian mencakup dua tingkat. Tingkat pertama adalah membentuk sampel yang layak dari data tracking, karena kelengkapan window, keterlacakan identitas pemain, dan validitas posisi menentukan apakah graph dapat dibangun secara konsisten. Tingkat kedua adalah mempelajari perilaku dari sampel berlabel dan mengevaluasi prediksi pada pertandingan berbeda. Keberhasilan menjalankan model tidak cukup untuk menjawab tingkat kedua apabila kualitas label dan jumlah sampel evaluasi masih terbatas.'),
intro[4],
P('Pertanyaan tersebut dirumuskan menjadi tiga fokus: pembentukan episode dan graph yang dapat direproduksi; penyediaan label gegenpressing yang terpisah dari outcome serta dapat diaudit; dan perbandingan deteksi menggunakan representasi graph temporal dengan representasi fitur ringkas. Pengamatan perkembangan anotasi merupakan bagian dari penilaian kesiapan eksperimen. Penelitian tidak menetapkan satu model sebagai pemenang sebelum prediksi akhir dibandingkan pada episode evaluasi yang sama.'),
H('Tujuan dan kontribusi yang diusulkan'),
intro[5],
P('Kontribusi yang diusulkan terletak pada keterhubungan definisi target, konstruksi sampel, representasi graph, dan protokol pembanding dalam satu proses yang dapat ditelusuri. Logistic regression memberikan pembanding sederhana, sementara XGBoost memungkinkan pengujian terhadap model nonlinier berbasis fitur. Jika kinerja kedua baseline sudah memadai, kompleksitas tambahan pada Temporal GNN harus dijustifikasi oleh bukti hasil atau karakter kesalahan yang relevan. Karena bentuk inputnya berbeda, evaluasi utama membandingkan pendekatan lengkap dan tidak langsung mengisolasi manfaat satu komponen arsitektur.'),
H('Ruang lingkup penelitian'),
P('Ruang lingkup mencakup tujuh pertandingan IDSSE dan episode yang memenuhi pemeriksaan struktur. Label perilaku ditentukan melalui visualisasi tracking dan indikator pendukung; video pertandingan tidak digunakan. Pengembangan ini merupakan penelitian awal pada dataset terbatas. Generalisasi lintas kompetisi, penggunaan pada pertandingan dengan kondisi roster berbeda, dan penerapan waktu nyata belum menjadi capaian yang telah diuji.'),
P('Proyek diberi nama VAEP-Track sebagai arah pengembangan yang menghubungkan deteksi perilaku dengan analisis efektivitas. Namun, pada cakupan artikel ini, pembahasan utama adalah deteksi gegenpressing dan kesiapan eksperimennya. Penerapan valuasi aksi masih membutuhkan pemetaan event dan pengujian model probabilitas secara terpisah. Pembatasan tersebut menjaga agar pertanyaan penelitian, bukti yang tersedia, dan kesimpulan tetap berada pada lingkup yang sama.')]

lit=SECTIONS[2]
def insert_after_text(items,prefix,extra):
    out=[]
    for b in items:
        out.append(b)
        if b[0]=='p' and b[1].startswith(prefix): out.extend(extra)
    return out
lit=insert_after_text(lit,'Bauer dan Anzer',[
P('Anotasi merupakan penghubung antara konsep taktik dan target statistik yang dipelajari model. Ketika definisi perilaku terlalu bergantung pada keberhasilan regain, target dapat bergeser dari pengenalan tekanan menjadi prediksi outcome. Sebaliknya, definisi yang terlalu longgar dapat menggolongkan setiap kedekatan pemain terhadap bola sebagai gegenpressing. Dalam penelitian ini, persoalan tersebut ditangani melalui pemisahan label perilaku, outcome, dan status ragu, kemudian direncanakan pemeriksaan konsistensi keputusan annotator.')])
lit=insert_after_text(lit,'Bassek et al.',[
P('Representasi tabel tracking dan event memiliki unit pencatatan berbeda. Baris tracking menggambarkan posisi objek pada waktu tertentu, sedangkan event menggambarkan kejadian diskret beserta peserta dan atributnya. Pemanfaatan keduanya memerlukan perhatian terhadap waktu, identitas objek, dan sistem koordinat. Pada penelitian ini, tabel tracking menjadi sumber utama perubahan penguasaan dan graph, sedangkan event memberikan konteks serta pemetaan identitas tim. Hasil pengolahan tetap perlu diaudit karena konversi format tidak menghapus keterbatasan sumber data.')])
lit=insert_after_text(lit,'GCN menggabungkan',[
P('Graph dalam pendekatan ini adalah konstruksi yang ditetapkan berdasarkan kebutuhan pemodelan. Pilihan jumlah tetangga, arah edge, fitur node, dan ruang koordinat menentukan informasi yang tersedia bagi model. Hubungan empat tetangga terdekat menyederhanakan struktur lokal dan membatasi banyaknya koneksi. Konfigurasi tersebut belum dianggap optimal. Apabila hasil eksperimen berubah ketika definisi hubungan diganti, perubahan itu perlu dipahami sebagai sensitivitas representasi, bukan semata-mata perubahan kemampuan belajar model.')])
lit=insert_after_text(lit,'GRU menggunakan',[
P('Penggabungan GCN dengan GRU dilakukan pada tingkat representasi frame. Setelah informasi node diringkas, GRU menerima satu vektor untuk setiap waktu pengamatan. Pendekatan ini mempertahankan urutan perubahan keadaan secara global, tetapi pooling juga merangkum detail node. Karena itu, istilah Temporal GNN dalam artikel ini merujuk khusus pada encoder GCN per frame yang diikuti GRU, bukan pada seluruh kemungkinan arsitektur graph dinamis. Pengaruh komponen urutan perlu diuji melalui ablasi jika penelitian hendak mengisolasi manfaat temporal.')])
lit=insert_after_text(lit,'Logistic regression digunakan',[
P('Kedua baseline memberikan pembanding dengan representasi yang sama sehingga perbedaan keduanya lebih langsung berkaitan dengan cara mempelajari fitur. Logistic regression memetakan kombinasi fitur ke probabilitas dengan fungsi sigmoid, sedangkan XGBoost membangun interaksi nonlinier melalui pohon. Perbedaan terhadap GNN lebih luas karena mencakup input, konteks waktu, dan arsitektur. Penggunaan split serta target identik diperlukan agar pembandingan tetap dapat ditafsirkan, meskipun tidak menghilangkan semua perbedaan representasi.')])
lit.insert(-1,H('Sintesis pustaka dan posisi penelitian'))
lit.insert(-1,P('Landasan pustaka mendukung tiga keputusan penelitian: menggunakan label perilaku yang terpisah dari outcome, menyusun representasi relasional dari data posisi, dan mengevaluasi model dengan pembanding yang jelas. Kontribusi penelitian dinilai melalui penerapan serta pengujian keputusan tersebut pada IDSSE. Telaah ini tidak digunakan untuk mengklaim bahwa GCN–GRU adalah pendekatan pertama untuk semua bentuk analisis tekanan atau bahwa kompleksitas model menjamin hasil yang lebih baik.'))
SECTIONS[2]=lit

method=SECTIONS[3]
method=insert_after_text(method,'Penelitian menggunakan pendekatan',[
P('Tahap penelitian meliputi akuisisi dan pemeriksaan data, pembentukan kandidat dan episode, anotasi, ekstraksi representasi, pengembangan model, serta evaluasi. Tahap pengolahan dan implementasi telah dikerjakan. Anotasi penuh masih berlangsung, sedangkan evaluasi akhir belum dijalankan. Pemisahan status ini digunakan agar prosedur yang telah tersedia dalam kode tidak disajikan seolah-olah telah menghasilkan temuan eksperimen akhir.'),
T('Tabel 2 Tahapan penelitian dan keluaran yang diperiksa',['Tahap','Keluaran','Pemeriksaan utama'],[
['Akuisisi dan konversi','CSV tracking dan event per pertandingan','Identitas pertandingan, waktu, objek, serta kolom yang diperlukan'],
['Pembentukan episode','Manifest kandidat dan validitas','Perubahan penguasaan, 101 frame, posisi valid, dan roster 11 lawan 11'],
['Anotasi','Label perilaku dan confidence','Kelengkapan keputusan, label sah, dan penanganan ragu'],
['Representasi','12 fitur baseline dan sequence graph','Identitas kandidat, ukuran tensor, dan konsistensi fitur'],
['Pelatihan dan evaluasi','Model, prediksi, metrik, serta metadata','Split pertandingan, preprocessing train, dan threshold validation']],[3.4,4.9,7.7])])
method=insert_after_text(method,'Data utama berasal',[
P('Satu contoh tracking diidentifikasi melalui kombinasi pertandingan, periode, nomor frame, dan waktu. Kolom pemain menyimpan koordinat x dan y serta kecepatan untuk identitas pemain tertentu. Posisi bola tersimpan terpisah. Pada keluaran Kloppy lokal, koordinat telah berada pada skala ternormalisasi. Metadata sumber dan aturan konversi perlu dicatat untuk menafsirkan satuan secara konsisten. Nilai posisi kosong diperlakukan sebagai masalah kelengkapan objek dan diperiksa sebelum episode dinyatakan valid.')])
method=insert_after_text(method,'Window episode ditetapkan',[
P('Penggunaan window yang mencakup waktu setelah turnover sesuai dengan tujuan mengenali respons awal terhadap kehilangan bola. Model baru dapat menghasilkan klasifikasi setelah observasi hingga +2 detik tersedia. Episode yang tidak memenuhi syarat tetap tercatat dalam manifest beserta alasan kegagalannya, sehingga penyaringan dapat dianalisis per pertandingan. Syarat jumlah pemain yang tetap juga berarti model saat ini tidak mencakup secara otomatis situasi dengan jumlah pemain berbeda.')])
method=insert_after_text(method,'Antrean anotasi dibentuk',[
P('Pemilihan sampel menggunakan kedua kategori outcome quick regain agar antrean mencakup respons yang diikuti regain dan yang tidak. Penggunaan outcome pada sampling tidak menjadikannya label target. Karena peluang pemilihan dipengaruhi outcome dan validitas struktur, distribusi label hasil anotasi harus dibaca sebagai distribusi sampel penelitian. Jarak minimal dua detik juga belum memastikan independensi penuh karena dua window empat detik dapat berbagi sebagian frame dalam pertandingan yang sama.')])
method=insert_after_text(method,'Anotasi dilakukan oleh peneliti',[
P('Label positif diberikan berdasarkan penilaian adanya respons tekanan segera dari tim yang kehilangan bola, dengan mempertimbangkan hubungan pemain terhadap bola dan perkembangan tekanan pada cuplikan waktu. Label negatif digunakan ketika bukti yang diamati tidak memenuhi interpretasi perilaku tersebut. Status ragu dipertahankan ketika informasi tidak cukup atau indikator saling bertentangan. Kriteria interpretatif ini harus dipertegas dalam audit pedoman sebelum training final agar konsistensi tidak hanya bergantung pada ingatan annotator.'),
P('Panel pengambilan keputusan yang diimplementasikan tidak menampilkan outcome quick regain, tetapi masih menampilkan indikator tekanan dan ringkasan numerik. Karena itu, proses ini tidak dianggap sepenuhnya bebas pengaruh indikator. Peninjauan lanjutan direncanakan dengan penilai independen pada subset sampel, pemisahan keputusan awal, dan pembahasan kasus tidak sepakat. Tingkat keyakinan annotator akan dilaporkan sebagai metadata keputusan, bukan sebagai pengganti pengukuran reliabilitas antarpenilai.')])
method=insert_after_text(method,'Pada setiap frame',[
P('Prosedur pembentukan graph dimulai dengan menentukan roster aktif pada frame kehilangan bola, menyusun urutan identitas node, dan mengambil fitur pada seluruh frame episode. Untuk setiap frame, matriks jarak dihitung dari posisi dua dimensi. Empat tetangga terdekat selain node itu sendiri dipilih sebagai tujuan edge. Daftar edge dihitung ulang pada setiap frame sehingga hubungan dapat berubah ketika objek bergerak. Tensor fitur dan edge kemudian disimpan dengan identitas kandidat yang sama dengan manifest anotasi.')])
method=insert_after_text(method,'Temporal GNN menggunakan',[
P('Urutan komputasi model adalah Xt → GCN pertama → GCN kedua → layer normalization → mean pooling node → GRU → dropout → klasifikasi dua kelas. Mask node digunakan pada pooling untuk membatasi kontribusi objek yang valid. Hidden state GRU pada frame terakhir mewakili episode untuk klasifikasi. Walaupun jarak antarobjek tersedia pada proses konstruksi, implementasi ini belum memasukkan jarak tersebut sebagai bobot edge pada operasi GCN; informasi spasial berasal dari posisi node dan struktur ketetanggaan.')])
method=insert_after_text(method,'Baseline menggunakan 12 fitur',[
P('Beberapa fitur dapat tidak terdefinisi ketika syarat pengukuran tidak terpenuhi, misalnya kekompakan lokal jika pemain dalam radius lokal terlalu sedikit. Implementasi baseline menggunakan imputasi median dari train, bukan menghapus nilai kosong secara diam-diam atau menghitung imputasi dari seluruh dataset. Logistic regression juga menggunakan standardisasi fitur dari train. Pembobotan kelas diterapkan pada data pelatihan untuk mengurangi dominasi kelas mayoritas, tetapi tidak diperlakukan sebagai solusi terhadap kesalahan label.')])
method=insert_after_text(method,'Konfigurasi pada Tabel 2',[
P('Runner akhir menyiapkan optimizer AdamW dengan learning rate 0,001 dan weight decay 0,0001 untuk GNN. Bobot kelas dihitung dari frekuensi label train. Batch berukuran delapan digunakan dengan batas 100 epoch dan penghentian ketika validation loss tidak membaik selama 15 epoch. Random seed 42 ditetapkan untuk membantu reproduksibilitas. Parameter ini adalah konfigurasi awal eksperimen yang tersedia; perubahan maupun pencarian parameter tambahan harus dicatat dan tidak dipilih berdasarkan hasil test.')])
method=insert_after_text(method,'Pembagian dilakukan menurut pertandingan',[
T('Tabel 4 Pembagian pertandingan dalam eksperimen',['Split','Pertandingan','Peran'],[
['Train','J03WMX, J03WN1, J03WOH, J03WOY, J03WR9','Mempelajari parameter model dan statistik preprocessing'],
['Validation','J03WQQ','Memilih checkpoint GNN dan ambang klasifikasi'],
['Test','J03WPY','Menilai konfigurasi model setelah keputusan pengembangan dikunci']],[2.4,7.1,6.5]),
P('Kesetaraan kandidat diperiksa melalui identitas episode sebelum prediksi digabungkan untuk evaluasi. Penggunaan satu pertandingan pada validation dan satu pada test membatasi jumlah kondisi yang terwakili. Metrik harus disertai jumlah sampel serta komposisi kelas. Hasil pilot yang sudah digunakan untuk memeriksa integrasi juga perlu dicatat dalam riwayat pengembangan, sehingga artefak tersebut tidak diperlakukan sebagai evaluasi final yang independen.')])
method=insert_after_text(method,'Evaluasi direncanakan',[
P('True positive menyatakan episode gegenpressing yang terdeteksi positif, false positive menyatakan episode negatif yang diprediksi positif, dan false negative menyatakan episode gegenpressing yang terlewat. Confusion matrix mempertahankan jumlah kesalahan pada kedua kelas agar nilai agregat dapat dijelaskan. ROC-AUC dan AP memanfaatkan skor probabilitas pada berbagai ambang, sedangkan precision, recall, dan F1 dilaporkan pada ambang yang dipilih dari validation. Jika sampel sangat sedikit atau salah satu kelas tidak tersedia, interpretasi metrik harus dibatasi dan kondisi tersebut dilaporkan.')])
method.extend([
H('Reproduksibilitas dan penguatan eksperimen'),
P('Artefak eksperimen akhir direncanakan memuat salinan anotasi yang dibekukan, manifest split, fitur atau graph cache yang digunakan, konfigurasi model, bobot terlatih, riwayat pelatihan, probabilitas prediksi, dan checksum input. Snapshot ini diperlukan karena anotasi dan manifest dapat berubah selama penelitian. Pembaruan label harus menghasilkan perhitungan ulang jumlah sampel, sehingga statistik lama tidak digunakan untuk mendeskripsikan dataset terbaru.'),
P('Penguatan eksperimen yang belum dilaksanakan meliputi peninjauan label oleh penilai kedua, penyelarasan ruang jarak graph dengan dimensi lapangan, serta pembandingan input pada window yang sama. Ablasi GCN tanpa GRU dapat digunakan untuk menilai kebutuhan komponen temporal, sedangkan evaluasi pada beberapa pemisahan pertandingan dapat menilai sensitivitas terhadap laga test. Hasil pengujian tambahan baru dapat dimasukkan sebagai temuan setelah prosedur, data, dan keluaran eksperimennya tersedia.')])
# Update caption references after adding the pipeline and split tables.
method=[tuple(x.replace('Tabel 2 Konfigurasi','Tabel 3 Konfigurasi').replace('Konfigurasi pada Tabel 2','Konfigurasi pada Tabel 3') if isinstance(x,str) else x for x in b) for b in method]
method=[P(b[1]+' Komponen GCN dan GRU menggunakan landasan pemodelan graph dan urutan pada [4] dan [5].') if b[0]=='p' and b[1].startswith('Temporal GNN menggunakan') else b for b in method]
method=[P(b[1]+' Implementasi model pembanding menggunakan XGBoost [6] dan scikit-learn [7].') if b[0]=='p' and b[1].startswith('Baseline menggunakan 12 fitur') else b for b in method]
SECTIONS[3]=method

def detailed_doc(n):
    d=Document()
    sec=d.sections[0]
    sec.page_width=Cm(21);sec.page_height=Cm(29.7)
    sec.top_margin=Cm(2.2);sec.bottom_margin=Cm(2.2);sec.left_margin=Cm(2.5);sec.right_margin=Cm(2.5)
    sec.footer_distance=Cm(1)
    for s in d.styles:
        if s.type in (1,2):
            try:font(s)
            except Exception:pass
    # Remove inherited decorative title rules and paragraph borders.
    for border in list(d.styles.element.iter(qn('w:pBdr'))):border.getparent().remove(border)
    for border in list(d.element.iter(qn('w:pBdr'))):border.getparent().remove(border)
    normal=d.styles['Normal'].paragraph_format
    normal.line_spacing=1.12;normal.space_after=Pt(7);normal.widow_control=True
    for name,size in [('Title',15),('Heading 1',12),('Heading 2',11)]:
        font(d.styles[name],size,True)
        pf=d.styles[name].paragraph_format
        pf.space_before=Pt(10);pf.space_after=Pt(5);pf.keep_with_next=True
    font(d.styles['Caption'],10);font(d.styles['Footer'],9)
    d.core_properties.title='Bagian '+ROMANS[n]+' '+NAMES[n]+' — '+TITLE
    d.core_properties.author=AUTHOR
    d.core_properties.subject='Draf artikel berdasarkan progres hingga '+DATE
    p=d.add_paragraph('Bagian '+ROMANS[n]+' '+NAMES[n],'Title')
    p.paragraph_format.space_before=Pt(0);p.paragraph_format.space_after=Pt(8)
    p=d.add_paragraph(TITLE);p.paragraph_format.space_after=Pt(6)
    for r in p.runs:r.bold=True
    p=d.add_paragraph(AUTHOR+' | '+AFFIL);p.paragraph_format.space_after=Pt(4)
    for r in p.runs:r.font.size=Pt(10)
    p=d.add_paragraph('Cakupan penelitian hingga '+DATE);p.paragraph_format.space_after=Pt(11)
    for r in p.runs:r.font.size=Pt(9)
    p=sec.footer.paragraphs[0];p.alignment=WD_ALIGN_PARAGRAPH.CENTER
    fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');p._p.append(fld)
    return d

manifest=[]
for n in [1,2,3]:
    d=detailed_doc(n)
    blocks(d,SECTIONS[n])
    if n==3:
        d.paragraphs[-1].paragraph_format.keep_together=True
    # Each upload can be read independently. Reference numbering is shared across the article.
    used=sorted({int(v) for b in SECTIONS[n] for v in re.findall(r'\[(\d+)\]',str(b))})
    d.add_paragraph('Rujukan bagian ini','Heading 1')
    for idx in used:
        p=paragraph(d,REFS[idx-1]);p.alignment=WD_ALIGN_PARAGRAPH.LEFT
        p.paragraph_format.left_indent=Cm(.65);p.paragraph_format.first_line_indent=Cm(-.65)
        p.paragraph_format.line_spacing=1.05;p.paragraph_format.space_after=Pt(6)
        p.paragraph_format.keep_together=True
        for r in p.runs:r.font.size=Pt(10)
    # Keep short tables together, allowing larger tables to continue with repeated headers.
    for t in d.tables:
        for row in t.rows[:-1]:
            for cell in row.cells:
                for p in cell.paragraphs:p.paragraph_format.keep_with_next=True
    path=DEST/('Bagian_'+ROMANS[n]+'_'+NAMES[n].replace(' ','_')+'.docx')
    d.save(path)
    words=len(' '.join(p.text for p in d.paragraphs).split())
    manifest.append({'path':str(path),'words':words,'references':used})
    print(path.name,words,'words')
(DEST/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(BASE/'_work'/'detailed_sections.json').write_text(json.dumps({str(n):SECTIONS[n] for n in [1,2,3]},ensure_ascii=False,indent=2),encoding='utf-8')
