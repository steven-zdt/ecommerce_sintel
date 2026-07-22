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

  await page.goto(`${base}/panel/ordenes/renting`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  console.log('URL:', page.url());
  const bodyText = await page.locator('body').innerText();
  console.log('Contains "Operaciones de Renting" (correct board):', bodyText.includes('Operaciones de Renting'));
  console.log('errors:', errors.length ? errors.join('\n') : '(none)');
  await browser.close();
})();
