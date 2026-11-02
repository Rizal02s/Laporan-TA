from pathlib import Path
import re, json, unicodedata
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.opc.constants import RELATIONSHIP_TYPE as RT

root = Path(r'C:\VAEP-Track')
bib = (root/'docs/referensi_tambahan_2026-10-25/Referensi_Tambahan_VAEP_Track.bib').read_text(encoding='utf-8-sig')
records=[]
for i, block in enumerate(re.split(r'(?=@article\{)',bib)[1:],1):
    fields={m.group(1):m.group(2).strip('{}') for m in re.finditer(r'^\s*(\w+)\s*=\s*\{(.*)\},?$',block,re.M)}
    fields.update(kind='journal',origin=f'Rekomendasi tambahan nomor {i}')
    if fields['doi']=='10.1038/s41467-024-45965-x':
        fields['origin']='Koleksi awal dan rekomendasi tambahan nomor 1; dihitung sekali'
    records.append(fields)

records.extend([
dict(author='Bauer, Pascal and Anzer, Gabriel',year='2021',title='Data-driven detection of counterpressing in professional football: A supervised machine learning task based on synchronized positional and event data with expert-based feature extraction',journal='Data Mining and Knowledge Discovery',volume='35',number='5',pages='2009--2049',doi='10.1007/s10618-021-00763-7',kind='journal',origin='Koleksi awal; PDF terjemahan Indonesia tidak dihitung lagi'),
dict(author='Bassek, Manuel and Rein, Robert and Weber, Hendrik and Memmert, Daniel',year='2025',title='An integrated dataset of spatiotemporal and event data in elite soccer',journal='Scientific Data',volume='12',pages='195',doi='10.1038/s41597-025-04505-y',kind='journal',origin='Koleksi awal'),
dict(author='Decroos, Tom and Bransen, Lotte and Van Haaren, Jan and Davis, Jesse',year='2019',title='Actions speak louder than goals: Valuing player actions in soccer',journal='Proceedings of the 25th ACM SIGKDD International Conference on Knowledge Discovery & Data Mining',pages='1851--1861',publisher='ACM',doi='10.1145/3292500.3330758',kind='conference',origin='Koleksi awal'),
dict(author='Xenopoulos, Peter and Silva, Claudio',year='2021',title='Graph neural networks to predict sports outcomes',journal='2021 IEEE International Conference on Big Data (Big Data)',pages='1757--1763',publisher='IEEE',doi='10.1109/BigData52589.2021.9671833',kind='conference',origin='Koleksi awal; tahun prosiding 2021, salinan arXiv diunggah 2022'),
dict(author='Bekkers, Joris and Sahasrabudhe, Amod',year='2024',title='A graph neural network deep-dive into successful counterattacks',journal='arXiv',doi='',url='https://arxiv.org/abs/2411.17450v1',kind='preprint',origin='Koleksi awal; mengikuti versi arXiv v1 tahun 2024 yang tersimpan')
])

# Sentence case while preserving proper nouns and acronyms.
titles={
'10.1109/TPAMI.2024.3443141':'A survey on graph neural networks for time series: Forecasting, classification, imputation, and anomaly detection',
'10.1080/24733938.2022.2158213':'The keys of pressing to gain the ball - Characteristics of defensive pressure in elite soccer using tracking data',
'10.52082/jssm.2023.707':'The success factors of rest defense in soccer - A mixed-methods approach of expert interviews, tracking data, and machine learning',
'10.1371/journal.pone.0118432':'The precision-recall plot is more informative than the ROC plot when evaluating binary classifiers on imbalanced datasets',
'10.1038/s41467-024-45965-x':'TacticAI: An AI assistant for football tactics',
}
for x in records:
    x['title']=titles.get(x['doi'],x['title']).replace('–','-')
    if x['kind']!='journal':
        x['decision']='Dikeluarkan: bukan artikel jurnal.'
        if x['year']=='2019':x['decision']='Dikeluarkan: prosiding konferensi dan tahun 2019 di bawah batas 2021.'
    elif int(x['year'])<2021:
        x['decision']=f"Dikeluarkan: tahun volume jurnal {x['year']} di bawah batas 2021; bukti SINTA 3-6 juga belum tersedia."
    else:
        x['decision']='Ditahan: tahun dan jenis publikasi sesuai; bukti akreditasi SINTA 3-6 belum tersedia.'

records.sort(key=lambda x:(unicodedata.normalize('NFKD',x['author']).casefold(),x['year']))
assert len(records)==15
assert sum(x['kind']=='journal' and int(x['year'])>=2021 for x in records)==9
(root/'tmp/bibliografi_gabungan_20261026/selection.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')

doc=Document()
s=doc.sections[0]
s.page_width=Inches(8.5);s.page_height=Inches(11)
s.top_margin=Inches(.7);s.bottom_margin=Inches(.7)
s.left_margin=Inches(.85);s.right_margin=Inches(.85)
for name in ['Normal','Title','Heading 1','Heading 2','List Bullet']:
    st=doc.styles[name];st.font.name='Calibri';st.font.color.rgb=RGBColor(0,0,0)
doc.styles['Normal'].font.size=Pt(11)
doc.styles['Normal'].paragraph_format.line_spacing=1.08
doc.styles['Normal'].paragraph_format.space_after=Pt(7)
for name,size in [('Title',22),('Heading 1',14),('Heading 2',12)]:
    st=doc.styles[name];st.font.size=Pt(size);st.font.bold=True
    st.paragraph_format.keep_with_next=True
    st.paragraph_format.space_before=Pt(12 if name!='Title' else 0)
    st.paragraph_format.space_after=Pt(7)
for border in doc.styles.element.xpath('.//w:pBdr'):border.getparent().remove(border)

def link(p,label,url):
    h=OxmlElement('w:hyperlink');h.set(qn('r:id'),p.part.relate_to(url,RT.HYPERLINK,is_external=True))
    r=OxmlElement('w:r');pr=OxmlElement('w:rPr')
    c=OxmlElement('w:color');c.set(qn('w:val'),'175A80');pr.append(c)
    u=OxmlElement('w:u');u.set(qn('w:val'),'single');pr.append(u)
    r.append(pr);t=OxmlElement('w:t');t.text=label;r.append(t);h.append(r);p._p.append(h)

header=s.header.paragraphs[0];header.alignment=WD_ALIGN_PARAGRAPH.RIGHT
r=header.add_run('VAEP-TRACK  |  PEMERIKSAAN REFERENSI');r.font.size=Pt(8);r.font.color.rgb=RGBColor(90,90,90)
f=s.footer.paragraphs[0];f.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=f.add_run('Hasil seleksi 26 Oktober 2026  |  ');r.font.size=Pt(8)
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');f._p.append(field)

doc.add_paragraph('Hasil Seleksi Daftar Pustaka Gabungan',style='Title')
doc.add_paragraph('Referensi awal dan sepuluh rekomendasi tambahan untuk riset VAEP-Track')
p=doc.add_paragraph();p.add_run('Tanggal pemeriksaan 26 Oktober 2026').italic=True
p=doc.add_paragraph();p.add_run('Jumlah referensi yang terverifikasi lolos seluruh syarat adalah 0. ').bold=True
p.add_run('Pengguna telah menegaskan bahwa setiap artikel referensi harus terbit mulai 2021 dan berasal dari jurnal SINTA 3-6. Belum ditemukan bukti profil jurnal atau SK akreditasi yang memenuhi ketentuan tersebut untuk kandidat dalam koleksi gabungan. Karena itu, dokumen ini belum dapat digunakan sebagai daftar pustaka final untuk pengumpulan.')

doc.add_paragraph('Cakupan dan hasil seleksi',style='Heading 1')
for text in [
'Bahan awal: 7 PDF milik pengguna dan 10 rekomendasi tambahan, berjumlah 17 catatan sumber.',
'Dua pengulangan dihapus dari hitungan: terjemahan Indonesia artikel Bauer dan Anzer, serta TacticAI yang muncul pada kedua daftar. Hasil penggabungan adalah 15 karya unik.',
'Sembilan karya memenuhi pemeriksaan tahun 2021 ke atas dan jenis artikel jurnal. Kesembilannya masih ditahan karena bukti SINTA 3-6 belum tersedia.',
'Enam karya lainnya dikeluarkan berdasarkan tahun volume sebelum 2021 atau jenis prosiding/preprint. Tidak ada sumber pada kedua kelompok yang dimasukkan ke daftar pustaka lolos.'
]:doc.add_paragraph(text,style='List Bullet')

doc.add_paragraph('Dasar keputusan dan keterbatasan',style='Heading 1')
p=doc.add_paragraph('Metadata dicocokkan dengan PDF, halaman penerbit atau repositori resmi, dan metadata DOI Crossref yang berhasil diakses. Penelusuran nama jurnal di situs SINTA belum menghasilkan profil atau SK akreditasi yang mendukung peringkat SINTA 3-6 untuk kandidat tersebut. Akses langsung ke direktori jurnal SINTA pada pemeriksaan ini mengembalikan HTTP 403, sehingga pemeriksaan ini bukan pencarian lengkap atas seluruh katalog.')
p=doc.add_paragraph('Artikel yang muncul pada profil penulis SINTA, daftar Scopus, atau Google Scholar belum membuktikan bahwa jurnalnya berperingkat SINTA 3-6. Bukti yang dibutuhkan adalah profil jurnal atau SK akreditasi yang sesuai nama dan ISSN, dengan masa akreditasi yang mencakup volume dan nomor artikel. Dasar penjelasan akreditasi: ')
link(p,'FAQ resmi SINTA','https://sinta.kemdiktisaintek.go.id/home/faq')
p.add_run('.')
p=doc.add_paragraph('Untuk mendapatkan daftar pustaka yang siap dikumpulkan dengan syarat ini, diperlukan sumber pengganti yang memiliki bukti akreditasi tersebut. Lampiran berikut menyimpan metadata seluruh kandidat dan alasan keputusan agar sumber dapat dilacak kembali.')

doc.add_page_break()
doc.add_paragraph('Lampiran Bibliografi Kandidat yang Belum Lolos',style='Heading 1')
doc.add_paragraph('Seluruh entri di bawah adalah catatan hasil pemeriksaan, bukan daftar pustaka yang sudah memenuhi syarat. Urutan alfabetis penulis dipakai agar mudah dicocokkan. Tautan DOI atau arXiv menunjuk identitas karya; tautan tersebut bukan bukti akreditasi SINTA.')

def author_string(raw):
    names=[]
    for a in raw.split(' and '):
        family,given=a.split(',',1)
        initials=' '.join(w[0]+'.' for w in given.strip().split() if w)
        names.append(f'{family.strip()}, {initials}')
    if len(names)>20:return ', '.join(names[:19])+', ... '+names[-1]
    if len(names)>1:return ', '.join(names[:-1])+', & '+names[-1]
    return names[0]

for n,x in enumerate(records,1):
    p=doc.add_paragraph();p.paragraph_format.left_indent=Inches(.25);p.paragraph_format.first_line_indent=Inches(-.25)
    p.paragraph_format.keep_together=True;p.paragraph_format.keep_with_next=True
    p.paragraph_format.space_after=Pt(3)
    p.add_run(author_string(x['author'])+f" ({x['year']}). ")
    if x['kind']=='preprint':
        p.add_run(x['title']).italic=True;p.add_run(' [Preprint, versi 1]. arXiv. ')
    else:
        p.add_run(x['title']+'. ')
        if x['kind']=='conference':
            p.add_run('In ');p.add_run(x['journal']).italic=True
            p.add_run(' (pp. '+x['pages'].replace('--','–')+'). '+x['publisher']+'. ')
        else:
            p.add_run(x['journal']+', '+x.get('volume','')).italic=True
            if x.get('number'):p.add_run('('+x['number']+')')
            pages=x.get('pages','').replace('--','–')
            if x['doi'].startswith('10.1038/'):pages='Article '+pages
            p.add_run(', '+pages+'. ')
    url='https://doi.org/'+x['doi'] if x['doi'] else x['url']
    link(p,url,url)
    p=doc.add_paragraph();p.paragraph_format.left_indent=Inches(.25)
    p.paragraph_format.keep_together=True;p.paragraph_format.space_after=Pt(11)
    r=p.add_run(x['decision']+' Asal: '+x['origin']+'.');r.font.size=Pt(10);r.font.color.rgb=RGBColor(70,70,70)
    if x['doi']=='10.1016/j.aiopen.2021.01.001':
        p.add_run(' Tahun volume 2020 digunakan secara konsisten, meskipun artikel tersedia daring pada 2021.').font.size=Pt(10)
    if x['doi']=='10.1080/24748668.2025.2473799':
        p.add_run(' Tahun volume 2026; terbit daring pertama pada 2025.').font.size=Pt(10)
    if x['doi']=='10.1080/24733938.2022.2158213':
        p.add_run(' Tahun volume 2024; terbit daring pertama pada 2022.').font.size=Pt(10)

doc.core_properties.title='Hasil Seleksi Daftar Pustaka Gabungan VAEP Track'
doc.core_properties.subject='Penyaringan 15 karya unik terhadap syarat tahun 2021 ke atas dan SINTA 3 sampai 6'
doc.core_properties.author=''
out=root/'docs/jurnalreferensi/Hasil_Seleksi_Daftar_Pustaka_Gabungan_2026-10-26.docx'
doc.save(out)
print(json.dumps({'output':str(out),'unique_works':len(records),'verified_pass':0,'year_and_type_only':9,'excluded_year_or_type':6},ensure_ascii=False))
