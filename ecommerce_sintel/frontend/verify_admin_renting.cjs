const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    args: ['--host-resolver-rules=MAP localhost:8000 ecommerce_sintel_django:8000'],
  });
  const page = await browser.newPage({ viewport: { width: 1500, height: 1100 } });
  const consoleErrors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
  page.on('pageerror', (err) => consoleErrors.push('pageerror: ' + err.message));

  await page.goto('http://localhost:5173/panel/login', { waitUntil: 'networkidle' });
  await page.fill('input[type="email"]', 'debug_auto_admin@example.com');
  await page.fill('input[type="password"]', 'DevTest12345!');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);
  console.log('After login URL:', page.url());

  await page.goto('http://localhost:5173/panel/renta', { waitUntil: 'networkidle' });
  await page.waitForTimeout(1000);

  // Abrir edicion de la fila del equipo demo especifico (por nombre exacto)
  const demoRow = page.locator('tr', { has: page.locator('text=Grua Hidraulica 20T Demo') }).first();
  await demoRow.waitFor({ timeout: 10000 });
  const editButton = demoRow.locator('button[title="Editar"]').first();
  await editButton.click();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: '/tmp/admin_form_datos.png' });

  const tabsToCheck = ['galeria', 'incluye', 'especificaciones', 'documentacion', 'videos', 'faq', 'seo'];
  const results = {};
  for (const tabKey of tabsToCheck) {
    const tabButton = page.locator(`button:has-text("${tabLabel(tabKey)}")`).first();
    if (await tabButton.count()) {
      await tabButton.click();
      await page.waitForTimeout(900);
      const screenshotPath = `/tmp/admin_tab_${tabKey}.png`;
      await page.screenshot({ path: screenshotPath });
      results[tabKey] = 'clicked+screenshot';
    } else {
      results[tabKey] = 'BUTTON NOT FOUND';
    }
  }
  console.log('Tab results:', JSON.stringify(results, null, 2));
  console.log('Console errors:', consoleErrors.length ? consoleErrors : 'NONE');

  await browser.close();

  function tabLabel(key) {
    const map = {
      galeria: 'Galeria',
      incluye: 'Incluye',
      especificaciones: 'Especificaciones',
      documentacion: 'Documentacion',
      videos: 'Videos',
      faq: 'FAQ',
      seo: 'SEO',
    };
    return map[key];
  }
})().catch((err) => { console.error('FATAL', err); process.exit(1); });
