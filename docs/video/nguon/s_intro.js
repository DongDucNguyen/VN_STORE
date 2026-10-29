// CHƯƠNG I–II: giọt nước, năm nghề, áo dài, montage nét đẹp, thời gian, lý do ra đời, cành tre.

// ---------- Dùng chung ----------
function ripplesAt(t, t0, n = 5, gap = 0.28, dur = 3.2, rmax = 540) {
  const out = [];
  for (let k = 0; k < n; k++) {
    const ti = t0 + k * gap, p = prog(t, ti, ti + dur);
    out.push({ on: t >= ti, p, r: 18 + rmax * eW(p) * (1 - k * 0.07) });
  }
  return out;
}

// Hồ sơ thân bình (u: 0 đáy → 1 miệng).
const VASE_U = [0, 0.1, 0.25, 0.4, 0.55, 0.68, 0.79, 0.9, 1];
const VASE_R = [70, 112, 146, 152, 132, 96, 60, 50, 64];
function vaseR(u) {
  const U = VASE_U, R = VASE_R;
  let i = 0; while (i < U.length - 2 && u > U[i + 1]) i++;
  const f = (u - U[i]) / (U[i + 1] - U[i]);
  const p0 = R[Math.max(0, i - 1)], p1 = R[i], p2 = R[i + 1], p3 = R[Math.min(R.length - 1, i + 2)];
  const f2 = f * f, f3 = f2 * f;
  return 0.5 * (2 * p1 + (-p0 + p2) * f + (2 * p0 - 5 * p1 + 4 * p2 - p3) * f2 + (-p0 + 3 * p1 - 3 * p2 + p3) * f3);
}
function vasePath(cx, base, h, g) {
  // g: 0 = khối đất thấp, 1 = dáng bình
  const pts = [];
  for (let i = 0; i <= 40; i++) {
    const u = i / 40;
    const mound = 155 * Math.pow(Math.max(0, 1 - u * u), 0.55) + 10;
    pts.push([lerp(mound, vaseR(u), g), base - u * h]);
  }
  let d = `M ${cx - pts[0][0]} ${pts[0][1]}`;
  for (const [r, y] of pts) d += ` L ${cx - r} ${y}`;
  for (let i = pts.length - 1; i >= 0; i--) d += ` L ${cx + pts[i][0]} ${pts[i][1]}`;
  return d + " Z";
}

function caption(parent, html, x, y, cls = "cap", style = {}) {
  const e = el("div", { class: cls, style: { left: x + "px", top: y + "px", ...style } }, parent);
  e.innerHTML = html;
  return e;
}
function label(parent, txt, x, y, color = C.muted) {
  const e = el("div", { class: "eyebrow", style: { left: x + "px", top: y + "px", color } }, parent);
  e.innerHTML = `<span class="mark"></span>${txt}`;
  return e;
}

// ---------- S1 · Sớm mai làng nghề (0 – 3.9) ----------
scene(0, 3.9, (root) => {
  const s = svg(root);
  const defs = el("defs", {}, s);
  const sun = el("radialGradient", { id: "dawnSun", cx: "78%", cy: "8%", r: "75%" }, defs);
  el("stop", { offset: 0, "stop-color": "#FFF1CF", "stop-opacity": .95 }, sun); el("stop", { offset: .45, "stop-color": "#F6DDB0", "stop-opacity": .35 }, sun); el("stop", { offset: 1, "stop-color": "#F6DDB0", "stop-opacity": 0 }, sun);
  const ray = el("linearGradient", { id: "ray", x1: 0, y1: 0, x2: 1, y2: 0 }, defs);
  el("stop", { offset: 0, "stop-color": "#FFF4DA", "stop-opacity": 0 }, ray); el("stop", { offset: .5, "stop-color": "#FFF4DA", "stop-opacity": .55 }, ray); el("stop", { offset: 1, "stop-color": "#FFF4DA", "stop-opacity": 0 }, ray);
  const bg = el("rect", { width: W, height: H, fill: "#0c1813" }, s);
  const glow = el("rect", { width: W, height: H, fill: "url(#dawnSun)", opacity: 0 }, s);
  const rays = [0, 1, 2, 3].map((i) => el("rect", { x: -200, y: -60, width: 260 + i * 70, height: 1900, fill: "url(#ray)", transform: `translate(${1150 + i * 210} -300) rotate(32)` }, s));
  const motes = []; for (let i = 0; i < 46; i++) motes.push(el("circle", { r: 1.2 + rand(i, 41) * 2.4, fill: "#FFF6E0" }, s));
  const shadow = el("img", { src: "art/bamboo-shadow-clean.png", class: "abs", style: { left: "380px", top: "160px", width: "1700px", opacity: 0, mixBlendMode: "multiply", transformOrigin: "80% 0%" } }, root);
  const branch = el("img", { src: "art/bamboo-opening-branch.png", class: "abs", style: { left: "1360px", top: "-170px", width: "660px", transformOrigin: "85% 0%", opacity: 0 } }, root);
  const mark = el("div", { class: "abs", style: { left: "170px", top: "300px", width: "64px", height: "2px", background: C.mark, transformOrigin: "left" } }, root);
  const line = caption(root, "<i>Mỗi sớm mai,</i><br>ở một làng nghề nào đó…", 170, 400);
  return (t) => {
    const dawn = eIO(prog(t, 0.1, 2.6));
    bg.setAttribute("fill", dawn < 0.5 ? mix("#0c1813", "#6b5a3e", dawn * 2) : mix("#6b5a3e", "#F5EBD6", (dawn - 0.5) * 2));
    glow.style.opacity = Math.min(1, prog(t, 0.2, 1.6)) * (1 - 0.6 * prog(t, 2.2, 3.4));
    rays.forEach((r, i) => {
      r.setAttribute("transform", `translate(${1150 + i * 210 - t * 18} -300) rotate(${32 + Math.sin(t * 0.6 + i) * 1.2})`);
      r.style.opacity = Math.sin(Math.PI * prog(t, 0.3, 3.6)) * (0.55 - i * 0.08);
    });
    motes.forEach((m, i) => {
      const x = 1000 + (rand(i, 42) - 0.3) * 1100 + Math.sin(t * 0.7 + i) * 30, y = 1080 * rand(i, 43) - t * (14 + 20 * rand(i, 44));
      m.setAttribute("cx", x); m.setAttribute("cy", y);
      m.style.opacity = Math.sin(Math.PI * prog(t, 0.4, 3.7)) * (0.25 + 0.6 * Math.abs(noise1(t * 1.5 + i, i)));
    });
    shadow.style.opacity = 0.34 * eW(prog(t, 1.0, 2.6));
    shadow.style.transform = `translateX(${Math.sin(t * 0.9) * 30}px) rotate(${Math.sin(t * 0.8) * 1.6}deg)`;
    branch.style.opacity = eW(prog(t, 1.2, 2.4)) * (1 - eIO(prog(t, 2.9, 3.6)));
    branch.style.transform = `rotate(${Math.sin(t * 1.5) * 1.3}deg) translateY(${(1 - eW(prog(t, 1.2, 2.6))) * -30}px)`;
    mark.style.transform = `scaleX(${eB(prog(t, 0.9, 1.6))})`;
    mark.style.opacity = 1;
    inkText(line, t, 1.0, 3.55, { fo: 0.45 });
    line.style.color = mix("#ECECE0", C.ink, eIO(prog(t, 1.0, 2.4)));
    // Khi khung ảnh đầu tiên lộ ra, nền sớm mai lui đi, trang giấy ngà của chuỗi ảnh nghề ở lại.
    root.style.opacity = 1 - eIO(prog(t, 3.05, 3.85));
  };
}, 2);

// ---------- Ảnh thật: khung ảnh kiểu ấn phẩm, Ken Burns, lộ ảnh bằng mặt nạ ----------
function photoEl(parent, src, style = {}, pos = "50% 50%") {
  const wrap = el("div", { class: "abs", style: { overflow: "hidden", ...style } }, parent);
  const img = el("img", { src, style: { position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", objectPosition: pos, transformOrigin: "50% 50%" } }, wrap);
  return { wrap, img };
}
// Lộ ảnh từ dưới lên (mặt nạ như dòng chữ “Nếp Việt” của trang chủ) + phóng nhẹ suốt thời gian hiện.
function maskPhoto(ph, t, a, b, { d = 0.95, z0 = 1.09, z1 = 1.0, dx = 0, dy = 0 } = {}) {
  const p = eB(prog(t, a, a + d));
  ph.wrap.style.clipPath = `inset(${(1 - p) * 100}% 0 0 0)`;
  const k = prog(t, a, b);
  ph.img.style.transform = `translate(${dx * k}px, ${dy * k}px) scale(${lerp(z0, z1, eOut(k))})`;
  ph.wrap.style.display = t >= a && t < b + 1.2 ? "block" : "none";
}

// ---------- S2 · Năm nghề, ảnh thật (2.95 – 17.95) ----------
scene(2.95, 17.95, (root) => {
  root.style.background = C.ivory;
  const FX = 900, FY = 120, FW = 860, FH = 830;
  const frameShadow = el("div", { class: "abs", style: { left: FX + "px", top: FY + "px", width: FW + "px", height: FH + "px", boxShadow: "0 40px 90px -45px rgba(34,53,43,.55)" } }, root);
  const P = [
    ["photos/p632.jpg", 3.25, 6.9, "Bát tre · Vietcraft", "50% 45%", "30% 80%"],
    ["photos/p595.jpg", 6.6, 9.9, "Gốm vẽ tay · Minh Long", "50% 50%", "50% 50%"],
    ["photos/p24.jpg", 9.6, 12.7, "Lụa tơ tằm trên khung cửi · Hanhsilk", "50% 60%", "50% 60%"],
    ["photos/p697.jpg", 12.4, 15.6, "Xưởng đan tre · Vietcraft", "40% 50%", "45% 85%"],
    ["photos/p627.jpg", 15.3, 18.2, "Vẽ sơn lên bát tre · Vietcraft", "45% 50%", "30% 85%"],
  ].map(([src, a, b, lb, pos, org], i) => {
    const ph = photoEl(root, src, { left: FX + "px", top: FY + "px", width: FW + "px", height: FH + "px" }, pos);
    ph.img.style.transformOrigin = org;
    return { ph, a, b, lb: label(root, lb, FX, FY + FH + 26), i };
  });
  const rule = el("div", { class: "abs", style: { left: "170px", top: "300px", width: "64px", height: "2px", background: C.mark, transformOrigin: "left" } }, root);
  const cap1 = caption(root, "Có những vẻ đẹp<br><i>không cần vội.</i>", 170, 400);
  const lines = ["Một nét men.", "Một sợi tơ.", "Một nan tre.", "Một lớp sơn."].map((txt, i) => caption(root, txt, 170, 360 + i * 84, "cap sm"));
  return (t) => {
    // Vòng gợn từ điểm giọt nước chạm mặt nước mở ra cả trang giấy.
    frameShadow.style.opacity = eW(prog(t, 3.5, 4.4));
    P.forEach(({ ph, a, b, lb, i }) => {
      if (i === 0) {
        ph.wrap.style.clipPath = `inset(${(1 - eB(prog(t, 3.2, 4.15))) * 100}% 0 0 0)`; ph.wrap.style.display = "block";
        ph.img.style.transform = `scale(${lerp(1.32, 1.18, eOut(prog(t, 3.25, 7.0)))})`;
      } else maskPhoto(ph, t, a, b, { dx: i % 2 ? -18 : 18, z0: i === 3 || i === 4 ? 1.3 : 1.09, z1: i === 3 || i === 4 ? 1.2 : 1.0 });
      inkText(lb, t, a + 0.5, b + 0.1, { dy: 6, blur: 2, fi: 0.5, fo: 0.35 });
    });
    rule.style.transform = `scaleX(${eB(prog(t, 4.6, 5.4))})`;
    rule.style.opacity = 1 - prog(t, 17.4, 17.8);
    inkText(cap1, t, 4.8, 8.4);
    lines.forEach((e, i) => {
      const a = [8.7, 10.3, 13.0, 15.7][i];
      inkText(e, t, a, 17.7, { fo: 0.4 });
      const next = [10.3, 13.0, 15.7, 99][i];
      e.style.color = mix(C.ink, "#9aa196", prog(t, next, next + 0.6));
    });
  };
});

// ---------- Tà áo dài lướt qua bằng chính tấm lụa thật (17.15 – 18.6) ----------
function silkWipe(a, tex = "photos/p248.jpg") {
  scene(a, a + 1.45, (root) => {
    el("img", { src: tex, style: { display: "none" } }, root);
    const s = svg(root);
    const defs = el("defs", {}, s);
    const id = "silk" + Math.round(a * 10);
    const pat = el("pattern", { id, patternUnits: "userSpaceOnUse", width: 2400, height: 3086 }, defs);
    el("image", { href: tex, width: 2400, height: 3086, preserveAspectRatio: "xMidYMid slice" }, pat);
    const sh = el("linearGradient", { id: id + "s", x1: 0, y1: 0, x2: 1, y2: 0.3 }, defs);
    el("stop", { offset: 0, "stop-color": "#fff", "stop-opacity": 0 }, sh); el("stop", { offset: .5, "stop-color": "#fff", "stop-opacity": .22 }, sh); el("stop", { offset: 1, "stop-color": "#fff", "stop-opacity": 0 }, sh);
    const fl = el("filter", { id: id + "b", x: "-20%", y: "-20%", width: "140%", height: "140%" }, defs);
    el("feGaussianBlur", { stdDeviation: 22 }, fl);
    const shadow = el("path", { fill: "#22352B", opacity: .25, filter: `url(#${id}b)` }, s);
    const body = el("path", { fill: `url(#${id})` }, s);
    const gloss = el("path", { fill: `url(#${id}s)` }, s);
    const edge = el("path", { fill: "none", stroke: "#ffffff", "stroke-width": 3, opacity: .35 }, s);
    const lead = (y, t) => 90 * Math.sin(y / 260 + t * 5) + 40 * Math.sin(y / 97 - t * 7);
    const trail = (y, t) => 120 * Math.sin(y / 300 + t * 4 + 1) + 50 * Math.sin(y / 130 + t * 6);
    return (t) => {
      const L = lerp(2150, -500, eIO(prog(t, a, a + 0.7)));
      const T = lerp(1650, -900, eIO(prog(t, a + 0.64, a + 1.3)));
      const ys = []; for (let y = -120; y <= 1200; y += 40) ys.push(y);
      let d = "", e = "";
      ys.forEach((y, i) => { const x = L + lead(y, t) + (y - 540) * 0.18; d += (i ? " L " : "M ") + x + " " + y; e += (i ? " L " : "M ") + (x + 6) + " " + y; });
      for (let i = ys.length - 1; i >= 0; i--) { const y = ys[i]; d += ` L ${Math.max(L, T + trail(y, t) + (y - 540) * 0.25 + 500)} ${y}`; }
      body.setAttribute("d", d + " Z"); gloss.setAttribute("d", d + " Z"); edge.setAttribute("d", e);
      body.querySelector && document.getElementById(id).setAttribute("patternTransform", `translate(${L * 0.35} -900) rotate(-8)`);
      let sd = "";
      ys.forEach((y, i) => { const x = L + lead(y, t) + (y - 540) * 0.18 - 30; sd += (i ? " L " : "M ") + x + " " + y; });
      for (let i = ys.length - 1; i >= 0; i--) sd += ` L ${L + lead(ys[i], t) + 60} ${ys[i]}`;
      shadow.setAttribute("d", sd + " Z");
    };
  }, 10);
}

// ---------- S4a · Tiêu đề “Nét đẹp Việt” bên ảnh áo dài (17.86 – 23.8) ----------
scene(17.86, 23.8, (root) => {
  root.style.background = C.ivory;
  const ph = photoEl(root, "photos/p29.jpg", { left: "1060px", top: "0", width: "860px", height: "1080px" }, "50% 30%");
  ph.img.style.transformOrigin = "75% 0%";
  const credit = label(root, "Khăn lụa vẽ tay · SenSilk", 1100, 1020, C.onScene);
  const eyebrow = el("div", { class: "eyebrow", style: { left: "176px", top: "300px" } }, root);
  eyebrow.innerHTML = '<span class="mark"></span>Đồ Việt · Người Việt · Cuộc sống đẹp hơn';
  const title = el("div", { class: "ftitle", style: { left: "164px", top: "340px", fontSize: "150px", lineHeight: "1.08", whiteSpace: "nowrap" } }, root);
  title.innerHTML = '<span class="mask"><span>Nét đẹp Việt</span></span>';
  const rule = el("div", { class: "abs", style: { left: "176px", top: "560px", width: "130px", height: "3px", background: C.mark, transformOrigin: "left" } }, root);
  const lede = el("div", { class: "fsub", style: { left: "176px", top: "600px", width: "800px", fontSize: "32px" } }, root);
  lede.innerHTML = "Những món đồ thuần Việt — kết tinh của đất, của tơ, của tre và của đôi bàn tay người thợ.";
  return (t) => {
    ph.wrap.style.clipPath = `inset(0 0 0 ${(1 - eB(prog(t, 17.86, 18.9))) * 100}%)`;
    ph.img.style.transform = `scale(${lerp(1.34, 1.24, eOut(prog(t, 17.86, 23.8)))})`;
    inkText(credit, t, 19.2, 23.6, { dy: 6, blur: 2 });
    inkText(eyebrow, t, 18.3, 23.6, { dy: 8, blur: 2 });
    maskLine(title.querySelector(".mask > span"), t, 18.55, 1.0);
    rule.style.transform = `scaleX(${eB(prog(t, 19.1, 19.8))})`;
    inkText(lede, t, 19.7, 23.6);
    const out = eIO(prog(t, 23.15, 23.8));
    root.style.opacity = 1 - out;
    title.style.transform = `translateY(${-out * 20}px)`;
  };
});
// ---------- Cánh sen lướt qua rồi hiện “Nét đẹp Việt” (17.45 – 21.8) ----------
const OPEN_PETAL = "M 0 -120 C 46 -86 62 -20 42 40 C 30 78 12 104 0 120 C -12 104 -30 78 -42 40 C -62 -20 -46 -86 0 -120 Z";
function openPetal(parent, id) {
  const defs = el("defs", {}, parent);
  const g = el("radialGradient", { id, cx: "50%", cy: "85%", r: "90%" }, defs);
  el("stop", { offset: 0, "stop-color": "#FBEFF0" }, g); el("stop", { offset: .55, "stop-color": "#E7AEBB" }, g); el("stop", { offset: 1, "stop-color": "#B9637A" }, g);
  const p = el("g", {}, parent);
  el("path", { d: OPEN_PETAL, fill: `url(#${id})`, stroke: "#97485F", "stroke-width": 1.6 }, p);
  for (let k = -2; k <= 2; k++) el("path", { d: `M 0 110 C ${k * 10} 40 ${k * 16} -30 ${k * 8} -100`, fill: "none", stroke: "#B9637A", "stroke-width": 1, opacity: .45 }, p);
  return p;
}
scene(17.45, 21.8, (root) => {
  const s = svg(root);
  const big = openPetal(s, "opBig");
  const smalls = [openPetal(s, "opS1"), openPetal(s, "opS2")];
  return (t) => {
    const bp = prog(t, 17.45, 18.35);
    big.setAttribute("transform", `translate(${lerp(-1400, 3200, bp)} ${lerp(-500, 1500, bp)}) rotate(${lerp(52, 68, bp)}) scale(${lerp(15, 17, bp)})`);
    op(big, bp < 1 ? 1 : 0);
    // hai cánh nhỏ còn trôi theo gió qua trang tiêu đề
    smalls.forEach((p, i) => {
      const a = 18.2 + i * 0.45, q = prog(t, a, a + 3.0);
      const x = lerp(-80 + i * 60, 2000, eIO(q)), y = lerp(160 + i * 380, 520 + i * 260, q) + Math.sin(q * 8 + i) * 40;
      p.setAttribute("transform", `translate(${x} ${y}) rotate(${70 + q * 220 + i * 40}) scale(${0.34 - i * 0.08}, ${0.22 - i * 0.04})`);
      op(p, q > 0 && q < 1 ? Math.sin(Math.PI * q) * 0.95 : 0);
    });
  };
}, 10);



// ---------- S4b · Montage ảnh thật toàn khung (23.4 – 36.1) ----------
scene(23.4, 36.1, (root) => {
  root.style.background = C.ivory;
  const M = [
    ["photos/p48.jpg", 23.4, 26.25, "Khăn lụa vẽ tay · SenSilk", "50% 40%", [1.24, 1.14, -30, 0], "70% 20%"],
    ["photos/p655.jpg", 26.0, 28.85, "Giỏ đan cỏ biển phơi nắng · Vietcraft", "50% 55%", [1.42, 1.48, 0, -10], "0% 100%"],
    ["photos/p336.jpg", 28.6, 31.45, "Sơn mài · Hanoia", "50% 62%", [1.12, 1.02, 20, 0], "50% 50%"],
    ["photos/p250.jpg", 31.2, 34.05, "Lụa the vân chữ Thọ · Hanhsilk", "50% 50%", [1.14, 1.24, -24, 0], "20% 20%"],
    ["photos/p742.jpg", 33.8, 36.1, "Sô cô la · Marou", "50% 50%", [1.04, 0.98, 430, 0], "50% 50%"],
  ].map(([src, a, b, lb, pos, kb, org]) => {
    const ph = photoEl(root, src, { left: 0, top: 0, width: W + "px", height: H + "px" }, pos);
    ph.img.style.transformOrigin = org;
    if (src.includes("742")) { ph.wrap.style.background = "#F3ECDC"; ph.img.style.objectFit = "contain"; }
    return { ph, a, b, kb, lb };
  });
  const shade = layer(root, "", { background: "linear-gradient(90deg, rgba(12,28,22,.72) 0%, rgba(12,28,22,.42) 38%, rgba(12,28,22,0) 62%)" });
  const shadeB = layer(root, "", { background: "linear-gradient(0deg, rgba(12,28,22,.45) 0%, rgba(12,28,22,0) 22%)" });
  const head = label(root, "Nét đẹp Việt", 170, 200, C.onScene);
  const capA = caption(root, "Công phu<br>trong từng <i>đường nét.</i>", 170, 420, "cap", { color: C.onScene });
  const capB = caption(root, "Tinh tế<br>trong từng <i>chất liệu.</i>", 170, 420, "cap", { color: C.onScene });
  const labels = M.map(({ lb, a, b }) => ({ e: label(root, lb, 1290, 1000, C.onScene), a, b }));
  labels.forEach(({ e }) => { e.style.width = "560px"; e.style.justifyContent = "flex-end"; });
  return (t) => {
    root.style.opacity = eW(prog(t, 23.4, 23.75)) * (1 - eIO(prog(t, 35.5, 36.1)));
    M.forEach(({ ph, a, b, kb }) => {
      const pin = eW(prog(t, a, a + 0.45)), pout = eIO(prog(t, b - 0.35, b));
      ph.wrap.style.display = t >= a && t < b ? "block" : "none";
      ph.wrap.style.opacity = pin;
      const k = prog(t, a, b);
      ph.img.style.transform = `translate(${kb[2] * k}px, ${kb[3] * k}px) scale(${lerp(kb[0], kb[1], k)})`;
      void pout;
    });
    // Ảnh cuối nền kem: chữ chuyển sang mực, bóng tối lui đi.
    const light = eIO(prog(t, 33.8, 34.25));
    shade.style.opacity = shadeB.style.opacity = 1 - light;
    [head, capB].forEach((e) => (e.style.color = mix(C.onScene, C.ink, light)));
    labels.forEach(({ e, a, b }) => { inkText(e, t, a + 0.35, b, { dy: 6, blur: 2, fi: 0.4, fo: 0.3 }); e.style.color = mix(C.onScene, C.muted, light); });
    inkText(head, t, 23.7, 35.7, { dy: 6, blur: 2 });
    inkText(capA, t, 25.5, 30.7);
    inkText(capB, t, 31.1, 35.6);
  };
});

// ---------- S5 · Thời gian & bàn tay (35.5 – 47.4) ----------
scene(35.5, 47.4, (root) => {
  root.style.background = C.ivory;
  const s = svg(root);
  const CX = 1270, CY = 560;
  const arc = el("path", { d: `M ${CX - 720} ${CY + 420} A 720 520 0 0 1 ${CX + 720} ${CY + 420}`, fill: "none", stroke: C.strawD, "stroke-width": 2.5, "stroke-dasharray": "2 16", "stroke-linecap": "round", opacity: .7 }, s);
  const sunG = el("g", {}, s);
  el("circle", { r: 92, fill: C.straw, opacity: .18 }, sunG);
  el("circle", { r: 54, fill: "#E9C77A" }, sunG);
  const shadow = el("ellipse", { cx: CX + 10, cy: CY + 300, rx: 260, ry: 26, fill: C.ink, opacity: .1 }, s);
  const base = el("circle", { cx: CX, cy: CY, r: 286, fill: "#EAD9AE", opacity: 0 }, s);
  const spokes = [], NS = 16;
  for (let k = 0; k < NS; k++) {
    const a = k / NS * Math.PI * 2;
    spokes.push(el("line", { x1: CX + Math.cos(a) * 16, y1: CY + Math.sin(a) * 16, x2: CX + Math.cos(a) * 282, y2: CY + Math.sin(a) * 282, stroke: "#B8964F", "stroke-width": 8, "stroke-linecap": "round" }, s));
  }
  // Xoắn ốc đan: tính sẵn điểm và độ dài cộng dồn.
  const TURNS = 14, R0 = 26, DR = 17.5;
  const pts = [], cum = [0];
  for (let th = 0; th <= TURNS * Math.PI * 2; th += Math.PI / 60) {
    const r = R0 + th / (Math.PI * 2) * DR;
    pts.push([CX + Math.cos(th) * r, CY + Math.sin(th) * r, th]);
    if (pts.length > 1) { const [x0, y0] = pts[pts.length - 2], [x1, y1] = pts[pts.length - 1]; cum.push(cum[cum.length - 1] + Math.hypot(x1 - x0, y1 - y0)); }
  }
  const total = cum[cum.length - 1];
  const dd = pts.map(([x, y], i) => (i ? "L" : "M") + x.toFixed(1) + " " + y.toFixed(1)).join(" ");
  const sOut = el("path", { d: dd, fill: "none", stroke: "#8a6d3b", "stroke-width": 13, "stroke-linecap": "round" }, s);
  const sIn = el("path", { d: dd, fill: "none", stroke: "#DCC285", "stroke-width": 9, "stroke-linecap": "round" }, s);
  const overs = [];
  for (let n = 0; n < TURNS; n++) for (let k = 0; k < NS; k++) if ((k + n) % 2 === 0) {
    const th = k / NS * Math.PI * 2 + n * Math.PI * 2, r = R0 + th / (Math.PI * 2) * DR, a = k / NS * Math.PI * 2;
    const idx = Math.min(pts.length - 1, Math.round(th / (Math.PI / 60)));
    overs.push({ f: cum[idx] / total, e: el("line", { x1: CX + Math.cos(a) * (r - 11), y1: CY + Math.sin(a) * (r - 11), x2: CX + Math.cos(a) * (r + 11), y2: CY + Math.sin(a) * (r + 11), stroke: "#C9A55A", "stroke-width": 8, "stroke-linecap": "round" }, s) });
  }
  const rim = el("circle", { cx: CX, cy: CY, r: 284, fill: "none", stroke: "#8a6d3b", "stroke-width": 16 }, s);
  const rimIn = el("circle", { cx: CX, cy: CY, r: 284, fill: "none", stroke: "#DCC285", "stroke-width": 9, "stroke-dasharray": "10 7" }, s);
  const c1 = caption(root, "Mỗi món đồ là kết tinh<br>của thời gian, kiên nhẫn", 170, 380);
  const c2 = caption(root, "và <i>đôi bàn tay người thợ.</i>", 170, 530);
  return (t) => {
    root.style.opacity = eW(prog(t, 35.5, 36.1)) * (1 - eIO(prog(t, 46.6, 47.4)));
    const day = prog(t, 35.7, 46.8);
    root.style.background = day < 0.5 ? mix(C.ivory, "#F4E9CF", day * 2) : mix("#F4E9CF", "#F2DED0", (day - 0.5) * 2);
    draw(arc, eIO(prog(t, 35.8, 37.2))); arc.style.strokeDasharray = "2 16"; arc.style.strokeDashoffset = 0; op(arc, 0.7 * prog(t, 35.8, 36.6));
    const th = Math.PI * (1 - day);
    sunG.setAttribute("transform", `translate(${CX + Math.cos(th) * 720} ${CY + 420 - Math.sin(th) * 520})`);
    op(sunG, prog(t, 35.9, 36.6));
    spokes.forEach((sp, k) => draw(sp, eB(prog(t, 35.8 + k * 0.05, 36.4 + k * 0.05))));
    const wp = prog(t, 36.6, 45.4);
    const wpe = 1 - Math.pow(1 - wp, 1.25);
    draw(sOut, wpe); draw(sIn, wpe);
    overs.forEach(({ f, e }) => op(e, wpe >= f ? 1 : 0));
    base.style.opacity = 0.0;
    draw(rim, eIO(prog(t, 45.2, 46.0))); draw(rimIn, eIO(prog(t, 45.3, 46.1)));
    rimIn.style.strokeDasharray = "10 7"; rimIn.style.strokeDashoffset = 0; op(rimIn, prog(t, 45.8, 46.1));
    shadow.style.opacity = 0.1 * prog(t, 36, 37);
    inkText(c1, t, 37.0, 46.5);
    inkText(c2, t, 40.0, 46.5);
  };
});

// ---------- S6 · Lý do ra đời (46.7 – 54.3) ----------
scene(46.7, 54.3, (root) => {
  root.style.background = "#F2DED0";
  const s = svg(root);
  const defs = el("defs", {}, s);
  const ink = { fill: "none", stroke: C.ink, "stroke-width": 2.6, "stroke-linecap": "round", "stroke-linejoin": "round" };
  const village = [];
  const add = (d, extra = {}) => { const p = el("path", { d, ...ink, ...extra }, s); village.push(p); return p; };
  add("M 120 860 L 820 860");
  // mái đình cong
  add("M 220 760 Q 300 740 340 700 Q 380 740 460 760 Q 470 750 482 748 M 212 760 Q 200 750 190 748");
  add("M 250 760 L 250 860 M 430 760 L 430 860 M 300 800 L 380 800 L 380 860 M 300 800 L 300 860");
  add("M 270 700 Q 340 670 410 700");
  add("M 500 800 Q 560 780 590 750 Q 620 780 680 800 M 520 800 L 520 860 M 660 800 L 660 860 M 570 820 L 610 820 L 610 860 M 570 820 L 570 860");
  // tre
  [[720, 860, 640], [748, 860, 610], [776, 860, 660], [150, 860, 650], [176, 860, 690]].forEach(([x, y0, y1]) => {
    add(`M ${x} ${y0} Q ${x - 6} ${(y0 + y1) / 2} ${x + 10} ${y1}`, { "stroke-width": 3 });
    for (let k = 0; k < 3; k++) { const yy = y1 + 30 + k * 50; add(`M ${x + 4} ${yy} q 26 -14 48 -6 M ${x} ${yy + 20} q -26 -12 -44 -2`, { "stroke-width": 2, stroke: "#3d6b53" }); }
  });
  // đường đi chấm bi, lộ dần bằng mặt nạ
  const routeD = "M 600 760 C 780 430, 1060 300, 1250 420";
  const rmask = el("mask", { id: "rmask" }, defs);
  const rm = el("path", { d: routeD, fill: "none", stroke: "#fff", "stroke-width": 16, "stroke-linecap": "round" }, rmask);
  el("path", { d: routeD, fill: "none", stroke: C.mark, "stroke-width": 5, "stroke-dasharray": "1 15", "stroke-linecap": "round", mask: "url(#rmask)" }, s);
  const traveler = el("g", {}, s);
  el("rect", { x: -20, y: -16, width: 40, height: 32, rx: 3, fill: "#E9DCC0", stroke: C.ink, "stroke-width": 2 }, traveler);
  el("path", { d: "M -20 0 L 20 0 M 0 -16 L 0 16", stroke: C.strawD, "stroke-width": 2.5 }, traveler);
  // địa cầu
  const GX = 1480, GY = 560, GR = 250;
  const globe = el("g", {}, s);
  el("circle", { cx: GX, cy: GY, r: GR, fill: C.surface, stroke: C.ink, "stroke-width": 2.6 }, globe);
  const mer = []; for (let i = 0; i < 6; i++) mer.push(el("ellipse", { cx: GX, cy: GY, ry: GR, fill: "none", stroke: C.ink, "stroke-width": 1.4, opacity: .35 }, globe));
  for (let j = -2; j <= 2; j++) { const y = GY + j * 82, w = Math.sqrt(GR * GR - (j * 82) ** 2); el("path", { d: `M ${GX - w} ${y} Q ${GX} ${y + 18} ${GX + w} ${y}`, fill: "none", stroke: C.ink, "stroke-width": 1.4, opacity: .35 }, globe); }
  const blooms = [[1390, 450], [1560, 420], [1620, 560], [1430, 640], [1520, 700], [1340, 560], [1600, 650]].map(([x, y]) => {
    const g = el("g", { transform: `translate(${x} ${y})` }, globe);
    const ring = el("circle", { r: 10, fill: "none", stroke: C.lotus, "stroke-width": 2 }, g);
    const dot = el("g", {}, g);
    el("path", { d: "M 0 6 C -10 0 -8 -10 0 -14 C 8 -10 10 0 0 6 Z", fill: C.lotus }, dot);
    el("path", { d: "M 0 6 C -12 6 -16 -2 -16 -8 C -8 -6 -2 0 0 6 Z M 0 6 C 12 6 16 -2 16 -8 C 8 -6 2 0 0 6 Z", fill: C.lotusL }, dot);
    return { ring, dot };
  });
  const c1 = caption(root, "Để những tinh hoa ấy không chỉ nằm lặng lẽ nơi làng nghề,", 170, 150, "cap sm");
  const c2 = caption(root, "mà đi xa hơn — <i>đến gần hơn với bạn bè năm châu.</i>", 170, 214, "cap sm");
  const c3 = el("div", { class: "ftitle", style: { left: "170px", top: "300px", fontSize: "76px", color: C.primary } }, root);
  c3.innerHTML = '<span class="mask"><span>VNStore ra đời.</span></span>';
  return (t) => {
    root.style.opacity = eW(prog(t, 46.7, 47.3));
    village.forEach((p, i) => draw(p, eIO(prog(t, 46.9 + i * 0.045, 47.6 + i * 0.045))));
    const rp = eIO(prog(t, 48.2, 51.0));
    draw(rm, rp);
    const pt = rm.getPointAtLength(rm._L * rp);
    traveler.setAttribute("transform", `translate(${pt.x} ${pt.y - 24}) rotate(${Math.sin(t * 3) * 4})`);
    op(traveler, prog(t, 48.1, 48.4) * (1 - prog(t, 50.9, 51.2)));
    op(globe, eW(prog(t, 47.6, 48.4)));
    globe.setAttribute("transform", `translate(${(1 - eW(prog(t, 47.6, 48.6))) * 60} 0)`);
    mer.forEach((m, i) => { const ph = i / 6 * Math.PI + t * 0.35; m.setAttribute("rx", Math.abs(Math.cos(ph)) * GR); });
    blooms.forEach(({ ring, dot }, i) => {
      const a = 51.0 + i * 0.25, p = prog(t, a, a + 0.6), q = prog(t, a, a + 1.4);
      dot.setAttribute("transform", `scale(${eB(p) * 1.4})`); op(dot, p > 0 ? 1 : 0);
      ring.setAttribute("r", 8 + 40 * eW(q)); ring.style.opacity = q > 0 && q < 1 ? 1 - q : 0;
    });
    inkText(c1, t, 47.5, 54.3, { fo: 0.01 });
    inkText(c2, t, 50.4, 54.3, { fo: 0.01 });
    maskLine(c3.querySelector(".mask > span"), t, 52.4, 0.9);
  };
});

// ---------- S7 · Cành tre lướt qua (53.25 – 55.0) ----------
scene(53.25, 55.0, (root) => {
  const b1 = el("img", { src: "art/bamboo-opening-branch.png", class: "abs", style: { left: "0", top: "0", width: "1500px", transformOrigin: "50% 50%" } }, root);
  const b2 = el("img", { src: "art/bamboo-opening-branch.png", class: "abs", style: { left: "0", top: "0", width: "1300px", transformOrigin: "50% 50%" } }, root);
  const veil = layer(root, "", { background: "rgba(247,243,232,0)" });
  return (t) => {
    const p = eIO(prog(t, 53.25, 54.8));
    const x1 = lerp(2100, -2700, p), x2 = lerp(2600, -2300, eIO(prog(t, 53.35, 54.95)));
    const v = Math.abs(Math.cos(Math.PI * (p - 0.5))) * 9;
    b1.style.transform = `translate(${x1}px, -620px) rotate(-78deg) scale(1.55)`;
    b1.style.filter = `blur(${v}px)`;
    b2.style.transform = `translate(${x2}px, -260px) rotate(-96deg) scale(1.3) scaleX(-1)`;
    b2.style.filter = `blur(${v * 1.2}px) brightness(.85)`;
    veil.style.background = `rgba(247,243,232,${0.55 * Math.sin(Math.PI * prog(t, 53.6, 54.4))})`;
  };
}, 10);
