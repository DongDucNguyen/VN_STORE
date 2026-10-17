// Run from repository root: node docs/design/verify-preview.cjs
// Only checks the standalone design preview; it does not test the VNStore app.
const { chromium } = require('../../frontend/node_modules/@playwright/test');
const { pathToFileURL } = require('node:url');
const path = require('node:path');
const fs = require('node:fs');
const assert = require('node:assert/strict');

(async () => {
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const errors = [];
  const checks = [];
  try {
    const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
    page.on('pageerror', e => errors.push(e.message));
    await page.goto(pathToFileURL(path.join(__dirname, 'preview.html')).href);
    await page.locator('figure img').evaluateAll(imgs => Promise.all(imgs.map(img => {
      img.loading = 'eager';
      return img.decode();
    })));
    assert.equal(await page.locator('figure img').count(), 3);
    assert.ok(await page.locator('figure img').evaluateAll(imgs => imgs.every(img => img.naturalWidth > 0)));
    const images = await page.locator('figure img').evaluateAll(imgs => imgs.map(img => ({
      file: img.getAttribute('src'), width: img.naturalWidth, height: img.naturalHeight,
    })));
    assert.ok(images.every(img => /0[567]-v2-/.test(img.file)));
    checks.push('All three v2 concept images decode; no v1 image in current gallery');
    assert.equal(await page.locator('.placement-grid article').count(), 6);
    checks.push('Six placement chapters present');
    for (const width of [320, 390, 768, 1440]) {
      await page.setViewportSize({ width, height: 1100 });
      assert.ok(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth), `Overflow at ${width}`);
      checks.push(`No horizontal page overflow at ${width}px`);
    }
    await page.setViewportSize({ width: 1440, height: 1100 });
    await page.locator('#play-all').click();
    assert.equal(await page.locator('.playing').count(), 4);
    assert.equal(await page.locator('.assistant-mini').isVisible(), true);
    checks.push('All four motion samples respond to play');
    await page.locator('#stop-all').click();
    assert.equal(await page.locator('.playing').count(), 0);
    await page.locator('#reduce').check();
    await page.locator('#play-all').click();
    assert.equal(await page.locator('.playing').count(), 0);
    assert.equal(await page.locator('html').getAttribute('data-reduced'), 'true');
    checks.push('Manual stop and reduced motion preserve interaction without animation');
    await page.locator('#reduce').uncheck();
    await page.emulateMedia({ reducedMotion: 'reduce' });
    await page.waitForFunction(() => document.documentElement.dataset.reduced === 'true');
    await page.locator('#play-all').click();
    assert.equal(await page.locator('.playing').count(), 0);
    checks.push('OS reduced motion overrides normal setting at runtime');
    await page.emulateMedia({ reducedMotion: 'no-preference' });
    await page.waitForFunction(() => document.documentElement.dataset.reduced === 'false');
    await page.locator('#placement').screenshot({ path: path.join(__dirname, 'mockups', '08-v2-placement-study.png') });
    await page.setViewportSize({ width: 390, height: 844 });
    await page.locator('#placement').screenshot({ path: path.join(__dirname, 'mockups', '09-v2-placement-mobile.png') });
    assert.deepEqual(errors, []);
    checks.push('No JavaScript page errors');
    fs.writeFileSync(path.join(__dirname, 'preview-verification.json'), JSON.stringify({
      scope: 'V2 standalone design preview only; no application E2E or performance/FPS claim',
      browser: await browser.version(), checks, images, errors,
    }, null, 2) + '\n');
    console.log(JSON.stringify({ checks, images, errors }, null, 2));
  } finally { await browser.close(); }
})().catch(e => { console.error(e); process.exitCode = 1; });
