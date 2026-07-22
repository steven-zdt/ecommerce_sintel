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

  await page.goto(`${base}/panel/cotizaciones`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  console.log('URL:', page.url());
  console.log('body length:', (await page.locator('body').innerText()).length);

  // Try clicking any tab that might reveal quotations list
  const tabs = ['Solicitudes', 'Plantillas', 'Cotizaciones'];
  for (const t of tabs) {
    const tab = page.locator(`text=${t}`).first();
    if (await tab.count()) {
      await tab.click().catch(() => {});
      await page.waitForTimeout(800);
      console.log(`clicked tab: ${t}`);
    }
  }

  // Click first row if any table exists (opens RequestViewer probably)
  const firstRow = page.locator('table tbody tr').first();
  if (await firstRow.count()) {
    await firstRow.click().catch(() => {});
    await page.waitForTimeout(1000);
  }

  console.log('--- Console/page errors ---');
  console.log(errors.length ? errors.join('\n') : '(none)');
  await page.screenshot({ path: '/tmp/quotes_stores_check.png', fullPage: true }).catch(() => {});
  await browser.close();
})();
