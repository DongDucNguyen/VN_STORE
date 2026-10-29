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

// ---------- S1 · Giọt nước (0 – 4.6) ----------
scene(0, 4.6, (root) => {
  const s = svg(root);
  const defs = el("defs", {}, s);
  const bg = el("radialGradient", { id: "s1bg", cx: "50%", cy: "58%", r: "75%" }, defs);
  el("stop", { offset: "0", "stop-color": "#1f4a3b" }, bg); el("stop", { offset: "1", "stop-color": "#0a1d17" }, bg);
  const wg = el("linearGradient", { id: "s1w", x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
  el("stop", { offset: "0", "stop-color": "#1a4134" }, wg); el("stop", { offset: "1", "stop-color": "#0b2019" }, wg);
  const dg = el("radialGradient", { id: "s1d", cx: "40%", cy: "60%", r: "70%" }, defs);
  el("stop", { offset: "0", "stop-color": "#ffffff" }, dg); el("stop", { offset: ".6", "stop-color": "#e8efe6" }, dg); el("stop", { offset: "1", "stop-color": "#9fb7aa" }, dg);
  const gl = el("radialGradient", { id: "s1g" }, defs);
  el("stop", { offset: "0", "stop-color": "#F7F3E8", "stop-opacity": ".55" }, gl); el("stop", { offset: "1", "stop-color": "#F7F3E8", "stop-opacity": "0" }, gl);
  el("rect", { width: W, height: H, fill: "url(#s1bg)" }, s);
  el("rect", { y: 640, width: W, height: 440, fill: "url(#s1w)" }, s);
  el("ellipse", { cx: 960, cy: 641, rx: 980, ry: 6, fill: "#F7F3E8", opacity: 0.06 }, s);
  const streaks = [];
  for (let i = 0; i < 12; i++) streaks.push(el("line", { y1: 670 + i * 32, y2: 670 + i * 32, stroke: "#F7F3E8", "stroke-width": 2, "stroke-linecap": "round", opacity: 0.05 + 0.03 * rand(i) }, s));
  // Mép lá sen phía trên, có chóp nhỏ nơi giọt nước tụ lại.
  const leaf = el("path", { d: "M 60 -20 C 420 150, 780 126, 932 134 Q 960 152 988 134 C 1140 126, 1500 150, 1860 -20 Z", fill: "#1d463a", stroke: "#2e5d4c", "stroke-width": 2 }, s);
  for (let i = 0; i < 9; i++) {
    const x = 200 + i * 190;
    el("path", { d: `M 960 -120 Q ${(960 + x) / 2} 40 ${x} ${110 - Math.abs(x - 960) * 0.1}`, stroke: "#2e5d4c", "stroke-width": 1.5, fill: "none", opacity: 0.8 }, s);
  }
  const rings = [];
  for (let k = 0; k < 5; k++) rings.push(el("ellipse", { cx: 960, cy: 640, fill: "none", stroke: "#F7F3E8" }, s));
  const glow = el("circle", { cx: 960, cy: 640, r: 360, fill: "url(#s1g)" }, s);
  const drops = [];
  for (let i = 0; i < 9; i++) drops.push(el("circle", { r: 3 + rand(i, 3) * 3, fill: "#e8efe6" }, s));
  const jet = el("ellipse", { cx: 960, rx: 6, fill: "#e8efe6" }, s);
  const drop = el("g", {}, s);
  el("path", { d: "M0,-34 C9,-15 18,-3 18,9 A18,18 0 0 1 -18,9 C-18,-3 -9,-15 0,-34 Z", fill: "url(#s1d)" }, drop);
  el("ellipse", { cx: -6, cy: 6, rx: 4, ry: 7, fill: "#fff", opacity: 0.9 }, drop);

  return (t) => {
    streaks.forEach((l, i) => {
      const w = 140 + 260 * rand(i, 2), x = 960 + (rand(i, 5) - 0.5) * 1300 + Math.sin(t * 0.6 + i) * 30;
      l.setAttribute("x1", x - w / 2); l.setAttribute("x2", x + w / 2);
    });
    // Giọt tụ ở chóp lá rồi rơi chậm (quay chậm).
    let dy = 152, sc = 0, sy = 1;
    if (t < 1.9) { sc = eW(prog(t, 0.5, 1.8)); sy = 1 + 0.18 * prog(t, 1.3, 1.9); dy = 152 + 14 * prog(t, 0.5, 1.9); }
    else if (t < 3.2) { const p = prog(t, 1.9, 3.2); dy = 166 + 474 * Math.pow(p, 1.7); sc = 1; sy = 1.12 + 0.12 * p; }
    drop.setAttribute("transform", `translate(960 ${dy}) scale(${sc * 0.95} ${sc * sy})`);
    drop.style.opacity = t < 3.2 ? 1 : 0;
    // Vương miện nước và cột bật.
    drops.forEach((d, i) => {
      const tau = t - 3.2 - rand(i, 9) * 0.04;
      if (tau < 0 || tau > 0.9) { d.style.opacity = 0; return; }
      const a = (i / drops.length) * Math.PI * 2, v = 160 + 120 * rand(i, 4), up = 260 + 200 * rand(i, 7);
      const x = 960 + Math.cos(a) * v * tau * 1.6, y = 640 + Math.sin(a) * v * tau * 0.35 - (up * tau - 700 * tau * tau);
      d.setAttribute("cx", x); d.setAttribute("cy", y); d.style.opacity = y > 646 ? 0 : 0.9;
    });
    const jp = prog(t, 3.24, 3.85);
    const jh = 78 * Math.sin(Math.PI * jp);
    jet.setAttribute("cy", 640 - jh / 2); jet.setAttribute("ry", Math.max(0.1, jh / 2)); jet.style.opacity = jp > 0 && jp < 1 ? 0.85 : 0;
    ripplesAt(t, 3.2).forEach((r, k) => {
      const e = rings[k];
      e.setAttribute("rx", r.r); e.setAttribute("ry", r.r * 0.24);
      e.setAttribute("stroke-width", 2.6 * (1 - r.p) + 0.6);
      e.style.opacity = r.on ? Math.pow(1 - r.p, 1.2) * 0.85 : 0;
    });
    glow.style.opacity = t >= 3.2 ? 0.9 * (1 - eOut(prog(t, 3.2, 4.2))) : 0;
    leaf.style.opacity = 1;
    root.style.opacity = 1 - eIO(prog(t, 3.75, 4.55));
  };
});

// ---------- S2 · Năm nghề (3.6 – 17.95) ----------
scene(3.6, 17.95, (root) => {
  root.style.background = C.ivory;
  const s = svg(root);
  const defs = el("defs", {}, s);
  const vg = el("linearGradient", { id: "vaseG", x1: 0, y1: 0, x2: 1, y2: 0 }, defs);
  const vs = [0, 0.33, 0.62, 1].map((o) => el("stop", { offset: o }, vg));
  const kiln = el("radialGradient", { id: "kiln" }, defs);
  el("stop", { offset: 0, "stop-color": "#E9A15A", "stop-opacity": .75 }, kiln); el("stop", { offset: 1, "stop-color": "#E9A15A", "stop-opacity": 0 }, kiln);

  // --- a. bàn xoay gốm ---
  const ga = el("g", {}, s);
  const kilnGlow = el("circle", { cx: 0, cy: -190, r: 420, fill: "url(#kiln)", opacity: 0 }, ga);
  const wheel = el("g", {}, ga);
  el("path", { d: "M -250 0 L -250 40 A 250 44 0 0 0 250 40 L 250 0", fill: "#B79A78", stroke: C.ink, "stroke-width": 2.5 }, wheel);
  el("ellipse", { cx: 0, cy: 0, rx: 250, ry: 44, fill: "#D9C4A3", stroke: C.ink, "stroke-width": 2.5 }, wheel);
  const ticks = el("ellipse", { cx: 0, cy: 0, rx: 205, ry: 36, fill: "none", stroke: C.ink, "stroke-width": 2, "stroke-dasharray": "14 26", opacity: .45 }, wheel);
  const rings = [];
  for (let k = 0; k < 5; k++) rings.push(el("ellipse", { fill: "none", stroke: C.ink, "stroke-dasharray": "28 16", "stroke-linecap": "round" }, ga));
  const vase = el("path", { fill: "url(#vaseG)", stroke: C.ink, "stroke-width": 2.6, "stroke-linejoin": "round" }, ga);
  const lip = el("ellipse", { fill: "#8f5b3a", stroke: C.ink, "stroke-width": 2.4 }, ga);
  const throws = [];
  for (let i = 0; i < 6; i++) throws.push(el("path", { fill: "none", stroke: C.ink, "stroke-width": 1.6, "stroke-dasharray": "40 22", opacity: .35 }, ga));
  // Họa tiết sen men lam, vẽ theo nét cọ.
  const motif = el("g", {}, ga);
  const MP = [
    "M 0 40 C -10 10 -6 -30 0 -62 C 6 -30 10 10 0 40",
    "M 0 40 C -30 26 -52 -6 -50 -44 C -26 -30 -8 0 0 40",
    "M 0 40 C 30 26 52 -6 50 -44 C 26 -30 8 0 0 40",
    "M -2 40 C -50 46 -86 24 -96 -10 C -60 -8 -26 12 -2 40",
    "M 2 40 C 50 46 86 24 96 -10 C 60 -8 26 12 2 40",
    "M 0 44 C 4 80 -6 110 -30 140",
    "M -30 120 C -90 96 -140 112 -150 146 C -104 168 -56 150 -30 120",
    "M -150 146 C -110 132 -70 128 -30 122",
  ];
  const motifPaths = MP.map((d) => el("path", { d, fill: "none", stroke: C.blue, "stroke-width": 3.2, "stroke-linecap": "round", "stroke-linejoin": "round" }, motif));
  const motifFill = el("g", { opacity: 0 }, motif);
  MP.slice(0, 5).forEach((d) => el("path", { d, fill: C.blue, opacity: .16 }, motifFill));
  const brush = el("g", {}, s);
  el("line", { x1: 0, y1: 0, x2: 120, y2: -150, stroke: "#6b4a2b", "stroke-width": 9, "stroke-linecap": "round" }, brush);
  el("path", { d: "M 0 0 C -4 -10 4 -26 16 -30 L 26 -18 C 20 -8 10 0 0 0 Z", fill: "#1b2a24" }, brush);

  // --- c. tơ và khung cửi ---
  const gc = el("g", {}, s);
  const cocoon = el("g", { transform: "translate(980 560) rotate(-14)" }, gc);
  el("ellipse", { rx: 74, ry: 46, fill: "#F3E2B0", stroke: C.ink, "stroke-width": 2.4 }, cocoon);
  for (let i = -3; i <= 3; i++) el("path", { d: `M ${-60 + Math.abs(i) * 6} ${i * 10} Q 0 ${i * 13 + 6} ${60 - Math.abs(i) * 6} ${i * 10}`, fill: "none", stroke: "#C9A55A", "stroke-width": 1.2 }, cocoon);
  const thread = el("path", { d: "M 1048 548 C 1120 420, 1170 660, 1240 520 S 1320 450, 1352 560", fill: "none", stroke: "#C9A24E", "stroke-width": 3, "stroke-linecap": "round" }, gc);
  const loom = el("g", {}, gc);
  el("rect", { x: 1352, y: 330, width: 360, height: 430, fill: "none", stroke: C.ink, "stroke-width": 3, rx: 4 }, loom);
  const warps = [];
  for (let i = 0; i < 16; i++) warps.push(el("line", { x1: 1374 + i * 21, x2: 1374 + i * 21, y1: 344, y2: 746, stroke: "#8f7a55", "stroke-width": 1.4 }, loom));
  const wefts = [];
  for (let j = 0; j < 26; j++) {
    const y = 740 - j * 15.5;
    wefts.push(el("path", { d: `M 1366 ${y} Q 1532 ${y + (j % 2 ? 3 : -3)} 1698 ${y}`, fill: "none", stroke: mix("#E8C77A", C.lotusL, j / 26), "stroke-width": 13, "stroke-linecap": "butt" }, loom));
  }
  const shuttle = el("path", { d: "M -34 0 Q 0 -12 34 0 Q 0 12 -34 0 Z", fill: "#8a5a34", stroke: C.ink, "stroke-width": 1.5 }, loom);
  const glints = [];
  for (let i = 0; i < 4; i++) glints.push(el("path", { d: "M 0 -11 L 2.5 -2.5 L 11 0 L 2.5 2.5 L 0 11 L -2.5 2.5 L -11 0 L -2.5 -2.5 Z", fill: "#fff7dc" }, gc));

  // --- d. nan đan ---
  const gd = el("g", {}, s);
  const matShadow = el("ellipse", { cx: 1240, cy: 860, rx: 300, ry: 26, fill: "#22352B", opacity: .12 }, gd);
  const mat = el("g", { transform: "translate(1240 540) rotate(45)" }, gd);
  const N = 9, SW = 46, GAP = 6, TOT = N * SW + (N - 1) * GAP, H0 = -TOT / 2;
  const matClip = el("clipPath", { id: "matClip" }, defs);
  el("rect", { x: H0, y: H0, width: TOT, height: TOT }, matClip);
  const warpEls = [], weftEls = [], overs = [];
  for (let i = 0; i < N; i++) warpEls.push(el("rect", { x: H0 + i * (SW + GAP), y: H0, width: SW, height: TOT, fill: "#D8BD7A", stroke: "#8a6d3b", "stroke-width": 1.4, rx: 3 }, mat));
  for (let j = 0; j < N; j++) {
    const holder = el("g", { "clip-path": "url(#matClip)" }, mat);
    const row = el("g", {}, holder);
    weftEls.push(row);
    el("rect", { x: H0, y: H0 + j * (SW + GAP), width: TOT, height: SW, fill: j % 2 ? "#C9A55A" : "#D2B26A", stroke: "#8a6d3b", "stroke-width": 1.4, rx: 3 }, row);
    for (let i = 0; i < N; i++) if ((i + j) % 2 === 0) {
      overs.push({ j, i, e: el("rect", { x: H0 + i * (SW + GAP), y: H0 + j * (SW + GAP) - 3, width: SW, height: SW + 6, fill: "#D8BD7A", stroke: "#8a6d3b", "stroke-width": 1.4 }, mat) });
    }
  }
  const sheen = el("rect", { x: H0 - 200, y: H0 - 600, width: 120, height: TOT + 1200, fill: "#fff", opacity: 0, "clip-path": "url(#matClip)" }, mat);

  // --- e. sơn mài ---
  const ge = el("g", {}, s);
  const PX = 920, PY = 300, PW = 640, PH = 440;
  const pclip = el("clipPath", { id: "pclip" }, defs);
  el("rect", { x: PX, y: PY, width: PW, height: PH, rx: 8 }, pclip);
  const gold = el("linearGradient", { id: "gold", x1: 0, y1: 0, x2: 1, y2: 1 }, defs);
  el("stop", { offset: 0, "stop-color": "#F0D489" }, gold); el("stop", { offset: .5, "stop-color": "#C9A04B" }, gold); el("stop", { offset: 1, "stop-color": "#E7C56F" }, gold);
  const art = el("g", { "clip-path": "url(#pclip)" }, ge);
  el("rect", { x: PX, y: PY, width: PW, height: PH, fill: "#5b1e14" }, art);
  [[1040, 640, 120], [1250, 600, 90], [1440, 660, 130], [1150, 470, 70]].forEach(([x, y, r]) => {
    el("ellipse", { cx: x, cy: y, rx: r, ry: r * 0.42, fill: "url(#gold)" }, art);
    for (let k = 0; k < 7; k++) { const a = Math.PI * (k / 6); el("line", { x1: x, y1: y, x2: x + Math.cos(a) * r * .95, y2: y - Math.sin(a) * r * .4, stroke: "#8a6526", "stroke-width": 1.4 }, art); }
  });
  [[1100, 420], [1330, 470]].forEach(([x, y]) => {
    el("path", { d: `M ${x} ${y + 90} L ${x} ${y + 150}`, stroke: "url(#gold)", "stroke-width": 4 }, art);
    el("path", { d: `M ${x} ${y + 90} C ${x - 40} ${y + 60} ${x - 30} ${y + 10} ${x} ${y} C ${x + 30} ${y + 10} ${x + 40} ${y + 60} ${x} ${y + 90} Z`, fill: "#E7A9A3", stroke: "#C9A04B", "stroke-width": 2 }, art);
  });
  for (let i = 0; i < 90; i++) {
    const x = PX + 40 + rand(i, 11) * (PW - 80), yb = PY + 70 + 90 * Math.sin((x - PX) / PW * Math.PI) * 0.6;
    const y = yb + rand(i, 12) * 70, r = 6 + rand(i, 13) * 9;
    const pts = [0, 1, 2, 3, 4].map((k) => { const a = k / 5 * Math.PI * 2 + rand(i * 5 + k, 14); const rr = r * (0.6 + 0.5 * rand(i * 7 + k, 15)); return `${x + Math.cos(a) * rr},${y + Math.sin(a) * rr}`; });
    el("polygon", { points: pts.join(" "), fill: "#F6F1E4", stroke: "#d8cdb3", "stroke-width": .8 }, art);
  }
  const shimmerG = el("linearGradient", { id: "shim", x1: 0, y1: 0, x2: 1, y2: 0 }, defs);
  el("stop", { offset: 0, "stop-color": "#fff", "stop-opacity": 0 }, shimmerG); el("stop", { offset: .5, "stop-color": "#fff", "stop-opacity": .55 }, shimmerG); el("stop", { offset: 1, "stop-color": "#fff", "stop-opacity": 0 }, shimmerG);
  const shimmer = el("rect", { x: 0, y: PY - 100, width: 220, height: PH + 200, fill: "url(#shim)", "clip-path": "url(#pclip)", style: { mixBlendMode: "screen" } }, ge);
  const lmask = el("mask", { id: "lmask" }, defs);
  el("rect", { x: 0, y: 0, width: W, height: H, fill: "#fff" }, lmask);
  const sand = el("path", { d: `M ${PX - 40} ${PY + 60} L ${PX + PW + 40} ${PY + 40} L ${PX - 40} ${PY + 190} L ${PX + PW + 40} ${PY + 210} L ${PX - 40} ${PY + 330} L ${PX + PW + 40} ${PY + 360} L ${PX - 20} ${PY + 470}`, fill: "none", stroke: "#000", "stroke-width": 150, "stroke-linecap": "round", "stroke-linejoin": "round" }, lmask);
  const lacquer = el("rect", { x: PX, y: PY, width: PW, height: PH, rx: 8, fill: "#1b1210", mask: "url(#lmask)" }, ge);
  el("rect", { x: PX, y: PY, width: PW, height: PH, rx: 8, fill: "none", stroke: C.ink, "stroke-width": 3 }, ge);
  const pad = el("rect", { x: -34, y: -22, width: 68, height: 44, rx: 10, fill: "#7d8f78", stroke: C.ink, "stroke-width": 2 }, ge);

  // --- chữ ---
  const cap1 = caption(root, "Có những vẻ đẹp<br><i>không cần vội.</i>", 170, 400);
  const lines = ["Một nét men.", "Một sợi tơ.", "Một nan tre.", "Một lớp sơn."].map((txt, i) => caption(root, txt, 170, 330 + i * 84, "cap sm"));
  const labels = [["Gốm", 4.9, 6.4], ["Men lam", 6.9, 9.4], ["Tơ tằm", 9.9, 12.3], ["Mây tre đan", 12.8, 15.2], ["Sơn mài", 15.6, 17.8]].map(([txt, a, b]) => ({ e: label(root, txt, 1240 - 260, 900), a, b }));

  return (t) => {
    root.style.opacity = eIO(prog(t, 3.7, 4.5));
    // a. vòng gợn → vòng bàn xoay (nhìn từ trên) → bàn xoay nghiêng.
    const toTop = eIO(prog(t, 3.6, 4.4)), toSide = eIO(prog(t, 4.6, 5.3)), settle = eIO(prog(t, 4.2, 4.9));
    const gx = lerp(960, 1240, eIO(prog(t, 4.6, 5.6)));
    const baseY = lerp(560, 760, toSide);
    const exitA = eIO(prog(t, 9.3, 9.9));
    ga.setAttribute("transform", `translate(${gx - exitA * 420} 0)`);
    op(ga, 1 - exitA);
    ripplesAt(t, 3.2).forEach((r, k) => {
      const e = rings[k];
      const wheelR = 70 + k * 44;
      const rad = lerp(r.r, wheelR, settle);
      const ratio = lerp(lerp(0.24, 1, toTop), 0.18, toSide);
      e.setAttribute("cx", 0); e.setAttribute("cy", lerp(lerp(640, 560, toTop), 760, toSide) - 0);
      e.setAttribute("rx", rad); e.setAttribute("ry", rad * ratio);
      e.setAttribute("stroke-width", lerp(2.6 * (1 - r.p) + 0.6, 2, settle));
      e.style.strokeDashoffset = (k % 2 ? 1 : -1) * t * 160;
      e.style.opacity = Math.max(r.on ? Math.pow(1 - r.p, 1.2) * 0.85 : 0, settle * 0.5) * (1 - eIO(prog(t, 5.0, 5.6)));
    });
    wheel.setAttribute("transform", `translate(0 ${baseY})`);
    op(wheel, toSide * (1 - eIO(prog(t, 6.3, 6.9))));
    ticks.style.strokeDashoffset = -t * 420;
    // Đất lên thành bình, rồi nung thành men.
    const grow = eIO(prog(t, 5.2, 6.5)), fire = eIO(prog(t, 6.25, 6.85));
    const sc = lerp(1, 1.22, eIO(prog(t, 6.4, 7.1)));
    const hgt = lerp(95, 380, grow);
    const by = lerp(baseY, 760, fire);
    vase.setAttribute("d", vasePath(0, by, hgt, grow));
    vase.setAttribute("transform", `translate(0 ${by}) scale(${sc}) translate(0 ${-by})`);
    lip.setAttribute("transform", vase.getAttribute("transform"));
    lip.setAttribute("cx", 0); lip.setAttribute("cy", by - hgt); lip.setAttribute("rx", lerp(10, 66, grow)); lip.setAttribute("ry", lerp(4, 12, grow));
    op(vase, prog(t, 5.0, 5.4)); op(lip, prog(t, 5.6, 6.0));
    const cl = ["#8a5634", "#D9A57C", "#C48A5E", "#7d4a2c"], gz = ["#cfc6b3", "#FFFDF7", "#F3EEE2", "#c9bfa9"];
    vs.forEach((st, i) => st.setAttribute("stop-color", mix(cl[i], gz[i], fire)));
    lip.setAttribute("fill", mix("#8f5b3a", "#d8cfbb", fire));
    kilnGlow.setAttribute("cy", by - 190); kilnGlow.style.opacity = Math.sin(Math.PI * prog(t, 6.05, 7.0)) * 0.9;
    throws.forEach((p, i) => {
      const u = 0.12 + i * 0.13, y = by - u * hgt, r = lerp(155 * Math.pow(Math.max(0, 1 - u * u), 0.55) + 10, vaseR(u), grow) - 4;
      p.setAttribute("d", `M ${-r} ${y} Q 0 ${y + r * 0.12} ${r} ${y}`);
      p.setAttribute("transform", vase.getAttribute("transform"));
      p.style.strokeDashoffset = -t * 300;
      op(p, 0.35 * prog(t, 5.1, 5.5) * (1 - fire));
    });
    // b. vẽ men lam.
    const mx = 0, my = by - 0.4 * hgt;
    motif.setAttribute("transform", `translate(0 ${by}) scale(${sc}) translate(0 ${-by}) translate(${mx} ${my}) scale(.95)`);
    const seg = [6.95, 7.25, 7.55, 7.85, 8.15, 8.45, 8.7, 9.05, 9.25];
    let tip = null;
    motifPaths.forEach((p, i) => {
      const pp = prog(t, seg[i], seg[i + 1]);
      draw(p, pp);
      if (pp > 0 && pp < 1) { const L = p._L * pp, pt = p.getPointAtLength(L); tip = pt; }
    });
    motifFill.style.opacity = 0.9 * prog(t, 8.5, 9.2);
    if (tip && t < 9.3) {
      const k = sc * 0.95, bx = gx + (tip.x * k) + mx * sc, byy = by + (my - by) * sc + tip.y * k;
      brush.setAttribute("transform", `translate(${bx} ${byy})`); op(brush, 1);
    } else op(brush, 0);

    // c. tơ.
    const cIn = eW(prog(t, 9.5, 10.1)), cOut = eIO(prog(t, 12.3, 12.8));
    gc.setAttribute("transform", `translate(${(1 - cIn) * 160 - cOut * 300} 0)`); op(gc, cIn * (1 - cOut));
    draw(thread, eIO(prog(t, 9.8, 10.8)));
    warps.forEach((w, i) => op(w, prog(t, 9.7 + i * 0.03, 10.0 + i * 0.03)));
    let rowY = 740;
    wefts.forEach((w, j) => {
      const a = 10.5 + j * 0.068, p = prog(t, a, a + 0.12);
      draw(w, p);
      w.style.strokeDasharray = `${w._L} ${w._L}`;
      if (j % 2) w.style.strokeDashoffset = -w._L * (1 - p);
      if (p > 0) rowY = 740 - j * 15.5;
    });
    const sp = (t * 1.9) % 2, sxp = sp < 1 ? sp : 2 - sp;
    shuttle.setAttribute("transform", `translate(${1380 + sxp * 300} ${rowY - 2})`); op(shuttle, prog(t, 10.4, 10.6) * (1 - prog(t, 12.1, 12.3)));
    glints.forEach((g, i) => {
      const L = thread._L || thread.getTotalLength(), f = ((t * 0.45 + i / 4) % 1);
      const pt = thread.getPointAtLength(L * f);
      g.setAttribute("transform", `translate(${pt.x} ${pt.y}) scale(${0.6 + 0.6 * Math.sin(Math.PI * f)}) rotate(${t * 90})`);
      op(g, prog(t, 10.8, 11.2) * Math.sin(Math.PI * f));
    });

    // d. nan đan.
    const dIn = eW(prog(t, 12.4, 12.9)), dOut = eIO(prog(t, 15.1, 15.6));
    op(gd, dIn * (1 - dOut)); gd.setAttribute("transform", `translate(${-dOut * 300} 0)`);
    warpEls.forEach((w, i) => { const p = eB(prog(t, 12.45 + i * 0.05, 12.95 + i * 0.05)); w.setAttribute("transform", `translate(0 ${(1 - p) * -560})`); op(w, p); });
    weftEls.forEach((row, j) => {
      const a = 12.95 + j * 0.17, p = eB(prog(t, a, a + 0.42));
      const off = (1 - p) * -(TOT + 120);
      row.setAttribute("transform", `translate(${off} 0)`); op(row, p > 0 ? 1 : 0);
    });
    overs.forEach(({ j, i, e }) => {
      const a = 12.95 + j * 0.17, p = eB(prog(t, a, a + 0.42));
      const front = H0 + TOT + (1 - p) * -(TOT + 120);
      op(e, front > H0 + i * (SW + GAP) + SW * 0.5 ? 1 : 0);
    });
    const shp = prog(t, 14.75, 15.35);
    sheen.setAttribute("x", H0 - 200 + shp * (TOT + 400)); sheen.style.opacity = Math.sin(Math.PI * shp) * 0.45;
    matShadow.style.opacity = 0.12 * dIn;

    // e. sơn mài.
    const eIn2 = eW(prog(t, 15.3, 15.8));
    op(ge, eIn2); ge.setAttribute("transform", `translate(${(1 - eIn2) * 160} 0)`);
    const sp2 = eIO(prog(t, 15.7, 17.5));
    draw(sand, sp2);
    if (sp2 > 0 && sp2 < 1) { const pt = sand.getPointAtLength(sand._L * sp2); pad.setAttribute("transform", `translate(${pt.x} ${pt.y}) rotate(${Math.sin(t * 20) * 6})`); op(pad, 1); }
    else op(pad, 0);
    const shp2 = prog(t, 16.6, 17.8);
    shimmer.setAttribute("x", PX - 240 + shp2 * (PW + 480)); shimmer.style.opacity = Math.sin(Math.PI * shp2);

    // chữ
    inkText(cap1, t, 4.8, 8.4);
    lines.forEach((e, i) => {
      const a = [8.7, 10.3, 13.0, 15.7][i];
      inkText(e, t, a, 17.7, { fo: 0.4 });
      const next = [10.3, 13.0, 15.7, 99][i];
      e.style.color = mix(C.ink, "#9aa196", prog(t, next, next + 0.6));
    });
    labels.forEach(({ e, a, b }) => inkText(e, t, a, b, { dy: 8, blur: 3, fi: 0.5, fo: 0.4 }));
  };
});

// ---------- Lụa áo dài lướt qua (17.15 – 18.6) ----------
function silkWipe(a, colors = [C.lotusL, "#F6E7E4", C.lotus]) {
  scene(a, a + 1.45, (root) => {
    const s = svg(root);
    const defs = el("defs", {}, s);
    const id = "silk" + Math.round(a * 10);
    const g = el("linearGradient", { id, x1: 0, y1: 0, x2: 1, y2: 0.35 }, defs);
    el("stop", { offset: 0, "stop-color": colors[0] }, g); el("stop", { offset: .45, "stop-color": colors[1] }, g); el("stop", { offset: 1, "stop-color": colors[2] }, g);
    const fl = el("filter", { id: id + "b", x: "-20%", y: "-20%", width: "140%", height: "140%" }, defs);
    el("feGaussianBlur", { stdDeviation: 22 }, fl);
    const shadow = el("path", { fill: "#22352B", opacity: .22, filter: `url(#${id}b)` }, s);
    const body = el("path", { fill: `url(#${id})` }, s);
    const folds = [];
    for (let i = 0; i < 6; i++) folds.push(el("path", { fill: "none", stroke: i % 2 ? "#ffffff" : "#8f3f52", "stroke-width": i % 2 ? 5 : 3, opacity: i % 2 ? 0.35 : 0.18, "stroke-linecap": "round" }, s));
    const lead = (y, t) => 90 * Math.sin(y / 260 + t * 5) + 40 * Math.sin(y / 97 - t * 7);
    const trail = (y, t) => 120 * Math.sin(y / 300 + t * 4 + 1) + 50 * Math.sin(y / 130 + t * 6);
    return (t) => {
      const L = lerp(2150, -500, eIO(prog(t, a, a + 0.7)));
      const T = lerp(1650, -900, eIO(prog(t, a + 0.64, a + 1.3)));
      const ys = []; for (let y = -120; y <= 1200; y += 40) ys.push(y);
      let d = "";
      ys.forEach((y, i) => { const x = L + lead(y, t) + (y - 540) * 0.18; d += (i ? " L " : "M ") + x + " " + y; });
      for (let i = ys.length - 1; i >= 0; i--) { const y = ys[i]; d += ` L ${Math.max(L, T + trail(y, t) + (y - 540) * 0.25 + 500)} ${y}`; }
      body.setAttribute("d", d + " Z");
      let sd = "";
      ys.forEach((y, i) => { const x = L + lead(y, t) + (y - 540) * 0.18 - 30; sd += (i ? " L " : "M ") + x + " " + y; });
      for (let i = ys.length - 1; i >= 0; i--) sd += ` L ${L + lead(ys[i], t) + 60} ${ys[i]}`;
      shadow.setAttribute("d", sd + " Z");
      folds.forEach((f, k) => {
        let fd = "";
        ys.forEach((y, i) => {
          const xl = L + lead(y, t) + (y - 540) * 0.18, xr = Math.max(xl, T + trail(y, t) + (y - 540) * 0.25 + 500);
          const fr = (k + 1) / 7, x = lerp(xl, Math.min(xr, xl + 2600), fr) + 30 * Math.sin(y / 180 + t * 6 + k);
          fd += (i ? " L " : "M ") + x + " " + y;
        });
        f.setAttribute("d", fd);
      });
    };
  }, 10);
}

// ---------- S4a · Tiêu đề “Nét đẹp Việt” (17.86 – 23.8) ----------
scene(17.86, 23.8, (root) => {
  root.style.background = C.ivory;
  const shadow = el("img", { src: "art/bamboo-shadow-clean.png", class: "abs", style: { left: "560px", top: "330px", width: "1500px", opacity: .32 } }, root);
  const branch = el("img", { src: "art/bamboo-opening-branch.png", class: "abs", style: { left: "1320px", top: "-160px", width: "720px", transformOrigin: "85% 0%" } }, root);
  const lotus = el("img", { src: "art/lotus-botanical-01.png", class: "abs", style: { left: "-30px", top: "640px", width: "330px", opacity: .5 } }, root);
  const eyebrow = el("div", { class: "eyebrow", style: { left: "212px", top: "300px" } }, root);
  eyebrow.innerHTML = '<span class="mark"></span>Đồ Việt · Người Việt · Cuộc sống đẹp hơn';
  const title = el("div", { class: "ftitle", style: { left: "196px", top: "336px", fontSize: "200px", lineHeight: "1.08" } }, root);
  title.innerHTML = '<span class="mask"><span>Nét đẹp Việt</span></span>';
  const rule = el("div", { class: "abs", style: { left: "212px", top: "610px", width: "130px", height: "3px", background: C.mark, transformOrigin: "left" } }, root);
  const lede = el("div", { class: "fsub", style: { left: "212px", top: "650px", width: "1300px", fontSize: "32px", whiteSpace: "nowrap" } }, root);
  lede.innerHTML = "Những món đồ thuần Việt — kết tinh của đất, của tơ, của tre<br>và của đôi bàn tay người thợ.";
  return (t) => {
    const sway = Math.sin((t - 17.9) * Math.PI / 2.1) * 1.3;
    branch.style.transform = `rotate(${sway}deg) translateY(${(1 - eW(prog(t, 17.9, 19))) * -40}px)`;
    shadow.style.transform = `translateX(${Math.sin(t * 0.9) * 24}px) skewX(${Math.sin(t * 0.9) * 2}deg)`;
    lotus.style.transform = `translateY(${(1 - eW(prog(t, 18.2, 20))) * 40 + Math.sin(t * 0.7) * 6}px)`;
    lotus.style.opacity = 0.5 * eW(prog(t, 18.2, 19.4));
    inkText(eyebrow, t, 18.3, 23.6, { dy: 8, blur: 2 });
    maskLine(title.querySelector(".mask > span"), t, 18.55, 1.0);
    rule.style.transform = `scaleX(${eB(prog(t, 19.1, 19.8))})`;
    inkText(lede, t, 19.7, 23.6);
    const out = eIO(prog(t, 23.15, 23.8));
    root.style.opacity = 1 - out;
    title.style.transform = `translateY(${-out * 20}px)`;
  };
});
silkWipe(17.15);

// ---------- S4b · Montage nét đẹp (23.4 – 36.0) ----------
scene(23.4, 36.1, (root) => {
  root.style.background = C.ivory;
  const dark = layer(root, "", { background: `radial-gradient(ellipse at 65% 40%, #22493b 0%, ${C.forest} 55%, ${C.forestD} 100%)` });
  const s = svg(root);
  const defs = el("defs", {}, s);
  const lg = (id, stops, x2 = 0, y2 = 1) => { const g = el("linearGradient", { id, x1: 0, y1: 0, x2, y2 }, defs); stops.forEach(([o, c]) => el("stop", { offset: o, "stop-color": c }, g)); return g; };
  lg("aoG", [[0, "#E7B7C2"], [1, "#B9637A"]]);
  lg("nonG", [[0, "#F2E2B5"], [.55, "#DCC285"], [1, "#B99A58"]], 1, 1);
  lg("tuiG", [[0, "#E1C584"], [1, "#B8964F"]]);
  lg("khanG", [[0, "#F3D9DF"], [.5, "#FFF8F2"], [1, "#E7B7C2"]], 1, 0);

  // v1 · áo dài
  const v1 = el("g", {}, s);
  el("circle", { cx: 1250, cy: 450, r: 300, fill: C.straw, opacity: .22 }, v1);
  const ao = el("g", { transform: "translate(1250 150)" }, v1);
  const pants = el("path", { fill: "#FBF7EE", stroke: C.ink, "stroke-width": 2.2 }, ao);
  const backFlap = el("path", { fill: "#A9546B", stroke: C.ink, "stroke-width": 2.2 }, ao);
  const bodyP = el("path", { fill: "url(#aoG)", stroke: C.ink, "stroke-width": 2.6, "stroke-linejoin": "round" }, ao);
  el("rect", { x: -30, y: 0, width: 60, height: 36, rx: 8, fill: "#C46F86", stroke: C.ink, "stroke-width": 2.4 }, ao);
  el("path", { d: "M 6 36 Q 40 70 96 150", fill: "none", stroke: C.ink, "stroke-width": 2 }, ao);
  [0.2, 0.45, 0.7].forEach((f) => el("circle", { cx: 6 + 90 * f, cy: 36 + 114 * f * f, r: 4, fill: C.straw, stroke: C.ink, "stroke-width": 1 }, ao));
  const embroidery = el("g", {}, ao);
  const flapD = (t, sign, dx = 0, ph = 0) => {
    const pts = [];
    for (let y = 330; y <= 760; y += 30) { const k = (y - 330) / 430; pts.push([k, y, 34 * Math.sin(t * 2.3 + y / 120 + ph) * k * k]); }
    let d = `M ${-96 + dx} 330`;
    pts.forEach(([k, y, w]) => { d += ` L ${-96 - 18 * k + dx + w} ${y}`; });
    const wb = pts[pts.length - 1][2];
    d += ` Q ${dx + wb} 790 ${112 + dx + wb} 760`;
    for (let i = pts.length - 1; i >= 0; i--) { const [k, y, w] = pts[i]; d += ` L ${96 + 18 * k + dx + w} ${y}`; }
    return d + " Z";
  };
  // v2 · nón lá
  const v2 = el("g", {}, s);
  el("ellipse", { cx: 1250, cy: 700, rx: 360, ry: 40, fill: C.ink, opacity: .1 }, v2);
  const non = el("g", {}, v2);
  const AX = 1250, AY = 250, BY = 640, RX = 390, RY = 74;
  const nonClip = el("clipPath", { id: "nonClip" }, defs);
  const coneD = `M ${AX} ${AY} L ${AX - RX} ${BY} A ${RX} ${RY} 0 0 0 ${AX + RX} ${BY} Z`;
  el("path", { d: coneD }, nonClip);
  el("path", { d: coneD, fill: "url(#nonG)", stroke: C.ink, "stroke-width": 2.6, "stroke-linejoin": "round" }, non);
  const ribs = [];
  for (let i = 1; i < 16; i++) { const a = Math.PI * (i / 16); ribs.push(el("path", { d: `M ${AX} ${AY} L ${AX - Math.cos(a) * RX} ${BY + Math.sin(a) * RY}`, stroke: "#9c7f45", "stroke-width": 1.3, fill: "none" }, non)); }
  const vong = [];
  for (let k = 1; k <= 8; k++) { const f = k / 9; vong.push(el("path", { d: `M ${AX - RX * f} ${AY + (BY - AY) * f} A ${RX * f} ${RY * f} 0 0 0 ${AX + RX * f} ${AY + (BY - AY) * f}`, stroke: "#9c7f45", "stroke-width": 1.4, fill: "none" }, non)); }
  const quai = el("path", { d: `M ${AX - 250} ${BY + 40} Q ${AX} ${BY + 210} ${AX + 250} ${BY + 40}`, stroke: C.lotus, "stroke-width": 5, fill: "none", "stroke-linecap": "round" }, non);
  const nonSheen = el("rect", { x: 0, y: 200, width: 160, height: 560, fill: "#fff", opacity: 0, "clip-path": "url(#nonClip)", transform: "skewX(-18)" }, non);
  // v3 · đèn lồng
  const v3 = el("g", {}, s);
  const glowG = el("radialGradient", { id: "lanG" }, defs);
  el("stop", { offset: 0, "stop-color": "#FFD48A", "stop-opacity": .55 }, glowG); el("stop", { offset: 1, "stop-color": "#FFD48A", "stop-opacity": 0 }, glowG);
  el("path", { d: "M 760 110 Q 1260 210 1800 130", stroke: "#c9b98a", "stroke-width": 2, fill: "none", opacity: .8 }, v3);
  const lanterns = [[1000, 158, 190, "#B8433A"], [1262, 176, 270, "#D9A441"], [1530, 164, 210, "#C95B72"]].map(([x, y, len, col], i) => {
    const g = el("g", {}, v3);
    el("circle", { cx: 0, cy: len + 110, r: 230, fill: "url(#lanG)" }, g);
    el("line", { x1: 0, y1: 0, x2: 0, y2: len, stroke: "#c9b98a", "stroke-width": 2 }, g);
    el("rect", { x: -34, y: len, width: 68, height: 18, rx: 3, fill: C.straw, stroke: "#5a4420", "stroke-width": 1.5 }, g);
    el("path", { d: `M -40 ${len + 18} C -110 ${len + 60} -110 ${len + 180} -40 ${len + 222} L 40 ${len + 222} C 110 ${len + 180} 110 ${len + 60} 40 ${len + 18} Z`, fill: col, stroke: "#3b1d14", "stroke-width": 2 }, g);
    for (let k = -2; k <= 2; k++) el("path", { d: `M ${k * 14} ${len + 18} C ${k * 44} ${len + 80} ${k * 44} ${len + 160} ${k * 14} ${len + 222}`, stroke: "#3b1d14", "stroke-width": 1.2, fill: "none", opacity: .55 }, g);
    el("ellipse", { cx: -22, cy: len + 100, rx: 18, ry: 50, fill: "#fff", opacity: .14 }, g);
    el("rect", { x: -30, y: len + 222, width: 60, height: 16, rx: 3, fill: C.straw, stroke: "#5a4420", "stroke-width": 1.5 }, g);
    for (let k = -2; k <= 2; k++) el("line", { x1: k * 6, y1: len + 238, x2: k * 7, y2: len + 300, stroke: col, "stroke-width": 2.4 }, g);
    return { g, x, y, i };
  });
  // v4 · khăn lụa
  const v4 = el("g", {}, s);
  const khan = el("path", { fill: "url(#khanG)", stroke: C.lotusT, "stroke-width": 1.6 }, v4);
  const blossoms = [];
  for (let i = 0; i < 9; i++) {
    const g = el("g", {}, v4);
    for (let k = 0; k < 5; k++) { const a = k / 5 * Math.PI * 2; el("ellipse", { cx: Math.cos(a) * 9, cy: Math.sin(a) * 9, rx: 8, ry: 6, transform: `rotate(${a * 57.3} ${Math.cos(a) * 9} ${Math.sin(a) * 9})`, fill: i % 2 ? C.lotus : "#D98A9C" }, g); }
    el("circle", { r: 4, fill: C.straw }, g);
    blossoms.push(g);
  }
  const fringeL = el("path", { fill: "none", stroke: C.lotusT, "stroke-width": 1.4 }, v4);
  const fringeR = el("path", { fill: "none", stroke: C.lotusT, "stroke-width": 1.4 }, v4);
  // v5 · giỏ lục bình
  const v5 = el("g", {}, s);
  const pat = el("pattern", { id: "weavePat", width: 28, height: 20, patternUnits: "userSpaceOnUse" }, defs);
  el("rect", { width: 28, height: 20, fill: "#D2B26A" }, pat);
  el("path", { d: "M 0 10 Q 7 2 14 10 T 28 10", stroke: "#9c7f45", "stroke-width": 2.2, fill: "none" }, pat);
  el("path", { d: "M 0 20 Q 7 12 14 20 T 28 20 M 0 0 Q 7 -8 14 0 T 28 0", stroke: "#B8964F", "stroke-width": 1.6, fill: "none" }, pat);
  el("ellipse", { cx: 1250, cy: 800, rx: 300, ry: 30, fill: C.ink, opacity: .1 }, v5);
  const handle = el("path", { d: "M 1080 470 C 1080 230, 1420 230, 1420 470", fill: "none", stroke: "#B8964F", "stroke-width": 26, "stroke-linecap": "round" }, v5);
  const handleIn = el("path", { d: "M 1080 470 C 1080 230, 1420 230, 1420 470", fill: "none", stroke: "#E1C584", "stroke-width": 14, "stroke-linecap": "round", "stroke-dasharray": "6 8" }, v5);
  el("path", { d: "M 980 470 L 1520 470 L 1470 760 Q 1250 810 1030 760 Z", fill: "url(#weavePat)", stroke: C.ink, "stroke-width": 2.6, "stroke-linejoin": "round" }, v5);
  el("path", { d: "M 980 470 L 1520 470", stroke: "#9c7f45", "stroke-width": 14, "stroke-linecap": "round" }, v5);
  [[1120, 560], [1250, 600], [1380, 560], [1180, 680], [1320, 680]].forEach(([x, y]) => {
    el("path", { d: `M ${x - 16} ${y} C ${x - 16} ${y - 24} ${x + 16} ${y - 24} ${x + 16} ${y} C ${x + 16} ${y + 12} ${x - 16} ${y + 12} ${x - 16} ${y} Z M ${x} ${y - 14} L ${x} ${y + 6}`, fill: "#FBF7EE", stroke: "#8a7a5c", "stroke-width": 1.6 }, v5);
  });

  const head = label(root, "Nét đẹp Việt", 170, 200);
  const capA = caption(root, "Công phu<br>trong từng <i>đường nét.</i>", 170, 420);
  const capB = caption(root, "Tinh tế<br>trong từng <i>chất liệu.</i>", 170, 420);
  const names = [["Áo dài", 23.7, 26.1], ["Nón lá", 26.35, 28.7], ["Đèn lồng", 28.95, 31.3], ["Khăn lụa vẽ tay", 31.55, 33.9], ["Túi lục bình", 34.15, 35.9]].map(([n, a, b]) => ({ e: label(root, n, 1100, 1000), a, b }));

  const V = [[v1, 23.4, 26.25], [v2, 26.0, 28.85], [v3, 28.6, 31.45], [v4, 31.2, 34.05], [v5, 33.8, 36.1]];
  return (t) => {
    root.style.opacity = eW(prog(t, 23.4, 23.9)) * (1 - eIO(prog(t, 35.5, 36.1)));
    const darkness = eIO(prog(t, 28.6, 29.0)) * (1 - eIO(prog(t, 31.2, 31.6)));
    dark.style.opacity = darkness;
    V.forEach(([g, a, b]) => {
      const pin = eW(prog(t, a, a + 0.45)), pout = eIO(prog(t, b - 0.35, b));
      op(g, Math.min(pin, 1 - pout));
      g.setAttribute("transform", `translate(${(1 - pin) * 60 - pout * 60} ${(1 - pin) * 8})`);
    });
    // áo dài
    ao.setAttribute("transform", `translate(1250 ${120 + Math.sin(t * 1.2) * 6}) rotate(${Math.sin(t * 0.9) * 1.4}) scale(.9)`);
    const sleeve = "M -30 30 C -70 40 -110 52 -126 66 C -150 120 -186 300 -206 412 L -170 420 C -150 330 -120 210 -96 150 C -92 200 -88 260 -88 300 L -96 330";
    const sleeveR = "L 96 330 L 88 300 C 88 260 92 200 96 150 C 120 210 150 330 170 420 L 206 412 C 186 300 150 120 126 66 C 110 52 70 40 30 30 Z";
    const flapF = flapD(t, 1, 0, 0);
    bodyP.setAttribute("d", sleeve + " " + flapF.replace(/^M [^L]+/, "L -96 330").replace(/ Z$/, "") + " " + sleeveR);
    backFlap.setAttribute("d", flapD(t, 1, 22, 0.9));
    pants.setAttribute("d", "M -88 300 L -110 820 L -10 820 L 0 420 L 10 820 L 110 820 L 88 300 Z");
    embroidery.innerHTML = "";
    const wb = 34 * Math.sin(t * 2.3 + 720 / 120);
    [[0, 610], [-36, 660], [30, 690]].forEach(([x, y], i) => {
      const k = (y - 330) / 430, w = 34 * Math.sin(t * 2.3 + y / 120) * k * k;
      const g = el("g", { transform: `translate(${x + w} ${y})` }, embroidery);
      for (let p = 0; p < 5; p++) { const a = p / 5 * Math.PI * 2; el("ellipse", { cx: Math.cos(a) * 9, cy: Math.sin(a) * 9, rx: 7, ry: 5, fill: C.straw, opacity: .9 }, g); }
      el("circle", { r: 3.5, fill: "#fff" }, g);
    });
    void wb;
    // nón lá
    non.setAttribute("transform", `rotate(${Math.sin(t * 1.1) * 2} 1250 520)`);
    ribs.forEach((r, i) => draw(r, prog(t, 26.3 + i * 0.05, 26.8 + i * 0.05)));
    vong.forEach((r, i) => draw(r, prog(t, 26.9 + i * 0.08, 27.5 + i * 0.08)));
    draw(quai, eIO(prog(t, 27.5, 28.1)));
    const shp = prog(t, 27.3, 28.6);
    nonSheen.setAttribute("x", 760 + shp * 1100); nonSheen.style.opacity = Math.sin(Math.PI * shp) * 0.45;
    // đèn lồng
    lanterns.forEach(({ g, x, y, i }) => g.setAttribute("transform", `translate(${x} ${y}) rotate(${Math.sin(t * 1.5 + i * 1.7) * 4})`));
    // khăn lụa
    const pts = [];
    for (let k = 0; k <= 48; k++) {
      const f = k / 48, x = 840 + f * 900;
      const y = 470 + 110 * Math.sin(f * 5.2 - t * 1.8) * (0.35 + f * 0.7) - 60 * f;
      const tw = Math.cos(f * 4.4 - t * 1.3);
      pts.push([x, y, 70 + 50 * Math.abs(tw)]);
    }
    let kd = "";
    pts.forEach(([x, y, w], i) => { kd += (i ? " L " : "M ") + x + " " + (y - w); });
    for (let i = pts.length - 1; i >= 0; i--) kd += ` L ${pts[i][0]} ${pts[i][1] + pts[i][2]}`;
    khan.setAttribute("d", kd + " Z");
    blossoms.forEach((b, i) => {
      const k = 4 + i * 5, [x, y, w] = pts[k];
      b.setAttribute("transform", `translate(${x} ${y + (i % 2 ? 0.45 : -0.4) * w}) rotate(${t * 20 + i * 40}) scale(${0.8 + 0.25 * (i % 3)})`);
    });
    const fr = (P, dir) => { let d = ""; for (let j = -4; j <= 4; j++) { const yy = P[1] + j * P[2] / 4.5; d += ` M ${P[0]} ${yy} l ${dir * 26} ${4 * Math.sin(t * 3 + j)}`; } return d; };
    fringeL.setAttribute("d", fr(pts[0], -1)); fringeR.setAttribute("d", fr(pts[48], 1));
    // giỏ
    v5.setAttribute("transform", (v5.getAttribute("transform") || "") + ` translate(0 ${Math.sin(t * 1.4) * 5})`);
    draw(handle, eIO(prog(t, 34.1, 34.8))); draw(handleIn, eIO(prog(t, 34.25, 34.9)));
    handleIn.style.strokeDasharray = "6 8"; handleIn.style.strokeDashoffset = 0; op(handleIn, prog(t, 34.6, 34.9));

    inkText(head, t, 23.7, 35.7, { dy: 6, blur: 2 });
    head.style.color = mix(C.muted, C.onScene, darkness);
    inkText(capA, t, 25.5, 30.7);
    inkText(capB, t, 31.1, 35.6);
    capA.style.color = mix(C.ink, C.onScene, darkness);
    names.forEach(({ e, a, b }) => { inkText(e, t, a, b, { dy: 6, blur: 2, fi: 0.4, fo: 0.35 }); e.style.color = mix(C.muted, C.onScene, darkness); });
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
