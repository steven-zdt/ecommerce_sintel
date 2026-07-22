const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  const uuid = '886922e0-8f36-4b58-8752-e18368a5e877';

  try {
    await page.goto(`https://www.sintel.net.co/servicios/${uuid}`, { waitUntil: 'networkidle', timeout: 20000 });
    await page.waitForTimeout(1500);
    console.log('=== DETAIL PAGE TEXT (first 3000 chars) ===');
    console.log((await page.locator('body').innerText()).slice(0, 3000));
    await page.screenshot({ path: '/tmp/prod_detail.png', fullPage: true });
  } catch (e) {
    console.error('DETAIL PAGE ERROR', e.message);
  }

  try {
    await page.goto(`https://www.sintel.net.co/servicios/${uuid}/solicitar`, { waitUntil: 'networkidle', timeout: 20000 });
    await page.waitForTimeout(1500);
    console.log('=== SOLICITAR PAGE TEXT (first 3000 chars) ===');
    console.log((await page.locator('body').innerText()).slice(0, 3000));
    await page.screenshot({ path: '/tmp/prod_solicitar.png', fullPage: true });
  } catch (e) {
    console.error('SOLICITAR PAGE ERROR', e.message);
  }

  await browser.close();
})();
