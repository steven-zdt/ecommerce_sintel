const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    args: ['--host-resolver-rules=MAP localhost:8000 ecommerce_sintel_django:8000'],
  });
  const page = await browser.newPage({ viewport: { width: 1400, height: 1000 } });
  const consoleErrors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err.message));

  await page.goto('http://localhost:5173/servicios', { waitUntil: 'networkidle', timeout: 30000 });
  await page.waitForTimeout(1200);

  const industryStrip = page.locator('.industry-strip');
  const splitSection = page.locator('.market-split-section');
  const footer = page.locator('footer, .customer-footer').first();

  const industryBox = await industryStrip.boundingBox();
  const splitBox = await splitSection.boundingBox();
  const footerBox = await footer.boundingBox();

  console.log('industry-strip Y:', industryBox?.y);
  console.log('market-split-section Y:', splitBox?.y);
  console.log('footer Y:', footerBox?.y);
  console.log('Order OK (split after industry, before footer):', splitBox.y > industryBox.y && splitBox.y < footerBox.y);

  await splitSection.scrollIntoViewIfNeeded();
  await page.waitForTimeout(500);
  await page.screenshot({ path: '/tmp/services_home_split_bottom.png' });

  console.log('Console errors:', consoleErrors.length ? consoleErrors : 'NONE');
  await browser.close();
})().catch((err) => { console.error('FATAL', err); process.exit(1); });
