const { chromium } = require('playwright');

const EQUIPMENT_UUID = process.argv[2];
if (!EQUIPMENT_UUID) {
  console.error('Usage: node verify_rental_detail.js <equipment-uuid>');
  process.exit(1);
}

(async () => {
  const browser = await chromium.launch({
    args: ['--host-resolver-rules=MAP localhost:8000 ecommerce_sintel_django:8000'],
  });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });

  const consoleErrors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err.message));

  const url = `http://localhost:5173/alquiler/equipo/${EQUIPMENT_UUID}`;
  console.log('Navigating to', url);
  await page.goto(url, { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(1500);

  await page.screenshot({ path: '/tmp/rental_detail_top.png' });

  const title = await page.textContent('h1.equipment-title').catch(() => null);
  console.log('H1 title:', title);

  const sectionsHeads = await page.$$eval('.section-head h2', (els) => els.map((e) => e.textContent.trim()));
  console.log('Detail sections found:', sectionsHeads);

  const includedCount = await page.locator('.eq-scope-card--included li').count();
  const excludedCount = await page.locator('.eq-scope-card--excluded li').count();
  const featureCount = await page.locator('.eq-feature-card').count();
  const specGroupCount = await page.locator('.eq-spec-group').count();
  const requirementCount = await page.locator('.eq-requirement-card').count();
  const manualCount = await page.locator('.eq-manual-card').count();
  const datasheetCount = await page.locator('.eq-datasheet-card').count();
  const downloadCount = await page.locator('.eq-download-row').count();
  const videoCount = await page.locator('.eq-video-card').count();
  const faqCount = await page.locator('.eq-faq-item').count();
  const serviceIncludedCount = await page.locator('.eq-service-card').count();

  console.log(JSON.stringify({
    includedCount, excludedCount, featureCount, specGroupCount, requirementCount,
    manualCount, datasheetCount, downloadCount, videoCount, faqCount, serviceIncludedCount,
  }, null, 2));

  // Scroll down to capture the full detail sections in a second screenshot
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight / 2));
  await page.waitForTimeout(500);
  await page.screenshot({ path: '/tmp/rental_detail_mid.png' });

  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
  await page.waitForTimeout(500);
  await page.screenshot({ path: '/tmp/rental_detail_bottom.png' });

  console.log('Console errors:', consoleErrors.length ? consoleErrors : 'NONE');

  await browser.close();
})().catch((err) => {
  console.error('FATAL', err);
  process.exit(1);
});
