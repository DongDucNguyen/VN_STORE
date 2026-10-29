const { chromium } = require('playwright');
const OUT = __dirname + '/shots/';
const B = 'http://127.0.0.1:5173/';
(async () => {
  const browser = await chromium.launch();
  const mk = async (scheme='light') => {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 1.334, reducedMotion: 'reduce', colorScheme: scheme });
    return [ctx, await ctx.newPage()];
  };
  const settle = async (p) => { await p.waitForLoadState('networkidle'); await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(800); };
  let [ctx, p] = await mk();
  await p.goto(B + '#/p/p-minhlong-binh-hoa-36-cm-hoa-sen-1071550628'); await settle(p);
  await p.screenshot({ path: OUT + 'product_full.png', fullPage: true });
  // assistant (basic mode)
  await p.goto(B + '#/'); await settle(p);
  await p.click('.assistant-fab'); await p.waitForTimeout(800);
  await p.screenshot({ path: OUT + 'assistant_open.png' });
  const starter = p.locator('.assistant-panel button', { hasText: 'Gợi ý quà tặng mẹ' }).first();
  if (await starter.count()) { await starter.click(); } else { await p.fill('textarea', 'Gợi ý quà tặng mẹ khoảng 500k'); await p.keyboard.press('Enter'); }
  await p.waitForTimeout(6000);
  await p.screenshot({ path: OUT + 'assistant_reply.png' });
  const txt = await p.locator('[role=dialog]').innerText().catch(()=> '');
  require('fs').writeFileSync(OUT + 'assistant_reply.txt', txt);
  await ctx.close();
  [ctx, p] = await mk('dark');
  await p.goto(B + '#/'); await settle(p);
  await p.screenshot({ path: OUT + 'home_full_dark.png', fullPage: true });
  await p.screenshot({ path: OUT + 'home_top_dark.png' });
  await ctx.close(); await browser.close();
})();
