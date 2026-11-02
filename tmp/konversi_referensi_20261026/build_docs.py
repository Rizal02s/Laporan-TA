from pathlib import Path
import re, json
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.opc.constants import RELATIONSHIP_TYPE as RT

ROOT = Path(__file__).resolve().parents[2]
SOURCES = [ROOT/'docs/referensi_tambahan_2026-10-25/10_Referensi_Tambahan_VAEP_Track.md', ROOT/'docs/jurnalreferensi/Audit_Kelayakan_Referensi_2026-10-25.md']

TOKEN = re.compile(r'\[([^\]]+)\]\(([^)]+)\)|\*\*(.+?)\*\*|\*([^*]+)\*|`([^`]+)`')

def inline(p, text):
    pos = 0
    for m in TOKEN.finditer(text):
        p.add_run(text[pos:m.start()])
        if m.group(1):
            h = OxmlElement('w:hyperlink')
            h.set(qn('r:id'),p.part.relate_to(m.group(2),RT.HYPERLINK,is_external=True))
            r = OxmlElement('w:r'); pr=OxmlElement('w:rPr')
            c=OxmlElement('w:color');c.set(qn('w:val'),'175A80');pr.append(c)
            u=OxmlElement('w:u');u.set(qn('w:val'),'single');pr.append(u)
            r.append(pr);t=OxmlElement('w:t');t.text=m.group(1);r.append(t);h.append(r);p._p.append(h)
        else:
            r=p.add_run(m.group(3) or m.group(4) or m.group(5))
            if m.group(3):r.bold=True
            if m.group(4):r.italic=True
        pos=m.end()
    p.add_run(text[pos:])

def paragraph(doc,text,style=None):
    p=doc.add_paragraph(style=style);inline(p,text);return p

def group(paras):
    for p in paras[:-1]:p.paragraph_format.keep_with_next=True
    for p in paras:p.paragraph_format.keep_together=True

report=[]
for source in SOURCES:
    text=source.read_text(encoding='utf-8-sig')
    doc=Document();sec=doc.sections[0]
    sec.page_width=Cm(21);sec.page_height=Cm(29.7)
    sec.top_margin=Cm(2);sec.bottom_margin=Cm(2);sec.left_margin=Cm(2.2);sec.right_margin=Cm(2.2)
    for name in ['Normal','Title','Heading 1','Heading 2','List Bullet','List Number']:
        s=doc.styles[name];s.font.name='Calibri';s.font.color.rgb=RGBColor(0,0,0)
    normal=doc.styles['Normal'];normal.font.size=Pt(11)
    normal.paragraph_format.line_spacing=1.12;normal.paragraph_format.space_after=Pt(7)
    normal.paragraph_format.keep_together=True
    for border in doc.styles.element.xpath('.//w:pBdr'):
        border.getparent().remove(border)
    for name,size in [('Title',22),('Heading 1',14),('Heading 2',12)]:
        s=doc.styles[name];s.font.size=Pt(size);s.font.bold=True
        s.paragraph_format.space_before=Pt(13 if name!='Title' else 0)
        s.paragraph_format.space_after=Pt(7)
        s.paragraph_format.keep_with_next=True
    for name in ['List Bullet','List Number']:
        doc.styles[name].paragraph_format.space_after=Pt(3)
    is_refs=source.name.startswith('10_')
    current=[];table_headers=None;record=0
    for line in text.splitlines():
        line=line.strip()
        if not line:continue
        if line.startswith('|'):
            cells=[x.strip() for x in line.strip('|').split('|')]
            if table_headers is None:table_headers=cells;continue
            if all(re.fullmatch(r'[-: ]+',x) for x in cells):continue
            record+=1
            block=[paragraph(doc,f'Referensi {record}','Heading 2')]
            block.extend(paragraph(doc,f'**{label}:** {val}') for label,val in zip(table_headers,cells))
            group(block);continue
        table_headers=None
        if line.startswith('# '):
            paragraph(doc,line[2:],'Title');doc.core_properties.title=line[2:];continue
        if line.startswith('## '):
            if current:group(current);current=[]
            title=line[3:]
            # Preserve exact bibliographic titles as body text rather than rewriting them.
            if is_refs and re.match(r'\d+ ',title):
                num,title=title.split(' ',1)
                p=paragraph(doc,'Referensi '+num,'Heading 1');current.append(p)
                p=paragraph(doc,'**'+title+'**');current.append(p)
            else:paragraph(doc,title,'Heading 1')
            continue
        if line.startswith('- '):p=paragraph(doc,line[2:],'List Bullet')
        elif re.match(r'^\d+\. ',line):p=paragraph(doc,re.sub(r'^\d+\. ','',line),'List Number')
        else:p=paragraph(doc,line)
        if is_refs and current:current.append(p)
    if current:group(current)
    doc.core_properties.author=''
    doc.core_properties.comments=''
    out=source.with_suffix('.docx');doc.save(out)
    links=[r.target_ref for r in doc.part.rels.values() if r.reltype==RT.HYPERLINK]
    expected=[m.group(2) for m in TOKEN.finditer(text) if m.group(1)]
    assert set(expected)==set(links),(source,'Missing links')
    # Verify each source line/cell is present after removing Markdown markup.
    full=' '.join(doc.element.xpath('//w:t/text()'))
    normalize=lambda s:re.sub(r'\s+','',s)
    full=normalize(full)
    def clean(s):
        return TOKEN.sub(lambda m:m.group(1) or m.group(3) or m.group(4) or m.group(5),s)
    for line in text.splitlines():
        line=line.strip()
        if not line:continue
        if line.startswith('|'):
            cells=[x.strip() for x in line.strip('|').split('|')]
            if all(re.fullmatch(r'[-: ]+',x) for x in cells):continue
            for c in cells:assert normalize(clean(c)) in full,c
        else:
            val=re.sub(r'^(?:#{1,6} |\d+\. |- )','',line)
            if is_refs and line.startswith('## '):val=re.sub(r'^\d+ ','',val)
            assert normalize(clean(val)) in full,val
    report.append({'file':str(out),'bytes':out.stat().st_size,'hyperlinks':len(links),'source_links':len(expected),'content_check':'all source text retained'})
print(json.dumps(report,ensure_ascii=False,indent=2))
