"""Build/verify the extended exploratory set, confined to tmp_data. Run -B."""
from collections import Counter, defaultdict
import hashlib
import html
from html.parser import HTMLParser
import io
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit, unquote

from PIL import Image, ImageDraw, ImageFont
from collect_images import BASE, ROOT, save, target, now, snapshot
from expand_dataset import BATCH, load
from verify_and_preview import rgb_on_white, dhash
sys.path.insert(0, str(ROOT / 'backend'))
from app.media import inspect_image

GROUPS={'gom-su':'Gốm sứ','det-may':'Dệt may','may-tre-coi':'Mây tre / đồ đan',
        'go-son-mai':'Gỗ / sơn mài','thuc-pham':'Bao bì thực phẩm','ngoai-catalog':'Ngoài catalog'}
ROLES={'similar_candidate':'Thử tìm mẫu tương tự','contrast_candidate':'Phân biệt vật liệu / loại hàng / nhãn',
       'negative_candidate':'Ngoài loại hàng đang có','gallery_control':'Đối chứng trùng gallery'}
TEXTS={
 'bowl':['bát sứ dưới 300k','không lấy màu đỏ'],
 'plate':['đĩa sứ dưới 500k','màu trắng'],
 'dinner-plate':['đĩa sứ','không lấy nhựa'],
 'mug':['cốc sứ dưới 500k','có nắp'],
 'ao-dai-street':['áo dài lụa','không lấy màu đỏ'],
 'shirt':['áo sơ mi','dưới 1 triệu'],
 'shirt-modern':['áo sơ mi','không lấy màu đỏ'],
 'dress':['váy lụa','dưới 2 triệu'],
 'lamp':['chụp đèn đan','bằng tre'],
 'wicker-lampshade':['chụp đèn','không lấy nhựa'],
 'chair':['đồ đan','bằng mây'],
 'woven-bag':['túi đan có quai','không lấy nhựa'],
 'straw-bag':['túi đan dưới 500k','có quai'],
 'lacquer-box':['hộp sơn mài','không lấy màu đỏ'],
 'wood-box-simple':['hộp gỗ','dưới 500k'],
 'jewellery-box':['hộp gỗ','hộp sơn mài'],
 'chocolate':['sô cô la Marou','dưới 200k'],
 'vietnam-cake':['sô cô la Marou','dưới 200k'],
 'vn-banh-com':['Marou','sô cô la dưới 200k'],
 'vn-keo-dua':['sô cô la','Marou'],
 'glass-mug':['cốc bằng sứ','không lấy thủy tinh'],
 'plastic-basket':['giỏ bằng tre','không lấy nhựa'],
 'leather-bag':['túi đan','không lấy da'],
}


def all_rows():
    old=load(f'{BATCH}/manifest.before.json')['images']
    additions=load(f'{BATCH}/downloads.json')['images']
    selected={x['id'] for x in load(f'{BATCH}/selection.json')['selected']}
    return old + [x for x in additions if x['id'] in selected]


def preview():
    rows=all_rows()
    for offset in range(0,len(rows),20):
        batch=rows[offset:offset+20]
        sheet=Image.new('RGB',(1400,((len(batch)+3)//4)*280),'white')
        draw=ImageDraw.Draw(sheet)
        for i,row in enumerate(batch):
            with Image.open(BASE/row['image_path']) as im:
                im=rgb_on_white(im); im.thumbnail((335,235))
                x,y=(i%4)*350,(i//4)*280
                sheet.paste(im,(x+(350-im.width)//2,y))
                draw.text((x+8,y+237),row['id'],fill='black')
                draw.text((x+8,y+253),row.get('topic',row['group']),fill='black')
        sheet.save(target(f'preview/contact-{offset//20+1:02}.jpg'),quality=92)
    print('Previewed',len(rows),'images')


def publish():
    rows=all_rows()
    notes=load(f'{BATCH}/curation.json')
    by_id={x['id']:x for x in rows}
    for row in rows:
        row['source_group_candidate']=row['source_asset_id']
        row['review_status']='pending_human_relevance_and_independence'
        row['scenario_tags']=[]
        if row['group']=='hard-negative':
            row['group']='gom-su' if row['topic']=='glass-mug' else 'may-tre-coi'
        if row['id'] in notes['row_notes']:
            row.update(notes['row_notes'][row['id']])
        if row['role']=='gallery_control':
            row['scenario_tags'].append('same_gallery_source')
    for grouping in notes['source_groups']:
        for key in grouping['image_ids']:
            if key in by_id:
                by_id[key]['source_group_candidate']=grouping['id']
    evidence=load(f'{BATCH}/downloads.json')
    catalog_hash=hashlib.sha256((ROOT/'database.json').read_bytes()).hexdigest()
    assert load(f'{BATCH}/manifest.before.json')['catalog_sha256']==catalog_hash
    manifest={'schema':'vnstore-tmp-image-test-2','dataset_version':'expanded-2026-10-13',
        'updated_at':now(),'created_for':'manual exploratory and regression input; no approved model-quality labels',
        'catalog_version':load('manifest.json')['catalog_version'],'catalog_sha256':catalog_hash,
        'benchmark_approved':False,'images':rows,'download_errors':evidence['errors']}
    save('manifest.json',manifest)
    cases=load(f'{BATCH}/test_cases.before.json')['cases']
    for case in cases:
        row=next(x for x in rows if x['image_path']==case['image_path'])
        if case['task']!='image_text': case['task']=row['role']
        case['source_group_candidate']=row['source_group_candidate']
        case['judgment_status']='pending'
        case['interpretation_note']='Source product ID is a gallery-control reference, not an answer for edited text.'
    added=[r for r in rows if r['id'].startswith('add-')]
    for row in added:
        base={'image_path':row['image_path'],'image_id':row['id'],
              'source_group_candidate':row['source_group_candidate'],'expected_relevance':None,'judgment_status':'pending'}
        cases.append(dict(base,case_id=row['id']+'-image',task=row['role'],text_vi='',
            check='Quan sát top 5/10 và đối chiếu loại vật thể; vai trò thử không phải nhãn relevance.'))
        for index,text in enumerate(TEXTS[row['topic']]):
            cases.append(dict(base,case_id=row['id']+f'-text-{index+1}',task='image_text',text_vi=text,
                check='Ghi diễn giải, bộ lọc, top-k; xác minh giá/phủ định theo catalog. Có thể không còn đáp án.',
                text_intent='conditional contrast' if row['role']=='contrast_candidate' else 'refine or edit request'))
    for crop in notes['crop_cases']:
        row=by_id[crop['image_id']]
        cases.append({'case_id':row['id']+'-crop','image_id':row['id'],'image_path':row['image_path'],
            'source_group_candidate':row['source_group_candidate'],'task':'manual_crop_comparison','text_vi':'',
            'crop_xyxy':None,'crop_instruction_vi':crop['instruction_vi'],
            'check':'Ghi vùng crop trước xem kết quả; so toàn ảnh và vùng cố định, không tạo mẫu độc lập mới.',
            'expected_relevance':None,'judgment_status':'pending'})
    save('test_cases.json',{'dataset_version':manifest['dataset_version'],'benchmark_approved':False,'cases':cases})
    save('review_template.json',{'catalog_sha256':catalog_hash,'status':'template_unreviewed',
        'instructions_vi':'Không tự coi nháp này là nhãn đã duyệt. Chấm relevance theo từng case, vì thêm chữ/crop có thể đổi đáp án. Giữ cùng nhóm nguồn qua mọi case.',
        'images':[{'image_id':r['id'],'sha256':r['sha256'],'source_group_candidate':r['source_group_candidate'],
                   'family_id':None,'capture_session_id':None,'independence_review':None,'rights_review':None} for r in rows],
        'cases':[{'case_id':c['case_id'],'has_answer':None,'relevance':{},'exact_product_id':None,
                  'reviewed_by':None,'reviewed_at':None,'notes':None} for c in cases]})
    # Ready-to-fill observations without claiming any model result.
    save('run_template.json',{'dataset_version':manifest['dataset_version'],'catalog_sha256':catalog_hash,
        'model_id':None,'revision':None,'search_config':None,'started_at':None,
        'cases':[{'case_id':c['case_id'],'result_product_ids':[],'timings_ms':None,'filters_observed':None,
                  'reviewer_observation':None,'status':'not_run'} for c in cases]})
    e=html.escape
    cards=[]
    for row in rows:
        group=GROUPS.get(row['group'],row['group']); role=ROLES[row['role']]
        rights=row['usage_rights']; texts=TEXTS.get(row.get('topic'),[])
        tags=' · '.join(row['scenario_tags'])
        cards.append(f'''<article data-role="{e(row['role'])}" data-group="{e(row['group'])}">
        <a href="{e(row['image_path'])}"><img src="{e(row['image_path'])}" loading="lazy" alt="{e(row['title'])}"></a>
        <h3>{e(row['id'])}</h3><p><strong>{e(group)}</strong> · {e(role)}</p><p>{e(row['title'])}</p>
        <p>{e(row.get('content_note_vi',''))}</p><p>{e(tags)}</p><p>Thử chữ: {e(' / '.join(texts))}</p>
        <p>{row['width']} × {row['height']} · {row['format']} · {row['bytes']/1024:.0f} KiB</p>
        <p>{e(rights.get('license',rights.get('status','unknown')))} · {e(rights.get('author',rights.get('credit','')))}</p>
        <a href="{e(row['source_page_url'])}" rel="noreferrer">Trang nguồn</a> · <a href="{e(row['image_path'])}" download>Mở / tải ảnh</a>
        <p class="path">{e(row['image_path'])}</p></article>''')
    options=''.join(f'<option value="{e(k)}">{e(v)}</option>' for k,v in GROUPS.items())
    roles=''.join(f'<option value="{e(k)}">{e(v)}</option>' for k,v in ROLES.items())
    page=f'''<!doctype html><html lang="vi"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
    <title>VNStore · Bộ ảnh test mở rộng</title><style>body{{font:16px/1.5 system-ui,sans-serif;background:#f5f4ef;color:#233a2c;max-width:1500px;margin:30px auto;padding:0 20px}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:16px}}article{{background:white;padding:14px;border:1px solid #d3ddd5;border-radius:10px}}img{{width:100%;height:220px;object-fit:contain;background:#eee}}.path{{font:12px monospace;overflow-wrap:anywhere}}a{{color:#15643d}}aside{{padding:18px;background:#e4eee5}}select,input{{padding:10px;max-width:95%;margin:8px}}[hidden]{{display:none!important}}h3{{margin-bottom:5px}}</style>
    <h1>{len(rows)} ảnh · VNStore image search</h1><aside>Ảnh tải thật phục vụ thử tay và quan sát hồi quy. Nhãn phù hợp/độc lập đang chờ duyệt; chưa phải benchmark nghiệm thu.
    <p>{len(added)} ảnh mới; {len(cases)} ca thử. Chọn file trên trang <b>#/image</b> của ứng dụng đang chạy.</p>
    <a href="README.md">Hướng dẫn</a> · <a href="manifest.json">Manifest / quyền / nguồn</a> · <a href="test_cases.json">Ca thử</a> ·
    <a href="{BATCH}/KET_QUA.md">Kết quả bổ sung</a> · <a href="{BATCH}/verification.json">Kiểm tra dữ liệu</a></aside>
    <p><label>Nhóm <select id="group"><option value="">Tất cả</option>{options}</select></label>
    <label>Vai trò <select id="role"><option value="">Tất cả</option>{roles}</select></label>
    <label>Tìm <input id="find" placeholder="ID, tên hoặc tình huống"></label> <span id="count"></span></p>
    <div class="grid">{''.join(cards)}</div>
    <script>const cards=[...document.querySelectorAll('article')];function filter(){{let n=0;for(const c of cards){{c.hidden=!!((group.value&&c.dataset.group!==group.value)||(role.value&&c.dataset.role!==role.value)||(find.value&&!c.textContent.toLowerCase().includes(find.value.toLowerCase())));if(!c.hidden)n++;}}document.getElementById('count').textContent=n+' ảnh';}}
    const group=document.getElementById('group'),role=document.getElementById('role'),find=document.getElementById('find');[group,role,find].forEach(x=>x.addEventListener('input',filter));filter();</script></html>'''
    target('index.html').write_text(page,encoding='utf-8')
    print('Published local dataset:',len(rows),'images;',len(cases),'cases')


def verify():
    m=load('manifest.json'); rows=m['images']; cases=load('test_cases.json')['cases']
    old=load(f'{BATCH}/manifest.before.json')['images']
    catalog=json.loads((ROOT/'database.json').read_text(encoding='utf-8'))
    gallery=defaultdict(list)
    for p in catalog['products']:
        for im in p['images']:
            path=(ROOT/im['local_path']).resolve(); assert path.is_relative_to(ROOT)
            gallery[hashlib.sha256(path.read_bytes()).hexdigest()].append(im['id'])
    hashes=defaultdict(list); pixels=defaultdict(list); near=[]; checks=[]; dh=[]
    for row in rows:
        path=(BASE/row['image_path']).resolve(); assert path.is_relative_to(BASE)
        raw=path.read_bytes(); sha=hashlib.sha256(raw).hexdigest(); info=inspect_image(raw)
        with Image.open(io.BytesIO(raw)) as im: im.verify()
        with Image.open(io.BytesIO(raw)) as im:
            im.load(); assert (im.width,im.height)==(info.width,info.height)==(row['width'],row['height'])
            assert im.format==row['format']; rgb=rgb_on_white(im)
            pixelsha=hashlib.sha256(str(rgb.size).encode()+rgb.tobytes()).hexdigest()
        assert sha==row['sha256'] and len(raw)==row['bytes']
        hashes[sha].append(row['id']);pixels[pixelsha].append(row['id']);dh.append((row['id'],dhash(path)))
        checks.append({'id':row['id'],'decode':'passed','api_media_check':'passed','sha256':'passed',
                       'gallery_matches':gallery.get(sha,[])})
    expected={r['image_path'] for r in rows}
    actual={p.relative_to(BASE).as_posix() for p in (BASE/'images').rglob('*') if p.is_file()}
    assert actual==expected,(actual-expected,expected-actual)
    assert len({r['id'] for r in rows})==len(rows)
    assert len({r['case_id'] for r in cases})==len(cases)
    assert all(r['image_path'] in expected for r in cases)
    assert all(hashlib.sha256((BASE/r['image_path']).read_bytes()).hexdigest()==r['sha256'] for r in old)
    assert all(len(v)==1 for v in hashes.values()),'Duplicate bytes require curation'
    assert all(len(v)==1 for v in pixels.values()),'Duplicate pixels require curation'
    for i,(a,ha) in enumerate(dh):
        near += [{'a':a,'b':b,'distance':(ha^hb).bit_count()} for b,hb in dh[i+1:] if (ha^hb).bit_count()<=6]
    class Links(HTMLParser):
        def handle_starttag(self,tag,attrs):
            for k,v in attrs:
                if k in ('href','src') and not urlsplit(v).scheme:
                    assert (BASE/unquote(v)).exists(),v
    # Check after writing verification file to satisfy its self-link.
    image_count=sum(1 for p in BASE.rglob('*') if p.is_file() and p.suffix.lower() in ('.jpg','.jpeg','.png','.webp','.gif','.bmp'))
    result={'checked_at':now(),'dataset_version':m['dataset_version'],'active_images':len(rows),
        'added_images':sum(r['id'].startswith('add-') for r in rows),'all_image_files_in_tmp_data':image_count,
        'active_image_bytes':sum(r['bytes'] for r in rows),'formats':dict(Counter(r['format'] for r in rows)),
        'roles':dict(Counter(r['role'] for r in rows)),'groups':dict(Counter(r['group'] for r in rows)),
        'added_topics':dict(Counter(r['topic'] for r in rows if r['id'].startswith('add-'))),
        'cases':len(cases),'case_tasks':dict(Counter(c['task'] for c in cases)),
        'image_text_non_gallery':sum(c['task']=='image_text' and '/gallery_control/' not in c['image_path'] for c in cases),
        'byte_duplicates':[],'pixel_duplicates':[],'near_duplicate_candidates':near,
        'gallery_matches':sum(bool(x['gallery_matches']) for x in checks),'original_40_images_unchanged':True,
        'benchmark_approved':False,'model_inference_performed':False,'checks':checks}
    save(f'{BATCH}/verification.json',result)
    save('checks/validation.json',result)
    parser=Links();parser.feed((BASE/'index.html').read_text(encoding='utf-8'))
    before=load(f'{BATCH}/outside_before.json');after=snapshot()
    diff={'checked_at':now(),'files_before':len(before),'files_after':len(after),'hashed_files':sum('sha256'in x for x in before.values()),
        'added':sorted(set(after)-set(before)),'removed':sorted(set(before)-set(after)),
        'changed':sorted(k for k in before.keys() & after.keys() if before[k]!=after[k]),
        'scope':'Size/mtime of all regular files outside tmp_data; SHA256 for project source/docs/data except git, environments, node_modules, artifacts and pytest cache.'}
    diff['unchanged']=not(diff['added'] or diff['removed'] or diff['changed'])
    save(f'{BATCH}/outside_comparison.json',diff)
    print(json.dumps({k:v for k,v in result.items() if k not in ('checks','near_duplicate_candidates')},ensure_ascii=False,indent=2))
    print('Near pairs:',len(near),'Outside:',json.dumps(diff,ensure_ascii=False))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('action',choices=['preview','publish','verify'])
    {'preview':preview,'publish':publish,'verify':verify}[p.parse_args().action]()
