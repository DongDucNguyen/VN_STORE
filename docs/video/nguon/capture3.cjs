const { chromium } = require('playwright');
const fs = require('fs');
const OUT = __dirname + '/shots/';
const B = 'http://127.0.0.1:5173/';
(async () => {
  const browser = await chromium.launch();
  const boxes = {};
  for (const scheme of ['light', 'dark']) {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.334, reducedMotion: 'reduce', colorScheme: scheme });
    const p = await ctx.newPage();
    await p.goto(B + '#/'); await p.waitForTimeout(1500);
    for (let y = 0; y < 7000; y += 400) { await p.evaluate(y => window.scrollTo(0, y), y); await p.waitForTimeout(120); }
    await p.evaluate(() => window.scrollTo(0, 0)); await p.waitForTimeout(1500);
    await p.evaluate(async () => { await document.fonts.ready; await Promise.all([...document.images].map(i => Promise.race([i.decode().catch(() => {}), new Promise(r => setTimeout(r, 1500))]))); });
    await p.waitForTimeout(600);
    await p.evaluate(() => { const f = document.querySelector('.assistant-fab'); if (f) f.style.visibility = 'hidden'; });
    await p.screenshot({ path: OUT + `home_full_${scheme}.png`, fullPage: true });
    if (scheme === 'light') {
      const q = async (sel) => (await p.$$eval(sel, els => els.map(e => { const r = e.getBoundingClientRect(); return { x: r.x, y: r.y + scrollY, w: r.width, h: r.height, t: e.textContent.trim() }; })));
      boxes.nav = await q('.primary-nav a');
      boxes.search = await q('.searchbar-lg .search-field');
      boxes.submit = await q('.searchbar-lg .search-submit');
      boxes.lotus = await q('.chapter-lotus');
      boxes.cat = await q('.chapter-categories');
      boxes.products = await q('.chapter-products');
      boxes.heart = await q('.chapter-products .fav-toggle, .chapter-products button[aria-pressed]');
    }
    await ctx.close();
  }
  fs.writeFileSync(OUT + 'boxes.json', JSON.stringify(boxes, null, 1));
  await browser.close();
})();
