const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    args: ['--host-resolver-rules=MAP localhost:8000 ecommerce_sintel_django:8000'],
  });
  const page = await browser.newPage();
  page.on('request', (req) => {
    if (req.url().includes('8000') || req.url().includes('admin-auth')) {
      console.log('REQ', req.method(), req.url());
    }
  });
  page.on('requestfailed', (req) => console.log('REQFAILED', req.url(), req.failure()?.errorText));
  page.on('response', (res) => console.log('RESP', res.status(), res.url()));
  page.on('console', (m) => console.log('CONSOLE', m.type(), m.text()));
  page.on('pageerror', (e) => console.log('PAGEERROR', e.message));

  await page.goto('http://localhost:5173/panel/login', { waitUntil: 'networkidle' });
  await page.locator('input[type="email"]').fill('debug_auto_admin@example.com');
  await page.locator('input[type="password"]').fill('AdminE2E123!');
  const emailVal = await page.locator('input[type="email"]').inputValue();
  const pwVal = await page.locator('input[type="password"]').inputValue();
  console.log('FIELD VALUES', emailVal, pwVal.length);

  await page.locator('button[type="submit"]').click();
  await page.waitForTimeout(4000);
  console.log('URL final:', page.url());
  await page.screenshot({ path: '/tmp/debug_login2.png' });
  await browser.close();
})();
