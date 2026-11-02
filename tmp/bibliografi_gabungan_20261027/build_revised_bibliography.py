from pathlib import Path
import json, unicodedata
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT

root=Path(r'C:\VAEP-Track')
old=json.loads((root/'tmp/bibliografi_gabungan_20261026/selection.json').read_text(encoding='utf-8'))
selected=[x for x in old if x['kind']=='journal' and int(x['year'])>=2021]
for x in selected:
    x['group']='awal' if 'Koleksi awal' in x['origin'] else 'tambahan'

science_direct=[
    dict(author='Gu, Chaoyi and De Silva, Varuna and Caine, Mike',year='2024',title='A machine learning framework for quantifying in-game space-control efficiency in football',journal='Knowledge-Based Systems',volume='283',pages='111123',doi='10.1016/j.knosys.2023.111123',url='https://www.sciencedirect.com/science/article/pii/S0950705123008730',role='Evaluasi ruang dan kontrol tim dari data tracking serta event; bukan deteksi gegenpressing langsung.'),
    dict(author='Borghesi, Matteo and Costa, Lorenzo Dusty and Morra, Lia and Lamberti, Fabrizio',year='2023',title='Using temporal convolutional networks to estimate ball possession in soccer games',journal='Expert Systems with Applications',volume='223',pages='119780',doi='10.1016/j.eswa.2023.119780',url='https://www.sciencedirect.com/science/article/pii/S0957417423002816',role='Estimasi penguasaan bola dari tracking sebagai dasar menentukan waktu kehilangan bola.'),
    dict(author='Li, Zujian and Yu, Dan',year='2025',title='A spatiotemporal graph transformer network for real-time ball trajectory monitoring and prediction in dynamic sports environments',journal='Alexandria Engineering Journal',volume='119',pages='246--258',doi='10.1016/j.aej.2024.11.053',url='https://www.sciencedirect.com/science/article/pii/S1110016824015242',role='Contoh graph temporal untuk prediksi lintasan bola; tugas prediksi berbeda dari klasifikasi gegenpressing.'),
    dict(author='Moussavi, Laleh and Andrienko, Gennady and Andrienko, Natalia and Slingsby, Aidan',year='2025',title='Visually-supported topic modeling for understanding behavioral patterns from spatio-temporal events',journal='Computers & Graphics',volume='129',pages='104245',doi='10.1016/j.cag.2025.104245',url='https://www.sciencedirect.com/science/article/pii/S009784932500086X',role='Segmentasi episode dan visualisasi pola peristiwa sepak bola; metode topic modeling, bukan GNN.')
]
for x in science_direct:
    x.update(kind='journal',group='tambahan',origin='Artikel jurnal terbuka di ScienceDirect')
selected += science_direct
assert len(selected)==13 and sum(x['group']=='awal' for x in selected)==3 and sum(x['group']=='tambahan' for x in selected)==10
assert len({x['doi'].lower() for x in selected})==13
selected.sort(key=lambda x:(unicodedata.normalize('NFKD',x['author']).casefold(),x['year']))

out=root/'docs/jurnalreferensi/Draf_Daftar_Pustaka_Gabungan_2026-10-27.docx'
out.parent.mkdir(exist_ok=True)
doc=Document()
sec=doc.sections[0]
sec.page_width=Inches(8.5);sec.page_height=Inches(11)
sec.top_margin=Inches(.78);sec.bottom_margin=Inches(.72)
sec.left_margin=Inches(.9);sec.right_margin=Inches(.9)
for name in ['Normal','Title','Heading 1','Heading 2','List Bullet']:
    style=doc.styles[name];style.font.name='Calibri';style.font.color.rgb=RGBColor(0,0,0)
normal=doc.styles['Normal'];normal.font.size=Pt(10.5)
normal.paragraph_format.line_spacing=1.12;normal.paragraph_format.space_after=Pt(7)
for name,size in [('Title',21),('Heading 1',13.5),('Heading 2',11.5)]:
    style=doc.styles[name];style.font.size=Pt(size);style.font.bold=True
    style.paragraph_format.keep_with_next=True
    style.paragraph_format.space_before=Pt(12 if name!='Title' else 0)
    style.paragraph_format.space_after=Pt(6)
for border in doc.styles.element.xpath('.//w:pBdr'):border.getparent().remove(border)

def hyperlink(p,label,url):
    h=OxmlElement('w:hyperlink');h.set(qn('r:id'),p.part.relate_to(url,RT.HYPERLINK,is_external=True))
    r=OxmlElement('w:r');pr=OxmlElement('w:rPr')
    c=OxmlElement('w:color');c.set(qn('w:val'),'175A80');pr.append(c)
    u=OxmlElement('w:u');u.set(qn('w:val'),'single');pr.append(u)
    r.append(pr);t=OxmlElement('w:t');t.text=label;r.append(t);h.append(r);p._p.append(h)

def authors(raw):
    names=[]
    for part in raw.split(' and '):
        family,given=part.split(',',1)
        initials=' '.join(word[0]+'.' for word in given.strip().split() if word)
        names.append(f'{family.strip()}, {initials}')
    if len(names)>20:return ', '.join(names[:19])+', ... '+names[-1]
    if len(names)>1:return ', '.join(names[:-1])+', & '+names[-1]
    return names[0]

header=sec.header.paragraphs[0];header.alignment=WD_ALIGN_PARAGRAPH.RIGHT
r=header.add_run('VAEP-TRACK  |  DRAF ARTIKEL JURNAL');r.font.size=Pt(8);r.font.color.rgb=RGBColor(100,100,100)
footer=sec.footer.paragraphs[0];footer.alignment=WD_ALIGN_PARAGRAPH.CENTER
r=footer.add_run('Draf daftar pustaka 27 Oktober 2026  •  ');r.font.size=Pt(8);r.font.color.rgb=RGBColor(100,100,100)
field=OxmlElement('w:fldSimple');field.set(qn('w:instr'),'PAGE');footer._p.append(field)

doc.add_paragraph('Draf Daftar Pustaka VAEP-Track',style='Title')
p=doc.add_paragraph('Tiga referensi awal dan sepuluh referensi tambahan yang memenuhi batas tahun dan jenis jurnal')
p.paragraph_format.space_after=Pt(5)
p=doc.add_paragraph();r=p.add_run('Pemeriksaan 27 Oktober 2026');r.italic=True;r.font.color.rgb=RGBColor(90,90,90)
p=doc.add_paragraph('Dokumen ini menggantikan hasil seleksi sebelumnya yang memakai syarat SINTA. Sesuai koreksi pengguna, tidak ada ketentuan peringkat SINTA bagi referensi. Syarat yang diterapkan adalah artikel jurnal terbit mulai 2021, relevan dengan riset, dan minimal setara jurnal nasional. Artikel jurnal internasional pada daftar ini memenuhi batas jenis terbitan. Semua entri masih perlu dicocokkan dengan kutipan yang benar-benar dipakai dalam naskah sebelum menjadi daftar pustaka final.')

doc.add_paragraph('Daftar pustaka',style='Heading 1')
doc.add_paragraph('Urutan alfabetis penulis. Tautan DOI menunjuk publikasi jurnal yang digunakan sebagai identitas sitasi.')
for x in selected:
    p=doc.add_paragraph()
    p.paragraph_format.left_indent=Inches(.35)
    p.paragraph_format.first_line_indent=Inches(-.35)
    p.paragraph_format.keep_together=True
    p.paragraph_format.space_after=Pt(10)
    p.add_run(authors(x['author'])+f" ({x['year']}). {x['title'].replace('–','-')}. ")
    p.add_run(x['journal']+', '+x['volume']).italic=True
    if x.get('number'):p.add_run('('+x['number']+')')
    pages=x['pages'].replace('--','–')
    if x['doi'] in {'10.1038/s41597-025-04505-y','10.1038/s41467-024-45965-x','10.1038/s44260-025-00047-x'}:
        pages='Article '+pages
    p.add_run(', '+pages+'. ')
    hyperlink(p,'https://doi.org/'+x['doi'],'https://doi.org/'+x['doi'])

doc.add_paragraph('Catatan pemilihan referensi',style='Heading 1')
p=doc.add_paragraph('Sepuluh referensi tambahan mencakup enam rekomendasi lama yang terbit mulai 2021 dan empat artikel terbuka dari ScienceDirect. TacticAI yang sudah ada pada koleksi awal dihitung satu kali. Enam kandidat gabungan lain tidak dimasukkan karena berupa prosiding atau preprint, atau tahun volume jurnalnya sebelum 2021. Artikel VAEP 2019 dapat tetap dibahas sebagai sumber dasar hanya bila pembimbing mengizinkan pengecualian batas tahun.')
p=doc.add_paragraph('ScienceDirect adalah tempat mengakses artikel penerbit, sedangkan ResearchGate dapat menyediakan salinan penulis. Nama penulis, tahun, jurnal, dan DOI tetap diambil dari publikasi resmi. Ketersediaan salinan pada ResearchGate tidak mengubah jenis publikasi.')

doc.add_paragraph('Artikel tambahan dari ScienceDirect',style='Heading 2')
for x in science_direct:
    p=doc.add_paragraph(style='List Bullet')
    p.add_run(f"{x['author'].split(',')[0]} dkk. ({x['year']}) - {x['role']} ")
    hyperlink(p,'Halaman ScienceDirect',x['url'])

doc.core_properties.title='Draf Daftar Pustaka Gabungan VAEP Track'
doc.core_properties.subject='Tiga referensi awal dan sepuluh tambahan yang berupa artikel jurnal sejak 2021'
doc.core_properties.author=''
doc.save(out)
(root/'tmp/bibliografi_gabungan_20261027/selected.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'file':str(out),'entries':len(selected),'initial':3,'additional':10,'sciencedirect_additions':4},ensure_ascii=False))
