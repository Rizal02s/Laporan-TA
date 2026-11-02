from pathlib import Path
from pypdf import PdfReader
base=Path(r'C:\VAEP-Track\docs\jurnalreferensi')
for p in sorted(base.glob('*.pdf')):
    reader=PdfReader(str(p))
    print('\n===',p.name,'pages=',len(reader.pages),'meta=',reader.metadata)
    text='\n'.join((page.extract_text() or '') for page in reader.pages[:2])
    print(text[:4200].replace('\x00',' '))
