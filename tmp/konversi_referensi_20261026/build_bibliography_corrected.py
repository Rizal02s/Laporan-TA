from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.section import WD_SECTION

out = Path(r'C:\VAEP-Track\docs\jurnalreferensi\Daftar_Pustaka_Koreksi_dan_Kelayakan_2026-10-26.docx')
out.parent.mkdir(parents=True, exist_ok=True)
doc = Document()
sec = doc.sections[0]
sec.page_width = Cm(21)
sec.page_height = Cm(29.7)
sec.top_margin = Cm(2.0)
sec.bottom_margin = Cm(2.0)
sec.left_margin = Cm(2.3)
sec.right_margin = Cm(2.3)

for name in ['Normal','Title','Heading 1','Heading 2','List Bullet']:
    s = doc.styles[name]
    s.font.name = 'Calibri'
    s.font.color.rgb = RGBColor(0,0,0)
normal=doc.styles['Normal']
normal.font.size=Pt(10.5)
normal.paragraph_format.line_spacing=1.12
normal.paragraph_format.space_after=Pt(6)
normal.paragraph_format.keep_together=True
for name,size in [('Title',21),('Heading 1',14),('Heading 2',11.5)]:
    s=doc.styles[name]
    s.font.size=Pt(size);s.font.bold=True
    s.paragraph_format.space_before=Pt(12 if name!='Title' else 0)
    s.paragraph_format.space_after=Pt(6)
    s.paragraph_format.keep_with_next=True
for p in doc.styles.element.xpath('.//w:pBdr'):
    p.getparent().remove(p)

# Simple running header and page number
header=sec.header.paragraphs[0]
header.alignment=WD_ALIGN_PARAGRAPH.RIGHT
r=header.add_run('VAEP-TRACK  |  DRAF REFERENSI')
r.font.name='Calibri';r.font.size=Pt(8);r.font.color.rgb=RGBColor(100,100,100)
footer=sec.footer.paragraphs[0]
footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
rr=footer.add_run('Rizal Andi Pranata  •  ')
rr.font.name='Calibri';rr.font.size=Pt(8);rr.font.color.rgb=RGBColor(100,100,100)
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');footer._p.append(fld)

def hyperlink(p, text, url):
    h=OxmlElement('w:hyperlink')
    h.set(qn('r:id'),p.part.relate_to(url,'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink',is_external=True))
    run=OxmlElement('w:r');pr=OxmlElement('w:rPr')
    color=OxmlElement('w:color');color.set(qn('w:val'),'175A80');pr.append(color)
    u=OxmlElement('w:u');u.set(qn('w:val'),'single');pr.append(u)
    run.append(pr);t=OxmlElement('w:t');t.text=text;run.append(t);h.append(run);p._p.append(h)

def set_cell_shading(cell, fill):
    tcPr=cell._tc.get_or_add_tcPr();shd=OxmlElement('w:shd');shd.set(qn('w:fill'),fill);tcPr.append(shd)

def set_cell_text(cell,text,bold=False):
    cell.text=''
    p=cell.paragraphs[0]
    p.paragraph_format.space_after=Pt(2)
    p.paragraph_format.line_spacing=1.0
    r=p.add_run(text);r.bold=bold;r.font.name='Calibri';r.font.size=Pt(9)
    cell.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER

def source_entry(num, chunks, note, url):
    p=doc.add_paragraph()
    p.paragraph_format.left_indent=Cm(.85)
    p.paragraph_format.first_line_indent=Cm(-.85)
    p.paragraph_format.space_after=Pt(2)
    p.paragraph_format.keep_together=True
    p.paragraph_format.keep_with_next=True
    for text, italic in chunks:
        r=p.add_run(text);r.italic=italic
    if url:
        p.add_run(' ')
        hyperlink(p,url,url)
    n=doc.add_paragraph()
    n.paragraph_format.left_indent=Cm(.85)
    n.paragraph_format.space_after=Pt(9)
    rr=n.add_run('Status: '+note);rr.italic=True;rr.font.size=Pt(9);rr.font.color.rgb=RGBColor(80,80,80)

# Title block
p=doc.add_paragraph(style='Title');p.add_run('Daftar Pustaka Riset VAEP-Track')
p=doc.add_paragraph();p.paragraph_format.space_after=Pt(2)
r=p.add_run('Koreksi metadata dan pemeriksaan kelayakan sumber');r.bold=True;r.font.size=Pt(12)
p=doc.add_paragraph();p.paragraph_format.space_after=Pt(10)
r=p.add_run('Draf kerja • Pemeriksaan 26 Oktober 2026');r.italic=True;r.font.size=Pt(9);r.font.color.rgb=RGBColor(90,90,90)

p=doc.add_paragraph()
r=p.add_run('Status pengumpulan: BELUM MEMENUHI syarat formal yang diketahui. ');r.bold=True
p.add_run('Ketentuan yang disampaikan adalah terbit mulai 2021 dan jurnal berada pada peringkat SINTA 3–6. Dari tujuh PDF yang diperiksa, tidak ada sumber yang dapat dipastikan memenuhi kedua syarat sekaligus. Tiga karya adalah artikel jurnal internasional terbit 2021 atau setelahnya, tetapi bukti akreditasi SINTA 3–6 tidak ditemukan. Tiga lainnya merupakan prosiding atau preprint; satu artikel prosiding tahun 2019 juga berada di luar batas tahun.')
p=doc.add_paragraph()
p.add_run('Dokumen ini merapikan sitasi dan membantu memilih bacaan ilmiah. ').bold=True
p.add_run('Dokumen ini belum boleh diperlakukan sebagai daftar pustaka yang telah disetujui pembimbing atau memenuhi ketentuan formulir. Status SINTA mengacu pada akreditasi jurnal melalui ARJUNA dan harus dibuktikan untuk jurnal serta masa akreditasi yang berlaku.')

h=doc.add_paragraph('Daftar pustaka hasil koreksi',style='Heading 1')
p=doc.add_paragraph('Enam karya unik dari tujuh PDF, disusun mendekati APA edisi ke-7. Entri prosiding dan preprint diberi keterangan agar tidak keliru disebut artikel jurnal.')

source_entry(1,[
 ('Bauer, P., & Anzer, G. (2021). Data-driven detection of counterpressing in professional football: A supervised machine learning task based on synchronized positional and event data with expert-based feature extraction. ',False),
 ('Data Mining and Knowledge Discovery, 35',True),
 (', 2009–2049.',False)],
 'Artikel jurnal; memenuhi batas tahun dan sangat relevan untuk counterpressing. Peringkat SINTA 3–6 belum terverifikasi.',
 'https://doi.org/10.1007/s10618-021-00763-7')
source_entry(2,[
 ('Bassek, M., Rein, R., Weber, H., & Memmert, D. (2025). An integrated dataset of spatiotemporal and event data in elite soccer. ',False),
 ('Scientific Data, 12',True),
 (', Article 195.',False)],
 'Artikel jurnal data descriptor; memenuhi batas tahun dan relevan untuk IDSSE. Peringkat SINTA 3–6 belum terverifikasi.',
 'https://doi.org/10.1038/s41597-025-04505-y')
source_entry(3,[
 ('Wang, Z., Veličković, P., Hennes, D., Tomašev, N., Prince, L., Kaisers, M., Bachrach, Y., Elie, R., Wenliang, L. K., Piccinini, F., Spearman, W., Graham, I., Connor, J., Yang, Y., Recasens, A., Khan, M., Beauguerlange, N., Sprechmann, P., Moreno, P., ... Tuyls, K. (2024). TacticAI: An AI assistant for football tactics. ',False),
 ('Nature Communications, 15',True),
 (', Article 1906.',False)],
 'Artikel jurnal; memenuhi batas tahun dan relevan sebagai contoh GNN sepak bola, tetapi meneliti tendangan sudut, bukan gegenpressing. Peringkat SINTA 3–6 belum terverifikasi.',
 'https://doi.org/10.1038/s41467-024-45965-x')
source_entry(4,[
 ('Decroos, T., Bransen, L., Van Haaren, J., & Davis, J. (2019). Actions speak louder than goals: Valuing player actions in soccer. In ',False),
 ('Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining',True),
 (' (pp. 1851–1861). ACM.',False)],
 'Prosiding konferensi; sumber dasar VAEP, tetapi tidak memenuhi batas tahun dan bukan jurnal SINTA. Gunakan hanya bila pembimbing menerima sumber seminal yang lebih lama.',
 'https://doi.org/10.1145/3292500.3330758')
source_entry(5,[
 ('Xenopoulos, P., & Silva, C. (2021). Graph neural networks to predict sports outcomes. In ',False),
 ('2021 IEEE International Conference on Big Data (Big Data)',True),
 (' (pp. 1757–1763). IEEE.',False)],
 'Prosiding IEEE, bukan artikel jurnal SINTA. Memenuhi batas tahun; relevansinya metodologis karena contoh datanya American football dan esports.',
 'https://doi.org/10.1109/BigData52589.2021.9671833')
source_entry(6,[
 ('Bekkers, J., & Sahasrabudhe, A. (2024). ',False),
 ('A graph neural network deep-dive into successful counterattacks',True),
 (' [Preprint]. arXiv.',False)],
 'Preprint arXiv; memenuhi batas tahun, tetapi bukan artikel jurnal dan membahas counterattack (setelah merebut bola), bukan counterpressing.',
 'https://arxiv.org/abs/2411.17450')

h=doc.add_paragraph('Pemeriksaan berkas dan kelayakan',style='Heading 1')
table=doc.add_table(rows=1, cols=4)
table.alignment=WD_TABLE_ALIGNMENT.CENTER
table.autofit=False
widths=[Cm(1.0),Cm(7.1),Cm(3.5),Cm(5.0)]
for cell,w in zip(table.rows[0].cells,widths):cell.width=w
headers=['No.','Karya','Jenis / tahun','Status syarat']
for cell,text in zip(table.rows[0].cells,headers):
    set_cell_text(cell,text,True);set_cell_shading(cell,'DCE6F1')
rows=[
('1','Data-driven detection of counterpressing','Jurnal, 2021','Tahun lolos; SINTA belum terbukti'),
('2','An integrated dataset of spatiotemporal and event data in elite soccer','Jurnal, 2025','Tahun lolos; SINTA belum terbukti'),
('3','TacticAI','Jurnal, 2024','Tahun lolos; SINTA belum terbukti'),
('4','Actions Speak Louder than Goals','Prosiding, 2019','Tahun dan jenis tidak lolos'),
('5','Graph Neural Networks to Predict Sports Outcomes','Prosiding, 2021','Tahun lolos; jenis tidak lolos'),
('6','A Graph Neural Network deep-dive into successful counterattacks','Preprint / konferensi, 2023–2024','Tahun lolos; jenis tidak lolos'),
]
for row in rows:
    cells=table.add_row().cells
    for cell,w,text in zip(cells,widths,row):
        cell.width=w;set_cell_text(cell,text)

p=doc.add_paragraph('Catatan koreksi',style='Heading 1')
for text in [
'PDF “Deteksi counterpressing berbasis data dalam sepak bola” adalah terjemahan mesin dari artikel Bauer dan Anzer dengan DOI yang sama. Gunakan artikel asli berbahasa Inggris sebagai satu entri; terjemahan tidak dihitung sebagai sumber terpisah.',
'“Actions Speak Louder than Goals” terbit sebagai prosiding KDD 2019, bukan artikel jurnal. Sumber ini penting untuk menjelaskan VAEP, tetapi perlu pengecualian dari pembimbing jika batas 2021 berlaku ketat.',
'“Graph Neural Networks to Predict Sports Outcomes” terbit di IEEE Big Data 2021 sebagai makalah konferensi. Tahun unggah salinan arXiv yang lebih baru tidak mengubah jenis publikasinya menjadi jurnal.',
'Berkas counterattacks merupakan preprint arXiv versi 2024; halaman resmi MIT Sloan juga memuat karya konferensi dengan judul sama dan nama penulis berurutan Sahasrabudhe lalu Bekkers. Pastikan versi yang benar-benar dibaca yang disitasi. Secara topik, counterattack berbeda dari counterpressing.',
'Jangan menyamakan indeks Scopus atau status jurnal internasional dengan peringkat akreditasi SINTA. Simpan bukti profil jurnal atau SK akreditasi dan masa berlakunya untuk sumber yang akan diajukan sebagai SINTA 3–6.'
]:
    p=doc.add_paragraph(style='List Bullet');p.add_run(text)

p=doc.add_paragraph('Langkah sebelum diunggah',style='Heading 1')
for text in [
'Minta konfirmasi pembimbing apakah batas tahun dan SINTA berlaku pada semua entri atau pada jumlah minimum artikel jurnal tertentu.',
'Cari dan tambahkan artikel jurnal terbit 2021 ke atas yang memiliki bukti SINTA 3–6 yang masih berlaku dan relevan dengan gegenpressing, tracking sepak bola, GNN temporal, atau evaluasi tekanan.',
'Setelah daftar sumber disetujui, cocokkan semua kutipan di tinjauan pustaka dengan daftar pustaka, lalu unggah versi yang disetujui ke Google Drive.'
]:
    p=doc.add_paragraph(style='List Number');p.add_run(text)

# metadata
doc.core_properties.title='Daftar Pustaka Riset VAEP-Track - Koreksi Metadata dan Pemeriksaan Kelayakan'
doc.core_properties.subject='Draf kerja untuk memeriksa enam karya unik dari tujuh PDF referensi'
doc.core_properties.author=''
doc.core_properties.keywords='VAEP-Track, gegenpressing, GNN, daftar pustaka, SINTA'
doc.save(out)
print(out)

