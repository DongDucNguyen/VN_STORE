"""Read-only audit of inputs; reports confined to tmp_data/audit-2026-10-13.
Run with Python -B. Never starts the app, builds an index or changes labels.
"""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import urllib.request
import urllib.error

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parent
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(ROOT / 'backend'))
from collect_images import snapshot
from verify_and_preview import rgb_on_white
from app.media import inspect_image
from PIL import Image


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def save(name, value):
    path = (HERE / name).resolve()
    if not path.is_relative_to(HERE):
        raise ValueError('Output outside audit directory')
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def stamp():
    return datetime.now(timezone.utc).isoformat()


def local():
    m = load(BASE / 'manifest.json')
    c = load(ROOT / 'database.json')
    cases = load(BASE / 'test_cases.json')['cases']
    candidates = {f'web-{x["candidate_id"]:03}': x for x in load(BASE / 'candidates.json')}
    products = {p['id']: p for p in c['products']}
    gallery = defaultdict(list)
    for p in c['products']:
        for im in p['images']:
            path = (ROOT / im['local_path']).resolve()
            assert path.is_relative_to(ROOT)
            gallery[digest(path.read_bytes())].append({'product_id': p['id'], 'image_id': im['id']})
    inventory = []
    for path in sorted(BASE.rglob('*')):
        if path.is_file() and path.suffix.lower() in {'.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp', '.tiff', '.tif', '.avif', '.svg'}:
            raw = path.read_bytes()
            with Image.open(io.BytesIO(raw)) as im:
                im.verify()
            with Image.open(io.BytesIO(raw)) as im:
                im.load()
                inventory.append({'path': path.relative_to(BASE).as_posix(), 'format': im.format,
                    'width': im.width, 'height': im.height, 'bytes': len(raw), 'sha256': digest(raw)})
    records = []
    pixels, byte_hashes = defaultdict(list), defaultdict(list)
    for row in m['images']:
        path = (BASE / row['image_path']).resolve()
        assert path.is_relative_to(BASE)
        raw = path.read_bytes()
        info = inspect_image(raw)
        with Image.open(io.BytesIO(raw)) as im:
            im.load()
            rgb = rgb_on_white(im)
            ph = digest(f'{rgb.size}:'.encode() + rgb.tobytes())
            pixel_size = im.size
            fmt, mode = im.format, im.mode
        sha = digest(raw)
        assert sha == row['sha256'] and len(raw) == row['bytes']
        assert pixel_size == (row['width'], row['height']) == (info.width, info.height)
        assert fmt == row['format']
        if row['id'] in candidates:
            ci = candidates[row['id']]['info']
            provenance_ok = (row['source_page_url'] == ci['descriptionurl']
                and row['source_image_url'] == ci['url']
                and row['download_url'] == ci.get('thumburl', ci['url']))
        else:
            product = products[row['expected_product_id']]
            provenance_ok = any(im['source_url'] == row['download_url'] and im['sha256'] == sha for im in product['images'])
        assert provenance_ok
        pixels[ph].append(row['id'])
        byte_hashes[sha].append(row['id'])
        records.append({'id': row['id'], 'path': row['image_path'], 'file_validation': 'passed',
            'source_metadata_consistent': provenance_ok, 'sha256': sha, 'normalized_pixel_sha256': ph,
            'mode': mode, 'gallery_matches': gallery.get(sha, []),
            'width': info.width, 'height': info.height, 'bytes': len(raw)})
    chosen = {r['image_path'] for r in m['images']}
    actual = {r['path'] for r in inventory if r['path'].startswith('images/')}
    assert chosen == actual
    assert len({r['id'] for r in m['images']}) == len(m['images'])
    assert all(case['image_path'] in chosen for case in cases)
    assert len({case['case_id'] for case in cases}) == len(cases)
    text_cases = [x for x in cases if x['task'] == 'image_text']
    controls = {x['image_path'] for x in m['images'] if x['role'] == 'gallery_control'}
    result = {
        'checked_at': stamp(), 'all_image_files': len(inventory),
        'inventory_groups': dict(Counter(x['path'].split('/')[0] for x in inventory)),
        'active_images': len(records), 'active_bytes': sum(x['bytes'] for x in records),
        'active_formats': dict(Counter(x['format'] for x in m['images'])),
        'roles': dict(Counter(x['role'] for x in m['images'])),
        'all_image_bytes': sum(x['bytes'] for x in inventory),
        'missing_or_unlisted_active_images': [],
        'byte_duplicate_groups': [v for v in byte_hashes.values() if len(v) > 1],
        'normalized_pixel_duplicate_groups': [v for v in pixels.values() if len(v) > 1],
        'gallery_match_count': sum(bool(r['gallery_matches']) for r in records),
        'gallery_reference_count': sum(len(p['images']) for p in c['products']),
        'current_catalog_version': c['catalog_version'],
        'catalog_sha256': digest((ROOT / 'database.json').read_bytes()),
        'manifest_catalog_matches': m['catalog_sha256'] == digest((ROOT / 'database.json').read_bytes()),
        'published_products': sum(p['status'] == 'published' for p in c['products']),
        'published_category_counts': dict(Counter(p['category_id'] for p in c['products'] if p['status'] == 'published')),
        'official_image_queries': len(load(ROOT / 'benchmarks/image/manifest.json')['samples']),
        'cases': len(cases), 'image_text_cases': len(text_cases),
        'image_text_cases_using_gallery': sum(x['image_path'] in controls for x in text_cases),
        'relevance_judgments_recorded': sum(x.get('judgment') is not None for x in m['images']),
        'independent_true_recorded': sum((x.get('independence_review') or {}).get('independent') is True for x in m['images']),
        'split_assignments': sum(x.get('split') is not None for x in m['images']),
        'rights_status': dict(Counter(x['usage_rights']['status'] for x in m['images'])),
        'licenses_declared': dict(Counter(x['usage_rights'].get('license', 'unknown') for x in m['images'])),
        'source_declared_empty_author': [x['id'] for x in m['images'] if x['usage_rights']['status']=='source_declared' and not x['usage_rights'].get('author')],
        'model_inference_performed': False, 'benchmark_approved': False,
        'records': records, 'inventory': inventory}
    save('local_checks.json', result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('records','inventory')}, ensure_ascii=False, indent=2))


def remote():
    rows = load(BASE / 'manifest.json')['images']
    checks = []
    for row in rows:
        item = {'id': row['id'], 'requested_url': row['download_url'], 'checked_at': stamp()}
        request = urllib.request.Request(row['download_url'], headers={'User-Agent': 'VNStore-local-image-audit/1.0'})
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                raw = response.read(8 * 1024 * 1024 + 1)
                item.update(status=response.status, final_url=response.geturl(), content_type=response.headers.get('Content-Type'))
            with Image.open(io.BytesIO(raw)) as im:
                im.verify()
            item.update(remote_sha256=digest(raw), local_sha256=row['sha256'],
                        remote_bytes=len(raw), identical_bytes=digest(raw)==row['sha256'])
        except urllib.error.HTTPError as e:
            item['error'] = str(e)
        except urllib.error.URLError as e:
            item['error'] = str(e)
            checks.append(item)
            save('remote_checks.json', {'checked_at': stamp(), 'complete': False, 'checks': checks})
            raise
        except Exception as e:
            item['error'] = str(e)
        checks.append(item)
        save('remote_checks.json', {'checked_at': stamp(), 'complete': len(checks)==len(rows), 'checks': checks})
        print(row['id'], 'same bytes' if item.get('identical_bytes') else item.get('error', 'different bytes'), flush=True)
        time.sleep(0.5)
    print('Remote match:', sum(x.get('identical_bytes',False) for x in checks), '/', len(checks))


def finish():
    before = load(HERE / 'outside_before.json')
    after = snapshot()
    result = {'checked_at':stamp(), 'files_before':len(before), 'files_after':len(after),
        'hashed_files':sum('sha256' in x for x in before.values()),
        'added': sorted(set(after)-set(before)), 'removed': sorted(set(before)-set(after)),
        'changed': sorted(k for k in before.keys() & after.keys() if before[k] != after[k]),
        'scope': 'All regular files outside tmp_data: size and mtime; SHA256 additionally for project files except git, environments, node_modules, artifacts and pytest cache.'}
    result['unchanged'] = not (result['added'] or result['removed'] or result['changed'])
    save('outside_comparison.json',result)
    print(json.dumps(result,ensure_ascii=False))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('action',choices=['local','remote','finish'])
    {'local':local,'remote':remote,'finish':finish}[parser.parse_args().action]()
