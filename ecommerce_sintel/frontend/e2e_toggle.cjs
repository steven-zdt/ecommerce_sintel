const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    args: ['--host-resolver-rules=MAP localhost:8000 ecommerce_sintel_django:8000'],
  });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (err) => errors.push('PAGEERROR: ' + err.message));

  const base = 'http://localhost:5173';
  const serviceUuid = 'ee85d731-825a-4660-8e15-152015a514f4';
  const packageUuid = '8ddc6a5d-c1c8-47f2-8aaf-9f463e021fd1';

  await page.goto(`${base}/login`, { waitUntil: 'networkidle' });
  await page.fill('input[type="email"]', 'e2e_pkg_test@example.com');
  await page.fill('input[type="password"]', 'TestPkg123!');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(1500);

  await page.goto(`${base}/servicios/${serviceUuid}/solicitar?package=${packageUuid}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  await page.locator('.srw-variant-card').first().click();
  await page.waitForTimeout(500);

  const totalBefore = await page.locator('text=Total estimado').locator('xpath=following-sibling::strong[1]').first().textContent();
  console.log('Total antes:', totalBefore);

  // Localizar la cost-card cuyo texto contiene "Trabajo en altura" y clicar su checkbox interno
  const costCard = page.locator('.cost-card', { hasText: 'Trabajo en altura' });
  console.log('cost-card count:', await costCard.count());
  const checkbox = costCard.locator('input[type="checkbox"]');
  console.log('is checked before:', await checkbox.isChecked());
  await checkbox.click({ force: true });
  await page.waitForTimeout(1000);
  console.log('is checked after:', await checkbox.isChecked());

  const totalAfter = await page.locator('text=Total estimado').locator('xpath=following-sibling::strong[1]').first().textContent();
  console.log('Total despues:', totalAfter);

  console.log('errors:', errors.length ? errors.join('\n') : '(none)');
  await browser.close();
})().catch((e) => { console.error('FATAL', e); process.exit(1); });
