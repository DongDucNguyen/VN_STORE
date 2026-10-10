"""Offline, deterministic staging builder. All writes confined to this directory."""
import copy, hashlib, html, json, re, unicodedata
from collections import Counter
from datetime import datetime, timezone, timedelta
from pathlib import Path
from inspect_text import plain
from inspect_sources import Tags

R=Path(__file__).resolve().parent
RAW=R/'raw'
def read(key): return json.loads((RAW/f'{key}.raw').read_text(encoding='utf-8'))
def meta(key): return json.loads((RAW/f'{key}.meta.json').read_text(encoding='utf-8'))
def save(name,obj):
    p=R/name; p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def clean(s): return unicodedata.normalize('NFC',html.unescape(re.sub(r'\s+',' ',s or '')).strip())
def slug(s):
    s=unicodedata.normalize('NFKD',s.lower().replace('đ','d'))
    return re.sub('[^a-z0-9]+','-', ''.join(c for c in s if not unicodedata.combining(c))).strip('-')
def money(n,div=1):
    try:
        from decimal import Decimal
        v=Decimal(str(n))/div
        return int(v) if v>0 and v==int(v) else None
    except Exception: return None
def around(s,pattern):
    m=re.search(pattern,s,re.I)
    return s[max(0,m.start()-70):min(m.end()+140,m.start()+270)] if m else None

baseline=json.loads((R/'baseline/database.before.json').read_text(encoding='utf-8'))
old_urls={s['url'].rstrip('/') for s in baseline['sources'] if s.get('url')}
old_skus={v['sku'] for p in baseline['products'] for v in p['variants']}
stamp=max(meta(p.stem)['retrieved_at'] for p in RAW.glob('*.raw'))
DAY=stamp[:10]
catalog={k:copy.deepcopy(baseline[k]) for k in ['schema_version','locale','currency','categories']}
catalog.update(catalog_version='tmp-2026-10-10-real-products-300',updated_at=stamp,brands=[],makers=[],places=[],sources=[],products=[],search_dictionary={'synonyms':[],'regional_terms':[],'brand_aliases':[],'unit_aliases':[]})
evidence=[]; rejected=[]; candidates=[]
SITE={
 'minhlong':('Minh Long','https://minhlong.com/','minhlong-about'),
 'hanoia':('Hanoia','https://hanoia.com/','hanoia-about'),
 'marou':('Marou','https://maisonmarou.com/','marou-about'),
 'hanhsilk':('Hanhsilk','https://hanhsilk.com/','hanhsilk-home'),
 'sensilk':('SenSilk','https://sensilk.vn/','sensilk-about'),
 'vietcraft':('Vietnam Handicraft Co., Ltd.','https://vietcraft.vn/','vietcraft-about'),
}
for site,(name,url,key) in SITE.items():
    m=meta(key); sid='src-tmp-'+key
    catalog['sources'].append({'id':sid,'url':m['url'],'publisher':name,'title':'Giới thiệu '+name,'source_type':'official_maker' if site=='vietcraft' else 'official_brand','retrieved_at':m['retrieved_at'],'archived_copy_path':f'raw/{key}.raw','supports':['identity'],'usage_rights_note':'Bằng chứng thông tin công khai; không cấp phép ảnh.'})
    if site!='vietcraft':
        catalog['brands'].append({'id':'brand-tmp-'+site,'name':name,'official_url':url,'origin_country':'VN' if site in ['minhlong','hanoia','sensilk'] else None,'origin_source_ids':[sid] if site in ['minhlong','hanoia','sensilk'] else [],'source_ids':[sid]})
    else:
        catalog['makers'].append({'id':'maker-tmp-vietcraft','name':name,'maker_type':'company','official_url':url,'source_ids':[sid]})

def new(site,key,rid,title,url,group,category):
    pid=f'p-tmp-{site}-{slug(str(rid))}'
    return {'id':pid,'site':site,'key':key,'source_record_id':rid,'name':clean(title),'url':url,'group':group,'category':category,'materials':[],'colors':[],'techniques':[],'dimensions':{},'claims':{},'claim_evidence':{},'images':[],'variants':[],'raw_record':None,'notes':[],'attribute_evidence':{}}
def claim(c,kind,detail,raw_evidence,site_scope=False):
    c['claims'][kind]={'detail':detail,'site_scope':site_scope}
    c['claim_evidence'][kind]=raw_evidence
def variant(c,sku,price,name='',available=None,original=None,attrs=None,source_variant_id=None):
    fallback=not sku
    if fallback: sku=f"VNS-TMP-{c['site'].upper()}-{c['source_record_id']}"+(f'-{source_variant_id}' if source_variant_id else '')
    c['variants'].append({'sku':str(sku),'name_vi':clean(name or c['name']),'attributes':attrs or {},'price_vnd':price,'original_price_vnd':original if original and price and original>price else None,'availability':'in_stock' if available is True else 'out_of_stock' if available is False else 'unknown','fallback_sku':fallback,'source_variant_id':source_variant_id})
    if fallback: c['notes'].append('SKU VNS-TMP là mã nội bộ staging do nguồn thiếu SKU, không phải mã nhà sản xuất.')

# Minh Long: product-level Haravan JSON; use actual vendor, not the store alone.
for path in sorted(RAW.glob('minhlong-detail-*.raw')):
    j=read(path.stem); title=clean(j['title']); low=title.lower()
    if not any(v.get('sku') for v in j.get('variants',[])):
        rejected.append({'url':meta(path.stem)['url'],'reason':'Record giới thiệu/thiếu SKU cụ thể; ưu tiên sản phẩm có SKU thật.'}); continue
    if j.get('vendor')!='Minh Long' or "lys" in low or 'nến thơm' in low:
        rejected.append({'url':meta(path.stem)['url'],'reason':'Khác thương hiệu xác minh hoặc ngoài nhóm gốm sứ ưu tiên.'}); continue
    cat='gom-su'
    if 'bình hoa' in low: cat='gom-su-binh-lo'
    elif any(x in low for x in ['bộ trà','ca trà','hủ đựng trà']): cat='gom-su-am-chen'
    elif any(x in low for x in ['chén','dĩa','tô ','đồ ăn']): cat='gom-su-bat-dia'
    c=new('minhlong',path.stem,j['id'],title,'https://minhlong.com'+j['url'],'gom-su',cat)
    c['raw_record']=j
    claim(c,'vn_brand','Thương hiệu Minh Long được giới thiệu là thương hiệu gốm sứ Việt Nam.','Minh Long thương hiệu gốm sứ hàng đầu Việt nam',True)
    s=plain(j.get('description'))
    if re.search(r'\bsứ\b',s,re.I): c['materials']=['sứ']; c['attribute_evidence']['materials']=around(s,r'\bsứ\b')
    if 'vẽ tay' in low: c['techniques']=['vẽ tay']; c['attribute_evidence']['craft_techniques']=title
    for v in j.get('variants',[]):
        opts={o['name']:v.get('option'+str(i+1)) for i,o in enumerate(j.get('options',[])) if v.get('option'+str(i+1))}
        variant(c,v.get('sku'),money(v.get('price'),100),v.get('title'),v.get('available'),money(v.get('compare_at_price'),100),opts,v.get('id'))
    c['images']=[{'url':u if u.startswith('http') else 'https:'+u,'source_variant_id':None} for u in j['images']]
    c['notes'].append('Giá Haravan .js chia 100; không dùng inventory_quantity làm tồn kho thời gian thực.')
    candidates.append(c)

# WooCommerce product data.
for site,keys in [('vietcraft',['vietcraft-products','vietcraft-page2']),('hanhsilk',['hanhsilk-products']),('sensilk',['sensilk-products'])]:
  for key in keys:
    for j in read(key):
        title=clean(j['name']); low=title.lower(); s=clean(plain(j.get('description','')+' '+j.get('short_description','')))
        if site=='vietcraft':
            categories=[clean(x['name']) for x in j['categories']]
            woven=bool(re.search('bamboo|rattan|seagrass|hyacinth|wicker|jute|macrame',low))
            if not woven: continue
            # Only explicit product/manufacturing language; supplier address is insufficient.
            pat=r'(?:made|handmade|handcrafted|handwoven|crafted|produced|manufactured)\s+in\s+Vietnam|Origin\s*:?\s*(?:Handmade\s+in\s+)?Vietnam|Vietnamese\s+(?:artisans|craftspeople)'
            ev=around(s,pat) or around(title,pat)
            if not ev:
                rejected.append({'url':j['permalink'],'reason':'Chưa có bằng chứng rõ về sản xuất tại Việt Nam cho sản phẩm.'}); continue
            cat='may-tre-coi-gio'
            if any(w in low for w in ['lampshade','light','table','bed','chair','pet house']): cat='may-tre-coi-noi-that'
            elif 'bag' in low: cat='may-tre-coi-tui'
            elif not any(w in low for w in ['basket','tray','box','bowl','dish','plate']):cat='may-tre-coi'
            c=new(site,key,j['id'],title,j['permalink'],'may-tre-coi',cat)
            claim(c,'made_in_vn','Nguồn sản phẩm công bố sản xuất/thực hiện thủ công tại Việt Nam.',ev)
            for en,vi in [('bamboo','tre'),('rattan','mây'),('seagrass','seagrass (theo nguồn)'),('water hyacinth','lục bình'),('jute','đay'),('coconut','gáo dừa'),('mother of pearl','xà cừ'),('ceramic','gốm')]:
                if en in low: c['materials'].append(vi)
            c['attribute_evidence']['materials']=title
            c['notes'].append('Nguồn là doanh nghiệp sản xuất và cung ứng; chưa xác định xưởng/làng nghề cụ thể. Seagrass không tự đổi thành cói. Giá 0 của API được chuyển thành null.')
            # Descriptive Vietnamese prefix, official name kept as alias/evidence.
            noun='Lồng bàn' if 'food tent' in low else 'Nhà cho thú cưng' if 'pet house' in low else 'Giỏ đan' if 'basket' in low else 'Chụp đèn' if 'lampshade' in low or 'light' in low else 'Khay' if 'tray' in low else 'Túi' if 'bag' in low else 'Bát' if 'bowl' in low else 'Hộp' if 'box' in low else 'Bình trang trí' if 'vase' in low else 'Gương trang trí' if 'mirror' in low else 'Bàn' if 'table' in low else 'Chậu' if 'pot' in low else 'Đĩa' if 'dish' in low or 'plate' in low else 'Đế lót cốc' if 'coaster' in low else 'Vật trang trí'
            c['name_vi']=f"{noun} {', '.join(c['materials'][:2])} — {j.get('sku') or 'Vietcraft '+str(j['id'])}"
        else:
            # Exclude bedding/art from clothing quota; no unrelated novelty merchandise.
            if not re.search('khăn|áo|váy|vải|lụa|cà vạt|jumpsuit|choàng',low) or re.search('chăn |gối|tranh |rèm',low): continue
            cat='det-may-khan' if 'khăn' in low else 'det-may-vai-lua' if low.startswith('vải') else 'det-may-thoi-trang'
            c=new(site,key,j['id'],title,j['permalink'],'det-may',cat)
            if site=='sensilk':
                claim(c,'vn_brand','Trang giới thiệu xác định SenSilk là thương hiệu khăn lụa thủ công tại Việt Nam.','SenSilk là thương hiệu khăn lụa tơ tằm thủ công cao cấp tại Việt Nam',True)
            else:
                ev=around(s,r'tơ tằm(?: tự nhiên)?(?: 100%)?(?: tự nhiên)? Việt Nam|lụa tơ tằm Việt Nam|lụa đũi tơ tằm Việt Nam|lụa đũi thủ công từ Hanhsilk|từ HTX lụa Đũi Nam Cao|dệt(?: thủ công)? tại Hợp tác xã Đũi Nam Cao|từ làng nghề Nam Cao')
                if ev:
                    claim(c,'vn_material','Nguồn sản phẩm nêu lụa/tơ tằm Việt Nam hoặc lụa đũi từ Nam Cao; chỉ áp dụng phần chất liệu lụa.',ev)
                else:
                    ev=around(s,r'nghệ nhân(?: của)? (?:làng dệt Đũi |đũi )Nam Cao|lụa đũi Nam Cao|nghệ nhân làng nghề Nam Cao')
                    if not ev or 'thủ công' not in s.lower(): continue
                    claim(c,'traditional_craft','Nguồn mô tả nghề thủ công của nghệ nhân/làng nghề Nam Cao cho sản phẩm; chưa kết luận quốc gia của mọi nguyên liệu.',ev)
            if re.search('tơ tằm|silk',low,re.I): c['materials']=['lụa tơ tằm']; c['attribute_evidence']['materials']=title
            for term in ['vẽ tay','thêu tay','dệt tay','thủy ấn']:
                if term in low: c['techniques'].append(term)
            if c['techniques']: c['attribute_evidence']['craft_techniques']=title
        c['raw_record']=j
        prices=j['prices']; div=10**prices.get('currency_minor_unit',0)
        price=money(prices.get('price'),div) if prices.get('currency_code')=='VND' else None
        if j['type']=='variable':
            # Listing minimum is not an identified variant price.
            price=None; c['notes'].append('Sản phẩm có biến thể; giá khoảng/min API chỉ giữ trong raw, chưa gán cho SKU cụ thể nên price_vnd=null.')
        variant(c,j.get('sku'),price,available=j.get('is_in_stock') if j['type']=='simple' else None,original=money(prices.get('regular_price'),div) if prices.get('currency_code')=='VND' else None)
        for im in j['images']:
            u=im['src']
            # Choose an exact official-host URL supplied by srcset, no invented rewrites.
            if site=='hanhsilk':
                entries=im.get('srcset','').split(', ')
                same=[entry.split(' ')[0] for entry in entries if entry.startswith('https://hanhsilk.com/') and '-300x' not in entry]
                if same: u=same[0]
            c['images'].append({'url':u,'source_variant_id':None})
        candidates.append(c)

# Marou: Shopify decimal VND prices; packaged chocolates only.
assert 'Shopify.currency = {"active":"VND"' in (RAW/'marou-home.raw').read_text(encoding='utf-8')
for j in read('marou-products')['products']:
    title=clean(j['title']); low=title.lower()
    if not re.search('bar|napolitain',low) or re.search('tote|masterclass|t-shirt|bag|baking set',low): continue
    c=new('marou','marou-products',j['id'],title,'https://maisonmarou.com/products/'+j['handle'],'thuc-pham','thuc-pham-banh-keo')
    c['name_vi']='Sô cô la Marou — '+title
    c['raw_record']=j
    claim(c,'vn_material','Marou công bố cacao dùng cho dòng chocolate bars được chọn từ sáu tỉnh miền Nam Việt Nam; không suy xuất xứ mọi phụ liệu.','MAROU CHOCOLATE BARS ARE MADE FROM CACAO BEANS CAREFULLY SELECTED FROM SIX PROVINCES IN SOUTHERN VIETNAM',True)
    c['notes'].append('Giá API Shopify products.json tính bằng VND theo cấu hình tiền tệ của trang chính. Tồn hàng API chỉ là ảnh chụp tại thời điểm thu, còn phụ thuộc địa điểm giao hàng.')
    for v in j['variants']:
        opts={o['name']:v.get('option'+str(i+1)) for i,o in enumerate(j.get('options',[])) if v.get('option'+str(i+1)) and v.get('option'+str(i+1))!='Default Title'}
        variant(c,v.get('sku'),money(v.get('price')),v['title'] if v['title']!='Default Title' else title,v.get('available'),money(v.get('compare_at_price')),opts,v.get('id'))
    for im in j['images']: c['images'].append({'url':im['src'],'source_variant_ids':im.get('variant_ids',[])})
    candidates.append(c)

# Hanoia JSON-LD and exact product attribute table; image gallery excludes recommendations.
for path in sorted(RAW.glob('hanoia-product-*.raw')):
    s=path.read_text(encoding='utf-8'); objects=[]
    for raw in re.findall(r'<script[^>]*type=[\"\x27]application/ld\+json[\"\x27][^>]*>(.*?)</script>',s,re.S):
        try: objects.append(json.loads(raw))
        except json.JSONDecodeError: pass
    j=next((o for o in objects if isinstance(o,dict) and o.get('@type')=='Product'),None)
    if not j: continue
    title=clean(j['name']); low=title.lower()
    if re.search('khăn|áo|váy|quần|túi|vòng|nhẫn|khuyên|bình giữ nhiệt|cài',low): continue
    cat='go-son-mai-binh-lo' if 'bình hoa' in low else 'go-son-mai'
    c=new('hanoia',path.stem,j['sku'],title,j['url'],'go-son-mai',cat); c['raw_record']=j
    if 'đan tre' in low:
        c['group']='may-tre-coi'; c['category']='may-tre-coi-gio'
    claim(c,'vn_brand','Trang câu chuyện thương hiệu ghi Hanoia ra đời tại Bình Dương, Việt Nam.','Hanoia ra đời năm 1997 tại tỉnh Bình Dương',True)
    tx=plain(s); product_text=tx.split('Mô tả sản phẩm',1)[-1].split('Có thể bạn quan tâm',1)[0]
    fields={}
    for field,nextfield in [('Chất liệu','Màu sắc'),('Màu sắc','Kích thước'),('Kích thước','Hướng dẫn bảo quản')]:
        m=re.search(re.escape(field)+r'\s+(.*?)\s+'+re.escape(nextfield),product_text,re.S)
        if m: fields[field]=clean(m.group(1))
    if fields.get('Chất liệu'): c['materials']=[x.strip() for x in fields['Chất liệu'].split(',') if x.strip()]
    if fields.get('Màu sắc'): c['colors']=[x.strip() for x in fields['Màu sắc'].split(',') if x.strip()]
    c['attribute_evidence']=fields
    size=fields.get('Kích thước',''); nums=re.findall(r'(\d+(?:[.,]\d+)?)\s*mm',size)
    if len(nums)==3:
        c['dimensions']={k:float(v.replace(',','.')) for k,v in zip(['length_mm','width_mm','height_mm'],nums)}
    elif len(nums)==2 and 'Đường kính' in size:
        c['dimensions']={'diameter_mm':float(nums[0].replace(',','.')),'height_mm':float(nums[1].replace(',','.'))}
    # Do not promote 'lacquer' / black paint to traditional son mai.
    if 'sơn mài' in product_text.lower(): c['techniques']=['sơn mài']; c['attribute_evidence']['craft_techniques']=around(product_text,'sơn mài')
    offers=j.get('offers',[]); offers=offers if isinstance(offers,list) else [offers]
    for offer in offers:
        if not offer: continue
        variant(c,offer.get('sku') or j.get('sku'),money(offer.get('price')) if offer.get('priceCurrency')=='VND' else None,available=None)
    tags=Tags(s).tags
    for t,a in tags:
        if t=='img' and 'gallery-placeholder__image' in a.get('class','') and a.get('data-original'):
            c['images'].append({'url':a['data-original'],'source_variant_id':None})
    # Only gallery JSON objects, never arbitrary images from the page.
    for raw in re.findall(r'<script[^>]*type=[\"\x27]text/x-magento-init[\"\x27][^>]*>(.*?)</script>',s,re.S):
        try: obj=json.loads(raw)
        except json.JSONDecodeError: continue
        def walk(x):
            if isinstance(x,dict):
                for k,v in x.items():
                    if 'gallery/gallery' in k and isinstance(v,dict):
                        for im in v.get('data',[]):
                            if isinstance(im,dict) and im.get('full'): c['images'].append({'url':im['full'],'source_variant_id':None})
                    walk(v)
            elif isinstance(x,list):
                for v in x: walk(v)
        walk(obj)
    if not c['images'] and j.get('image'): c['images']=[{'url':j['image'],'source_variant_id':None}]
    c['notes'].append('Giá theo JSON-LD VND, chưa tách SKU màu nếu nguồn chỉ có SKU cha; màu được giữ như danh sách nguồn. Không suy nơi sản xuất từ thương hiệu.')
    candidates.append(c)

# Select by quota, source diversity, deterministic ID/URL/SKU dedup.
seen_ids=set(); seen_urls=set(old_urls); seen_skus=set(old_skus); counts=Counter(); site_counts=Counter(); selected=[]
def priority(c):
    # Prefer informative ceramic names and nonseasonal packaged food.
    if c['site']=='minhlong': return (0 if c['category']!='gom-su' else 1,c['id'])
    if c['site']=='marou': return (1 if 'halloween' in c['name'].lower() else 0,c['id'])
    return (0,c['id'])
for c in sorted(candidates,key=priority):
    if c['group']=='det-may' and site_counts[c['site']]>=30: continue
    if counts[c['group']]>=60: continue
    skus=[v['sku'] for v in c['variants']]
    reason=None
    if c['id'] in seen_ids or c['url'].rstrip('/') in seen_urls: reason='Trùng ID/URL với catalog cũ hoặc ứng viên đã chọn.'
    elif len(skus)!=len(set(skus)) or any(x in seen_skus for x in skus):reason='Trùng SKU thật với catalog cũ/ứng viên; không tự sửa SKU.'
    elif not c['variants'] or not c['images'] or not c['claims']: reason='Thiếu biến thể/ảnh/bằng chứng tiêu chí Việt.'
    if reason: rejected.append({'url':c['url'],'reason':reason}); continue
    selected.append(c); counts[c['group']]+=1; site_counts[c['site']]+=1
    seen_ids.add(c['id']);seen_urls.add(c['url'].rstrip('/'));seen_skus.update(skus)

for c in selected:
    site=c['site']; name=SITE[site][0]; pid=c['id']; psrc='src-'+pid; ss='src-tmp-'+SITE[site][2]; m=meta(c['key'])
    rawpath=f"records/{pid}.json"; save(rawpath,c['raw_record'])
    catalog['sources'].append({'id':psrc,'url':c['url'],'publisher':name,'title':c['name'],'source_type':'official_maker' if site=='vietcraft' else 'official_brand','retrieved_at':m['retrieved_at'],'archived_copy_path':rawpath,'supports':['name','variants','images']+(['price'] if any(v['price_vnd'] for v in c['variants']) else [])+(['materials'] if c['materials'] else []),'usage_rights_note':'Dữ liệu công khai từ website nguồn; quyền tái sử dụng ảnh chưa xác định.'})
    title=c.get('name_vi',c['name']); claims=[]
    for kind in ['vn_brand','made_in_vn','vn_material','traditional_craft','craft_village']:
        spec=c['claims'].get(kind)
        claims.append({'claim_type':kind,'value':True if spec else 'unknown','status':'manufacturer_declared' if spec else 'unverified','source_ids':([ss] if spec['site_scope'] else [psrc]) if spec else [],'checked_at':m['retrieved_at'][:10] if spec else None,**({'detail_vi':spec['detail']} if spec else {})})
    variants=[]
    for v in c['variants']:
        out={k:v[k] for k in ['sku','name_vi','attributes','price_vnd','original_price_vnd','availability']}
        out.update(price_source_id=psrc if v['price_vnd'] else None,observed_at=m['retrieved_at'][:10] if v['price_vnd'] else None)
        variants.append(out)
    images=[]; urls=set()
    for im in c['images']:
        u=im['url']
        if not u.startswith('https://') or u in urls: continue
        urls.add(u)
        if len(images)>=4: break
        iid=f"img-{pid.removeprefix('p-')}-{len(images)+1}"
        vids=im.get('source_variant_ids',[])
        match=[v['sku'] for v in c['variants'] if v['source_variant_id'] in vids]
        images.append({'id':iid,'local_path':None,'source_url':u,'alt_vi':title+' — ảnh nguồn '+str(len(images)+1),'view_type':'other','variant_sku':match[0] if len(match)==1 else None,'sha256':None,'width':None,'height':None,'usage_rights':{'status':'unknown','source_id':psrc,'note':'Ảnh gốc của website nguồn, chưa có bằng chứng cho phép tái sử dụng; chỉ phục vụ staging/review.'}})
    desc=title+'.'
    if c['materials']: desc+=' Chất liệu theo nguồn: '+', '.join(c['materials'])+'.'
    desc=desc[:399]
    p={'id':pid,'slug':pid.removeprefix('p-'),'name_vi':title,'status':'draft','category_id':c['category'],'brand_id':'brand-tmp-'+site if site!='vietcraft' else None,'maker_id':'maker-tmp-vietcraft' if site=='vietcraft' else None,'short_description_vi':desc,'description_vi':desc,'aliases':[c['name']] if title!=c['name'] else [],'tags':[],'intended_uses':[],'materials':c['materials'],'colors':c['colors'],'dimensions':{**c['dimensions'],**({'source_ids':[psrc]} if c['dimensions'] else {})},'craft_techniques':c['techniques'],'motifs':[],'variants':variants,'origin':{'brand_origin_country':'VN' if 'vn_brand' in c['claims'] else None,'manufacturing_country':'VN' if 'made_in_vn' in c['claims'] else None,'material_origins':[],'place_ids':[],'craft_village_id':None},'origin_claims':claims,'certifications':[],'images':images,'source_ids':[psrc,ss],'created_at':m['retrieved_at'],'updated_at':m['retrieved_at'],'reviewed_at':None,'editor_note':' '.join(dict.fromkeys(c['notes']))+' Chưa được con người duyệt; không tự công bố.'}
    if 'vn_material' in c['claims']:
        p['origin']['material_origins']=[{'material':'cacao' if site=='marou' else 'lụa tơ tằm','country':'VN','place_ids':[],'source_ids':[ss if c['claims']['vn_material']['site_scope'] else psrc]}]
    catalog['products'].append(p)
    evidence.append({k:c[k] for k in ['id','site','key','source_record_id','name','url','group','claim_evidence','attribute_evidence','notes']}|{'raw_path':rawpath,'response_path':f"raw/{c['key']}.raw",'response_sha256':m['sha256'],'retrieved_at':m['retrieved_at'],'original_variants':c['variants'],'review_status':'pending_human_review'})
sources_by_id={s['id']:s for s in catalog['sources']}
for p in catalog['products']:
    for cl in p['origin_claims']:
        if cl['value'] is True:
            for sid in cl['source_ids']:
                if cl['claim_type'] not in sources_by_id[sid]['supports']:sources_by_id[sid]['supports'].append(cl['claim_type'])
    own=sources_by_id['src-'+p['id']]['supports']
    for field in ['dimensions','colors','craft_techniques']:
        if p[field] and field not in own: own.append(field)
save('catalog.json',catalog);save('product_evidence.json',evidence);save('excluded.json',rejected)
save('selection_summary.json',{'products':len(selected),'groups':dict(counts),'sites':dict(site_counts),'candidate_records':len(candidates),'excluded_records':len(rejected),'target':300,'quota_per_group':60})
print(json.dumps({'products':len(selected),'groups':dict(counts),'sites':dict(site_counts)},ensure_ascii=False))
