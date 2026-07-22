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
  const serviceUuid = 'ee85d731-825a-4660-8e15-152015a514f4';
  const packageUuid = '8ddc6a5d-c1c8-47f2-8aaf-9f463e021fd1';

  console.log('--- 1. Login como cliente ---');
  await page.goto(`${base}/login`, { waitUntil: 'networkidle' });
  await page.fill('input[type="email"]', 'e2e_pkg_test@example.com');
  await page.fill('input[type="password"]', 'TestPkg123!');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(2000);
  console.log('URL tras login:', page.url());

  console.log('--- 2. ServiceDetailView: ver paquetes ---');
  await page.goto(`${base}/servicios/${serviceUuid}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);
  const pkgCardVisible = await page.locator('text=Paquete E2E Completo').first().isVisible().catch(() => false);
  console.log('Paquete visible en ServiceDetailView:', pkgCardVisible);

  console.log('--- 3. Ir al wizard con package preseleccionado ---');
  await page.goto(`${base}/servicios/${serviceUuid}/solicitar?package=${packageUuid}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(2000);

  const packageSelectorVisible = await page.locator('text=Personaliza tu paquete').first().isVisible().catch(() => false);
  console.log('PackageSelector heading visible:', packageSelectorVisible);

  const includedItemsVisible = await page.locator('text=8 camaras IP').first().isVisible().catch(() => false);
  console.log('Included items visible:', includedItemsVisible);

  const costCardVisible = await page.locator('text=Trabajo en altura').first().isVisible().catch(() => false);
  console.log('Additional cost card visible:', costCardVisible);

  // Seleccionar variante (paso 1 requiere variante seleccionada)
  const variantCards = page.locator('.srw-variant-card');
  const variantCount = await variantCards.count();
  console.log('Variant cards count:', variantCount);
  if (variantCount > 0) {
    await variantCards.first().click();
    await page.waitForTimeout(500);
  }

  // Toggle el costo adicional "Trabajo en altura"
  const toggleCheckbox = page.locator('text=Trabajo en altura').locator('xpath=ancestor::*[contains(@class,"pkg-cost") or self::div][1]');
  const breakdownBefore = await page.locator('text=Resumen de costos').first().isVisible().catch(() => false);
  console.log('Cost breakdown visible before toggle:', breakdownBefore);

  await page.waitForTimeout(500);
  console.log('--- 4. Continuar al paso 2 ---');
  const continueBtn = page.locator('button:has-text("Continuar")').first();
  const continueDisabled = await continueBtn.isDisabled().catch(() => true);
  console.log('Continuar button disabled?', continueDisabled);
  if (!continueDisabled) {
    await continueBtn.click();
    await page.waitForTimeout(800);
    console.log('Step after continue, url:', page.url());
  }

  console.log('--- Console errors ---');
  console.log(errors.length ? errors.join('\n') : '(none)');

  await page.screenshot({ path: '/tmp/e2e_step1.png', fullPage: true });
  await browser.close();
})().catch((e) => { console.error('FATAL', e); process.exit(1); });
