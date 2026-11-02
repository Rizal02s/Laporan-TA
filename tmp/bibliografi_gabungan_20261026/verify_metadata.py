import json,re,urllib.request,concurrent.futures
from pathlib import Path
base=Path(r'C:\VAEP-Track')
bib=(base/'docs/referensi_tambahan_2026-10-25/Referensi_Tambahan_VAEP_Track.bib').read_text(encoding='utf-8-sig')
dois=re.findall(r'doi = \{([^}]+)\}',bib)
dois += ['10.1007/s10618-021-00763-7','10.1038/s41597-025-04505-y','10.1145/3292500.3330758','10.1109/BigData52589.2021.9671833']
def fetch(doi):
 try:
  req=urllib.request.Request('https://api.crossref.org/works/'+doi,headers={'User-Agent':'VAEPTrackBibliographyAudit/1.0'})
  with urllib.request.urlopen(req,timeout=35) as response: m=json.load(response)['message']
  return {'doi':doi,'metadata':m}
 except Exception as e: return {'doi':doi,'error':str(e)}
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as ex: results=list(ex.map(fetch,dois))
(base/'tmp/bibliografi_gabungan_20261026/crossref.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
for r in results:
 m=r.get('metadata',{})
 print(json.dumps({'doi':r['doi'],'error':r.get('error'),'type':m.get('type'),'title':m.get('title'),'journal':m.get('container-title'),'volume':m.get('volume'),'issue':m.get('issue'),'pages':m.get('page'),'article':m.get('article-number'),'print':m.get('published-print'),'online':m.get('published-online'),'published':m.get('published')},ensure_ascii=False))
