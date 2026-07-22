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
  console.log('URL after login:', page.url());

  await page.goto(`${base}/panel/servicios`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);
  console.log('rows in service list:', await page.locator('table tbody tr').count().catch(() => 0));

  const row = page.locator('tr', { hasText: 'Servicio Fijo Prueba' }).first();
  if (await row.count()) {
    await row.locator('button:has(i.bi-three-dots-vertical)').click();
    await page.waitForTimeout(400);
    await page.locator('.dropdown-menu.show button', { hasText: 'Editar' }).first().click();
    await page.waitForTimeout(1000);
    console.log('Offcanvas open, has Paquetes tab:', await page.locator('button:has-text("Paquetes")').count());
    await page.locator('button:has-text("Paquetes")').first().click();
    await page.waitForTimeout(1000);
    console.log('Paquete listado:', await page.locator('text=Paquete E2E Completo').first().isVisible().catch(() => false));

    // Cambiar a tab Variantes tambien (usa el store "services")
    await page.locator('.nav-link', { hasText: 'Variantes' }).first().click();
    await page.waitForTimeout(800);
    console.log('Variantes tab rows:', await page.locator('.border.rounded-3').count().catch(() => 0));

    // Cambiar a tab Costos (usa CostCalculationPanel, ya arreglado antes)
    await page.locator('.nav-link', { hasText: 'Costos' }).first().click();
    await page.waitForTimeout(800);
    console.log('Costos tab visible content length:', (await page.locator('body').innerText()).length);
  }

  await page.goto(`${base}/panel/s-categorias`, { waitUntil: 'networkidle' }).catch(() => {});
  await page.waitForTimeout(1000);
  console.log('categorias URL:', page.url());
  console.log('categorias rows:', await page.locator('table tbody tr').count().catch(() => 0));

  console.log('--- Console/page errors ---');
  console.log(errors.length ? errors.join('\n') : '(none)');
  await page.screenshot({ path: '/tmp/services_stores_check.png', fullPage: true }).catch(() => {});
  await browser.close();
})();
