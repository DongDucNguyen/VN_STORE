import concurrent.futures, hashlib, json, urllib.request, urllib.error, sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
ROOT = Path(__file__).resolve().parent
def fetch(pair):
    key,url=pair
    existing=ROOT/'raw'/f'{key}.raw'
    if existing.exists():
        metadata=json.loads(existing.with_suffix('.meta.json').read_text(encoding='utf-8'))
        return key,{'cached':True,'url':metadata['url'],'requested_url':url,'note':'Existing evidence preserved; use a new key for a fresh retrieval.'}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'VNStoreResearch/1.0 (product catalog research)','Accept':'application/json,text/html,*/*'})
        with urllib.request.urlopen(req,timeout=35) as r:
            data=r.read(); headers=dict(r.headers); final=r.url
        out=ROOT/'raw'/f'{key}.raw'; out.parent.mkdir(exist_ok=True); out.write_bytes(data)
        meta={'url':url,'final_url':final,'retrieved_at':datetime.now(timezone(timedelta(hours=7))).isoformat(),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'headers':headers}
        out.with_suffix('.meta.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
        try:
            j=json.loads(data); info={'type':type(j).__name__,'keys':list(j)[:10] if isinstance(j,dict) else len(j)}
        except Exception: info={'start':data[:90].decode('utf-8','replace')}
        return key,info
    except Exception as e:
        (ROOT/'errors').mkdir(exist_ok=True)
        (ROOT/'errors'/f'{key}.json').write_text(json.dumps({'url':url,'error':str(e),'at':datetime.now(timezone.utc).isoformat()}),encoding='utf-8')
        return key,{'error':str(e)}
if __name__=='__main__':
    urls={
      'minhlong-products':'https://minhlong.com/products.json?limit=250&page=1',
      'marou-products':'https://maisonmarou.com/products.json?limit=250&page=1',
      'vietcraft-products':'https://vietcraft.vn/wp-json/wc/store/v1/products?per_page=100&page=1',
      'kilomet-products':'https://www.kilomet109.com/wp-json/wc/store/v1/products?per_page=100&page=1',
      'hanoia-sitemap':'https://hanoia.com/sitemap.xml',
    }
    if len(sys.argv)>1: urls=json.loads((ROOT/sys.argv[1]).read_text(encoding='utf-8'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for result in pool.map(fetch,urls.items()): print(json.dumps(result,ensure_ascii=False),flush=True)
