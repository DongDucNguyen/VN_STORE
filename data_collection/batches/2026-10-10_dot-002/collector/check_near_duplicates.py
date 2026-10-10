"""dHash candidate audit; hints only, never benchmark labels or automatic exclusions."""
import json,html
from collections import Counter
from pathlib import Path
from PIL import Image,ImageOps
R=Path(__file__).resolve().parent
cat=json.loads((R/'catalog.json').read_text(encoding='utf-8'))
ev={x['id']:x for x in json.loads((R/'product_evidence.json').read_text(encoding='utf-8'))}
items=[]
for p in cat['products']:
    for im in p['images']:
        with Image.open(R/im['local_path']) as src:
            rgba=src.convert('RGBA'); bg=Image.new('RGBA',rgba.size,'white');bg.alpha_composite(rgba)
            px=list(bg.convert('L').resize((9,8),Image.Resampling.LANCZOS).get_flattened_data())
        bits=0
        for y in range(8):
            for x in range(8):bits=(bits<<1)|int(px[y*9+x]>px[y*9+x+1])
        items.append({'product_id':p['id'],'image_id':im['id'],'path':im['local_path'],'sha256':im['sha256'],'dhash':bits,'name':p['name_vi'],'group':ev[p['id']]['group']})
pairs=[]
for i,a in enumerate(items):
    for b in items[i+1:]:
        if a['product_id']==b['product_id']:continue
        dist=(a['dhash']^b['dhash']).bit_count()
        if dist<=5:
            pairs.append({'distance':dist,'a':{k:a[k] for k in ['product_id','image_id','path','name']},'b':{k:b[k] for k in ['product_id','image_id','path','name']},'same_group':a['group']==b['group'],'status':'candidate_not_confirmed'})
pairs.sort(key=lambda x:(x['distance'],x['a']['product_id'],x['b']['product_id']))
base=json.loads((R/'baseline/database.before.json').read_text(encoding='utf-8'))
old_hashes={i['sha256']:p['id'] for p in base['products'] for i in p['images'] if i.get('sha256')}
overlap=[{'image_id':x['image_id'],'product_id':x['product_id'],'original_product_id':old_hashes[x['sha256']]} for x in items if x['sha256'] in old_hashes]
report={'method':'64-bit dHash, grayscale 9x8, alpha on white; Hamming <=5, cross-product pairs only','candidate_pairs':len(pairs),'confirmed_duplicate_pairs':None,'exact_hash_overlap_with_original_catalog':overlap,'threshold_not_calibrated':True,'warning':'Low dHash distance is not proof of a duplicate; different products on plain backgrounds can collide. Human review required. No images auto-removed by this audit.','pairs':pairs}
(R/'near_duplicate_candidates.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
cards=[]
for pair in pairs:
    imgs=''.join(f'<figure><a href="{html.escape(pair[k]["path"])}"><img loading="lazy" src="{html.escape(pair[k]["path"])}"></a><figcaption>{html.escape(pair[k]["name"])}<br>{pair[k]["image_id"]}</figcaption></figure>' for k in ['a','b'])
    cards.append(f'<article><h2>dHash distance {pair["distance"]}</h2><div>{imgs}</div></article>')
(R/'near_duplicate_review.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><title>Ảnh gần trùng: ứng viên cần xem</title><style>body{font:16px system-ui;margin:24px}main{display:grid;grid-template-columns:repeat(auto-fill,minmax(520px,1fr));gap:20px}article{border:1px solid #ccc;padding:12px}article div{display:flex}figure{width:50%;margin:6px}img{width:100%;height:220px;object-fit:contain}figcaption{overflow-wrap:anywhere;font-size:13px}h2{font-size:16px}</style><h1>Ứng viên gần trùng</h1><p>'+str(len(pairs))+' cặp, dHash ≤5. Chỉ là gợi ý kiểm tra; không phải kết luận trùng và không phải nhãn benchmark.</p><main>'+''.join(cards)+'</main></html>',encoding='utf-8')
print(json.dumps({'images':len(items),'candidate_pairs':len(pairs),'exact_overlap_original':len(overlap)}))
