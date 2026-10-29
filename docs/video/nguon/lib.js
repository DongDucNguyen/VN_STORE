// Thư viện nhỏ cho sân khấu: mọi trạng thái là hàm thuần của thời gian t (giây), không dùng CSS transition.
const W = 1920, H = 1080;
const SVGNS = "http://www.w3.org/2000/svg";
const C = {
  ivory: "#F7F3E8", deep: "#EFE9DA", surface: "#FFFDF7", well: "#F0EBDD", ink: "#22352B", muted: "#616B60",
  primary: "#214B3B", soft: "#E7EDE1", line: "#DBDECE", border: "#7B8474", lotus: "#AD586C", lotusL: "#DEA5B2",
  lotusT: "#97485F", straw: "#D8BD7A", strawD: "#B8964F", forest: "#183E33", forestD: "#102A23", onScene: "#ECECE0",
  mark: "#A84432", warnSoft: "#F5ECD2", warn: "#79530E", blue: "#2D5A8C", clay: "#C48A5E",
};

const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const prog = (t, a, b) => clamp((t - a) / (b - a));
const lerp = (a, b, p) => a + (b - a) * p;
const mix = (c1, c2, p) => {
  const h = (c) => [1, 3, 5].map((i) => parseInt(c.slice(i, i + 2), 16));
  const a = h(c1), b = h(c2);
  return "#" + a.map((v, i) => Math.round(lerp(v, b[i], p)).toString(16).padStart(2, "0")).join("");
};

function bezier(x1, y1, x2, y2) {
  const cx = 3 * x1, bx = 3 * (x2 - x1) - cx, ax = 1 - cx - bx;
  const cy = 3 * y1, by = 3 * (y2 - y1) - cy, ay = 1 - cy - by;
  const sx = (u) => ((ax * u + bx) * u + cx) * u;
  const sy = (u) => ((ay * u + by) * u + cy) * u;
  const dx = (u) => (3 * ax * u + 2 * bx) * u + cx;
  return (x) => {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    let u = x;
    for (let i = 0; i < 8; i++) {
      const e = sx(u) - x;
      if (Math.abs(e) < 1e-5) break;
      const d = dx(u);
      if (Math.abs(d) < 1e-6) break;
      u -= e / d;
    }
    return sy(clamp(u));
  };
}
const eB = bezier(0.22, 1, 0.36, 1);      // ease-bamboo
const eW = bezier(0.2, 0.65, 0.3, 1);     // ease-water
const eIO = bezier(0.65, 0, 0.35, 1);
const eOut = bezier(0.33, 1, 0.68, 1);
const eIn = bezier(0.32, 0, 0.67, 0);

// Cửa sổ hiện/ẩn mềm: 0 trước a, lên 1 trong fi giây, giữ, xuống 0 trong fo giây trước b.
const win = (t, a, b, fi = 0.5, fo = 0.5) => Math.min(eW(prog(t, a, a + fi)), 1 - eIn(prog(t, b - fo, b)));

// Nhiễu mượt có tính quyết định (để sóng âm, đung đưa không lặp đều).
function noise1(x, seed = 0) {
  const r = (i) => { const s = Math.sin((i + seed * 131.7) * 127.1) * 43758.5453; return s - Math.floor(s); };
  const i = Math.floor(x), f = x - i, u = f * f * (3 - 2 * f);
  return lerp(r(i), r(i + 1), u) * 2 - 1;
}
const rand = (i, seed = 0) => { const s = Math.sin((i + 1) * 12.9898 + seed * 78.233) * 43758.5453; return s - Math.floor(s); };

function el(tag, attrs = {}, parent = null, text = null) {
  const svgTags = new Set(["svg", "g", "path", "circle", "ellipse", "rect", "line", "polyline", "polygon", "defs",
    "linearGradient", "radialGradient", "stop", "mask", "clipPath", "filter", "feGaussianBlur", "feTurbulence",
    "feDisplacementMap", "feColorMatrix", "text", "use", "pattern", "image", "feOffset", "feMerge", "feMergeNode", "feBlend"]);
  const e = svgTags.has(tag) ? document.createElementNS(SVGNS, tag) : document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "style" && typeof v === "object") Object.assign(e.style, v);
    else if (k === "class") e.setAttribute("class", v);
    else e.setAttribute(k, v);
  }
  if (text != null) e.textContent = text;
  if (parent) parent.appendChild(e);
  return e;
}
const svg = (parent, attrs = {}) => el("svg", { width: W, height: H, viewBox: `0 0 ${W} ${H}`, ...attrs, style: { position: "absolute", left: 0, top: 0, overflow: "visible", ...(attrs.style || {}) } }, parent);
const layer = (parent, cls = "", style = {}) => el("div", { class: "layer " + cls, style }, parent);

// Vẽ nét: p=0 chưa có, p=1 trọn nét.
function prepDraw(path) { const L = path.getTotalLength(); path._L = L; path.style.strokeDasharray = `${L} ${L}`; path.style.strokeDashoffset = L; return path; }
function draw(path, p) { if (path._L == null) prepDraw(path); path.style.strokeDashoffset = path._L * (1 - clamp(p)); path.style.opacity = p > 0.001 ? "" : 0; }

function setT(e, { x = 0, y = 0, s = 1, sx = null, sy = null, r = 0, o = null, blur = null, origin = null } = {}) {
  e.style.transform = `translate(${x}px, ${y}px) rotate(${r}deg) scale(${sx ?? s}, ${sy ?? s})`;
  if (origin) e.style.transformOrigin = origin;
  if (o != null) e.style.opacity = clamp(o);
  if (blur != null) e.style.filter = blur > 0.05 ? `blur(${blur}px)` : "none";
}
const op = (e, o) => { e.style.opacity = clamp(o); e.style.visibility = o <= 0.002 ? "hidden" : "visible"; };

// Chữ hiện như mực thấm: mờ → rõ, trồi 14px.
function inkText(e, t, a, b, { dy = 14, blur = 6, fi = 0.7, fo = 0.5 } = {}) {
  const pin = eW(prog(t, a, a + fi)), pout = eIn(prog(t, b - fo, b));
  const o = Math.min(pin, 1 - pout);
  setT(e, { y: (1 - pin) * dy - pout * 6, blur: (1 - pin) * blur + pout * 3 });
  op(e, o);
}
// Chữ trồi lên từ mặt nạ (display-mask của trang chủ).
function maskLine(inner, t, a, d = 0.9) { const p = eB(prog(t, a, a + d)); inner.style.transform = `translateY(${(1 - p) * 110}%)`; }

// Gõ chữ từng ký tự.
function typed(str, t, a, cps = 12) { const n = Math.floor(clamp((t - a) * cps, 0, str.length)); return t < a ? "" : str.slice(0, n); }
const caretOn = (t) => Math.floor(t * 2.2) % 2 === 0;

// Gợn mặt sen trong một nút: vòng lan từ điểm bấm.
function ripple(circle, t, t0, size = 260) {
  const p = prog(t, t0, t0 + 0.62);
  if (t < t0 || p >= 1) { circle.style.opacity = 0; return; }
  const s = lerp(0.15, 1, eW(p));
  circle.style.transform = `translate(-50%, -50%) scale(${s})`;
  circle.style.width = circle.style.height = size + "px";
  circle.style.opacity = 0.34 * (1 - p);
}

function fmtVnd(v) { return v == null ? "Liên hệ" : v.toLocaleString("vi-VN").replace(/,/g, ".") + "đ"; }

const SCENES = [];
function scene(a, b, build, z = 1) { const root = layer(document.getElementById("stage"), "scene"); root.style.display = "none"; root.style.zIndex = z; const update = build(root); SCENES.push({ a, b, root, update }); }
function renderAt(t) {
  for (const s of SCENES) {
    const on = t >= s.a && t < s.b;
    s.root.style.display = on ? "block" : "none";
    if (on) s.update(t);
  }
}
