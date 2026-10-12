"""Offline validation and preview; writes only under tmp_data. Run Python -B."""
import collections
import hashlib
import html
import io
import json
from pathlib import Path
import sys

from PIL import Image, ImageOps, ImageDraw

from collect_images import BASE, ROOT, save, target, catalog, snapshot, now

sys.path.insert(0, str(ROOT / 'backend'))
from app.media import inspect_image


def rgb_on_white(image):
    image = ImageOps.exif_transpose(image)
    if image.mode in ('RGBA', 'LA', 'P'):
        rgba = image.convert('RGBA')
        background = Image.new('RGB', rgba.size, 'white')
        background.paste(rgba, mask=rgba.getchannel('A'))
        return background
    return image.convert('RGB')


def dhash(path):
    with Image.open(path) as image:
        image = rgb_on_white(image)
        small = image.convert('L').resize((9, 8))
        px = list(small.get_flattened_data())
        value = 0
        for y in range(8):
            for x in range(8):
                value = (value << 1) | (px[y * 9 + x] > px[y * 9 + x + 1])
        return value


def main():
    manifest = json.loads((BASE / 'manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schema') != 'vnstore-tmp-image-test-1':
        raise SystemExit('For the expanded dataset use: python -B tmp_data/build_dataset.py verify. No files changed.')
    data = catalog()
    gallery_hashes = collections.defaultdict(list)
    gallery_pixels = []
    for product in data['products']:
        for image in product['images']:
            path = (ROOT / image['local_path']).resolve()
            if not path.is_relative_to(ROOT):
                raise ValueError('Unexpected catalog path')
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            gallery_hashes[digest].append(image['id'])
            gallery_pixels.append((image['id'], dhash(path)))
    checks, seen, query_pixels = [], collections.defaultdict(list), []
    for row in manifest['images']:
        path = (BASE / row['image_path']).resolve()
        assert path.is_relative_to(BASE)
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        info = inspect_image(raw)
        with Image.open(io.BytesIO(raw)) as im:
            im.verify()
        with Image.open(io.BytesIO(raw)) as im:
            im.load()
            assert (im.width, im.height) == (info.width, info.height)
        assert digest == row['sha256']
        assert len(raw) == row['bytes']
        assert (info.width, info.height) == (row['width'], row['height'])
        seen[digest].append(row['id'])
        dh = dhash(path)
        query_pixels.append((row['id'], dh))
        near = sorted(((dh ^ h).bit_count(), iid) for iid, h in gallery_pixels)[:3]
        checks.append({'id': row['id'], 'pillow_decode': 'passed', 'api_inspect_image': 'passed',
                       'sha256_matches': True, 'exact_gallery_image_ids': gallery_hashes.get(digest, []),
                       'dhash_hex': f'{dh:016x}',
                       'near_gallery_candidates': [{'image_id': iid, 'distance': dist} for dist, iid in near if dist <= 6]})
    duplicates = [ids for ids in seen.values() if len(ids) > 1]
    near_queries = [{'a': a, 'b': b, 'distance': (ha ^ hb).bit_count()}
                    for i, (a, ha) in enumerate(query_pixels) for b, hb in query_pixels[i + 1:]
                    if (ha ^ hb).bit_count() <= 6]
    report = {'checked_at': now(), 'image_count': len(checks), 'gallery_images_checked': len(gallery_pixels),
              'total_image_bytes': sum(x['bytes'] for x in manifest['images']),
              'formats': dict(collections.Counter(x['format'] for x in manifest['images'])),
              'by_role': dict(collections.Counter(x['role'] for x in manifest['images'])),
              'by_group': dict(collections.Counter(x['group'] for x in manifest['images'])),
              'duplicate_query_byte_groups': duplicates, 'near_query_candidates': near_queries,
              'checks': checks, 'benchmark_approved': False,
              'note': 'dHash <= 6 only proposes review; neither independence nor identity is proven. No inference/API server was run.'}
    save('checks/validation.json', report)
    cases = []
    for row in manifest['images']:
        cases.append({'case_id': row['id'] + '-image', 'image_path': row['image_path'],
            'task': row['role'], 'text_vi': '', 'suggested_reference_product_id': row['expected_product_id'],
            'check': 'Quan sát top 5/10, hình dáng và loại vật thể; không suy nguồn gốc từ ảnh.',
            'expected_relevance': None})
    text_by_group = {
        'gom-su': ['dưới 500k', 'không lấy màu đỏ'],
        'may-tre-coi': ['có quai, dưới 400k', 'bằng tre, không lấy nhựa'],
        'det-may': ['khăn lụa dưới 500k', 'không lấy màu đỏ'],
        'go-son-mai': ['hộp sơn mài', 'dưới 500k'],
        'thuc-pham': ['sô cô la dưới 200k', 'Marou'],
    }
    for group, texts in text_by_group.items():
        rows = [r for r in manifest['images'] if r['group'] == group and r['role'] == 'gallery_control']
        for i, text in enumerate(texts):
            row = rows[i % len(rows)] if rows else next(r for r in manifest['images'] if r['group'] == group)
            cases.append({'case_id': row['id'] + f'-text-{i}', 'image_path': row['image_path'],
                'task': 'image_text', 'text_vi': text,
                'check': 'Kiểm tra interpreted_query, applied_filters và giá/phủ định; có thể không còn đáp án.',
                'expected_relevance': None})
    save('test_cases.json', {'benchmark_approved': False, 'cases': cases})
    e = html.escape
    sections = []
    labels = {'similar_candidate': 'Ảnh ngoài gallery: thử mẫu tương tự',
              'negative_candidate': 'Ảnh ngoài phạm vi: quan sát kết quả ít liên quan',
              'gallery_control': 'Đối chứng gallery: chỉ kiểm tra smoke'}
    for role, label in labels.items():
        cards = []
        for row in manifest['images']:
            if row['role'] != role:
                continue
            rights = row['usage_rights']
            license = rights.get('license', rights.get('status', 'unknown'))
            author = rights.get('author', '')
            cards.append(f'''<article><a href="{e(row['image_path'])}"><img loading="lazy" src="{e(row['image_path'])}" alt="{e(row['title'])}"></a>
            <h3>{e(row['id'])} · {e(row['group'])}</h3><p>{e(row['title'])}</p>
            <p>{row['width']} × {row['height']} · {row['format']} · {row['bytes'] / 1024:.0f} KiB</p>
            <p>Quyền nguồn: {e(license)}<br>{e(author)}</p>
            <a href="{e(row['source_page_url'])}" rel="noreferrer">Trang nguồn</a> ·
            <a href="{e(row['image_path'])}" download>Tải / mở ảnh</a><p class="path">{e(row['image_path'])}</p></article>''')
        sections.append(f'<h2>{e(label)}</h2><div class="grid">{"".join(cards)}</div>')
    page = '''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>VNStore — bộ ảnh thử cục bộ</title><style>
    body{font:16px/1.55 system-ui,sans-serif;background:#f5f4ef;color:#203027;margin:32px auto;max-width:1440px;padding:0 20px}
    h1{font-size:30px}h2{margin-top:40px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:18px}
    article{background:white;border:1px solid #d5dcd6;border-radius:10px;padding:14px}img{width:100%;height:220px;object-fit:contain;background:#eee}
    h3{font-size:16px}p{margin:8px 0}.path{font:12px monospace;overflow-wrap:anywhere}a{color:#15643d}aside{padding:18px;background:#e5eee6;border-radius:10px}
    </style><h1>VNStore · Ảnh test search image</h1>
    <aside>Mở từng ảnh rồi chọn file đó trong VNStore → <b>#/image</b>. Thử toàn ảnh, chọn vùng và thêm yêu cầu tiếng Việt.
    Đây là bộ thử thủ công, chưa có nhãn nghiệm thu; nhóm đối chứng gallery trùng nguồn dữ liệu tìm kiếm.
    <p><a href="README.md">Hướng dẫn</a> · <a href="PHAN_TICH_DU_AN.md">Phân tích dự án</a> · <a href="manifest.json">Nguồn / hash / quyền ảnh</a> ·
    <a href="test_cases.json">Ca thử</a> · <a href="checks/validation.json">Kiểm tra file</a></p></aside>'''
    target('index.html').write_text(page + ''.join(sections) + '</html>', encoding='utf-8')
    for offset in range(0, len(manifest['images']), 20):
        batch = manifest['images'][offset:offset + 20]
        sheet = Image.new('RGB', (1200, ((len(batch) + 3) // 4) * 235), 'white')
        draw = ImageDraw.Draw(sheet)
        for i, row in enumerate(batch):
            with Image.open(BASE / row['image_path']) as im:
                im = rgb_on_white(im)
                im.thumbnail((286, 195))
                x, y = (i % 4) * 300, (i // 4) * 235
                sheet.paste(im, (x + (300 - im.width) // 2, y))
                draw.text((x + 8, y + 197), row['id'] + ' / ' + row['group'], fill='black')
                draw.text((x + 8, y + 213), row['role'], fill='black')
        sheet.save(target(f'preview/contact-{offset // 20 + 1:02}.jpg'), quality=90)
    before = json.loads((BASE / 'checks/outside_before.json').read_text(encoding='utf-8'))
    after = snapshot()
    diff = {'checked_at': now(), 'files_before': len(before), 'files_after': len(after),
            'content_hashes_checked': sum('sha256' in x for x in before.values()),
            'added': sorted(set(after) - set(before)), 'removed': sorted(set(before) - set(after)),
            'changed': [k for k in before.keys() & after.keys() if before[k] != after[k]],
            'scope': 'Every regular file outside tmp_data: size/mtime. SHA256 additionally for project source/docs/data/assets; excludes .git, venvs, node_modules, artifacts, pytest cache from hashing.'}
    diff['unchanged'] = not (diff['added'] or diff['removed'] or diff['changed'])
    save('checks/outside_comparison.json', diff)
    print(json.dumps({k: v for k, v in report.items() if k not in ('checks', 'near_query_candidates')}, ensure_ascii=False, indent=2))
    print('Near-query candidates:', len(near_queries))
    print('Outside:', json.dumps(diff, ensure_ascii=False))


if __name__ == '__main__':
    main()
