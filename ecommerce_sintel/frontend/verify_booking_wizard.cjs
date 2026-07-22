const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    args: ['--host-resolver-rules=MAP localhost:8000 ecommerce_sintel_django:8000'],
  });
  const page = await browser.newPage();
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', (err) => errors.push('PAGEERROR: ' + err.message));

  const base = 'http://localhost:5173';
  const uuid = '6f02beb4-4144-411e-9941-6a3ab1521d36';

  await page.goto(`${base}/login`, { waitUntil: 'networkidle' });
  await page.fill('input[type="email"]', 'e2e_pkg_test@example.com');
  await page.fill('input[type="password"]', 'TestPkg123!');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(1500);

  await page.goto(`${base}/alquiler/equipo/${uuid}/solicitar`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  console.log('URL:', page.url());
  console.log('body length:', (await page.locator('body').innerText()).length);
  console.log('Step 1 heading visible:', await page.locator('.step-page h1').first().isVisible().catch(() => false));

  // Avanzar al paso 2
  const continueBtn = page.locator('button.primary');
  if (await continueBtn.count()) {
    await continueBtn.click();
    await page.waitForTimeout(800);
    console.log('After continue, step heading:', await page.locator('.step-page h1').first().textContent().catch(() => null));
  }

  console.log('--- Console/page errors ---');
  console.log(errors.length ? errors.join('\n') : '(none)');
  await page.screenshot({ path: '/tmp/booking_wizard_check.png', fullPage: true }).catch(() => {});
  await browser.close();
})();
