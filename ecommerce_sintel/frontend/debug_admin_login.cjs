const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    args: ['--host-resolver-rules=MAP localhost:8000 ecommerce_sintel_django:8000'],
  });
  const page = await browser.newPage();
  page.on('response', async (res) => {
    if (res.url().includes('/auth/') || res.url().includes('/login')) {
      console.log('RESP', res.status(), res.url());
      try { console.log('BODY', JSON.stringify(await res.json())); } catch {}
    }
  });
  page.on('console', (m) => console.log('CONSOLE', m.type(), m.text()));
  page.on('pageerror', (e) => console.log('PAGEERROR', e.message));

  await page.goto('http://localhost:5173/panel/login', { waitUntil: 'networkidle' });
  await page.fill('input[type="email"]', 'debug_auto_admin@example.com');
  await page.fill('input[type="password"]', 'AdminE2E123!');
  await page.click('button:has-text("Ingresar al Panel")');
  await page.waitForTimeout(3000);
  console.log('URL final:', page.url());
  await browser.close();
})();
