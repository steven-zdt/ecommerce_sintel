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

  await page.goto(`${base}/panel/login`, { waitUntil: 'networkidle' });
  await page.fill('input[type="email"]', 'debug_auto_admin@example.com');
  await page.fill('input[type="password"]', 'AdminE2E123!');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(1500);

  await page.goto(`${base}/panel/renta/${uuid}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  console.log('URL:', page.url());
  console.log('body has content:', (await page.locator('body').innerText()).length > 50);

  // Try clicking tabs if present (Variantes / Logistica / Bloqueos) to exercise the catalog store further
  const tabTexts = ['Variantes', 'Log', 'Bloqueo'];
  for (const t of tabTexts) {
    const tab = page.locator(`text=${t}`).first();
    if (await tab.count()) {
      await tab.click().catch(() => {});
      await page.waitForTimeout(600);
    }
  }

  await page.goto(`${base}/panel/r-categorias`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  console.log('categorias rows:', await page.locator('table tbody tr').count().catch(() => 0));

  await page.goto(`${base}/panel/r-labor`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);
  console.log('labor rows:', await page.locator('table tbody tr').count().catch(() => 0));

  console.log('--- Console/page errors ---');
  console.log(errors.length ? errors.join('\n') : '(none)');
  await page.screenshot({ path: '/tmp/equipment_detail_check.png', fullPage: true }).catch(() => {});
  await browser.close();
})();
