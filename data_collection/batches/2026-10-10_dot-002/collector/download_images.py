"""Download only catalog-listed public image URLs, write only under tmp_data."""
import concurrent.futures,hashlib,io,json,time,urllib.request
from pathlib import Path
from datetime import datetime,timezone,timedelta
from PIL import Image
R=Path(__file__).resolve().parent
def dump(path,obj): path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
cat=json.loads((R/'catalog.json').read_text(encoding='utf-8'))
manifest_path=R/'image_manifest.json'
previous=json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.exists() else []
cached={x['source_url']:x for x in previous if x.get('status')=='downloaded' and (R/x['local_path']).is_file()}
cached.update({x['source_url']:x for x in previous if x.get('status')=='failed' and '404' in x.get('error','')})
tasks={}
for p in cat['products']:
    for im in p['images']: tasks.setdefault(im['source_url'],(p['id'],im))
def one(task):
    url,(pid,im)=task
    if url in cached: return cached[url]
    entry={'source_url':url,'image_id':im['id'],'product_id':pid,'downloaded_at':datetime.now(timezone(timedelta(hours=7))).isoformat()}
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'VNStoreResearch/1.0 (product catalog research)'})
        with urllib.request.urlopen(req,timeout=40) as response:
            data=response.read(32*1024*1024+1); entry.update(final_url=response.url,content_type=response.headers.get('Content-Type'))
        if len(data)>32*1024*1024: raise ValueError('Image exceeds 32 MiB')
        with Image.open(io.BytesIO(data)) as img:
            fmt=img.format; width,height=img.size; img.verify()
        with Image.open(io.BytesIO(data)) as img: img.load()
        ext={'JPEG':'.jpg','PNG':'.png','WEBP':'.webp'}.get(fmt)
        if not ext: raise ValueError('Unsupported image format '+str(fmt))
        out=R/'images'/pid/(im['id']+ext); out.parent.mkdir(parents=True,exist_ok=True); out.write_bytes(data)
        entry.update(status='downloaded',local_path=out.relative_to(R).as_posix(),sha256=hashlib.sha256(data).hexdigest(),width=width,height=height,bytes=len(data),format=fmt)
    except Exception as exc: entry.update(status='failed',error=str(exc))
    time.sleep(.08)
    return entry
results=[]
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    for n,item in enumerate(pool.map(one,tasks.items()),1):
        results.append(item)
        if n%40==0:
            dump(manifest_path,results)
            print(f'{n}/{len(tasks)} URLs; failures={sum(x["status"]=="failed" for x in results)}',flush=True)
dump(manifest_path,results)
by_url={x['source_url']:x for x in results}
for p in cat['products']:
    for im in p['images']:
        m=by_url[im['source_url']]
        if m['status']=='downloaded':
            for k in ['local_path','sha256','width','height']: im[k]=m[k]
dump(R/'catalog.json',cat)
print(json.dumps({'unique_urls':len(results),'downloaded':sum(x['status']=='downloaded' for x in results),'failed':sum(x['status']=='failed' for x in results),'bytes':sum(x.get('bytes',0) for x in results)}),flush=True)
