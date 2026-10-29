// node render.cjs <start_frame> <end_frame_exclusive> <out.mp4>
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const [a, b, out] = [parseInt(process.argv[2]), parseInt(process.argv[3]), process.argv[4]];
const FPS = 30;
(async () => {
  const browser = await chromium.launch({ args: ['--disable-gpu-vsync', '--disable-frame-rate-limit'] });
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  page.on('pageerror', (e) => console.error('PAGEERR', e.message));
  await page.goto('http://127.0.0.1:8765/stage.html');
  await page.evaluate(() => window.ready);
  const ff = spawn('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '16', '-pix_fmt', 'yuv420p', '-r', String(FPS), out], { stdio: ['pipe', 'inherit', 'inherit'] });
  const t0 = Date.now();
  for (let f = a; f < b; f++) {
    await page.evaluate((t) => window.renderAt(t), f / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 95 });
    if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
    if ((f - a) % 150 === 0) console.log(`[${out}] frame ${f} (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
  }
  ff.stdin.end();
  await new Promise((r) => ff.on('close', r));
  await browser.close();
  console.log(`[${out}] done in ${((Date.now() - t0) / 1000).toFixed(0)}s`);
})();
