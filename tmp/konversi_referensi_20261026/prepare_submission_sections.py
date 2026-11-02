from pathlib import Path
from copy import deepcopy
import csv, json, re
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT
from docx.text.paragraph import Paragraph
from docx.table import Table

ROOT=Path(r'C:\VAEP-Track')
SOURCE=ROOT/'docs/artikel_progres_2026-10-19/Artikel_Jurnal_Deteksi_Gegenpressing_2026-10-23.docx'
OUT=ROOT/'docs/draf_pengumpulan_2026-10-26'
OUT.mkdir(parents=True,exist_ok=True)

manifest=ROOT/'data/processed/gegenpressing_annotation_manifest.csv'
with manifest.open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
label_count=sum(r.get('is_gegenpressing') in ('0','1') for r in rows)
unlabeled=len(rows)-label_count
if (len(rows),label_count,unlabeled)!=(1873,264,1609):raise ValueError('Annotation counts changed; review before generating files')

doc=Document(SOURCE)
parts={x:[] for x in ['I','II','III','IV','V','VI']}
current='VI'
heading_map={'I Pendahuluan':'I','II Tinjauan Pustaka':'II','III Metode':'III','IV Hasil dan Pembahasan':'IV','V Simpulan':'V','Daftar Pustaka':'VI','Abstrak':'VI','Abstract':'VI'}
article_title='Deteksi Gegenpressing Menggunakan Temporal Graph Neural Network pada Data Tracking IDSSE'
for child in doc.element.body.iterchildren():
    if child.tag==qn('w:p'):
        p=Paragraph(child,doc)
        txt=p.text.strip()
        if p.style and p.style.name=='Heading 1' and txt in heading_map:current=heading_map[txt]
        if txt==article_title or txt.startswith('Program Studi Teknik Informatika,') or txt.startswith('Naskah penelitian'):
            continue
        if txt=='Rizal Andi Pranata':
            continue
        if txt:parts[current].append(('p',child))
    elif child.tag==qn('w:tbl'):
        parts[current].append(('t',child))

section_statuses={
 'I':('Bagian I Pendahuluan','Isi sudah tersedia sebagai draf awal. Periksa lagi kesesuaian tujuan dengan ruang lingkup final penelitian.'),
 'II':('Bagian II Tinjauan Pustaka','Isi sudah tersedia sebagai draf awal. Daftar sumber masih perlu disesuaikan dengan syarat tahun dan peringkat SINTA yang diminta pembimbing.'),
 'III':('Bagian III Metode','Metode saat ini menjelaskan eksperimen pilot dengan 264 label. Perbarui rancangan, jumlah data, dan evaluasi setelah anotasi penuh selesai.'),
 'IV':('Bagian IV Hasil dan Pembahasan','Hasil ini khusus pilot 264 label dengan 40 data uji dari satu pertandingan. Jangan sajikan sebagai hasil final cakupan 1.873 episode.'),
 'V':('Bagian V Simpulan','Simpulan merangkum hasil pilot. Tulis ulang setelah evaluasi untuk cakupan penuh dan per pertandingan.'),
 'VI':('Bagian VI Daftar Pustaka dan Abstrak','Abstrak dan pustaka tersedia, tetapi angka abstrak berasal dari pilot 264 label. Verifikasi syarat tahun dan peringkat SINTA sebelum pengumpulan.')}

def rel_copy(src_part,dst_part,element):
    for el in element.iter():
        for attr in (qn('r:id'),qn('r:embed'),qn('r:link')):
            old=el.get(attr)
            if old and old in src_part.rels:
                rel=src_part.rels[old]
                if rel.is_external:new=dst_part.relate_to(rel.target_ref,rel.reltype,is_external=True)
                else:new=dst_part.relate_to(rel.target_part,rel.reltype)
                el.set(attr,new)

files=[]
for key,(heading,status) in section_statuses.items():
    out=Document();section=out.sections[0]
    section.top_margin=doc.sections[0].top_margin;section.bottom_margin=doc.sections[0].bottom_margin
    section.left_margin=doc.sections[0].left_margin;section.right_margin=doc.sections[0].right_margin
    for name in ['Normal','Title','Heading 1','Heading 2','List Bullet','List Number']:
        out.styles[name].font.name='Calibri';out.styles[name].font.color.rgb=RGBColor(0,0,0)
    out.styles['Subtitle'].font.name='Calibri';out.styles['Subtitle'].font.color.rgb=RGBColor(0,0,0)
    for border in out.styles.element.xpath('.//w:pBdr'):
        border.getparent().remove(border)
    out.styles['Normal'].font.size=Pt(11)
    out.styles['Normal'].paragraph_format.line_spacing=1.12
    out.styles['Normal'].paragraph_format.space_after=Pt(7)
    p=out.add_paragraph(heading,style='Title');p.paragraph_format.keep_with_next=True
    p=out.add_paragraph(article_title,style='Subtitle');p.paragraph_format.keep_with_next=True
    p=out.add_paragraph(status);p.paragraph_format.space_after=Pt(14)
    for kind,element in parts[key]:
        clone=deepcopy(element);rel_copy(doc.part,out.part,clone)
        if kind=='p':out.element.body.insert(-1,clone)
        else:out.element.body.insert(-1,clone)
    out.core_properties.title=heading
    out.core_properties.author='Rizal Andi Pranata'
    path=OUT/f'{key}_{re.sub(r"[^A-Za-z0-9]+","_",heading).strip("_")}.docx'
    out.save(path);files.append(path)

# Short status document for the hand-in checklist.
status_doc=Document();s=status_doc.sections[0]
s.top_margin=doc.sections[0].top_margin;s.bottom_margin=doc.sections[0].bottom_margin
s.left_margin=doc.sections[0].left_margin;s.right_margin=doc.sections[0].right_margin
for name in ['Normal','Title','Heading 1','Heading 2']:
    status_doc.styles[name].font.name='Calibri';status_doc.styles[name].font.color.rgb=RGBColor(0,0,0)
for border in status_doc.styles.element.xpath('.//w:pBdr'):
    border.getparent().remove(border)
status_doc.styles['Normal'].font.size=Pt(11);status_doc.styles['Normal'].paragraph_format.space_after=Pt(7)
status_doc.add_paragraph('Status Kesiapan Pengumpulan Draf Artikel',style='Title')
status_doc.add_paragraph('Pemeriksaan 26 Oktober 2026')
status_doc.add_heading('Kesimpulan',level=1)
status_doc.add_paragraph('Secara struktur, draf sudah memiliki keenam bagian pada formulir. Sebagai naskah penelitian final, belum siap dikumpulkan: hasil yang tersedia berasal dari pilot 264 label, sedangkan antrean penelitian penuh masih menyisakan 1.609 episode belum berlabel.')
status_doc.add_heading('Status bagian formulir',level=1)
items=[('I Pendahuluan','Draf tersedia; perlu penyelarasan akhir dengan tujuan penelitian penuh.'),('II Tinjauan Pustaka','Draf tersedia; kepatuhan syarat tahun dan SINTA masih perlu diverifikasi. Beberapa sumber fondasi memang terbit sebelum 2021.'),('III Metode','Draf tersedia untuk pilot 264 label; perlu diperbarui setelah anotasi penuh dan desain evaluasi lintas pertandingan.'),('IV Hasil dan Pembahasan','Ada hasil uji 40 episode dari satu pertandingan; bukti proof of concept, belum hasil final cakupan penuh.'),('V Simpulan','Simpulan pilot tersedia; belum menjawab hasil evaluasi penuh.'),('VI Daftar Pustaka dan Abstrak','Keduanya tersedia; abstrak memakai angka pilot dan pustaka perlu dicocokkan dengan ketentuan pembimbing.')]
for a,b in items:
    p=status_doc.add_paragraph(style='List Bullet');r=p.add_run(a+': ');r.bold=True;p.add_run(b)
status_doc.add_heading('Bukti status data',level=1)
status_doc.add_paragraph(f'Manifest saat diperiksa berisi {len(rows):,} episode valid. Sebanyak {label_count} episode telah berlabel biner (222 positif dan 42 negatif), sementara {unlabeled:,} belum berlabel. Artefak training pilot bertanggal 22 Oktober 2026 berisi split 184 train, 40 validation, dan 40 test; test berasal dari satu pertandingan.')
status_doc.add_heading('Urutan kerja sebelum pengumpulan final',level=1)
for t in ['Selesaikan anotasi yang tersisa dan audit mutu label.','Tetapkan evaluasi lintas pertandingan serta perbarui tabel hasil dan simpulan.','Periksa rujukan terhadap syarat minimal tahun dan rentang SINTA yang disampaikan pembimbing.','Selaraskan abstrak Indonesia dan Inggris dengan hasil final.','Masukkan tautan Google Drive setelah berkas diunggah.']:
    status_doc.add_paragraph(t,style='List Number')
status_doc.add_paragraph('Dokumen bagian I dan II dapat dipakai sebagai draf awal untuk ditinjau. Bagian III sampai VI sebaiknya diberi status sementara sampai pekerjaan di atas selesai.')
status_doc.core_properties.title='Status Kesiapan Pengumpulan Draf Artikel'
status_doc.core_properties.author='Rizal Andi Pranata'
status_path=OUT/'Status_Kesiapan_Pengumpulan.docx';status_doc.save(status_path);files.append(status_path)

# Re-label the working master so its first page does not suggest the pilot is the final full-scope study.
master=Document(SOURCE)
for p in master.paragraphs:
    if p.text.startswith('Naskah penelitian'):
        p.text='Draf kerja • hasil pilot 264 label; anotasi penuh 1.873 episode belum selesai.'
        break
master.save(SOURCE)

print(json.dumps({'files':[{'path':str(p),'bytes':p.stat().st_size} for p in files],'sections':{k:len(v) for k,v in parts.items()},'counts':{'valid':len(rows),'labeled':label_count,'unlabeled':unlabeled},'master_updated':str(SOURCE)},ensure_ascii=False,indent=2))
