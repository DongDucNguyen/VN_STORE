// CHƯƠNG IV: cánh sen, đầm sen bình minh, logo, lặng.

const PETAL = "M 0 -120 C 46 -86 62 -20 42 40 C 30 78 12 104 0 120 C -12 104 -30 78 -42 40 C -62 -20 -46 -86 0 -120 Z";
function petalEl(parent, id) {
  const defs = el("defs", {}, parent);
  const g = el("radialGradient", { id, cx: "50%", cy: "85%", r: "90%" }, defs);
  el("stop", { offset: 0, "stop-color": "#FBEFF0" }, g); el("stop", { offset: .55, "stop-color": "#E7AEBB" }, g); el("stop", { offset: 1, "stop-color": "#B9637A" }, g);
  const p = el("g", {}, parent);
  el("path", { d: PETAL, fill: `url(#${id})`, stroke: "#97485F", "stroke-width": 1.6 }, p);
  for (let k = -2; k <= 2; k++) el("path", { d: `M 0 110 C ${k * 10} 40 ${k * 16} -30 ${k * 8} -100`, fill: "none", stroke: "#B9637A", "stroke-width": 1, opacity: .45 }, p);
  return p;
}

// ---------- S17 · Đầm sen bình minh (100.9 – 108.2) ----------
scene(100.55, 108.2, (root) => {
  const s = svg(root);
  const defs = el("defs", {}, s);
  const sky = el("linearGradient", { id: "dawn", x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
  el("stop", { offset: 0, "stop-color": "#E9C9BE" }, sky); el("stop", { offset: .5, "stop-color": "#F4DFCF" }, sky); el("stop", { offset: 1, "stop-color": "#F7EBDC" }, sky);
  const wat = el("linearGradient", { id: "pond", x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
  el("stop", { offset: 0, "stop-color": "#5f8577" }, wat); el("stop", { offset: .35, "stop-color": "#2f5b4b" }, wat); el("stop", { offset: 1, "stop-color": "#183E33" }, wat);
  const sunG = el("radialGradient", { id: "dsun" }, defs);
  el("stop", { offset: 0, "stop-color": "#FFF4DA" }, sunG); el("stop", { offset: .4, "stop-color": "#FBE3BE", "stop-opacity": .8 }, sunG); el("stop", { offset: 1, "stop-color": "#FBE3BE", "stop-opacity": 0 }, sunG);
  el("rect", { width: W, height: 620, fill: "url(#dawn)" }, s);
  const sun = el("circle", { cx: 1260, cy: 560, r: 260, fill: "url(#dsun)" }, s);
  el("path", { d: "M 0 560 C 260 470 420 520 620 480 C 820 440 980 520 1200 470 C 1420 420 1640 500 1920 450 L 1920 620 L 0 620 Z", fill: "#b9c4b4", opacity: .55 }, s);
  el("path", { d: "M 0 600 C 300 540 520 590 760 550 C 1000 510 1240 590 1500 545 C 1700 515 1820 560 1920 540 L 1920 620 L 0 620 Z", fill: "#8fa597", opacity: .7 }, s);
  el("rect", { y: 618, width: W, height: 462, fill: "url(#pond)" }, s);
  const shimmer = []; for (let i = 0; i < 16; i++) shimmer.push(el("line", { stroke: "#FFF4DA", "stroke-width": 2.5, "stroke-linecap": "round" }, s));
  // lá sen
  const leaves = [[180, 900, 210, "#2a5c47"], [520, 760, 150, "#336b53"], [1560, 820, 190, "#2a5c47"], [1820, 700, 120, "#3c7559"], [860, 980, 230, "#24503f"], [1290, 1000, 200, "#2a5c47"], [330, 700, 110, "#3c7559"]].map(([x, y, r, c], i) => {
    const g = el("g", { transform: `translate(${x} ${y})` }, s);
    el("ellipse", { rx: r, ry: r * 0.3, fill: c, stroke: "#183E33", "stroke-width": 2 }, g);
    for (let k = 0; k < 10; k++) { const a = k / 10 * Math.PI * 2; el("line", { x1: 0, y1: 0, x2: Math.cos(a) * r * .92, y2: Math.sin(a) * r * .27, stroke: "#5c8f73", "stroke-width": 1.2, opacity: .7 }, g); }
    el("path", { d: `M 0 0 L ${r * 0.9} ${-r * 0.05} L ${r * 0.9} ${r * 0.07} Z`, fill: "#183E33", opacity: .6 }, g);
    return { g, x, y, i };
  });
  // hoa sen
  const flower = (x, y, sc, open) => {
    const g = el("g", { transform: `translate(${x} ${y}) scale(${sc})` }, s);
    el("path", { d: "M 0 0 C 4 60 -2 120 6 190", stroke: "#3c6b52", "stroke-width": 6, fill: "none" }, g);
    [-58, -30, 30, 58, 0].forEach((a) => el("path", { d: "M 0 0 C 26 -26 30 -80 0 -118 C -30 -80 -26 -26 0 0 Z", transform: `rotate(${a * open})`, fill: a === 0 ? "#F2C6CF" : "#E5A3B2", stroke: "#97485F", "stroke-width": 1.6 }, g));
    return g;
  };
  const flowers = [flower(420, 690, 0.8, 1), flower(1640, 640, 0.65, 0.9), flower(250, 760, 0.55, 0.7)];
  const rings = []; for (let k = 0; k < 5; k++) rings.push(el("ellipse", { cx: 960, cy: 760, fill: "none", stroke: "#FFF4DA" }, s));
  const small = petalEl(s, "pet1");
  const bigS = svg(root);
  const big = petalEl(bigS, "pet2");
  const t1 = el("div", { class: "cap", style: { left: "0", width: "1920px", textAlign: "center", top: "200px", fontSize: "56px", color: C.ink } }, root);
  t1.innerHTML = "<i>Gìn giữ tinh hoa.</i>";
  const t2 = el("div", { class: "ftitle", style: { left: "0", width: "1920px", textAlign: "center", top: "282px", fontSize: "118px", color: C.ink } }, root);
  t2.innerHTML = '<span class="mask"><span>Tôn vinh nét đẹp Việt.</span></span>';
  return (t) => {
    root.style.opacity = 1;
    for (const e of [t1, t2]) if (t < 101.0) e.style.visibility = "hidden";
    sun.setAttribute("cy", 560 - 60 * prog(t, 101, 108));
    shimmer.forEach((l, i) => {
      const y = 640 + i * 22, w = 40 + 140 * rand(i, 31) * (1 - i / 20), x = 1260 + (rand(i, 32) - 0.5) * 300 * (1 + i / 8) + Math.sin(t * 1.4 + i) * 14;
      l.setAttribute("x1", x - w / 2); l.setAttribute("x2", x + w / 2); l.setAttribute("y1", y); l.setAttribute("y2", y); l.style.opacity = 0.25 + 0.3 * Math.abs(noise1(t * 2 + i, i));
    });
    leaves.forEach(({ g, x, y, i }) => g.setAttribute("transform", `translate(${x + Math.sin(t * 0.5 + i) * 4} ${y + Math.sin(t * 0.8 + i) * 2})`));
    flowers.forEach((f, i) => f.setAttribute("transform", f.getAttribute("transform").replace(/rotate\([^)]*\)/, "") + ` rotate(${Math.sin(t * 0.9 + i) * 1.5})`));
    // cánh sen lớn lướt sát ống kính: phủ khung tại 101.0
    const bp = prog(t, 100.55, 101.45);
    big.setAttribute("transform", `translate(${lerp(-1400, 3200, bp)} ${lerp(-500, 1500, bp)}) rotate(${lerp(52, 68, bp)}) scale(${lerp(15, 17, bp)})`);
    op(big, bp < 1 ? 1 : 0);
    s.style.opacity = t >= 101.0 ? 1 : 0;
    // cánh nhỏ trôi xuống và đậu trên mặt nước
    const sp = prog(t, 101.3, 103.9);
    const sx = lerp(560, 960, eIO(sp)) + Math.sin(sp * 7) * 60 * (1 - sp), sy = lerp(80, 752, eIn(sp) * 0.6 + sp * 0.4);
    const land = t >= 103.9;
    small.setAttribute("transform", `translate(${land ? 960 + Math.sin(t) * 3 : sx} ${land ? 752 : sy}) rotate(${land ? 80 : lerp(-40, 80, sp) + Math.sin(sp * 9) * 25}) scale(${land ? 0.5 : 0.5}, ${land ? 0.18 : lerp(0.5, 0.3, sp)})`);
    op(small, prog(t, 101.25, 101.5));
    ripplesAt(t, 103.9, 5, 0.35, 3.6, 520).forEach((r, k) => {
      const e = rings[k];
      e.setAttribute("rx", r.r); e.setAttribute("ry", r.r * 0.22);
      e.setAttribute("stroke-width", 2.4 * (1 - r.p) + 0.5);
      e.style.opacity = r.on ? Math.pow(1 - r.p, 1.2) * 0.8 : 0;
    });
    inkText(t1, t, 102.0, 108.1, { fo: 0.5 });
    maskLine(t2.querySelector(".mask > span"), t, 105.0, 1.0);
    root.style.opacity = 1 - eIO(prog(t, 107.7, 108.2));
  };
});

// ---------- S18–19 · Logo và lặng (107.6 – 120) ----------
scene(107.6, 120.01, (root) => {
  root.style.background = C.forest;
  const land = el("img", { src: "art/footer-landscape.png", class: "abs", style: { left: "-60px", bottom: "-20px", width: "2040px", transformOrigin: "50% 100%" } }, root);
  const sky = layer(root, "", { background: `linear-gradient(180deg, ${C.forestD} 0%, rgba(24,62,51,0) 70%)` });
  const s = svg(root);
  const mk = el("g", { transform: "translate(960 300) scale(5.2) translate(-24 -24)" }, s);
  const parts = [
    "M24 39C12 30 13 17 24 6c11 11 12 24 0 33Z", "M24 39C10 39 4 28 5 15c12 2 19 12 19 24Z",
    "M24 39c14 0 20-11 19-24-12 2-19 12-19 24Z", "M5 32c4 11 12 12 19 10 7 2 15 1 19-10",
  ].map((d) => el("path", { d, fill: "none", stroke: "#ECECE0", "stroke-width": 1.4, "stroke-linecap": "round", "stroke-linejoin": "round" }, mk));
  const fills = parts.slice(0, 3).map((p) => el("path", { d: p.getAttribute("d"), fill: C.lotusL, opacity: 0 }, mk));
  fills.forEach((f) => mk.insertBefore(f, mk.firstChild));
  const word = el("div", { class: "ftitle", style: { left: "0", width: "1920px", textAlign: "center", top: "476px", fontSize: "150px", color: "#ECECE0" } }, root);
  word.innerHTML = '<span class="mask"><span>VNStore</span></span>';
  const slogan = el("div", { class: "cap", style: { left: "0", width: "1920px", textAlign: "center", top: "666px", fontSize: "50px", color: C.straw } }, root);
  slogan.innerHTML = "<i>Nếp Việt trong từng món đồ</i>";
  const eyebrow = el("div", { class: "eyebrow", style: { left: "0", width: "1920px", justifyContent: "center", top: "760px", color: "#C3CCBF" } }, root);
  eyebrow.innerHTML = '<span class="mark"></span>Đồ Việt · Người Việt · Cuộc sống đẹp hơn';
  // kết trên nền giấy ngà
  const paper = layer(root, "", { background: C.ivory });
  const ps = svg(paper);
  const pm = el("g", { transform: "translate(960 294) scale(5.2) translate(-24 -24)" }, ps);
  ["M24 39C12 30 13 17 24 6c11 11 12 24 0 33Z", "M24 39C10 39 4 28 5 15c12 2 19 12 19 24Z", "M24 39c14 0 20-11 19-24-12 2-19 12-19 24Z", "M5 32c4 11 12 12 19 10 7 2 15 1 19-10"]
    .forEach((d, i) => { if (i < 3) el("path", { d, fill: C.lotusL, opacity: .85 }, pm); });
  ["M24 39C12 30 13 17 24 6c11 11 12 24 0 33Z", "M24 39C10 39 4 28 5 15c12 2 19 12 19 24Z", "M24 39c14 0 20-11 19-24-12 2-19 12-19 24Z", "M5 32c4 11 12 12 19 10 7 2 15 1 19-10"]
    .forEach((d) => el("path", { d, fill: "none", stroke: C.primary, "stroke-width": 1.4, "stroke-linecap": "round", "stroke-linejoin": "round" }, pm));
  const pw = el("div", { class: "ftitle", style: { left: "0", width: "1920px", textAlign: "center", top: "476px", fontSize: "150px", color: C.ink } }, paper);
  pw.textContent = "VNStore";
  const pslog = el("div", { class: "cap", style: { left: "0", width: "1920px", textAlign: "center", top: "666px", fontSize: "50px", color: C.lotusT } }, paper);
  pslog.innerHTML = "<i>Nếp Việt trong từng món đồ</i>";
  const pr = []; for (let k = 0; k < 4; k++) pr.push(el("ellipse", { cx: 960, cy: 850, fill: "none", stroke: C.ink }, ps));
  return (t) => {
    root.style.opacity = eW(prog(t, 107.6, 108.3));
    land.style.transform = `scale(${lerp(1, 1.035, prog(t, 107.6, 118))}) translateX(${-prog(t, 107.6, 118) * 20}px)`;
    parts.forEach((p, i) => draw(p, eIO(prog(t, 107.9 + i * 0.18, 108.9 + i * 0.18))));
    fills.forEach((f, i) => f.style.opacity = 0.85 * eW(prog(t, 108.8 + i * 0.1, 109.5 + i * 0.1)));
    const bloom = eB(prog(t, 108.7, 109.5));
    mk.setAttribute("transform", `translate(960 ${300 - 6 * bloom}) scale(${5.0 + 0.2 * bloom}) translate(-24 -24)`);
    maskLine(word.querySelector(".mask > span"), t, 108.7, 1.0);
    inkText(slogan, t, 109.6, 120.1, { fo: 0.01 });
    inkText(eyebrow, t, 110.5, 120.1, { dy: 6, blur: 2, fo: 0.01 });
    // 116.4 → hòa sang giấy ngà, giọt nước cuối ở 119.0
    const pp = eIO(prog(t, 116.4, 117.9));
    op(paper, pp);
    ripplesAt(t, 119.0, 4, 0.3, 1.6, 240).forEach((r, k) => {
      const e = pr[k]; e.setAttribute("rx", r.r); e.setAttribute("ry", r.r * 0.22); e.setAttribute("stroke-width", 1.6 * (1 - r.p) + .4);
      e.style.opacity = r.on ? (1 - r.p) * 0.45 : 0;
    });
    const fin = eIO(prog(t, 119.2, 120));
    [pm, pw, pslog].forEach((e) => (e.style.opacity = 1 - fin));
  };
});
