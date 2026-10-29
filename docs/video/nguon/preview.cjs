const { chromium } = require('playwright');
const times = process.argv.slice(3).map(Number);
const out = process.argv[2];
(async () => {
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1920, height: 1080 } });
  const errs = [];
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  p.on('pageerror', e => errs.push('PAGEERR ' + e.message));
  await p.goto('http://127.0.0.1:8765/stage.html');
  await p.evaluate(() => window.ready);
  for (const t of times) {
    await p.evaluate(t => window.renderAt(t), t);
    await p.screenshot({ path: `${out}/f_${t.toFixed(2)}.jpg`, type: 'jpeg', quality: 80 });
  }
  console.log(errs.slice(0, 10).join('\n') || 'no errors');
  await b.close();
})();
