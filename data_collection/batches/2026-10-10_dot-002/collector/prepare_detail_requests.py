import json,re,hashlib
from pathlib import Path
from urllib.parse import urljoin
from inspect_sources import links
R=Path(__file__).resolve().parent
if (R/'baseline/database.before.json').exists():
    raise SystemExit('Baseline already exists: do not overwrite the original session snapshot. Use a new batch directory.')
base=json.loads((R.parent/'database.json').read_text(encoding='utf-8'))
(R/'baseline').mkdir(exist_ok=True)
(R/'baseline'/'database.before.json').write_text(json.dumps(base,ensure_ascii=False,indent=2),encoding='utf-8')
(R/'baseline'/'database.schema.json').write_bytes((R.parent/'database.schema.json').read_bytes())
(R/'baseline'/'input_hashes.json').write_text(json.dumps({x:hashlib.sha256((R.parent/x).read_bytes()).hexdigest() for x in ['database.json','database.schema.json','PLAN.md','docs/huong-dan-nhap-lieu.md']},indent=2),encoding='utf-8')
old={s['url'].rstrip('/') for s in base['sources'] if s.get('url')}
requests={}; discovered={}
for site,keys in [('minhlong',['minhlong-list','minhlong-list2','minhlong-list3']),('hanoia',['hanoia-vases','hanoia-boxes','hanoia-trays','hanoia-frames','hanoia-tea','hanoia-office','hanoia-other'])]:
    candidates=[]
    for key in keys:
        xs=[]
        for x in links(key):
            x=urljoin('https://'+('minhlong.com' if site=='minhlong' else 'hanoia.com'),x.strip())
            if site=='minhlong' and '/products/' not in x: continue
            if site=='hanoia' and not re.search(r'-[a-z]{1,4}\d{2}[a-z]{1,3}\d{2}\.html$',x): continue
            if x.rstrip('/') in old or x in candidates: continue
            xs.append(x)
        # balanced across collection pages, spare candidates for filtering
        candidates.extend(xs[:32] if site=='minhlong' else xs)
    discovered[site]=candidates
    for n,u in enumerate(candidates): requests[f'{site}-detail-{n:03}']=u+('.js' if site=='minhlong' else '')
(R/'detail_requests.json').write_text(json.dumps(requests,ensure_ascii=False,indent=2),encoding='utf-8')
(R/'discovered.json').write_text(json.dumps(discovered,ensure_ascii=False,indent=2),encoding='utf-8')
print({k:len(v) for k,v in discovered.items()})
