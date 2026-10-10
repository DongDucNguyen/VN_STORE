"""Offline audit and handoff; uses project validator read-only with python -B."""
import csv,hashlib,html,json,sys,unicodedata
from collections import Counter,defaultdict
from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
from inspect_text import plain
R=Path(__file__).resolve().parent
sys.path.insert(0,str(R.parent/'backend'))
from app.catalog.validation import validate_catalog
def load(name):return json.loads((R/name).read_text(encoding='utf-8'))
def dump(name,obj):(R/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def h(data):return hashlib.sha256(data).hexdigest()
def norm(s):return ' '.join(unicodedata.normalize('NFC',s).lower().split())
def esc(s):return html.escape(str(s),quote=True)
cat=load('catalog.json'); ev=load('product_evidence.json'); baseline=load('baseline/database.before.json')
by_ev={x['id']:x for x in ev}; by_source={x['id']:x for x in cat['sources']}
hashgroups=defaultdict(list)
for p in cat['products']:
    for im in p['images']:
        if im.get('sha256'):hashgroups[im['sha256']].append((p['id'],im['id']))
shared={sha:items for sha,items in hashgroups.items() if len({x[0] for x in items})>1}
historic_shared=load('shared_images.json') if (R/'shared_images.json').exists() else []
all_shared={x['sha256']:x['uses'] for x in historic_shared}
all_shared.update(shared)
decisions=[]
# Remove exact duplicate images within a product. Shared images with no alternative remain flagged.
for p in cat['products']:
    seen=set(); kept=[]
    has_unique=any(im.get('sha256') and im['sha256'] not in shared for im in p['images'])
    for im in p['images']:
        reason=None
        if not im.get('local_path'):reason='download_failed'
        elif im['sha256'] in seen:reason='duplicate_bytes_same_product'
        elif has_unique and im['sha256'] in shared:reason='shared_bytes_across_products_with_unique_alternative'
        if reason:
            decisions.append({'product_id':p['id'],'image_id':im['id'],'source_url':im['source_url'],'local_path':im.get('local_path'),'reason':reason,'action':'excluded_from_catalog_gallery'});continue
        kept.append(im);seen.add(im['sha256'])
    p['images']=kept
dump('catalog.json',cat)
old_decisions=load('image_selection.json') if (R/'image_selection.json').exists() else []
decisions=list({(d['product_id'],d['image_id']):d for d in old_decisions+decisions}.values())
dump('image_selection.json',decisions)
errors=[]; warnings=[];image_checks=[]
for p in cat['products']:
    evidence=by_ev[p['id']]
    response=R/evidence['response_path']
    if h(response.read_bytes())!=evidence['response_sha256']:errors.append('Raw hash mismatch '+p['id'])
    if not p['images']:errors.append('No local image '+p['id'])
    for im in p['images']:
        path=(R/im['local_path']).resolve()
        if R not in path.parents: errors.append('Escaped path '+im['id']);continue
        try:
            data=path.read_bytes()
            with Image.open(path) as img: img.load(); size=img.size
            if h(data)!=im['sha256'] or size!=(im['width'],im['height']):errors.append('Image mismatch '+im['id'])
            image_checks.append({'id':im['id'],'sha256':im['sha256'],'width':size[0],'height':size[1],'decoded':True})
            if min(size)<250:warnings.append({'code':'small_image','image_id':im['id'],'size':size})
        except Exception as e:errors.append(im['id']+': '+str(e))
    for claim in p['origin_claims']:
        if claim['value'] is not True:continue
        snippet=evidence['claim_evidence'][claim['claim_type']]
        src=by_source[claim['source_ids'][0]]
        if src['id'].startswith('src-tmp-'):
            text=plain((R/src['archived_copy_path']).read_text(encoding='utf-8'))
        else:
            rec=load(evidence['raw_path'])
            text=plain(rec.get('description','')+' '+rec.get('short_description','')+' '+rec.get('name',rec.get('title','')))
        if norm(snippet) not in norm(text):errors.append('Evidence excerpt not found '+p['id']+' '+claim['claim_type'])
old_urls={s['url'].rstrip('/') for s in baseline['sources'] if s.get('url')}
old_skus={v['sku'].casefold() for p in baseline['products'] for v in p['variants']}
urls=[x['url'].rstrip('/') for x in ev]; skus=[v['sku'].casefold() for p in cat['products'] for v in p['variants']]
if len(urls)!=len(set(urls)):errors.append('Duplicate source URLs')
if old_urls.intersection(urls):errors.append('Source URL overlaps original catalog')
if len(skus)!=len(set(skus)):errors.append('Case insensitive duplicate SKU')
if old_skus.intersection(skus):errors.append('SKU overlaps original catalog')
if any(p['status']!='draft' or p['reviewed_at'] is not None for p in cat['products']):errors.append('Invalid editorial status')
if any(im['usage_rights']['status']!='unknown' for p in cat['products'] for im in p['images']):errors.append('Image rights must remain unknown')
schema=load('baseline/database.schema.json')
validation=validate_catalog(cat,R,check_files=True,schema=schema)
errors.extend(str(x) for x in validation.errors)
warnings.extend({'code':x.code,'message':x.message} for x in validation.warnings)
groups=Counter(x['group'] for x in ev); sites=Counter(x['site'] for x in ev)
before=load('baseline/input_hashes.json')
current={k:h((R.parent/k).read_bytes()) for k in before}
quality={'passed':not errors,'errors':errors,'warnings':warnings,'catalog_sha256':h((R/'catalog.json').read_bytes()),'products':len(cat['products']),'groups':dict(groups),'sites':dict(sites),'variants':len(skus),'local_gallery_images':len(image_checks),'unique_gallery_image_hashes':len({x['sha256'] for x in image_checks}),'products_without_price':sum(not any(v['price_vnd'] for v in p['variants']) for p in cat['products']),'products_with_2_to_4_images':sum(2<=len(p['images'])<=4 for p in cat['products']),'products_with_one_image':sum(len(p['images'])==1 for p in cat['products']),'products_without_materials':sum(not p['materials'] for p in cat['products']),'draft_products':sum(p['status']=='draft' for p in cat['products']),'human_reviewed_products':0,'images_with_unknown_rights':len(image_checks),'shared_image_hashes_before_selection':len(shared),'excluded_images':len(decisions),'overlap_existing_urls':len(old_urls.intersection(urls)),'overlap_existing_skus':len(old_skus.intersection(skus)),'original_input_hashes':before,'current_input_hashes':current,'original_catalog_unchanged':before['database.json']==current['database.json'],'validation_scope':'Schema frozen at start; current project validator read-only. No full-project tests or index builds.','disclaimer':'Source declarations, not independent authenticity verification. All human review and image permission pending.'}
quality['shared_image_hashes_history']=len(all_shared)
final_hash_uses=defaultdict(set)
for product in cat['products']:
    for im in product['images']:final_hash_uses[im['sha256']].add(product['id'])
quality['shared_image_hashes_current_gallery']=sum(len(v)>1 for v in final_hash_uses.values())
quality['excluded_images_history']=len(decisions)
quality['excluded_images']=sum(d['product_id'] in by_ev for d in decisions)
dump('quality_report.json',quality);dump('image_checks.json',image_checks);dump('shared_images.json',[{'sha256':k,'uses':v} for k,v in all_shared.items()])
with (R/'products.csv').open('w',encoding='utf-8-sig',newline='') as f:
    w=csv.writer(f);w.writerow(['id','name_vi','group','category_id','source','source_url','sku','min_price_vnd','materials','colors','local_image_count','origin_claims_true','status','image_rights','observed_at'])
    for p in cat['products']:
        e=by_ev[p['id']];prices=[v['price_vnd'] for v in p['variants'] if v['price_vnd']]
        w.writerow([p['id'],p['name_vi'],e['group'],p['category_id'],e['site'],e['url'],' | '.join(v['sku'] for v in p['variants']),min(prices) if prices else '',', '.join(p['materials']),', '.join(p['colors']),len(p['images']),', '.join(x['claim_type'] for x in p['origin_claims'] if x['value'] is True),'draft','unknown',e['retrieved_at']])
# Static local review page: no external scripts, tracking, forms or remote images.
cards=[]
cats={c['id']:c['name_vi'] for c in cat['categories']}
for n,p in enumerate(cat['products'],1):
    e=by_ev[p['id']];prices=[v['price_vnd'] for v in p['variants'] if v['price_vnd']]
    price=f'{min(prices):,} VND' if prices else 'Chưa rõ giá VND'
    ims=''.join(f'<a href="{esc(im["local_path"])}"><img loading="lazy" src="{esc(im["local_path"])}" alt="{esc(im["alt_vi"])}"></a>' for im in p['images'])
    fact='; '.join(x['detail_vi'] for x in p['origin_claims'] if x['value'] is True)
    variants=''.join(f'<li>{esc(v["sku"])} — {esc(v["name_vi"])} — {v["price_vnd"] or "Chưa rõ giá"}</li>' for v in p['variants'])
    cards.append(f'<article data-site="{esc(e["site"])}" data-group="{esc(e["group"])}"><div class="photos">{ims}</div><small>#{n} · {esc(e["site"])} · {esc(cats[p["category_id"]])}</small><h2>{esc(p["name_vi"])}</h2><b>{esc(price)}</b><p>{esc(", ".join(p["materials"]) or "Chưa ghi nhận chất liệu")}</p><p>{esc(fact)}</p><a target="_blank" rel="noopener noreferrer" href="{esc(e["url"])}">Trang sản phẩm thật ↗</a> · <a href="{esc(e["raw_path"])}">Bản ghi nguồn</a><details><summary>SKU, ghi chú và trạng thái</summary><ul>{variants}</ul><p>{esc(p["editor_note"])}</p><code>{esc(p["id"])}</code><p>draft · reviewed_at=null · quyền ảnh: unknown</p></details></article>')
page='''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>VNStore · 300 sản phẩm thật · staging</title><style>
*{box-sizing:border-box}body{margin:0;background:#f5f2ec;color:#173529;font:16px/1.55 system-ui,sans-serif}header{padding:32px max(20px,5vw);background:#173529;color:#fff}h1{font-size:32px;margin:0}header p{max-width:1000px;color:#e0e7d9}nav{padding:16px max(20px,5vw);background:#fff;position:sticky;top:0;z-index:2;display:flex;gap:12px;flex-wrap:wrap}input,select{font:inherit;padding:9px;border:1px solid #bbb;border-radius:6px}main{padding:24px max(20px,5vw);display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:20px}article{padding:16px;background:white;border-radius:10px;border:1px solid #deded3}h2{font-size:19px;line-height:1.35}a{color:#19684b}small{color:#56685c}.photos{display:flex;overflow-x:auto;gap:8px;scroll-snap-type:x mandatory}.photos a{flex:0 0 100%;scroll-snap-align:start}.photos img{width:100%;height:250px;object-fit:contain;background:#fafafa}details{margin-top:12px}code{font-size:12px;overflow-wrap:anywhere}[hidden]{display:none!important}footer{padding:24px 5vw}</style>
<header><h1>VNStore · 300 sản phẩm thật</h1><p>60 sản phẩm mỗi nhóm · 6 website chính thức · dữ liệu thu ngày 10/10/2026.</p><p>Bộ staging độc lập. Giá và thông tin là ghi nhận từ nguồn tại thời điểm thu. Tất cả là bản nháp, chưa được người duyệt và chưa xác định quyền tái sử dụng ảnh. Ảnh này là gallery, không phải query benchmark độc lập.</p></header>
<nav><input id="q" type="search" placeholder="Tìm tên, SKU, chất liệu…" aria-label="Tìm sản phẩm"><select id="g" aria-label="Nhóm"><option value="">Tất cả nhóm</option>'''
page+=''.join(f'<option value="{esc(k)}">{esc(cats[k])}</option>' for k in groups)
page+='</select><select id="s" aria-label="Nguồn"><option value="">Tất cả nguồn</option>'+''.join(f'<option>{esc(k)}</option>' for k in sites)+'</select><span id="count"></span></nav><main>'+''.join(cards)+'''</main><footer><a href="quality_report.json">Báo cáo kiểm tra</a> · <a href="products.csv">Danh sách CSV</a> · <a href="catalog.json">Catalog JSON</a> · <a href="PROJECT_ANALYSIS.md">Phân tích dự án</a></footer><script>
const q=document.querySelector('#q'),g=document.querySelector('#g'),s=document.querySelector('#s'),cards=[...document.querySelectorAll('article')];function norm(x){return x.toLowerCase().normalize('NFD').replace(/[\u0300-\u036f]/g,'').replace(/đ/g,'d')}function filter(){let n=0;for(const c of cards){const ok=(!g.value||c.dataset.group===g.value)&&(!s.value||c.dataset.site===s.value)&&norm(c.textContent).includes(norm(q.value));c.hidden=!ok;if(ok)n++}document.querySelector('#count').textContent=n+' / 300 sản phẩm'}[q,g,s].forEach(e=>e.addEventListener('input',filter));filter();</script></html>'''
(R/'review.html').write_text(page,encoding='utf-8')
# Contact sheets contain originals resized only for visual inspection; not catalog assets.
(R/'review_sheets').mkdir(exist_ok=True)
try:font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',13)
except OSError:font=ImageFont.load_default()
for group in groups:
    products=[p for p in cat['products'] if by_ev[p['id']]['group']==group]
    for start in range(0,len(products),30):
        sheet=Image.new('RGB',(1200,1320),'white');draw=ImageDraw.Draw(sheet)
        for i,p in enumerate(products[start:start+30]):
            x=(i%5)*240;y=(i//5)*220
            if p['images']:
                with Image.open(R/p['images'][0]['local_path']) as im:
                    rgba=im.convert('RGBA'); bg=Image.new('RGBA',rgba.size,'white'); bg.alpha_composite(rgba)
                    thumb=ImageOps.contain(bg.convert('RGB'),(230,180));sheet.paste(thumb,(x+(230-thumb.width)//2,y))
            draw.text((x+5,y+184),p['id'].replace('p-tmp-','')[:32],fill='black',font=font)
            draw.text((x+5,y+202),p['name_vi'][:30],fill='black',font=font)
        sheet.save(R/'review_sheets'/f'{group}-{start//30+1}.jpg',quality=88)
lines=['# Kết quả kiểm tra bộ staging','',f"- Sản phẩm: **{quality['products']}**; schema/tham chiếu/file ảnh: **{'ĐẠT' if quality['passed'] else 'CHƯA ĐẠT'}**.",f"- Ảnh gallery local giải mã được: **{quality['local_gallery_images']}**; {quality['products_with_2_to_4_images']} sản phẩm có 2–4 ảnh; {quality['products_with_one_image']} có 1 ảnh.",f"- Chưa rõ giá: **{quality['products_without_price']}** sản phẩm; thiếu chất liệu: **{quality['products_without_materials']}**.",f"- Trùng URL/SKU với catalog gốc: **{quality['overlap_existing_urls']}/{quality['overlap_existing_skus']}**.",f"- Hash database.json chính giữ nguyên: **{quality['original_catalog_unchanged']}** tại lúc kiểm tra.",'','| Nhóm | Sản phẩm |','|---|---:|']+[f'| {cats[k]} | {v} |' for k,v in groups.items()]+['','## Giới hạn','', '300 draft, 0 được người duyệt; quyền tất cả ảnh là unknown. Không đủ điều kiện công bố. Nguồn là lời công bố của nhà sản xuất/thương hiệu, không phải chứng nhận độc lập. Không dùng bộ này thay ảnh query test.', '', 'Hạn ngạch đếm product record của website nguồn; các màu/size/hộp quà có thể cùng họ sản phẩm. Phải nhóm họ trước benchmark để tránh rò dữ liệu.', '', 'Giá của sản phẩm WooCommerce dạng variable giữ null nếu chưa có ánh xạ biến thể chính xác. Mã VNS-TMP là định danh nội bộ khi nguồn không có SKU.', '', 'Xem image_selection.json cho ảnh bị loại, shared_images.json cho trùng bytes và image_manifest.json cho tất cả lượt tải. Không tự suy nhãn góc chụp: view_type=other.', '', '## Lỗi', '']+(errors or ['Không có lỗi kỹ thuật.'])
(R/'QUALITY_REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(quality,ensure_ascii=False,indent=2))
if errors:raise SystemExit(1)
