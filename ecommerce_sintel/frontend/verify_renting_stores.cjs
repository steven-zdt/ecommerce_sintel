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

  await page.goto(`${base}/panel/login`, { waitUntil: 'networkidle' });
  await page.fill('input[type="email"]', 'debug_auto_admin@example.com');
  await page.fill('input[type="password"]', 'AdminE2E123!');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(1500);

  await page.goto(`${base}/panel/renta`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  console.log('URL renting list:', page.url());
  const rowsCount = await page.locator('table tbody tr').count().catch(() => 0);
  console.log('Equipment rows found:', rowsCount);

  // Click first equipment row to open detail (exercises catalog store: equipment/variants/logistics/blocks)
  const firstRow = page.locator('table tbody tr').first();
  if (await firstRow.count()) {
    await firstRow.click();
    await page.waitForTimeout(1000);
    console.log('After row click URL:', page.url());
  }

  await page.goto(`${base}/panel/renta/solicitudes`, { waitUntil: 'networkidle' }).catch(() => {});
  await page.waitForTimeout(1200);
  console.log('URL rental requests:', page.url());
  const reqRows = await page.locator('table tbody tr').count().catch(() => 0);
  console.log('Rental request rows found:', reqRows);

  console.log('--- Console/page errors ---');
  console.log(errors.length ? errors.join('\n') : '(none)');
  await page.screenshot({ path: '/tmp/renting_stores_check.png', fullPage: true }).catch(() => {});
  await browser.close();
})();
