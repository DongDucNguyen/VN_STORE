const {chromium}=require('../../../frontend/node_modules/@playwright/test');
const fs=require('node:fs');const path=require('node:path');const {pathToFileURL}=require('node:url');const assert=require('node:assert/strict');
(async()=>{
 const root=__dirname;const qa=path.join(root,'qa');fs.mkdirSync(qa,{recursive:true});
 const manifest=JSON.parse(fs.readFileSync(path.join(root,'manifest.json'),'utf8'));
 assert.equal(manifest.assets.length,36);
 for(const a of manifest.assets){assert(fs.existsSync(path.join(root,a.file)),a.file);assert(a.bytes>0);}
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
 const page=await browser.newPage({viewport:{width:1440,height:1000},reducedMotion:'no-preference'});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(pathToFileURL(path.join(root,'index.html')).href);
 await page.locator('img').evaluateAll(images=>Promise.all(images.map(i=>{i.loading='eager';return i.decode();})));
 assert.equal(await page.locator('.card').count(),36);
 const links=await page.locator('a[href]').evaluateAll(a=>a.map(x=>x.getAttribute('href')).filter(x=>!x.startsWith('#')));
 for(const file of links)assert(fs.existsSync(path.resolve(root,file)),file);
 const widths=[];for(const width of [1440,768,390,320]){await page.setViewportSize({width,height:1000});const result=await page.evaluate(()=>({viewport:innerWidth,scroll:document.documentElement.scrollWidth}));assert(result.scroll<=width,JSON.stringify(result));widths.push(result);if(width===390)await page.screenshot({path:path.join(qa,'gallery-mobile.png'),fullPage:true});}
 await page.setViewportSize({width:1440,height:1000});await page.locator('#surface').selectOption('forest');assert.equal(await page.locator('body').getAttribute('data-surface'),'forest');await page.locator('#cutouts').screenshot({path:path.join(qa,'cutouts-dark.png')});await page.locator('#surface').selectOption('checker');assert.equal(await page.locator('body').getAttribute('data-surface'),'checker');await page.locator('#surface').selectOption('ivory');
 await page.locator('#categories').screenshot({path:path.join(qa,'categories.png')});await page.locator('#scenes').screenshot({path:path.join(qa,'scenes.png')});
 await page.locator('[data-demo=".nv-bamboo"]').click();assert.equal(await page.locator('.nv-bamboo').evaluate(el=>getComputedStyle(el).animationName),'nv-bamboo');
 await page.locator('#reduce').check();assert.equal(await page.locator('.nv-bamboo').evaluate(el=>getComputedStyle(el).animationName),'none');await page.locator('#reduce').uncheck();await page.emulateMedia({reducedMotion:'reduce'});await page.locator('[data-demo=".nv-lotus"]').click();assert.equal(await page.locator('.nv-lotus #petal-left').evaluate(el=>getComputedStyle(el).animationName),'none');
 await page.emulateMedia({reducedMotion:'no-preference'});await page.locator('#motion').screenshot({path:path.join(qa,'motion.png')});await page.evaluate(()=>scrollTo(0,0));await page.screenshot({path:path.join(qa,'gallery-desktop.png'),fullPage:true});assert.deepEqual(errors,[]);
 fs.writeFileSync(path.join(qa,'verification.json'),JSON.stringify({checkedAt:new Date().toISOString(),browser:await browser.version(),assetCount:36,imagesDecoded:await page.locator('img').count(),localLinksChecked:links.length,widths,alphaSurfaceToggle:'passed',motionTrigger:'passed',manualReducedMotion:'passed',systemReducedMotion:'passed',pageErrors:errors,scope:'Offline asset gallery only; not production app performance'},null,2));console.log('Verified 36 assets, local links, 4 widths, motion and reduced motion.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
