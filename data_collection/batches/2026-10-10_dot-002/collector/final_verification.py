"""Independent checks against archived vendor payloads; writes only tmp_data."""
import hashlib,html,json,re
from collections import Counter
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit,unquote
from inspect_sources import Tags
R=Path(__file__).resolve().parent
def load(name):return json.loads((R/name).read_text(encoding='utf-8'))
def normalized_url(u):
    s=urlsplit(u);return s.netloc.casefold()+unquote(s.path).rstrip('/')
cat=load('catalog.json');ev={x['id']:x for x in load('product_evidence.json')}; failures=[]; checks=Counter()
def check(ok,label,detail):
    checks[label]+=1
    if not ok:failures.append({'check':label,'detail':detail})
pages={x['product_id']:x for x in load('source_page_checks.json')}
for p in cat['products']:
    e=ev[p['id']];raw=load(e['raw_path']);response=(R/e['response_path']).read_text(encoding='utf-8');site=e['site']
    if site=='hanoia':
        rs=[]
        for fragment in re.findall(r'<script[^>]*type=[\"\x27]application/ld\+json[\"\x27][^>]*>(.*?)</script>',response,re.S):
            try:rs.append(json.loads(fragment))
            except json.JSONDecodeError:pass
        check(raw in rs,'archived_record_matches_response',p['id'])
        offers=raw['offers'] if isinstance(raw['offers'],list) else [raw['offers']]
        source_variants=offers
    else:
        parsed=json.loads(response)
        records=parsed.get('products',[parsed]) if isinstance(parsed,dict) else parsed
        check(raw in records,'archived_record_matches_response',p['id'])
        source_variants=raw.get('variants',[raw])
    for v in p['variants']:
        if site in ['minhlong','marou']:
            s=next((x for x in source_variants if x.get('sku')==v['sku']),None)
            if s is None and v['sku'].startswith('VNS-TMP'):s=source_variants[0]
            check(s is not None,'variant_found',v['sku'])
            price=Decimal(str(s['price']))/(100 if site=='minhlong' else 1) if s else 0
            expected=int(price) if price>0 else None
        elif site=='hanoia':
            offer=source_variants[0];expected=int(Decimal(str(offer['price']))) if offer['priceCurrency']=='VND' else None
        else:
            prices=raw['prices'];amount=Decimal(prices['price'])/(10**prices['currency_minor_unit'])
            expected=int(amount) if prices['currency_code']=='VND' and amount>0 and raw['type']=='simple' else None
        check(v['price_vnd']==expected,'price_matches_vendor_units',v['sku'])
        if not v['sku'].startswith('VNS-TMP'):check(any(x.get('sku')==v['sku'] for x in source_variants),'source_sku_preserved',v['sku'])
    for im in p['images']:
        decoded=html.unescape(response.replace('\\/','/'))
        check(im['source_url'] in decoded,'image_url_in_source_response',im['id'])
    page=pages.get(p['id'])
    check(page is not None and page.get('status')==200,'product_page_http_200',p['id'])
    if page and page.get('status')==200:
        check(normalized_url(page['final_url'])==normalized_url(e['url']),'product_page_redirect',p['id'])
        if page.get('canonical_url'):check(normalized_url(page['canonical_url'])==normalized_url(e['url']),'canonical_product_url',p['id'])
        check(hashlib.sha256((R/page['path']).read_bytes()).hexdigest()==page['sha256'],'product_page_hash',p['id'])
        check(page['source_name_found'],'source_name_on_product_page',p['id'])
# review.html references only real local artifacts; no external image or script dependencies.
review=(R/'review.html').read_text(encoding='utf-8');tags=Tags(review).tags
for tag,attrs in tags:
    for key in ['src','href']:
        target=attrs.get(key)
        if not target or target.startswith(('https://','http://','#')):continue
        path=(R/target).resolve()
        check(R in path.parents and path.is_file(),'review_local_link',target)
    if tag in ['img','script'] and attrs.get('src'):
        check(not attrs['src'].startswith(('http:','https:','//')),'review_offline_assets',attrs['src'])
check(sum(t=='article' for t,a in tags)==300,'review_300_cards','review.html')
check(len(cat['products'])==300 and all(n==60 for n in Counter(e['group'] for e in ev.values()).values()),'five_groups_60_each','catalog')
report={'passed':not failures,'checks':dict(checks),'total_checks':sum(checks.values()),'failures':failures,'scope':'Independent payload → record/SKU/price/image checks; 300 live pages; static review link integrity. Not human editorial approval or a browser rendering test.'}
(R/'final_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
if failures:raise SystemExit(1)
