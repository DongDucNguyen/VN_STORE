import json,re
from pathlib import Path
from inspect_sources import links
R=Path(__file__).resolve().parent
old=json.loads((R/'baseline/database.before.json').read_text(encoding='utf-8'))
old={s['url'].rstrip('/') for s in old['sources'] if s.get('url')}
urls=set()
for p in (R/'raw').glob('hanoia-*.raw'):
    for x in links(p.stem):
        x=x.strip()
        if re.search(r'https://hanoia.com/[^/]+-[a-z]{1,4}\d{2}[a-z]{1,3}\d{2}\.html$',x) and x not in old: urls.add(x)
requests={}
known={json.loads(p.read_text())['url'] for p in (R/'raw').glob('hanoia-*.meta.json')}
for u in sorted(urls-known):
    key='hanoia-product-'+u.rsplit('-',1)[1].replace('.html','')
    if len(requests)<16: requests[key]=u
(R/'hanoia_details.json').write_text(json.dumps(requests,ensure_ascii=False,indent=2),encoding='utf-8')
print('Discovered',len(urls),'new requests',len(requests))
