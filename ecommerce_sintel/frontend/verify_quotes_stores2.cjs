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
  await page.waitForTimeout(1000);
  const tab = page.locator('text=Solicitudes').locator('xpath=self::*[not(@href)]').first();
  const count = await page.locator('text=Solicitudes').count();
  console.log('Solicitudes matches:', count);
  for (let i = 0; i < count; i++) {
    const el = page.locator('text=Solicitudes').nth(i);
    const href = await el.getAttribute('href').catch(() => null);
    if (!href) { await el.click().catch(() => {}); break; }
  }
  await page.waitForTimeout(1200);
  console.log('rows in Solicitudes tab:', await page.locator('table tbody tr').count().catch(() => 0));

  const viewBtn = page.locator('button[title="Ver detalle"]').first();
  if (await viewBtn.count()) {
    await viewBtn.click().catch(() => {});
    await page.waitForTimeout(1500);
    console.log('modal/detail body length:', (await page.locator('body').innerText()).length);
    console.log('has "Cambiar estado":', (await page.locator('body').innerText()).includes('Cambiar estado'));
  } else {
    console.log('no view button found');
  }

  console.log('--- Console/page errors ---');
  console.log(errors.length ? errors.join('\n') : '(none)');
  await page.screenshot({ path: '/tmp/quotes_stores_check2.png', fullPage: true }).catch(() => {});
  await browser.close();
})();
