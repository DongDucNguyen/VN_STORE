"""Extend the local exploratory image set. All writes stay in tmp_data.
Use -B. Does not run application models or modify the catalog.
"""
import argparse
import hashlib
import html
import io
import json
from pathlib import Path
import sys
import time
import urllib.parse

from PIL import Image
from collect_images import BASE, ROOT, get, now, plain, save, target

BATCH = 'expansion-2026-10-13'
SEARCHES = [
    ('gom-su', 'bowl', 'ceramic bowl'),
    ('gom-su', 'plate', 'porcelain plate'),
    ('gom-su', 'mug', 'ceramic mug'),
    ('det-may', 'ao-dai', 'ao dai mannequin'),
    ('det-may', 'shirt', 'linen shirt'),
    ('det-may', 'dress', 'silk dress mannequin'),
    ('may-tre-coi', 'lamp', 'rattan lamp'),
    ('may-tre-coi', 'chair', 'rattan chair'),
    ('may-tre-coi', 'bag', 'straw handbag'),
    ('go-son-mai', 'lacquer-box', 'lacquer box'),
    ('go-son-mai', 'wooden-box', 'wooden box modern'),
    ('thuc-pham', 'chocolate', 'chocolate bar wrapper'),
    ('thuc-pham', 'vietnam-label', 'Vietnam candy packaging'),
    ('thuc-pham', 'vietnam-cake', 'banh dau xanh'),
    ('hard-negative', 'glass-mug', 'glass mug'),
    ('hard-negative', 'plastic-basket', 'plastic basket'),
    ('hard-negative', 'leather-bag', 'leather handbag'),
    ('det-may', 'ao-dai-street', '"ao dai" -museum'),
    ('det-may', 'shirt-modern', '"shirt" -DPLA -Museum -MET -drawing -engraving'),
    ('may-tre-coi', 'woven-bag', '"woven bag"'),
    ('may-tre-coi', 'bamboo-lamp', '"bamboo" "lamp"'),
    ('gom-su', 'dinner-plate', '"dinner plate"'),
    ('go-son-mai', 'wood-box-simple', '"wooden box" -Wellcome -NGA -ushabti'),
    ('thuc-pham', 'vn-banh-com', '"banh com"'),
    ('thuc-pham', 'vn-keo-dua', '"kẹo dừa"'),
    ('may-tre-coi', 'wicker-lampshade', 'wicker lampshade'),
    ('may-tre-coi', 'straw-bag', '"straw bag" -DPLA'),
    ('go-son-mai', 'jewellery-box', '"wooden" "jewellery box"'),
]


def load(rel):
    return json.loads((BASE / rel).read_text(encoding='utf-8'))


def discover():
    all_candidates = {}
    errors = []
    for group, topic, query in SEARCHES:
        cache_hit = False
        rel = f'{BATCH}/evidence/{topic}.json'
        params = dict(action='query', format='json', generator='search',
            gsrsearch=query + ' filetype:bitmap', gsrnamespace=6, gsrlimit=8,
            prop='imageinfo', iiprop='url|size|mime|extmetadata', iiurlwidth=1280)
        url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params)
        try:
            if (BASE / rel).exists():
                payload = load(rel)['response']
                cache_hit = True
            else:
                raw, final_url, _ = get(url)
                payload = json.loads(raw)
                if 'error' in payload:
                    raise ValueError(payload['error'])
                save(rel, {'requested_url': url, 'final_url': final_url, 'retrieved_at': now(), 'response': payload})
            for page in sorted(payload.get('query', {}).get('pages', {}).values(), key=lambda x: x.get('index', 0)):
                if not page.get('imageinfo'):
                    continue
                info = page['imageinfo'][0]
                if info.get('mime') not in ('image/jpeg','image/png','image/webp'):
                    continue
                key = f'add-{page["pageid"]}'
                row = {'id':key,'pageid':page['pageid'],'title':page['title'],'group':group,'topic':topic,
                       'query':query,'info':info,'evidence_path':rel}
                if key not in all_candidates:
                    all_candidates[key] = row
                    print(key, topic, page['title'], flush=True)
        except Exception as exc:
            errors.append({'topic':topic,'url':url,'error':str(exc)})
            print('SEARCH FAILED',topic,str(exc),flush=True)
        save(f'{BATCH}/candidates.json', list(all_candidates.values()))
        save(f'{BATCH}/search_errors.json', errors)
        time.sleep(0.02 if cache_hit else 3)


def fetch():
    candidates = {x['id']:x for x in load(f'{BATCH}/candidates.json')}
    selection = load(f'{BATCH}/selection.json')
    existing = {x['id']:x for x in load(f'{BATCH}/downloads.json')['images']} if (BASE / BATCH / 'downloads.json').exists() else {}
    rows, errors = [], []
    for selected in selection['selected']:
        key = selected['id']
        if key in existing:
            row = existing[key]
            p = (BASE / row['image_path']).resolve()
            assert p.is_relative_to(BASE) and hashlib.sha256(p.read_bytes()).hexdigest() == row['sha256']
            rows.append(row)
            continue
        try:
            c = candidates[key]
            info = c['info']; meta = info.get('extmetadata',{})
            url = info.get('thumburl', info['url'])
            raw, final, content_type = get(url)
            with Image.open(io.BytesIO(raw)) as im:
                im.verify()
            with Image.open(io.BytesIO(raw)) as im:
                im.load(); fmt, w, h = im.format, im.width, im.height
            if fmt not in ('JPEG','PNG','WEBP') or min(w,h)<32 or w*h>40_000_000:
                raise ValueError(f'Unsupported {fmt}, {w}x{h}')
            ext = {'JPEG':'jpg','PNG':'png','WEBP':'webp'}[fmt]
            path = f'images/additions/{c["topic"]}/{key}.{ext}'
            dest = target(path)
            if dest.exists() and dest.read_bytes()!=raw:
                raise ValueError('Refusing to overwrite changed file')
            if not dest.exists(): dest.write_bytes(raw)
            row = dict(id=key, group=c['group'], topic=c['topic'], title=c['title'],
                role=selected.get('role','similar_candidate'), test_intent_vi=selected.get('intent_vi',''),
                source_page_url=info['descriptionurl'], source_image_url=info['url'], download_url=url,
                final_download_url=final, http_content_type=content_type, retrieved_at=now(),
                source_asset_id=f'commons:{c["pageid"]}', source_evidence_path=c['evidence_path'],
                usage_rights={'status':'source_declared','license':plain(meta.get('LicenseShortName',{}).get('value','unknown')),
                    'license_url':plain(meta.get('LicenseUrl',{}).get('value','')),
                    'author':plain(meta.get('Artist',{}).get('value','')),
                    'credit':plain(meta.get('Credit',{}).get('value','')),'evidence':info['descriptionurl']},
                source_description=plain(meta.get('ImageDescription',{}).get('value','')),
                image_path=path,sha256=hashlib.sha256(raw).hexdigest(),downloaded_asset_sha256=hashlib.sha256(raw).hexdigest(),
                full_resolution_source_sha256=None, hash_scope='downloaded rendition bytes',
                format=fmt,width=w,height=h,bytes=len(raw),transformations='none',
                expected_product_id=None,judgment=None,independence_review=None,split=None)
            rows.append(row)
            print('OK',key,c['topic'],len(raw),flush=True)
        except Exception as exc:
            errors.append({'id':key,'error':str(exc),'at':now()})
            print('FAILED',key,str(exc),flush=True)
        # Keep already known rows during interrupted resume; selection governs final output.
        pending = [v for k,v in existing.items() if k not in {r['id'] for r in rows}]
        save(f'{BATCH}/downloads.json',{'images':rows+pending,'errors':errors})
        time.sleep(0.4)
    save(f'{BATCH}/downloads.json',{'images':rows,'errors':errors})
    print('Additional downloads:',len(rows),'errors:',len(errors),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['discover','fetch'])
    {'discover':discover,'fetch':fetch}[parser.parse_args().action]()
