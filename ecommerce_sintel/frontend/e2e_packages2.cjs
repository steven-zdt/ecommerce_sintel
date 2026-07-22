const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    args: ['--host-resolver-rules=MAP localhost:8000 ecommerce_sintel_django:8000'],
  });
  const page = await browser.newPage();
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
  page.on('pageerror', (err) => errors.push('PAGEERROR: ' + err.message));
  page.on('response', (res) => {
    if (res.url().includes('/service-orders/') && res.request().method() === 'POST') {
      console.log('ORDER_CREATE_RESPONSE_STATUS', res.status());
    }
  });

  const base = 'http://localhost:5173';
  const serviceUuid = 'ee85d731-825a-4660-8e15-152015a514f4';
  const packageUuid = '8ddc6a5d-c1c8-47f2-8aaf-9f463e021fd1';

  await page.goto(`${base}/login`, { waitUntil: 'networkidle' });
  await page.fill('input[type="email"]', 'e2e_pkg_test@example.com');
  await page.fill('input[type="password"]', 'TestPkg123!');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(1500);

  await page.goto(`${base}/servicios/${serviceUuid}/solicitar?package=${packageUuid}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1500);

  await page.locator('.srw-variant-card').first().click();
  await page.waitForTimeout(300);

  // Activar el costo adicional opcional "Trabajo en altura" (checkbox dentro de su card)
  const alturaCard = page.locator('text=Trabajo en altura').locator('xpath=ancestor::div[contains(@class,"") ][1]');
  const checkboxes = page.locator('input[type="checkbox"]');
  console.log('checkbox count on step1:', await checkboxes.count());

  // Capturar breakdown total antes/despues
  const totalBefore = await page.locator('text=Total estimado').locator('xpath=following-sibling::strong[1]').first().textContent().catch(() => null);
  console.log('Total antes de marcar altura:', totalBefore);

  // Buscar el checkbox mas cercano al texto "Trabajo en altura"
  const alturaRow = page.locator('div', { hasText: 'Trabajo en altura' }).last();
  const alturaCheckbox = alturaRow.locator('input[type="checkbox"]').first();
  if (await alturaCheckbox.count()) {
    await alturaCheckbox.check().catch(async () => { await alturaCheckbox.click(); });
    await page.waitForTimeout(800);
  }
  const totalAfter = await page.locator('text=Total estimado').locator('xpath=following-sibling::strong[1]').first().textContent().catch(() => null);
  console.log('Total despues de marcar altura:', totalAfter);

  await page.click('button:has-text("Continuar")');
  await page.waitForTimeout(500);
  const step2Header = await page.locator('text=Direccion y contacto').first().isVisible().catch(() => false);
  console.log('Step2 header visible:', step2Header);

  // Rellenar paso 2
  await page.fill('input[placeholder="Nombre y apellidos"]', 'Cliente E2E Paquetes');
  await page.selectOption('select:near(:text("Tipo de documento"))', 'CC').catch(async () => {
    await page.locator('select').nth(0).selectOption('CC');
  });
  const docInput = page.locator('input[placeholder="Numero de identificacion"], input[maxlength="20"]').first();
  await docInput.fill('1099887766');
  await page.fill('input[placeholder="correo@empresa.com"]', 'e2e_pkg_test@example.com');
  await page.locator('input[placeholder="3001234567"]').first().fill('3001234567');

  await page.locator('select').filter({ hasText: '' }).nth(0); // no-op guard
  // Departamento / Ciudad
  const deptSelect = page.locator('select').nth(1);
  await deptSelect.selectOption({ label: 'Bogota D.C.' }).catch(() => {});
  await page.waitForTimeout(300);
  const citySelect = page.locator('select').nth(2);
  await citySelect.selectOption({ label: 'Bogota' }).catch(() => {});

  await page.locator('input[placeholder="85A"]').fill('80');
  await page.locator('input[placeholder="45"]').fill('12');
  await page.locator('input[placeholder="20"]').fill('30');

  await page.click('button:has-text("Continuar"):visible');
  await page.waitForTimeout(500);
  const step3Header = await page.locator('text=Fecha y jornada').first().isVisible().catch(() => false);
  console.log('Step3 header visible:', step3Header);

  const dateInput = page.locator('input[type="date"]');
  const minDate = await dateInput.getAttribute('min');
  await dateInput.fill(minDate);
  await page.locator('input[placeholder="Nombre del contacto"]').fill('Contacto Visita E2E');
  await page.locator('input[placeholder="Cargo o rol"]').fill('Administrador');
  await page.locator('input[placeholder="3001234567"]').first().fill('3007654321');

  await page.click('button:has-text("Continuar al pago")');
  await page.waitForTimeout(700);
  const step4Header = await page.locator('text=Confirmar y pagar').first().isVisible().catch(() => false);
  console.log('Step4 header visible:', step4Header);

  const pkgSummaryVisible = await page.locator('text=Paquete seleccionado').first().isVisible().catch(() => false);
  console.log('Package summary card visible on step4:', pkgSummaryVisible);
  const finalTotal = await page.locator('text=Total estimado').last().locator('xpath=following-sibling::strong[1]').first().textContent().catch(() => null);
  console.log('Total final mostrado en resumen:', finalTotal);

  // Aceptar terminos y enviar
  const termsCheckbox = page.locator('input[type="checkbox"]').last();
  await termsCheckbox.check().catch(() => {});
  await page.waitForTimeout(300);

  await page.click('button:has-text("Confirmar y pagar")');
  await page.waitForTimeout(3000);

  const successVisible = await page.locator('text=Solicitud enviada').first().isVisible().catch(() => false);
  console.log('Orden creada (pantalla de exito):', successVisible);

  console.log('--- Console errors ---');
  console.log(errors.length ? errors.join('\n') : '(none)');

  await page.screenshot({ path: '/tmp/e2e_final.png', fullPage: true });
  await browser.close();
})().catch((e) => { console.error('FATAL', e); process.exit(1); });
