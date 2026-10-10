import concurrent.futures,hashlib,json,time,urllib.request,urllib.error,unicodedata
from datetime import datetime,timezone,timedelta
from pathlib import Path
from inspect_sources import Tags
from inspect_text import plain
R=Path(__file__).resolve().parent
ev=json.loads((R/'product_evidence.json').read_text(encoding='utf-8'))
(R/'product_pages').mkdir(exist_ok=True)
def norm(s):return ' '.join(unicodedata.normalize('NFC',s).casefold().split())
def one(e):
    dest=R/'product_pages'/(e['id']+'.html');md=dest.with_suffix('.meta.json')
    if md.exists():
        m=json.loads(md.read_text(encoding='utf-8'))
        if dest.exists():
            m['source_name_found']=norm(e['name']) in norm(plain(dest.read_text(encoding='utf-8')))
            md.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        return m
    m={'product_id':e['id'],'url':e['url'],'checked_at':datetime.now(timezone(timedelta(hours=7))).isoformat()}
    try:
        req=urllib.request.Request(e['url'],headers={'User-Agent':'VNStoreResearch/1.0 (product catalog research)'})
        with urllib.request.urlopen(req,timeout=35) as response:
            data=response.read(12*1024*1024);m.update(status=response.status,final_url=response.url)
        dest.write_bytes(data);txt=data.decode('utf-8','replace');tags=Tags(txt).tags
        canonical=next((a.get('href') for t,a in tags if t=='link' and a.get('rel')=='canonical'),None)
        m.update(path=dest.relative_to(R).as_posix(),sha256=hashlib.sha256(data).hexdigest(),bytes=len(data),canonical_url=canonical,source_name_found=norm(e['name']) in norm(plain(txt)))
    except urllib.error.HTTPError as exc:m.update(status=exc.code,error=str(exc))
    except Exception as exc:m.update(status=None,error=str(exc))
    md.write_text(json.dumps(m,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');time.sleep(.1)
    return m
out=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for i,m in enumerate(pool.map(one,ev),1):
        out.append(m)
        if i%40==0: print(i,'checked;',sum(x.get('status')!=200 for x in out),'non-200',flush=True)
(R/'source_page_checks.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('Complete',len(out),'non-200',sum(x.get('status')!=200 for x in out),flush=True)
