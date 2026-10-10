import json
from pathlib import Path
from urllib.parse import urljoin
from inspect_sources import links
R=Path(__file__).resolve().parent
urls=[]
known={json.loads(p.read_text())['url'] for p in (R/'raw').glob('*.meta.json')}
for key in ['minhlong-list4','minhlong-list5','minhlong-list6']:
    for u in links(key):
        u=urljoin('https://minhlong.com',u)
        if '/products/' in u and u+'.js' not in known and u not in urls:urls.append(u)
requests={'minhlong-detail-extra-'+str(n).zfill(3):u+'.js' for n,u in enumerate(urls[:100])}
(R/'more_details.json').write_text(json.dumps(requests,indent=2),encoding='utf-8')
print(len(requests))
