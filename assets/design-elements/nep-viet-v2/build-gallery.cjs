// Builds documents only. Original PNGs are read, never rewritten.
const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const root=__dirname;
const groups=[
 ['cutouts','01 / Vật thể tách nền','Đặt ở mép chương; giữ khoảng thở cho chữ và thao tác.'],
 ['botanical','02 / Nét sen','Hai biến thể cho lề nội dung, dùng có chọn lọc.'],
 ['scenes','03 / Khoảng lặng','Đầm sen giữa trang và phong cảnh chân trang.'],
 ['textures','04 / Chạm vào chất liệu','Một dải đan ở lề hoặc giữa hai chương.'],
 ['editorial','05 / Bàn tay & nghề','Ảnh minh họa AI, không gắn tên nghệ nhân hay địa danh thật.'],
 ['categories','06 / Năm chất liệu','Minh họa danh mục; ảnh hàng bán vẫn lấy từ catalog.'],
 ['svg','07 / Nét nhỏ','6 đồ họa trang trí/chuyển động và 12 biểu tượng tác vụ.']
];
const details={
 'bamboo-opening-branch':['Nhánh tre','opening-margin','Mép phải mở đầu; rộng 180–320px desktop, 90–140px mobile.'],
 'bamboo-shadow-clean':['Bóng tre · bản sạch','opening-margin','Opacity 0.08–0.16; multiply trong lớp cô lập; không phủ ô tìm kiếm.'],
 'ceramic-opening-still-life':['Tĩnh vật gốm','opening-margin','Điểm nhỏ ở góc thấp; rộng 100–160px, mobile 64–90px.'],
 'non-la-section-cutout':['Nón lá','chapter-edge','Chỉ tại chương danh mục; crop 30–45% ở mép, mobile giảm còn 96–140px.'],
 'textile-edge':['Mép lụa','chapter-edge','Mép phải chương nghề; desktop 120–180px, mobile ẩn nếu chật.'],
 'lotus-botanical-01':['Sen nở · nét khắc','content-gutter','Lề nhóm sản phẩm; 100–160px, không nằm sau chữ.'],
 'lotus-botanical-02':['Lá sen & gương sen','content-gutter','Lề câu chuyện nguồn gốc; không lặp cùng sen nở trong một vùng nhìn.'],
 'lotus-midpage-desktop':['Đầm sen · ngang','midpage-scene','Khoảng nghỉ giữa trang, không đưa lên opening. Focal point 67% 50%.'],
 'lotus-midpage-mobile':['Đầm sen · dọc','midpage-scene','Bố cục riêng cho màn hình hẹp; dùng picture thay ảnh ngang.'],
 'footer-landscape':['Phong cảnh · nét mực','footer-scene','Cảnh ở đáy; liên kết nằm trên vùng nền đặc phía trên.'],
 'bamboo-weave-macro':['Nhịp đan · macro','content-gutter','Crop dải dọc 64–120px desktop hoặc dải ngang mobile; không tile.'],
 'craft-hands-editorial':['Bàn tay đan','editorial-story','Ảnh chính chương nghề; caption “Minh họa bằng AI về thao tác đan”.'],
 'craft-workbench':['Góc bàn nghề','editorial-story','Ảnh phụ/chuyển cảnh chương nghề; không gắn làng nghề cụ thể.'],
 'category-ceramics':['Gốm','category-card','Ảnh vuông, object-fit: contain; dùng trong danh mục gốm.'],
 'category-weaving':['Đan lát','category-card','Ảnh vuông; giữ nguyên quai túi và miệng khay.'],
 'category-textiles':['Dệt & lụa','category-card','Ảnh vuông; không crop sát mép khăn.'],
 'category-wood-lacquer':['Gỗ & sơn','category-card','Ảnh vuông; giữ cả hộp và bát.'],
 'category-specialties':['Đặc sản đóng gói','category-card','Minh họa nhóm thực phẩm; không suy ra thương hiệu/xuất xứ.']
};
const assets=[];
for(const [dir] of groups)for(const name of fs.readdirSync(path.join(root,dir)).sort()){
 if(!/\.(png|svg)$/.test(name)||name==='bamboo-shadow.png')continue;
 const file=dir+'/'+name,id=name.replace(/\.(png|svg)$/,''),buffer=fs.readFileSync(path.join(root,file));
 const isSvg=name.endsWith('.svg'),box=isSvg?buffer.toString().match(/viewBox="([^"]+)"/)[1].split(' ').map(Number):null;
 const [title,placement,note]=details[id]||[id.replace(/^icon-/,'').replaceAll('-',' '),id.startsWith('icon-')?'ui-control':'micro-motion','SVG currentColor; nhúng inline để đổi màu hoặc animate từng nhóm.'];
 assets.push({id,title,file,format:isSvg?'svg':'png',width:isSvg?box[2]:buffer.readUInt32BE(16),height:isSvg?box[3]:buffer.readUInt32BE(20),bytes:buffer.length,sha256:crypto.createHash('sha256').update(buffer).digest('hex'),hasAlphaChannel:isSvg?null:[4,6].includes(buffer[25]),role:isSvg?(id.startsWith('icon-')?'functional-icon':'decorative-vector'):['categories','editorial'].includes(dir)?'illustrative-editorial':'decoration',alt:['categories','editorial'].includes(dir)?title+' — minh họa AI':'',placement,note,allowedRoutes:placement==='ui-control'||placement==='micro-motion'?['shared-ui']:placement==='content-gutter'?['home','product','brands','places']:['home'],focalPoint:id==='lotus-midpage-desktop'?[.67,.5]:[.5,.5],mobileVariant:id==='lotus-midpage-desktop'?'lotus-midpage-mobile':null,source:isSvg?'authored-svg':'built-in-imagegen',rights:isSvg?'Project-authored vector':'AI-generated illustration; not a licensed documentary photograph or catalog product',reviewStatus:'visually-reviewed-master; web-optimization-pending'});
}
const manifest={name:'Nếp Việt v2',design:'../../../design.md',assetCount:assets.length,excluded:[{file:'cutouts/bamboo-shadow.png',reason:'Bản đầu giữ mảng nền trắng; chỉ tham khảo QA. Dùng bamboo-shadow-clean.png.'}],assets};
fs.writeFileSync(path.join(root,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
const escape=s=>s.replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
const cards=dir=>assets.filter(a=>a.file.startsWith(dir+'/')).map(a=>`<article class="card ${a.format==='svg'?'vector':''}"><a class="stage" href="${a.file}" aria-label="Mở ${escape(a.title)}"><img src="${a.file}" width="${a.width}" height="${a.height}" loading="lazy" alt="${escape(a.title)}"></a><div class="caption"><h3>${a.title}</h3><p>${a.note}</p><small>${a.width} × ${a.height} · ${a.format.toUpperCase()} · ${(a.bytes/1024).toFixed(0)} KB</small><a class="file" href="${a.file}" download>${a.file}</a></div></article>`).join('');
const inline=name=>fs.readFileSync(path.join(root,'svg',name+'.svg'),'utf8');
fs.writeFileSync(path.join(root,'index.html'),`<!doctype html>
<html lang="vi"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Nếp Việt — Thư viện elements</title><link rel="stylesheet" href="gallery.css"><link rel="stylesheet" href="motion.css"></head>
<body data-surface="ivory"><a class="skip" href="#library">Đến thư viện</a><header><p class="eyebrow">VNSTORE / ART ASSETS / V2</p><h1>Nếp Việt<span>Chất liệu của một giao diện.</span></h1><p class="intro">Tre nghiêng một chút ở đầu trang. Nón dừng ở một mép danh mục. Sen mở ra giữa hành trình. Mỗi hình có một chỗ đứng, mỗi khoảng trống có lý do.</p><div class="meta">18 ảnh PNG · 6 vector trang trí · 12 biểu tượng</div><nav aria-label="Tài liệu"><a href="README.md">Hướng dẫn sử dụng ↗</a><a href="manifest.json">Manifest ↗</a><a href="PROMPTS.md">Prompt tạo ảnh ↗</a></nav></header>
<main id="library"><div class="toolbar"><label for="surface">Nền kiểm tra alpha</label><select id="surface"><option value="ivory">Giấy ngà</option><option value="forest">Xanh rừng</option><option value="checker">Ô trong suốt</option></select></div>
${groups.map(([dir,title,desc])=>`<section id="${dir}"><div class="section-head"><h2>${title}</h2><p>${desc}</p></div><div class="grid ${dir==='svg'?'icons':''}">${cards(dir)}</div></section>`).join('')}
<section id="motion"><div class="section-head"><h2>08 / Những chuyển động nhỏ</h2><p>Phát theo tương tác, kết thúc ở trạng thái yên. Các nút bên dưới dùng để xem từng nhịp.</p></div><label class="reduce"><input id="reduce" type="checkbox"> Giảm chuyển động</label><div class="motion-grid">
<article class="demo"><div class="demo-stage"><img class="nv-motion nv-bamboo" src="svg/bamboo-motion.svg" alt="" width="120" height="160"></div><h3>Gió qua tre</h3><p>4 giây · ±1,2° · một lượt</p><button data-demo=".nv-bamboo">Phát nhịp tre</button></article>
<article class="demo"><div class="demo-stage"><img class="nv-motion nv-ripple" src="svg/water-ripple.svg" alt="" width="180" height="60"></div><h3>Gợn mặt sen</h3><p>480ms · lan nhẹ rồi tan</p><button data-demo=".nv-ripple">Phát gợn nước</button></article>
<article class="demo"><div class="demo-stage"><div class="nv-motion nv-weave"><i style="--i:0"></i><i style="--i:1"></i><i style="--i:2"></i><i style="--i:3"></i><i style="--i:4"></i><i style="--i:5"></i></div></div><h3>Nhịp đan</h3><p>240ms · lệch nhịp 24ms</p><button data-demo=".nv-weave">Phát nhịp đan</button></article>
<article class="demo"><div class="demo-stage"><div class="nv-motion nv-lotus">${inline('lotus-mark')}</div></div><h3>Sen mở</h3><p>240ms · mở hai cánh nhỏ</p><button data-demo=".nv-lotus">Phát cánh sen</button></article></div><p id="motion-status" role="status">Chuyển động theo thiết lập hệ thống.</p></section>
</main><footer><strong>Một bộ chất liệu, nhiều khoảng thở.</strong><p>Ảnh minh họa được tạo bằng AI. Đây là bộ master phục vụ triển khai; ảnh sản phẩm thật vẫn lấy từ catalog.</p><a href="../../../design.md">Đọc design.md ↗</a></footer><script src="gallery.js"></script></body></html>`);
console.log('Built gallery and manifest:',assets.length,'assets');
