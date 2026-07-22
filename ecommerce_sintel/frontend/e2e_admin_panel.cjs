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

  try {
    await page.goto(`${base}/panel/login`, { waitUntil: 'networkidle' });
    await page.fill('input[type="email"]', 'debug_auto_admin@example.com');
    const pwd = process.env.ADMIN_PW || 'admin12345';
    await page.fill('input[type="password"]', pwd);
    await page.click('button[type="submit"]');
    await page.waitForTimeout(2000);
    console.log('URL tras login admin:', page.url());

    await page.goto(`${base}/panel/servicios`, { waitUntil: 'networkidle' });
    await page.waitForTimeout(1500);
    console.log('URL panel servicios:', page.url());

    const row = page.locator('tr', { hasText: 'Servicio Fijo Prueba' }).first();
    const rowVisible = await row.isVisible().catch(() => false);
    console.log('Fila del servicio visible:', rowVisible);
    if (rowVisible) {
      await row.locator('button:has(i.bi-three-dots-vertical)').click();
      await page.waitForTimeout(400);
      await page.locator('.dropdown-menu.show button', { hasText: 'Editar' }).first().click();
      await page.waitForTimeout(1000);
      const packagesTab = page.locator('button:has-text("Paquetes")');
      console.log('Tab Paquetes visible:', await packagesTab.first().isVisible().catch(() => false));
      await packagesTab.first().click();
      await page.waitForTimeout(1000);
      const pkgVisible = await page.locator('text=Paquete E2E Completo').first().isVisible().catch(() => false);
      console.log('Paquete listado en tab admin:', pkgVisible);
      const expandBtn = page.locator('button[title="Gestionar incluidos y costos"]').first();
      if (await expandBtn.count()) {
        await expandBtn.click();
        await page.waitForTimeout(1000);
        const includedVisible = await page.locator('text=8 camaras IP').first().isVisible().catch(() => false);
        console.log('Item incluido visible en admin:', includedVisible);
        const costVisible = await page.locator('text=Urgencia').first().isVisible().catch(() => false);
        console.log('Costo adicional visible en admin:', costVisible);
      }
    }
    console.log('--- Console errors ---');
    console.log(errors.length ? errors.join('\n') : '(none)');
  } catch (e) {
    console.error('ERROR DURING FLOW:', e.message);
  } finally {
    console.log('--- Console/page errors (finally) ---');
    console.log(errors.length ? errors.join('\n---\n') : '(none)');
    await page.screenshot({ path: '/tmp/e2e_admin_panel.png', fullPage: true }).catch(() => {});
    await browser.close();
  }
})();
