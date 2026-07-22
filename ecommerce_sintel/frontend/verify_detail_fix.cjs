const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({
    args: ['--host-resolver-rules=MAP localhost:8000 ecommerce_sintel_django:8000'],
  });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', (e) => errors.push(e.message));
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });

  const uuid = 'ee85d731-825a-4660-8e15-152015a514f4'; // Servicio Fijo Prueba (con paquete real)

  await page.goto(`http://localhost:5173/servicios/${uuid}`, { waitUntil: 'networkidle' });
  await page.waitForTimeout(1200);

  const bodyText = await page.locator('body').innerText();
  console.log('Contiene "Elige el alcance del servicio" (viejo, debe ser false):', bodyText.includes('Elige el alcance del servicio'));
  console.log('Contiene "Paquetes comerciales" viejo kicker (debe ser false):', bodyText.includes('Paquetes comerciales'));
  console.log('Contiene "Agenda tu servicio con Sintel" (nuevo, debe ser true):', bodyText.includes('Agenda tu servicio con Sintel'));
  console.log('Contiene boton "Solicitar servicio":', bodyText.includes('Solicitar servicio'));
  console.log('Contiene seccion real "Paquetes disponibles":', bodyText.includes('Paquetes disponibles'));

  const buyBtn = page.locator('a.buy-btn, .buy-btn');
  console.log('buy-btn count:', await buyBtn.count());
  const href = await buyBtn.first().getAttribute('href').catch(() => null);
  console.log('buy-btn href:', href);

  await page.screenshot({ path: '/tmp/detail_fix.png', fullPage: true });
  console.log('errors:', errors.length ? errors.join('\n') : '(none)');
  await browser.close();
})();
