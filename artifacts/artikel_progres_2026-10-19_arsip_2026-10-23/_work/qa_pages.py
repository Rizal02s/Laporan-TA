from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from pdf2image import convert_from_path
from pypdf import PdfReader
from PIL import Image, ImageOps, ImageDraw
import json,sys
ROOT=Path(sys.argv[1]) if len(sys.argv)>1 else Path(r'C:\VAEP-Track\docs\artikel_progres_2026-10-19')
QA=ROOT/'_qa'
POP=r'C:\Users\rizal\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin'
def render(pdf):
    folder=QA/pdf.stem;folder.mkdir(exist_ok=True)
    images=convert_from_path(str(pdf),dpi=120,poppler_path=POP,thread_count=2)
    for i,im in enumerate(images,1):im.save(folder/f'page-{i}.png')
    pages=PdfReader(pdf).pages
    rec={'file':pdf.name,'pages':len(pages),'page_words':[len((p.extract_text() or '').split()) for p in pages]}
    print(json.dumps(rec))
    return rec
with ThreadPoolExecutor(max_workers=3) as ex:
    recs=list(ex.map(render,sorted(QA.glob('*.pdf'))))
(QA/'page_audit.json').write_text(json.dumps(recs,indent=2),encoding='utf-8')
for folder in sorted(p for p in QA.iterdir() if p.is_dir() and p.name!='renderer_check'):
    ims=sorted(folder.glob('page-*.png'),key=lambda p:int(p.stem.split('-')[-1]))
    for start in range(0,len(ims),4):
        group=ims[start:start+4]
        canvas=Image.new('RGB',(1000,730*((len(group)+1)//2)),'#b5b5b5')
        draw=ImageDraw.Draw(canvas)
        for idx,p in enumerate(group):
            im=Image.open(p);im.thumbnail((480,685))
            x=10+(idx%2)*500;y=25+(idx//2)*730
            canvas.paste(im,(x,y));draw.text((x,y-19),f'{folder.name[:45]} / {p.stem}',fill='black')
        canvas.save(QA/(folder.name+f'_contact_{start//4+1}.png'))
