// CHƯƠNG III: giao diện thật của VNStore + các tính năng, dựng lại bằng token màu/chữ của web.

const ICON = {
  search: '<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>',
  mic: '<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><rect x="9" y="3" width="6" height="12" rx="3"/><path d="M5 11a7 7 0 0 0 14 0M12 18v3"/></svg>',
  cam: '<svg width="30" height="30" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="M4 8h3l2-3h6l2 3h3v11H4Z"/><circle cx="12" cy="13" r="3.5"/></svg>',
  heart: '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#22352B" stroke-width="1.8" stroke-linejoin="round"><path class="hp" d="M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.6A4 4 0 0 1 19 10c0 5.6-7 10-7 10Z"/></svg>',
  warn: '<svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="#79530E" stroke-width="1.8" stroke-linejoin="round"><path d="M12 4 2.5 20h19Z"/><path d="M12 10v5M12 17.5v.5"/></svg>',
  arrow: '<svg width="46" height="24" viewBox="0 0 46 24" fill="none" stroke="#A84432" stroke-width="2" stroke-linecap="round"><path d="M2 12h40M34 4l8 8-8 8"/></svg>',
  lotus: '<svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round"><path class="pc" d="M24 39C12 30 13 17 24 6c11 11 12 24 0 33Z"/><path class="pl" d="M24 39C10 39 4 28 5 15c12 2 19 12 19 24Z"/><path class="pr" d="M24 39c14 0 20-11 19-24-12 2-19 12-19 24Z"/><path d="M5 32c4 11 12 12 19 10 7 2 15 1 19-10"/></svg>',
};

function uiSearch(parent, x, y, w, h = 78, btnText = "Tìm", ph = "Bạn đang tìm món gì?") {
  const box = el("div", { class: "ui-search", style: { left: x + "px", top: y + "px", width: w + "px", height: h + "px" } }, parent);
  const field = el("div", { class: "ui-field" }, box);
  field.innerHTML = `<span style="color:#616B60;display:flex">${ICON.search}</span><span class="tx"></span><span class="caret"></span><span class="ph">${ph}</span><span style="flex:1"></span><span class="mic" style="color:#22352B;display:flex">${ICON.mic}</span><span style="color:#22352B;display:flex">${ICON.cam}</span>`;
  const btn = el("div", { class: "ui-btn" }, box);
  btn.innerHTML = `<span class="rip"></span>${btnText}`;
  return { box, field, btn, tx: field.querySelector(".tx"), caret: field.querySelector(".caret"), ph: field.querySelector(".ph"), rip: btn.querySelector(".rip") };
}
function setTyped(ui, str, t, a, cps = 12, tEnd = 99) {
  const s = typed(str, t, a, cps);
  ui.tx.textContent = s;
  ui.ph.style.display = s ? "none" : "";
  ui.caret.style.opacity = t < tEnd && (caretOn(t) || (t > a && s.length < str.length)) ? 1 : 0;
}
function uiCard(parent, item, x, y, w, opts = {}) {
  const c = el("div", { class: "card", style: { left: x + "px", top: y + "px", width: w + "px" } }, parent);
  c.innerHTML = `<div class="img"><img src="${item.img}"><span class="heart">${ICON.heart}</span></div>
    <div class="nm" style="font-size:${opts.fs || 20}px">${item.name}</div>
    ${item.brand ? `<div class="br">${item.brand}</div>` : ""}<div class="pr">${fmtVnd(item.price)}</div>
    ${opts.badge ? `<span class="bd">${opts.badge}</span>` : ""}`;
  if (opts.noHeart) c.querySelector(".heart").remove();
  return c;
}
function hCard(parent, item, x, y, w, imgW, extra = "") {
  const c = el("div", { class: "panel", style: { left: x + "px", top: y + "px", width: w + "px", padding: "18px", display: "flex", gap: "24px", alignItems: "center" } }, parent);
  c.innerHTML = `<div style="width:${imgW}px;height:${imgW}px;flex:none;border-radius:6px;overflow:hidden;background:#F0EBDD"><img src="${item.img}" style="width:100%;height:100%;object-fit:cover"></div>
    <div><div style="font-size:26px;font-weight:500;line-height:1.35">${item.name}</div><div style="color:#616B60;font-size:20px;margin-top:6px">${item.brand || ""}</div>
    <div style="font-size:26px;font-weight:600;margin-top:10px">${fmtVnd(item.price)}</div>${extra}</div>`;
  return c;
}
function featureHead(parent, no, title, sub, { x = 160, y = 230, color = C.ink, subColor = C.muted, tsize = 92 } = {}) {
  const ch = el("div", { class: "chno", style: { left: x + "px", top: y + "px" } }, parent);
  ch.innerHTML = `<span>${no}</span><span class="rule"></span>`;
  const ti = el("div", { class: "ftitle", style: { left: x + "px", top: y + 56 + "px", color, fontSize: tsize + "px", width: "720px" } }, parent);
  ti.innerHTML = title.split("<br>").map((l) => `<span class="mask"><span>${l}</span></span>`).join("");
  const su = el("div", { class: "fsub", style: { left: x + "px", top: y + 76 + tsize * 1.04 * title.split("<br>").length + "px", width: "640px", color: subColor } }, parent);
  su.innerHTML = sub;
  const inner = [...ti.querySelectorAll(".mask > span")];
  return (t, a, b) => {
    const o = 1 - eIO(prog(t, b - 0.4, b));
    op(ch, eW(prog(t, a, a + 0.5)) * o); ch.querySelector(".rule").style.transform = `scaleX(${eB(prog(t, a, a + 0.8))})`;
    inner.forEach((s, i) => maskLine(s, t, a + 0.12 + i * 0.12, 0.85));
    op(ti, o);
    inkText(su, t, a + 0.5, b, { fo: 0.4 });
  };
}
function note(parent, txt, x, y, color = C.lotusT) { const e = el("div", { class: "note", style: { left: x + "px", top: y + "px", color } }, parent); e.innerHTML = txt; return e; }
function popIn(e, t, a, d = 0.45, dy = 18) { const p = eB(prog(t, a, a + d)); e.style.transform = `translateY(${(1 - p) * dy}px)`; op(e, eW(prog(t, a, a + d * 0.8))); }
function browser(parent, x, y, w, h, srcs, url = "VNStore — Nếp Việt trong từng món đồ") {
  const b = el("div", { class: "browser", style: { left: x + "px", top: y + "px", width: w + "px", height: h + "px" } }, parent);
  b.innerHTML = `<div class="bar"><i></i><i></i><i></i><span class="url">${url}</span></div>`;
  const view = el("div", { class: "view", style: { height: h - 44 + "px" } }, b);
  const imgs = srcs.map((s) => el("img", { src: s }, view));
  return { b, view, imgs };
}
function cursor(parent) {
  const c = el("div", { class: "abs", style: { width: "34px", height: "34px", marginLeft: "-17px", marginTop: "-17px", borderRadius: "50%", border: "2.5px solid #22352B", background: "rgba(255,253,247,.55)", boxShadow: "0 4px 14px rgba(0,0,0,.18)", zIndex: 20 } }, parent);
  return (x, y, o = 1, press = 0) => { c.style.left = x + "px"; c.style.top = y + "px"; c.style.opacity = o; c.style.transform = `scale(${1 - 0.25 * press})`; };
}
const pathPos = (t, keys) => {
  // keys: [[t, x, y], ...] nội suy mượt từng đoạn
  if (t <= keys[0][0]) return [keys[0][1], keys[0][2]];
  for (let i = 0; i < keys.length - 1; i++) {
    const [ta, xa, ya] = keys[i], [tb, xb, yb] = keys[i + 1];
    if (t <= tb) { const p = eIO(prog(t, ta, tb)); return [lerp(xa, xb, p), lerp(ya, yb, p)]; }
  }
  const k = keys[keys.length - 1]; return [k[1], k[2]];
};

// ---------- S8 · Trang chủ thật (53.9 – 60.4) ----------
scene(53.9, 60.4, (root) => {
  root.style.background = C.deep;
  const BX = 300, BY = 56, BW = 1320, BH = 820;
  const shadowImg = el("img", { src: "art/bamboo-shadow-clean.png", class: "abs", style: { left: "900px", top: "-120px", width: "1500px", opacity: .3, zIndex: 3, mixBlendMode: "multiply" } }, root);
  const br = browser(root, BX, BY, BW, BH, ["shots/home_full_light.png"]);
  const K = (BW / 1921) * 1.334; // px CSS của web → px khung
  const covers = [[110, 176, 430, 124], [110, 302, 430, 70]].map(([x, y, w, h]) => el("div", { class: "abs", style: { left: x + "px", top: y + "px", width: w + "px", height: h + "px", background: C.ivory } }, br.view));
  const ink = el("div", { class: "abs", style: { height: "3px", background: C.primary, transformOrigin: "left center", borderRadius: "2px" } }, br.view);
  const cur = cursor(root);
  const n1 = note(root, "Gió qua tre", 1460, 150);
  const n2 = note(root, "Nét tre", 760, 26);
  const cap = caption(root, "Một ấn phẩm Việt — <i>có thể chạm vào.</i>", 0, 924, "cap sm", { width: "1920px", textAlign: "center" });
  const NAV = [[288.6, 73.9], [394.5, 76.4], [502.9, 89.0], [623.9, 66.8]];
  return (t) => {
    root.style.opacity = 1;
    const pin = eB(prog(t, 53.95, 54.9));
    br.b.style.transform = `translateY(${(1 - pin) * 40}px) scale(${lerp(1.04, 1, pin)})`;
    const sc = eIO(prog(t, 57.6, 58.7)) * 830 + eIO(prog(t, 58.9, 60.2)) * 690;
    br.imgs[0].style.transform = `translateY(${-sc * K}px)`;
    covers.forEach((c, i) => {
      const p = eB(prog(t, 54.15 + i * 0.25, 55.0 + i * 0.25));
      c.style.transform = `translateY(${-sc * K}px)`;
      c.style.clipPath = `inset(0 0 ${p * 100}% 0)`;
    });
    shadowImg.style.transform = `translate(${Math.sin(t * 0.8) * 40}px, ${Math.cos(t * 0.6) * 10}px) rotate(${Math.sin(t * 0.8) * 2}deg)`;
    shadowImg.style.opacity = 0.32 * eW(prog(t, 54.2, 55.2)) * (1 - prog(t, 57.6, 58.4));
    // nét tre theo con trỏ
    const hov = t < 56.0 ? -1 : t < 56.55 ? 0 : t < 57.05 ? 1 : t < 57.55 ? 2 : -1;
    const tgt = hov >= 0 ? NAV[hov] : NAV[2];
    const ip = eB(prog(t, [56.0, 56.55, 57.05][Math.max(0, hov)] || 56, ([56.0, 56.55, 57.05][Math.max(0, hov)] || 56) + 0.25));
    const prev = hov > 0 ? NAV[hov - 1] : NAV[0];
    const nx = lerp(prev[0], tgt[0], hov > 0 ? ip : 1), nw = lerp(prev[1], tgt[1], hov > 0 ? ip : 1);
    ink.style.left = nx * K + "px"; ink.style.width = nw * K + "px"; ink.style.top = (14 + 44 - 9) * K - sc * K + "px";
    ink.style.opacity = hov >= 0 ? 1 : (t >= 57.55 ? 1 - prog(t, 57.55, 57.8) : 0);
    ink.style.transform = `scaleX(${hov === 0 ? eB(prog(t, 56.0, 56.2)) : 1})`;
    const [cx, cy] = pathPos(t, [[55.4, 1300, 700], [56.0, BX + (288 + 37) * K, BY + 44 + 34 * K], [56.55, BX + (394 + 38) * K, BY + 44 + 34 * K], [57.05, BX + (503 + 44) * K, BY + 44 + 34 * K], [57.7, 1100, 640]]);
    cur(cx, cy, win(t, 55.3, 58.0, 0.3, 0.3));
    inkText(n1, t, 55.0, 56.7, { dy: 6, blur: 2 });
    inkText(n2, t, 56.15, 57.8, { dy: 6, blur: 2 });
    inkText(cap, t, 58.2, 60.4, { fo: 0.35 });
    root.style.opacity = 1 - eIO(prog(t, 59.95, 60.4));
  };
});

// ---------- S9 · 01 Sự trân trọng tiếng Việt (60.0 – 67.3) ----------
scene(60.0, 71.9, (root) => {
  root.style.background = C.ivory;
  const lotus = el("img", { src: "art/lotus-botanical-02.png", class: "abs", style: { left: "-120px", top: "700px", width: "640px", opacity: .28 } }, root);
  const head1 = featureHead(root, "01", "Sự trân trọng<br>tiếng Việt", "Hiểu cả cách người Việt nói:<br>gõ không dấu, gõ vội, nói “tầm”, “không lấy”.");
  const head2 = featureHead(root, "01", "Lắng nghe<br>tiếng Việt", "Lời nói ra, được lắng nghe trọn vẹn —<br>và luôn để bạn xem lại trước khi tìm.");
  const RX = 960, RW = 820;
  const ui = uiSearch(root, RX, 214, RW);
  const ripNote = note(root, "Gợn mặt sen", RX + RW - 190, 300);
  const res = el("div", { class: "abs", style: { left: RX + "px", top: "340px", width: RW + "px" } }, root);
  const lead = el("div", { class: "serif", style: { fontSize: "36px" } }, res); lead.innerHTML = "Bạn đang tìm “<b style='font-weight:500'>khăn lụa tầm 1tr5</b>”";
  const chips = el("div", { style: { display: "flex", gap: "12px", marginTop: "18px" } }, res);
  const ch1 = el("span", { class: "chip" }, chips); ch1.innerHTML = "Từ khóa: <b style='font-weight:600'>khăn lụa</b>";
  const ch2 = el("span", { class: "chip hard" }, chips); ch2.textContent = "Giá khoảng 1.200.000đ–1.800.000đ";
  const nt = el("div", { class: "notice", style: { marginTop: "18px" } }, res); nt.innerHTML = `${ICON.warn}<span>Hiểu “tầm 1 tr 5” là khoảng giá ±20%</span>`;
  const card = uiCard(root, DATA.khan[0], RX, 600, 270, { badge: "Nguyên liệu Việt", fs: 19 });
  const cardNote = el("div", { class: "abs", style: { left: RX + 310 + "px", top: "640px", width: "480px", fontSize: "24px", lineHeight: "1.6", color: C.muted } }, root);
  cardNote.innerHTML = "<span class='serif it' style='font-size:30px;color:#22352B'>“tầm 1tr5”</span><br>là cách người Việt nói giá —<br>VNStore hiểu đó là <b style='color:#214B3B;font-weight:600'>khoảng 1,2 – 1,8 triệu</b>.";
  const rows = [
    ["bìn hoa sen", "Hiểu “bìn” là “bình”", "gõ vội vẫn hiểu"],
    ["binh hoa duoi 5 trieu", "Giá dưới 5.000.000đ", "gõ không dấu vẫn hiểu"],
    ["giỏ mây không lấy tre", "Không lấy chất liệu tre", "hiểu cả lời từ chối"],
  ].map(([q, r, tag], i) => {
    const row = el("div", { class: "abs", style: { left: RX + "px", top: 360 + i * 170 + "px", width: RW + "px", display: "flex", alignItems: "center", gap: "22px" } }, root);
    row.innerHTML = `<span class="chip" style="background:#FFFDF7;font-size:26px;padding:14px 24px;border-radius:10px">${q}</span>${ICON.arrow}<span class="chip hard" style="font-size:24px;padding:12px 22px">${r}</span>`;
    const tg = el("div", { class: "note", style: { left: RX + "px", top: 360 + i * 170 + 74 + "px", fontSize: "22px", color: C.muted } }, root); tg.textContent = tag;
    return { row, tg };
  });
  // --- giọng nói ---
  const mic = el("div", { class: "abs", style: { left: RX + "px", top: "220px", width: "136px", height: "136px", borderRadius: "50%", background: C.primary, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center" } }, root);
  mic.innerHTML = ICON.mic.replace(/width="30" height="30"/, 'width="58" height="58"');
  const micRings = [0, 1, 2].map(() => el("div", { class: "abs", style: { left: RX + 68 + "px", top: 288 + "px", width: "136px", height: "136px", marginLeft: "-68px", marginTop: "-68px", borderRadius: "50%", border: "2px solid #AD586C" } }, root));
  const live = el("div", { class: "abs", style: { left: RX + 170 + "px", top: "236px", fontSize: "26px", display: "flex", gap: "14px", alignItems: "center" } }, root);
  live.innerHTML = `<span style="width:16px;height:16px;border-radius:50%;background:#A02D2D;display:inline-block"></span><span>Đang nghe… <b class="tm" style="font-variant-numeric:tabular-nums">0:00</b> / 0:12</span>`;
  const bars = el("div", { class: "abs", style: { left: RX + 170 + "px", top: "288px", height: "70px", display: "flex", alignItems: "center", gap: "7px" } }, root);
  const barEls = []; for (let i = 0; i < 40; i++) barEls.push(el("span", { style: { width: "6px", borderRadius: "3px", background: C.primary, display: "inline-block", height: "8px" } }, bars));
  const bubble = el("div", { class: "abs serif", style: { left: RX + 170 + "px", top: "380px", fontSize: "44px", fontStyle: "italic", color: C.lotusT } }, root);
  const review = el("div", { class: "panel", style: { left: RX + "px", top: "470px", width: RW + "px", padding: "28px 32px" } }, root);
  review.innerHTML = `<div style="font-weight:600;font-size:26px">Kiểm tra lời nói trước khi tìm</div>
    <div style="margin-top:10px;font-size:22px;color:#616B60">Bản chép lời gốc: <span style="color:#22352B">áo dài lụa</span> · Ngôn ngữ nhận dạng: vi</div>
    <div style="margin-top:16px;border:1.5px solid #7B8474;border-radius:8px;padding:14px 18px;font-size:26px;background:#fff">áo dài lụa</div>
    <div style="display:flex;gap:12px;margin-top:18px"><span class="ui-btn rb" style="height:60px;font-size:23px"><span class="rip"></span>Tìm theo câu này</span><span class="ui-btn ghost" style="height:60px;font-size:23px">Ghi lại</span><span class="ui-btn ghost" style="height:60px;font-size:23px">Hủy</span></div>`;
  const rbRip = review.querySelector(".rb .rip");
  const aoCard = hCard(root, DATA.ao[0], RX, 470, RW, 230, `<span class="bd" style="display:inline-block;margin-top:12px;font-size:17px;border:1px solid #DBDECE;border-radius:4px;padding:4px 10px;color:#616B60">Hanhsilk · Lụa tơ tằm</span>`);
  const pho = el("div", { class: "abs", style: { left: RX + "px", top: "770px", width: RW + "px", fontSize: "22px", color: C.muted, lineHeight: 1.5 } }, root);
  pho.innerHTML = "Nhận dạng giọng nói bằng <b style='color:#22352B;font-weight:600'>PhoWhisper</b> — mô hình dành riêng cho tiếng Việt.";
  const cur = cursor(root);

  return (t) => {
    root.style.opacity = eW(prog(t, 60.0, 60.4));
    lotus.style.transform = `translate(${Math.sin(t * 0.5) * 10}px, ${Math.cos(t * 0.4) * 6}px)`;
    head1(t, 60.15, 67.05);
    head2(t, 67.15, 71.9);
    // search
    const sIn = eB(prog(t, 60.2, 60.8)), sOut = eIO(prog(t, 64.15, 64.55));
    ui.box.style.transform = `translateY(${(1 - sIn) * 20 - sOut * 20}px)`; op(ui.box, eW(prog(t, 60.2, 60.7)) * (1 - sOut));
    setTyped(ui, "khăn lụa tầm 1tr5", t, 60.55, 12.5, 62.0);
    ripple(ui.rip, t, 62.0, 320);
    ui.btn.style.transform = `scale(${1 - 0.04 * Math.sin(Math.PI * prog(t, 61.95, 62.2))})`;
    inkText(ripNote, t, 62.05, 63.6, { dy: 6, blur: 2, fi: 0.3 });
    const [cx, cy] = pathPos(t, [[61.2, 1500, 520], [61.9, RX + RW - 62, 252], [62.5, RX + RW - 50, 300]]);
    cur(cx, cy, win(t, 61.2, 62.6, 0.25, 0.25), Math.sin(Math.PI * prog(t, 61.9, 62.15)));
    const rIn = 62.3;
    popIn(lead, t, rIn); popIn(ch1, t, rIn + 0.2); popIn(ch2, t, rIn + 0.35); popIn(nt, t, rIn + 0.55);
    op(res, 1 - sOut); res.style.transform = `translateY(${-sOut * 20}px)`;
    popIn(card, t, 62.95, 0.5, 24); if (t > 64.15) { op(card, 1 - sOut); }
    inkText(cardNote, t, 63.2, 64.55, { fo: 0.4 });
    rows.forEach(({ row, tg }, i) => {
      const a = 64.5 + i * 0.65;
      popIn(row, t, a, 0.5, 26);
      const arr = row.querySelector("svg"); arr.style.clipPath = `inset(0 ${(1 - eB(prog(t, a + 0.2, a + 0.55))) * 100}% 0 0)`;
      const last = row.lastElementChild; last.style.opacity = eW(prog(t, a + 0.4, a + 0.75)); last.style.transform = `translateX(${(1 - eB(prog(t, a + 0.4, a + 0.8))) * -16}px)`;
      inkText(tg, t, a + 0.55, 67.05, { dy: 6, blur: 2, fi: 0.4, fo: 0.3 });
      if (t > 66.75) { op(row, 1 - eIO(prog(t, 66.75, 67.05))); }
    });
    // voice
    const vIn = eB(prog(t, 67.15, 67.6));
    popIn(mic, t, 67.15, 0.45, 20);
    mic.style.transform += ` scale(${1 - 0.06 * Math.sin(Math.PI * prog(t, 67.35, 67.55))})`;
    micRings.forEach((r, i) => {
      const t0 = 67.45 + i * 0.53, p = prog(t, t0, t0 + 1.6);
      const on = t >= t0 && t < 68.9 + 1.6 && t0 < 68.9;
      r.style.transform = `scale(${1 + 0.9 * eW(p)})`; r.style.opacity = on && p < 1 ? (1 - p) * 0.7 : 0;
    });
    const rec = t >= 67.45 && t < 68.95;
    op(live, rec ? eW(prog(t, 67.45, 67.65)) : (t >= 68.95 ? 1 - prog(t, 68.95, 69.2) : 0));
    live.querySelector(".tm").textContent = "0:0" + Math.min(9, Math.floor(Math.max(0, t - 67.45) * 1.4));
    barEls.forEach((b, i) => {
      const env = Math.sin(Math.PI * prog(t, 67.55, 68.85));
      const a = Math.abs(noise1(t * 9 + i * 0.7, i)) * env;
      b.style.height = 8 + a * 60 + "px";
    });
    op(bars, rec ? 1 : (t >= 68.95 ? 1 - prog(t, 68.95, 69.2) : 0));
    bubble.textContent = t < 67.7 ? "" : "“" + ["áo", "áo dài", "áo dài lụa"][Math.min(2, Math.floor((t - 67.75) / 0.32))] + "”";
    op(bubble, eW(prog(t, 67.7, 67.9)) * (1 - prog(t, 69.0, 69.3)));
    popIn(review, t, 68.85, 0.45, 26);
    ripple(rbRip, t, 69.1, 300);
    if (t > 69.4) op(review, 1 - eIO(prog(t, 69.4, 69.65)));
    popIn(aoCard, t, 69.6, 0.5, 26);
    inkText(pho, t, 69.9, 71.9, { fo: 0.3 });
    const [mx, my] = pathPos(t, [[67.0, 1500, 700], [67.35, RX + 68, 290], [68.7, RX + 68, 300], [69.08, RX + 150, 690], [69.5, RX + 200, 720]]);
    cur(mx, my, win(t, 67.0, 69.6, 0.2, 0.2), Math.max(Math.sin(Math.PI * prog(t, 67.3, 67.55)), Math.sin(Math.PI * prog(t, 69.05, 69.3))));
    if (t < 67.15) { op(mic, 0); op(review, 0); op(aoCard, 0); op(pho, 0); }
    void vIn;
    root.style.opacity = eW(prog(t, 60.0, 60.4)) * (1 - prog(t, 71.75, 71.9));
  };
});

// ---------- S11 · Cánh cò vụt lên (70.8 – 73.8) ----------
function egretShape(parent, fill = "#FFFDF7", stroke = C.ink) {
  const g = el("g", {}, parent);
  const wingBack = el("path", { fill: mix(fill, "#d9dcd2", 0.5), stroke, "stroke-width": 2 }, g);
  el("path", { d: "M -70 10 C -20 -6 40 -10 86 -4 C 112 -2 128 -18 132 -46 C 136 -70 150 -84 168 -84 C 178 -84 186 -80 190 -74 L 246 -72 L 192 -64 C 186 -56 176 -52 166 -56 C 154 -50 150 -30 146 -10 C 140 18 110 30 70 30 C 20 32 -30 26 -70 10 Z", fill, stroke, "stroke-width": 2.2, "stroke-linejoin": "round" }, g);
  el("path", { d: "M 10 28 L -40 92 M 30 28 L -10 96", stroke, "stroke-width": 3, "stroke-linecap": "round" }, g);
  el("circle", { cx: 174, cy: -74, r: 3, fill: stroke }, g);
  const wing = el("path", { fill, stroke, "stroke-width": 2.2, "stroke-linejoin": "round" }, g);
  const setWing = (ph) => {
    const up = Math.sin(ph); // 1 lên, -1 xuống
    const tipX = -40 + 30 * Math.cos(ph), tipY = -230 * up, midY = -90 * up;
    const d = `M 70 0 C 40 ${midY - 20} 0 ${midY - 40} ${tipX - 120} ${tipY} C ${tipX - 60} ${tipY + 40} ${-20} ${midY + 40} -40 ${10 + 30 * up} C -10 20 30 14 70 0 Z`;
    wing.setAttribute("d", d);
    wingBack.setAttribute("d", `M 80 -4 C 60 ${midY * 0.6 - 10} 20 ${midY * 0.6 - 30} ${tipX - 60} ${tipY * 0.6} C ${tipX - 20} ${tipY * 0.6 + 30} 10 ${midY * 0.4} -10 4 Z`);
  };
  return { g, setWing };
}
scene(70.8, 73.9, (root) => {
  const s = svg(root);
  const flash = el("rect", { width: W, height: H, fill: "#FFFDF7", opacity: 0 }, s);
  const big = egretShape(s);
  return (t) => {
    // Cò cất cánh từ góc phải dưới, lao sát ống kính, cánh phủ kín khung đúng 71.6.
    const p = prog(t, 70.8, 71.75);
    const x = lerp(1500, 700, eIn(p)), y = lerp(900, 380, eIn(p)), sc = lerp(0.6, 14, Math.pow(p, 2.6));
    big.setWing(t * 9.5);
    big.g.setAttribute("transform", `translate(${x} ${y}) scale(${sc}) rotate(-24)`);
    op(big.g, p < 1 ? 1 : 0);
    flash.style.opacity = Math.max(0, 1 - Math.abs(t - 71.62) / 0.16) * 0.9;
  };
}, 10);

// ---------- S12 · 02 Nhịp cầu năm châu (71.55 – 82.2) ----------
scene(71.55, 82.2, (root) => {
  root.style.background = `linear-gradient(180deg, #122f27 0%, ${C.forest} 45%, #24503f 100%)`;
  const s = svg(root);
  const stars = []; for (let i = 0; i < 70; i++) stars.push(el("circle", { cx: rand(i, 21) * W, cy: rand(i, 22) * 560, r: 0.8 + rand(i, 23) * 1.6, fill: "#F7F3E8" }, s));
  const hills = [["#1d4537", 860, 70, 0.3], ["#173a2e", 920, 50, 0.55], ["#102a23", 980, 40, 0.85]].map(([col, y0, amp, sp], i) => {
    const p = el("path", { fill: col }, s); return { p, y0, amp, sp, i };
  });
  const small = egretShape(s);
  const lanG = el("radialGradient", { id: "skyL" }, el("defs", {}, s));
  el("stop", { offset: 0, "stop-color": "#FFD58C", "stop-opacity": .7 }, lanG); el("stop", { offset: 1, "stop-color": "#FFD58C", "stop-opacity": 0 }, lanG);
  const pairs = [["Silk", "Lụa"], ["Bamboo", "Tre"], ["Water hyacinth", "Lục bình"], ["Mother of pearl", "Xà cừ"], ["Lacquer", "Sơn mài"]];
  const lan = pairs.map(([en, vi], i) => {
    const g = el("g", {}, s);
    el("circle", { r: 120, fill: "url(#skyL)" }, g);
    el("path", { d: "M -34 -50 L 34 -50 L 44 40 Q 0 54 -44 40 Z", fill: "#F1B866", stroke: "#8a5a20", "stroke-width": 1.6 }, g);
    el("path", { d: "M -34 -50 L 34 -50 L 38 -20 Q 0 -10 -38 -20 Z", fill: "#FFE3A8", opacity: .7 }, g);
    el("ellipse", { cx: 0, cy: 42, rx: 12, ry: 5, fill: "#FFF2C8" }, g);
    const tEn = el("text", { y: 102, "text-anchor": "middle", "font-family": "Newsreader", "font-style": "italic", "font-size": 32, fill: "#C3CCBF" }, g, en);
    const tVi = el("text", { y: 150, "text-anchor": "middle", "font-family": "Newsreader", "font-size": 50, fill: "#F7F3E8" }, g, vi);
    return { g, i, x: [330, 690, 1010, 1330, 1630][i] };
  });
  const head = featureHead(root, "02", "Nhịp cầu<br>năm châu", "<i class='serif' style='font-size:34px;color:#D8BD7A'>A bridge to the world</i><br>Bạn bè quốc tế tìm bằng chính ngôn ngữ của mình.", { color: C.onScene, subColor: "#C3CCBF" });
  const RX = 960, RW = 820;
  const ui = uiSearch(root, RX, 214, RW, 78, "Search", "Bạn đang tìm món gì?");
  const exp = el("div", { class: "abs", style: { left: RX + "px", top: "318px", fontSize: "22px", color: "#C3CCBF" } }, root);
  exp.innerHTML = "Tìm thêm cách gọi khác: <b style='color:#F7F3E8;font-weight:500'>khăn, scarves, shawl</b>";
  const cards = DATA.silk.slice(0, 4).map((it, i) => {
    const c = uiCard(root, it, RX + i * 210, 372, 190, { fs: 16, noHeart: true });
    c.querySelectorAll(".nm,.pr").forEach((e) => (e.style.color = "#F7F3E8")); c.querySelectorAll(".br").forEach((e) => (e.style.color = "#C3CCBF"));
    return c;
  });
  const capEn = caption(root, "<i>Speak your language. Discover Vietnamese craft.</i>", 0, 170, "cap sm", { width: "1920px", textAlign: "center", color: C.straw });
  const capVi = caption(root, "Bạn nói bằng ngôn ngữ của bạn — VNStore đáp lại bằng tinh hoa Việt.", 0, 240, "cap sm", { width: "1920px", textAlign: "center", color: C.onScene, fontSize: "38px" });
  const lang = el("div", { class: "abs", style: { left: RX + "px", top: "240px", fontSize: "24px", color: "#C3CCBF", display: "flex", gap: "14px", alignItems: "center" } }, root);
  lang.innerHTML = `Ngôn ngữ giọng nói <span class="chip" style="background:#20372C;color:#F7F3E8;border-color:#9CAA94;font-size:24px"><span class="lv">Tiếng Việt</span> ▾</span>`;
  const mic = el("div", { class: "abs", style: { left: RX + "px", top: "320px", width: "110px", height: "110px", borderRadius: "50%", background: "#B8D4B6", color: C.forest, display: "flex", alignItems: "center", justifyContent: "center" } }, root);
  mic.innerHTML = ICON.mic.replace(/width="30" height="30"/, 'width="48" height="48"');
  const ring = el("div", { class: "abs", style: { left: RX + 55 + "px", top: 375 + "px", width: "110px", height: "110px", marginLeft: "-55px", marginTop: "-55px", borderRadius: "50%", border: "2px solid #D8BD7A" } }, root);
  const sayEn = el("div", { class: "abs serif", style: { left: RX + 150 + "px", top: "340px", fontSize: "52px", fontStyle: "italic", color: "#F7F3E8" } }, root);
  const bCard = hCard(root, { ...DATA.bamboo[0], brand: "Vietcraft · đan tay" }, RX, 480, RW, 230);
  bCard.style.background = "#20372C"; bCard.style.borderColor = "#42594A"; bCard.style.color = "#ECECDF";
  const cur = cursor(root);
  return (t) => {
    root.style.opacity = 1 - eIO(prog(t, 81.85, 82.2));
    stars.forEach((st, i) => st.style.opacity = 0.25 + 0.5 * Math.abs(noise1(t * 1.3 + i, i)));
    hills.forEach(({ p, y0, amp, sp, i }) => {
      let d = `M 0 ${H}`;
      for (let x = 0; x <= W + 40; x += 40) d += ` L ${x} ${y0 + amp * Math.sin(x / (260 + i * 90) + i * 2 + t * 0.05 * sp) + 18 * Math.sin(x / 70 + i)}`;
      p.setAttribute("d", d + ` L ${W} ${H} Z`);
      p.setAttribute("transform", `translate(${-t * 6 * sp % 40} 0)`);
    });
    // Cò bay xa dần lên trời
    const bp = prog(t, 71.6, 74.2);
    small.setWing(t * 7);
    small.g.setAttribute("transform", `translate(${lerp(700, 1700, eOut(bp))} ${lerp(420, 70, eOut(bp))}) scale(${lerp(2.4, 0.22, eOut(bp))}) rotate(-18)`);
    op(small.g, bp < 1 ? 1 - Math.pow(bp, 3) : 0);
    head(t, 71.95, 75.85);
    const sOut = eIO(prog(t, 75.55, 75.9));
    popIn(ui.box, t, 72.2, 0.5, 20); if (t > 75.55) op(ui.box, 1 - sOut);
    setTyped(ui, "silk scarf", t, 72.65, 11, 73.6);
    ripple(ui.rip, t, 73.6, 320);
    const [cx, cy] = pathPos(t, [[72.9, 1500, 620], [73.55, RX + RW - 70, 252], [74.2, RX + RW - 40, 330]]);
    cur(cx, cy, win(t, 72.9, 74.2, 0.25, 0.25), Math.sin(Math.PI * prog(t, 73.5, 73.75)));
    popIn(exp, t, 73.85, 0.45, 12); if (t > 75.55) op(exp, 1 - sOut);
    cards.forEach((c, i) => { popIn(c, t, 74.0 + i * 0.12, 0.45, 14); if (t > 75.55) op(c, 1 - sOut); });
    // đèn trời mang cặp từ song ngữ
    lan.forEach(({ g, i, x }) => {
      const a = 75.9 + i * 0.42, p = prog(t, a, a + 6.5);
      const y = lerp(1180, 560 - (i % 2) * 90, eOut(p));
      const sway = Math.sin(t * 1.3 + i * 1.7) * 16;
      g.setAttribute("transform", `translate(${x + sway} ${y}) rotate(${Math.sin(t * 1.1 + i) * 3})`);
      const fade = t < 79.2 ? 1 : 1 - eIO(prog(t, 79.2, 79.9)) * 0.88;
      op(g, eW(prog(t, a, a + 0.5)) * fade);
    });
    inkText(capEn, t, 76.6, 79.6, { fo: 0.4 });
    inkText(capVi, t, 77.3, 79.6, { fo: 0.4 });
    // giọng nói English
    popIn(lang, t, 79.55, 0.4, 12);
    lang.querySelector(".lv").textContent = t < 79.95 ? "Tiếng Việt" : "English";
    popIn(mic, t, 79.6, 0.4, 16);
    const rp = prog(t, 80.2, 81.4); ring.style.transform = `scale(${1 + 0.8 * eW(rp)})`; ring.style.opacity = t > 80.2 && rp < 1 ? (1 - rp) * 0.8 : 0;
    sayEn.textContent = t < 80.3 ? "" : "“" + ["bamboo", "bamboo basket"][t < 80.6 ? 0 : 1] + "”";
    op(sayEn, eW(prog(t, 80.3, 80.5)));
    popIn(bCard, t, 81.0, 0.5, 22);
    if (t < 79.5) { op(lang, 0); op(mic, 0); op(sayEn, 0); op(bCard, 0); }
  };
});

// ---------- S13 · 03 Một ánh nhìn (82.0 – 86.75) ----------
scene(82.0, 86.75, (root) => {
  root.style.background = C.ivory;
  const head = featureHead(root, "03", "Một<br>ánh nhìn", "Thấy một món đẹp ngoài chợ —<br>chụp lại, khoanh vùng, tìm mẫu tương tự.");
  const PX = 860, PY = 150, PW = 380, PH = 760;
  const phone = el("div", { class: "abs", style: { left: PX + "px", top: PY + "px", width: PW + "px", height: PH + "px", borderRadius: "46px", background: "#22352B", padding: "14px", boxSizing: "border-box", boxShadow: "0 40px 90px -40px rgba(0,0,0,.5)" } }, root);
  const scr = el("div", { style: { position: "relative", width: "100%", height: "100%", borderRadius: "34px", overflow: "hidden", background: C.ivory } }, phone);
  const photo = el("img", { src: DATA.tui[0].img, style: { position: "absolute", left: "0", top: "80px", width: "352px", height: "352px", objectFit: "cover" } }, scr);
  const flash = el("div", { style: { position: "absolute", inset: 0, background: "#fff", opacity: 0 } }, scr);
  const shutter = el("div", { style: { position: "absolute", left: "50%", bottom: "34px", width: "78px", height: "78px", marginLeft: "-39px", borderRadius: "50%", border: "5px solid #FFFDF7", boxShadow: "0 0 0 3px #22352B inset", background: "#e9e2d0" } }, scr);
  const crop = el("div", { style: { position: "absolute", border: "2.5px dashed #214B3B", boxShadow: "0 0 0 2000px rgba(34,53,43,.28)" } }, scr);
  const field = el("div", { style: { position: "absolute", left: "18px", right: "18px", top: "470px", height: "58px", border: "1.5px solid #7B8474", borderRadius: "8px", background: "#FFFDF7", display: "flex", alignItems: "center", padding: "0 14px", fontSize: "22px" } }, scr);
  field.innerHTML = '<span class="tx"></span><span class="caret" style="display:inline-block;width:2px;height:26px;background:#214B3B;margin-left:2px"></span><span class="ph" style="color:#8b928a">Ví dụ: có quai, dưới 400k…</span>';
  const fb = el("div", { class: "ui-btn", style: { position: "absolute", left: "18px", right: "18px", top: "544px", height: "62px", fontSize: "22px" } }, scr);
  fb.innerHTML = '<span class="rip"></span>Tìm mẫu tương tự';
  const scrTitle = el("div", { style: { position: "absolute", left: "22px", top: "26px", fontFamily: "Newsreader", fontSize: "30px" } }, scr); scrTitle.textContent = "Tìm bằng ảnh";
  const items = [DATA.luc[0], DATA.tui[0], DATA.tui[1], DATA.tui[2], DATA.may[0], DATA.tui[4]];
  const gridLbl = el("div", { class: "abs serif", style: { left: "1290px", top: "150px", fontSize: "34px" } }, root); gridLbl.textContent = "Mẫu tương tự";
  const grid = items.map((it, i) => { const c = el("div", { class: "abs", style: { left: 1290 + (i % 3) * 170 + "px", top: 212 + Math.floor(i / 3) * 196 + "px", width: "156px", height: "156px", borderRadius: "6px", overflow: "hidden", background: C.well } }, root); c.innerHTML = `<img src="${it.img}" style="width:100%;height:100%;object-fit:cover">`; return c; });
  const gNote = note(root, "Nhịp đan", 1290, 620);
  const disclaimer = el("div", { class: "abs", style: { left: "1290px", top: "680px", width: "500px", fontSize: "21px", lineHeight: 1.5, color: C.muted } }, root);
  disclaimer.textContent = "Kết quả là các mẫu tương tự trong catalog; ảnh được thu nhỏ và bỏ thông tin vị trí trước khi gửi.";
  const cur = cursor(root);
  return (t) => {
    root.style.opacity = eW(prog(t, 82.0, 82.35)) * (1 - eIO(prog(t, 86.4, 86.75)));
    head(t, 82.1, 86.75);
    popIn(phone, t, 82.05, 0.5, 30);
    const fp = prog(t, 82.4, 82.75); flash.style.opacity = t > 82.4 ? 0.9 * (1 - fp) : 0;
    shutter.style.transform = `scale(${1 - 0.12 * Math.sin(Math.PI * prog(t, 82.35, 82.55))})`;
    op(shutter, 1 - prog(t, 82.75, 82.95));
    const cp = eB(prog(t, 82.95, 83.7));
    const full = [6, 86, 340, 340], tight = [40, 108, 276, 300];
    const [x, y, w, h] = full.map((v, i) => lerp(v, tight[i], cp));
    Object.assign(crop.style, { left: x + "px", top: y + "px", width: w + "px", height: h + "px" });
    op(crop, eW(prog(t, 82.95, 83.2)));
    op(field, eW(prog(t, 83.4, 83.6))); op(fb, eW(prog(t, 83.5, 83.7)));
    const s = typed("có quai", t, 83.65, 12); field.querySelector(".tx").textContent = s; field.querySelector(".ph").style.display = s ? "none" : "";
    field.querySelector(".caret").style.opacity = t < 84.2 && t > 83.6 && caretOn(t) ? 1 : 0;
    ripple(fb.querySelector(".rip"), t, 84.25, 300);
    const [cx, cy] = pathPos(t, [[83.0, 1100, 980], [83.45, PX + 190, PY + 500], [84.2, PX + 190, PY + 590], [84.6, PX + 260, PY + 650]]);
    cur(cx, cy, win(t, 83.0, 84.7, 0.2, 0.2), Math.sin(Math.PI * prog(t, 84.2, 84.45)));
    popIn(gridLbl, t, 84.45, 0.4, 10);
    grid.forEach((g, i) => popIn(g, t, 84.55 + i * 0.1, 0.42, 12));
    inkText(gNote, t, 84.8, 86.5, { dy: 6, blur: 2, fi: .3 });
    inkText(disclaimer, t, 85.2, 86.6, { fo: 0.3 });
  };
});

// ---------- S14 · 04 Uống nước nhớ nguồn (86.45 – 91.3) ----------
scene(86.45, 91.3, (root) => {
  root.style.background = C.ivory;
  const head = featureHead(root, "04", "Uống nước<br>nhớ nguồn", "Mỗi nhãn nguồn gốc đều đi kèm căn cứ —<br>và nói thật cả điều chưa rõ.");
  const hero = DATA.vase.find((v) => v.name.startsWith("Bình hoa 36 cm"));
  const others = DATA.vase.filter((v) => v !== hero).slice(0, 3);
  const RX = 900;
  const grid = [hero, ...others].map((it, i) => uiCard(root, { ...it, brand: "Minh Long" }, RX + i * 225, 220, 205, { fs: 16, badge: "Thương hiệu Việt" }));
  const fly = el("div", { class: "abs", style: { borderRadius: "6px", overflow: "hidden", background: C.well } }, root);
  fly.innerHTML = `<img src="${hero.img}" style="width:100%;height:100%;object-fit:cover">`;
  const qNote = note(root, "Qua hiên", RX, 170);
  const info = el("div", { class: "abs", style: { left: RX + 400 + "px", top: "210px", width: "520px" } }, root);
  info.innerHTML = `<div class="serif" style="font-size:40px;line-height:1.15;white-space:nowrap">Bình hoa 36 cm – Hoa Sen<span class="mark" style="margin-left:12px"></span></div>
   <div style="color:#616B60;font-size:22px;margin-top:12px">Thương hiệu: <u>Minh Long</u></div>
   <div style="font-size:38px;font-weight:600;margin-top:14px">${fmtVnd(hero.price)}</div>
   <div style="margin-top:12px"><span class="bd" style="display:inline-block;font-size:17px;border:1px solid #DBDECE;border-radius:4px;padding:4px 10px;color:#616B60">Thương hiệu Việt · Nhà sản xuất công bố</span></div>`;
  const tbl = el("div", { class: "panel", style: { left: RX + "px", top: "580px", width: "880px", padding: "22px 26px" } }, root);
  const rows = [["Thương hiệu Việt", "yes", "Có", "Nhà sản xuất công bố", "10/10/2026", "Công ty TNHH Minh Long I"],
    ["Sản xuất tại Việt Nam", "unk", "Chưa rõ", "Chưa xác minh", "—", "—"],
    ["Nguyên liệu Việt", "unk", "Chưa rõ", "Chưa xác minh", "—", "—"],
    ["Thủ công/truyền thống", "unk", "Chưa rõ", "Chưa xác minh", "—", "—"]];
  tbl.innerHTML = `<div class="serif" style="font-size:32px;margin-bottom:14px">Nguồn gốc và căn cứ<span class="mark" style="margin-left:12px"></span></div>
   <div style="position:relative"><div class="hl" style="position:absolute;top:0;bottom:0;background:#D8BD7A;opacity:.35;border-radius:4px;transform-origin:top"></div>
   <table class="origin" style="position:relative"><thead><tr><th>Tiêu chí</th><th>Giá trị</th><th class="mv">Mức xác minh</th><th>Ngày kiểm tra</th><th>Nguồn</th></tr></thead>
   <tbody>${rows.map(([a, c, v, m, d, s]) => `<tr><td>${a}</td><td><span class="claim ${c}">${v}</span></td><td>${m}</td><td>${d}</td><td>${s === "—" ? s : `<u style="color:#214B3B">${s}</u>`}</td></tr>`).join("")}</tbody></table></div>`;
  const trs = [...tbl.querySelectorAll("tbody tr")];
  const hl = tbl.querySelector(".hl");
  const cur = cursor(root);
  let mvBox = null;
  return (t) => {
    root.style.opacity = eW(prog(t, 86.45, 86.8)) * (1 - eIO(prog(t, 90.95, 91.3)));
    head(t, 86.55, 91.3);
    const g0 = grid[0].querySelector(".img").getBoundingClientRect();
    grid.forEach((g, i) => { popIn(g, t, 86.5 + i * 0.07, 0.4, 14); if (t > 86.95) op(g, i === 0 ? 0 : 1 - eIO(prog(t, 86.95, 87.25))); });
    const [cx, cy] = pathPos(t, [[86.4, 1400, 900], [86.85, RX + 100, 320], [87.2, RX + 120, 330]]);
    cur(cx, cy, win(t, 86.45, 87.3, 0.15, 0.2), Math.sin(Math.PI * prog(t, 86.8, 87.0)));
    // ảnh thẻ bay sang vị trí ảnh lớn ở trang chi tiết
    const fp = eB(prog(t, 86.97, 87.75));
    const from = [RX, 220, 205, 205], to = [RX, 200, 370, 370];
    const [x, y, w, h] = from.map((v, i) => lerp(v, to[i], fp));
    Object.assign(fly.style, { left: x + "px", top: y + "px", width: w + "px", height: h + "px" });
    op(fly, t > 86.95 ? 1 : 0);
    void g0;
    inkText(qNote, t, 87.05, 88.4, { dy: 6, blur: 2, fi: .3 });
    popIn(info, t, 87.45, 0.5, 16);
    popIn(tbl, t, 88.05, 0.55, 40);
    trs.forEach((r, i) => popIn(r, t, 88.35 + i * 0.12, 0.4, 10));
    if (!mvBox && t > 88.0) {
      const th = tbl.querySelector(".mv"), tb = tbl.querySelector("table").getBoundingClientRect(), b = th.getBoundingClientRect();
      mvBox = { l: b.left - tb.left, w: b.width };
    }
    if (mvBox) { hl.style.left = mvBox.l + "px"; hl.style.width = mvBox.w + "px"; }
    hl.style.transform = `scaleY(${eIO(prog(t, 89.25, 89.95))})`;
  };
});

// ---------- S15 · 05 Người bạn tri âm (90.95 – 95.75) ----------
scene(90.95, 95.75, (root) => {
  root.style.background = C.ivory;
  const head = featureHead(root, "05", "Người bạn<br>tri âm", "Tư vấn tận tâm như người bán hàng quen —<br>chỉ nói điều có căn cứ trong catalog.");
  const consent = el("div", { class: "abs", style: { left: "160px", top: "720px", width: "640px", fontSize: "22px", color: C.ink } }, root);
  consent.innerHTML = `<div style="color:#616B60;margin-bottom:10px">Bạn chọn điều được ghi nhớ:</div>` + ["Không lưu", "Lưu lịch sử", "Ghi nhớ sở thích"].map((x, i) => `<div class="cr" style="display:flex;gap:12px;align-items:center;margin:8px 0"><span class="rd" style="width:22px;height:22px;border-radius:50%;border:2px solid #7B8474;display:inline-flex;align-items:center;justify-content:center"><i style="width:10px;height:10px;border-radius:50%;background:#214B3B;display:${i === 0 ? "block" : "none"}"></i></span>${x}</div>`).join("");
  const crs = [...consent.querySelectorAll(".cr")];
  const fab = el("div", { class: "abs", style: { left: "1600px", top: "930px", height: "64px", padding: "0 26px", borderRadius: "32px", background: C.primary, color: "#fff", display: "flex", alignItems: "center", gap: "12px", fontSize: "24px", fontWeight: 500, boxShadow: "0 18px 40px -18px rgba(0,0,0,.45)" } }, root);
  fab.innerHTML = `<span class="lm" style="width:36px;height:36px;display:inline-block;color:#fff">${ICON.lotus}</span>Trợ lý`;
  const pl = fab.querySelector(".pl"), pr = fab.querySelector(".pr");
  const sNote = note(root, "Sen mở", 1470, 870);
  const panel = el("div", { class: "panel", style: { left: "1100px", top: "150px", width: "640px", height: "690px", overflow: "hidden" } }, root);
  panel.innerHTML = `<div style="display:flex;align-items:center;gap:12px;padding:20px 26px;border-bottom:1px solid #DBDECE"><span style="width:34px;height:34px;color:#214B3B">${ICON.lotus}</span><b style="font-size:24px;font-weight:600">Trợ lý VNStore</b></div>`;
  const body = el("div", { style: { padding: "22px 26px", display: "flex", flexDirection: "column", gap: "16px" } }, panel);
  const ub = el("div", { style: { alignSelf: "flex-end", background: C.primary, color: "#fff", borderRadius: "16px 16px 4px 16px", padding: "14px 20px", fontSize: "23px" } }, body); ub.textContent = "Gợi ý quà tặng mẹ khoảng 500k";
  const ab = el("div", { style: { fontSize: "22px", lineHeight: 1.55, color: C.ink } }, body); ab.textContent = "Mình tìm được một số sản phẩm có thể hợp với yêu cầu của bạn, bạn xem thử bên dưới nhé.";
  const mc = DATA.marou.map((it, i) => {
    const c = el("div", { style: { display: "flex", gap: "16px", alignItems: "center", border: "1px solid #DBDECE", borderRadius: "10px", padding: "10px", background: "#fff" } }, body);
    c.innerHTML = `<b style="color:#A84432;font-family:Newsreader;font-size:24px;width:22px">${i + 1}</b><img src="${it.img}" style="width:86px;height:86px;object-fit:cover;border-radius:6px"><div><div style="font-size:18px;font-weight:500;line-height:1.35">${it.name.replace("Sô cô la Marou — ", "Marou — ")}</div><div style="font-size:20px;font-weight:600;margin-top:4px">${fmtVnd(it.price)}</div><div style="font-size:15px;color:#616B60">Marou · Nguyên liệu Việt</div></div>`;
    return c;
  });
  const qk = el("div", { style: { display: "flex", gap: "10px" } }, body);
  qk.innerHTML = `<span class="chip sug" style="font-size:18px">So sánh #1 và #2</span><span class="chip sug" style="font-size:18px">#1 có tốt không?</span>`;
  const cur = cursor(root);
  return (t) => {
    root.style.opacity = eW(prog(t, 90.95, 91.3)) * (1 - eIO(prog(t, 95.4, 95.75)));
    head(t, 91.05, 95.75);
    popIn(fab, t, 91.0, 0.35, 16);
    const open = Math.sin(Math.PI * prog(t, 91.35, 91.75));
    pl.style.transformOrigin = pr.style.transformOrigin = "24px 39px";
    pl.style.transform = `rotate(${-14 * open}deg)`; pr.style.transform = `rotate(${14 * open}deg)`;
    fab.style.transform += ` scale(${1 - 0.05 * Math.sin(Math.PI * prog(t, 91.3, 91.5))})`;
    const [cx, cy] = pathPos(t, [[90.95, 1300, 700], [91.3, 1690, 962], [91.7, 1700, 990]]);
    cur(cx, cy, win(t, 90.95, 91.8, 0.15, 0.2), Math.sin(Math.PI * prog(t, 91.25, 91.45)));
    inkText(sNote, t, 91.4, 92.8, { dy: 6, blur: 2, fi: .3 });
    const pp = eB(prog(t, 91.45, 91.85));
    panel.style.transform = `translateY(${(1 - pp) * 24}px)`; op(panel, eW(prog(t, 91.45, 91.75)));
    popIn(ub, t, 91.95, 0.4, 12);
    popIn(ab, t, 92.45, 0.4, 8);
    mc.forEach((c, i) => popIn(c, t, 92.85 + i * 0.2, 0.4, 14));
    popIn(qk, t, 93.6, 0.4, 8);
    inkText(consent, t, 93.9, 95.75, { fo: 0.35 });
    crs.forEach((c, i) => c.style.opacity = 0.35 + 0.65 * eW(prog(t, 94.0 + i * 0.15, 94.3 + i * 0.15)));
  };
});

// ---------- S16 · Từng chi tiết nhỏ (95.4 – 101.6) ----------
scene(95.4, 101.6, (root) => {
  root.style.background = C.ivory;
  const ti = el("div", { class: "ftitle", style: { left: "0", width: "1920px", textAlign: "center", top: "120px", fontSize: "76px" } }, root);
  ti.innerHTML = '<span class="mask"><span>Từng chi tiết nhỏ</span></span>';
  const cap = caption(root, "Đến cả một cái chạm <i>cũng được chăm chút.</i>", 0, 900, "cap sm", { width: "1920px", textAlign: "center" });
  // ba tương tác nhỏ
  const c1 = uiCard(root, DATA.silk[0], 330, 300, 300, { fs: 18 });
  const hp = c1.querySelector(".hp");
  const hRing = el("div", { class: "abs", style: { width: "44px", height: "44px", borderRadius: "50%", border: "2px solid #AD586C", left: 330 + 300 - 12 - 44 + "px", top: 300 + 12 + "px" } }, root);
  const n1 = note(root, "Giữ một món", 330, 820);
  const b2 = el("div", { class: "ui-btn", style: { left: "810px", top: "470px", width: "300px", height: "96px", position: "absolute", fontSize: "32px" } }, root);
  b2.innerHTML = '<span class="rip"></span>Tìm';
  const r2 = b2.querySelector(".rip");
  const n2 = note(root, "Gợn mặt sen", 870, 820);
  const nav = el("div", { class: "abs", style: { left: "1290px", top: "490px", display: "flex", gap: "40px", fontSize: "30px" } }, root);
  nav.innerHTML = "<span>Khám phá</span><span>Làng nghề</span><span>Thương hiệu</span>";
  const nInk = el("div", { class: "abs", style: { height: "4px", top: "548px", background: C.primary, borderRadius: "2px" } }, root);
  const n3 = note(root, "Nét tre", 1290, 820);
  const items = [c1, b2, nav];
  // sáng → tối
  const br = browser(root, 300, 220, 1320, 640, ["shots/home_full_light.png", "shots/home_full_dark.png"]);
  const n4 = note(root, "Sáng → Tối · “đêm trong vườn”", 300, 875);
  const cur = cursor(root);
  let spans = null;
  return (t) => {
    root.style.opacity = eW(prog(t, 95.4, 95.7));
    maskLine(ti.querySelector(".mask > span"), t, 95.45, 0.8);
    const dark = eIO(prog(t, 98.0, 98.65));
    root.style.background = mix(C.ivory, "#15271F", dark);
    ti.style.color = mix(C.ink, "#ECECDF", dark);
    const mOut = eIO(prog(t, 97.35, 97.7));
    items.forEach((e, i) => { popIn(e, t, 95.5 + i * 0.12, 0.45, 16); if (t > 97.35) op(e, 1 - mOut); });
    // tim
    const hpp = prog(t, 95.75, 95.95);
    hp.setAttribute("fill", t > 95.75 ? C.lotus : "none"); hp.setAttribute("stroke", t > 95.75 ? C.lotus : C.ink);
    c1.querySelector(".heart svg").style.transform = `scale(${1 + 0.18 * Math.sin(Math.PI * hpp)})`;
    const hr = prog(t, 95.75, 96.35); hRing.style.transform = `scale(${1 + 1.2 * eW(hr)})`; hRing.style.opacity = t > 95.75 && hr < 1 ? (1 - hr) * (1 - mOut) : 0;
    ripple(r2, t, 96.3, 420);
    if (!spans) spans = [...nav.children].map((s) => [s.offsetLeft + 1290, s.offsetWidth]);
    const k = t < 96.75 ? 0 : t < 97.0 ? 0 : t < 97.25 ? 1 : 2;
    const pA = spans[Math.max(0, k - 1)], pB = spans[k], ip = eB(prog(t, [96.75, 97.0, 97.25][k], [96.75, 97.0, 97.25][k] + 0.22));
    nInk.style.left = lerp(pA[0], pB[0], k ? ip : 1) + "px"; nInk.style.width = lerp(pA[1], pB[1], k ? ip : 1) + "px";
    nInk.style.opacity = t > 96.75 ? (1 - mOut) : 0;
    nInk.style.transformOrigin = "left"; nInk.style.transform = `scaleX(${k === 0 ? eB(prog(t, 96.75, 96.95)) : 1})`;
    const [cx, cy] = pathPos(t, [[95.45, 900, 760], [95.7, 330 + 300 - 34, 334], [96.2, 960, 520], [96.7, spans[0][0] + 60, 512], [96.95, spans[1][0] + 60, 512], [97.25, spans[2][0] + 60, 512], [97.7, 1200, 760]]);
    cur(cx, cy, win(t, 95.45, 97.6, 0.15, 0.25), Math.max(Math.sin(Math.PI * prog(t, 95.7, 95.9)), Math.sin(Math.PI * prog(t, 96.25, 96.45))));
    [[n1, 95.85], [n2, 96.35], [n3, 96.85]].forEach(([n, a]) => inkText(n, t, a, 97.6, { dy: 6, blur: 2, fi: .3, fo: .3 }));
    // trình duyệt sáng → tối
    popIn(br.b, t, 97.45, 0.45, 26);
    if (t < 97.45) op(br.b, 0);
    const K = (1320 / 1921) * 1.334;
    const sc = eIO(prog(t, 98.9, 101.2)) * 1420;
    br.imgs.forEach((im) => im.style.transform = `translateY(${-sc * K}px)`);
    br.imgs[1].style.opacity = dark;
    br.b.querySelector(".bar").style.background = mix(C.deep, "#112019", dark);
    inkText(n4, t, 98.1, 101.4, { dy: 6, blur: 2, fo: .3 });
    n4.style.color = mix(C.lotusT, "#E7BAC5", dark);
    inkText(cap, t, 98.7, 101.4, { fo: 0.3 });
    cap.style.color = mix(C.ink, "#ECECDF", dark);
  };
});
