"""Local test assets only. Every write is confined to this script's directory.

Run with Python -B to prevent bytecode outside tmp_data. No app startup/model load.
"""
import argparse
import collections
import hashlib
import html
import io
import json
import os
from pathlib import Path
import re
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

from PIL import Image, ImageOps, ImageDraw

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
UA = 'VNStore-local-image-test/1.0 (manual research; small image sample)'
QUERIES = {
    'gom-su': ['ceramic teapot', 'porcelain vase'],
    'may-tre-coi': ['wicker basket', 'woven bamboo basket'],
    'det-may': ['silk scarf', 'Vietnam conical hat'],
    'go-son-mai': ['Vietnam lacquerware', 'wooden decorative box'],
    'thuc-pham': ['chocolate bar packaging', 'coffee package'],
    'ngoai-catalog': ['laptop computer', 'bicycle parked', 'football ball'],
}


def now():
    return datetime.now(timezone.utc).isoformat()


def target(rel):
    path = (BASE / rel).resolve()
    if not path.is_relative_to(BASE) or path == BASE:
        raise ValueError('Write outside tmp_data refused')
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def save(rel, data):
    target(rel).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def get(url, max_bytes=8 * 1024 * 1024):
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=35) as response:
                data = response.read(max_bytes + 1)
                if len(data) > max_bytes:
                    raise ValueError('Response too large')
                return data, response.geturl(), response.headers.get('Content-Type')
        except Exception:
            if attempt == 2:
                raise
            time.sleep(5 * (attempt + 1))


def catalog():
    return json.loads((ROOT / 'database.json').read_text(encoding='utf-8'))


def snapshot():
    # Inspect metadata for every regular file outside tmp_data. Hash project
    # source/docs/data; avoid hashing multi-GB models and installed dependencies.
    result = {}
    excluded_hash = {'.git', '.venv', '.venv-ml', '.pytest_cache', 'node_modules', 'artifacts'}
    for folder, dirs, files in os.walk(ROOT, followlinks=False):
        dirs[:] = [d for d in dirs if not (Path(folder) / d).is_symlink()
                   and (Path(folder) / d).resolve() != BASE]
        for name in files:
            path = Path(folder) / name
            if path.is_symlink():
                continue
            rel = path.relative_to(ROOT)
            s = path.stat()
            item = {'size': s.st_size, 'mtime_ns': s.st_mtime_ns}
            if not (set(rel.parts) & excluded_hash):
                item['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
            result[rel.as_posix()] = item
    return result


def baseline():
    if (BASE / 'checks/outside_before.json').exists():
        raise ValueError('Baseline already exists; preserving it')
    data = snapshot()
    save('checks/outside_before.json', data)
    print('Outside baseline:', len(data), 'files;', sum('sha256' in x for x in data.values()), 'hashed', flush=True)


def discover():
    output = []
    for group, searches in QUERIES.items():
        for query in searches:
            params = dict(action='query', format='json', generator='search',
                          gsrsearch=query + ' filetype:bitmap', gsrnamespace=6,
                          gsrlimit=6, prop='imageinfo', iiprop='url|size|mime|extmetadata', iiurlwidth=1280)
            url = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode(params)
            cached = None
            for path in (BASE / 'evidence').glob('search-*.json'):
                saved = json.loads(path.read_text(encoding='utf-8'))
                if saved.get('requested_url') == url:
                    cached = saved['response']
                    break
            if cached is None:
                raw, _, _ = get(url)
                response = json.loads(raw)
            else:
                response = cached
            save(f'evidence/search-{len(output):02}.json', {'requested_url': url, 'retrieved_at': now(), 'response': response})
            for page in sorted(response.get('query', {}).get('pages', {}).values(), key=lambda p: p.get('index', 0)):
                if not page.get('imageinfo'):
                    continue
                info = page['imageinfo'][0]
                if info.get('mime') not in ('image/jpeg', 'image/png', 'image/webp'):
                    continue
                row = {'candidate_id': len(output), 'group': group, 'query': query,
                       'title': page['title'], 'pageid': page['pageid'], 'info': info}
                output.append(row)
                print(row['candidate_id'], group, page['title'], info.get('size'),
                      info.get('extmetadata', {}).get('LicenseShortName', {}).get('value'), flush=True)
            save('candidates.json', output)
            time.sleep(3)
    save('candidates.json', output)


def plain(value):
    return html.unescape(re.sub('<[^>]+>', '', str(value)))


def fetch():
    candidates = json.loads((BASE / 'candidates.json').read_text(encoding='utf-8'))
    selections = json.loads((BASE / 'selection.json').read_text(encoding='utf-8'))
    d = catalog()
    sources = {s['id']: s for s in d['sources']}
    downloads = []
    for cid in selections['commons_candidate_ids']:
        c = next(c for c in candidates if c['candidate_id'] == cid)
        info = c['info']
        meta = info.get('extmetadata', {})
        downloads.append(dict(id=f'web-{cid:03}', group=c['group'], title=c['title'],
            role='negative_candidate' if c['group'] == 'ngoai-catalog' else 'similar_candidate',
            source_page_url=info['descriptionurl'], source_image_url=info['url'],
            download_url=info.get('thumburl', info['url']), source_asset_id=f'commons:{c["pageid"]}',
            usage_rights={'status': 'source_declared', 'license': plain(meta.get('LicenseShortName', {}).get('value', 'unknown')),
                          'license_url': plain(meta.get('LicenseUrl', {}).get('value', '')),
                          'author': plain(meta.get('Artist', {}).get('value', '')),
                          'credit': plain(meta.get('Credit', {}).get('value', '')),
                          'evidence': info['descriptionurl']},
            source_description=plain(meta.get('ImageDescription', {}).get('value', '')),
            expected_product_id=None, judgment=None, independence_review=None, split=None))
    for pid in selections['catalog_product_ids']:
        p = next(p for p in d['products'] if p['id'] == pid)
        im = p['images'][0]
        group = p['category_id']
        parents = {c['id']: c.get('parent_id') for c in d['categories']}
        while parents[group]:
            group = parents[group]
        downloads.append(dict(id=f'control-{len(downloads):03}', group=group, title=p['name_vi'],
            role='gallery_control', source_page_url=sources[p['source_ids'][0]]['url'],
            source_image_url=im['source_url'], download_url=im['source_url'], source_asset_id=im['id'],
            usage_rights=im['usage_rights'], expected_product_id=pid,
            judgment=None, independence_review={'independent': False, 'reason': 'Catalog source image; smoke control only'}, split=None))
    existing = {}
    if (BASE / 'manifest.json').exists():
        existing = {x['id']: x for x in json.loads((BASE / 'manifest.json').read_text(encoding='utf-8'))['images']}
    wanted = {row['id'] for row in downloads}
    for key, row in existing.items():
        if key not in wanted:
            source = (BASE / row['image_path']).resolve()
            destination = target('excluded/' + source.name)
            if not source.is_relative_to(BASE) or not destination.is_relative_to(BASE):
                raise ValueError('Move outside tmp_data refused')
            if destination.exists():
                raise ValueError('Refusing to overwrite excluded asset')
            source.rename(destination)
            row['excluded_path'] = destination.relative_to(BASE).as_posix()
            row['reason'] = selections.get('excluded_reasons', {}).get(key, 'Deselected')
            save('evidence/excluded-' + key + '.json', row)
    images, errors = [], []
    for row in downloads:
        try:
            old = existing.get(row['id'])
            if old and (BASE / old['image_path']).exists():
                data = (BASE / old['image_path']).read_bytes()
                if hashlib.sha256(data).hexdigest() != old['sha256']:
                    raise ValueError('Existing file checksum mismatch')
                images.append(old)
                continue
            data, final, mime = get(row['download_url'])
            with Image.open(io.BytesIO(data)) as im:
                im.verify()
            with Image.open(io.BytesIO(data)) as im:
                im.load()
                fmt, size = im.format, im.size
            if fmt not in {'JPEG', 'PNG', 'WEBP'} or min(size) < 32 or size[0] * size[1] > 40_000_000:
                raise ValueError(f'Unsupported image: {fmt} {size}')
            ext = {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp'}[fmt]
            rel = f'images/{row["role"]}/{row["group"]}/{row["id"]}.{ext}'
            dest = target(rel)
            if dest.exists():
                if dest.read_bytes() != data:
                    raise ValueError('Refusing untracked file overwrite')
            else:
                dest.write_bytes(data)
            row.update(image_path=rel, sha256=hashlib.sha256(data).hexdigest(),
                       downloaded_asset_sha256=hashlib.sha256(data).hexdigest(),
                       full_resolution_source_sha256=hashlib.sha256(data).hexdigest() if row['role'] == 'gallery_control' else None,
                       hash_scope='downloaded rendition bytes; original full-resolution bytes not necessarily fetched',
                       retrieved_at=now(), final_download_url=final, http_content_type=mime,
                       format=fmt, width=size[0], height=size[1], bytes=len(data), transformations='none')
            images.append(row)
            print('OK', row['id'], row['group'], len(data), flush=True)
        except Exception as exc:
            errors.append({'id': row['id'], 'url': row['download_url'], 'error': str(exc), 'at': now()})
            print('FAILED', row['id'], str(exc), flush=True)
        save('manifest.json', {'schema': 'vnstore-tmp-image-test-1', 'created_for': 'manual smoke/exploratory search only',
             'catalog_version': d['catalog_version'], 'catalog_sha256': hashlib.sha256((ROOT / 'database.json').read_bytes()).hexdigest(),
             'benchmark_approved': False, 'images': images, 'download_errors': errors})
        time.sleep(0.15)
    save('manifest.json', {'schema': 'vnstore-tmp-image-test-1', 'created_for': 'manual smoke/exploratory search only',
         'catalog_version': d['catalog_version'], 'catalog_sha256': hashlib.sha256((ROOT / 'database.json').read_bytes()).hexdigest(),
         'benchmark_approved': False, 'images': images, 'download_errors': errors})
    print('Downloaded', len(images), 'errors', len(errors), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['baseline', 'discover', 'fetch'])
    action = parser.parse_args().action
    if (BASE / 'manifest.json').exists() and json.loads((BASE / 'manifest.json').read_text(encoding='utf-8')).get('schema') != 'vnstore-tmp-image-test-1':
        raise SystemExit('Legacy collector is frozen after expansion. Use expand_dataset.py; this command made no changes.')
    {'baseline': baseline, 'discover': discover, 'fetch': fetch}[action]()


if __name__ == '__main__':
    main()
