/**
 * E2E — Checkout Wompi (ADR-001, Fase 9) — 2026-07-13.
 *
 * Cubre el comportamiento real end-to-end del proyecto de migracion a
 * integracion API propia con Wompi (payment/.AGENT/docs/ADR_001_MIGRACION_API_WOMPI.md):
 * el sub-metodo "Tarjeta" del checkout ya no abre el Widget completo de Wompi,
 * "PSE / Otros" sigue exactamente igual que siempre, y el feature flag de la
 * Fase 5 controla en vivo cual de los dos esta disponible.
 *
 * REGLA DURA de este proyecto, respetada en todos los specs de este archivo:
 * NUNCA se deja pasar una llamada real hacia la API de Wompi (ni tokenizacion
 * en el navegador ni creacion de transaccion en el backend) -- se intercepta
 * con page.route() en los dos unicos puntos donde el navegador cruza esa
 * frontera (fetch a api.wompi.co, y el POST a nuestro propio initialize/
 * cuando lleva card_token).
 *
 * Gotcha real de infraestructura encontrado al escribir este spec (2026-07-13):
 * `VITE_API_BASE_URL=http://localhost:8000/...` (frontend/.env.development)
 * asume que el navegador corre en el HOST (donde Docker publica los puertos
 * 5173/8000). Cuando Playwright/Chromium corren DENTRO del contenedor
 * `ecommerce_sintel_frontend` (que es como este proyecto documenta correr la
 * suite formal, ver ai_skills/frontend/testing/playwright.md), "localhost:8000"
 * dentro de ese contenedor no tiene nada escuchando -- ningun bug de la app,
 * es la topologia de red de Docker. `http://django:8000` SI es alcanzable por
 * nombre de servicio, pero Django lo rechaza con DisallowedHost (ALLOWED_HOSTS
 * de desarrollo solo incluye localhost/127.0.0.1). La solucion (bridgeBackend
 * abajo): interceptar cada request a localhost:8000 y reenviarla via un
 * http.request crudo de Node hacia el contenedor `nginx` (puerto 80, ya hace
 * proxy_pass a django) forzando el header Host a "localhost" -- fetch() del
 * navegador NO permite spoofear el header Host (esta en la lista prohibida del
 * spec), pero el modulo http nativo de Node si, y por eso el bridge se
 * implementa con http.request en vez de fetch.
 */
import { test, expect } from '@playwright/test';
import http from 'http';

const ADMIN_EMAIL = 'admin@sintel.com';
const ADMIN_PASSWORD = 'Sintel@Admin2026';

// token_id unico por corrida: payment/cards/ tiene constraint unique(token_id)
// -- Fase 3a guarda TODA tarjeta nueva de forma permanente, asi que reusar el
// mismo id entre corridas del spec provocaria un 409 real en la segunda vez
// (encontrado corriendo este spec dos veces seguidas).
function buildWompiTokenizeMock() {
  const uniqueId = `tok_e2e_test_${Date.now()}`;
  return { status: 'CREATED', data: {
    id: uniqueId, brand: 'VISA', last_four: '4242',
    exp_month: '12', exp_year: '29', card_holder: 'E2E Test',
  } };
}

function forwardToNginx(pathAndQuery, method, headers, postDataBuffer) {
  return new Promise((resolve, reject) => {
    const forwardHeaders = { ...headers, host: 'localhost' };
    delete forwardHeaders['content-length']; // recalculado por Node segun el body real
    const req = http.request(
      { host: 'nginx', port: 80, path: pathAndQuery, method, headers: forwardHeaders },
      (res) => {
        const chunks = [];
        res.on('data', (c) => chunks.push(c));
        res.on('end', () => resolve({ status: res.statusCode, headers: res.headers, body: Buffer.concat(chunks) }));
      },
    );
    req.on('error', reject);
    if (postDataBuffer) req.write(postDataBuffer);
    req.end();
  });
}

/**
 * Bridge de red (ver comentario de cabecera) + el unico punto de interceptacion
 * real hacia Wompi que nos interesa: initialize/ con card_token en el body se
 * responde con datos simulados en vez de reenviarse (evita que el backend real
 * dispare una llamada saliente real a Wompi, cosa que este proyecto nunca hace
 * sin autorizacion explicita).
 */
async function setupNetworkBridge(page) {
  await page.route('https://api.wompi.co/v1/tokens/cards', (route) => {
    const mock = buildWompiTokenizeMock();
    page.__lastTokenizedCardId = mock.data.id;
    return route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(mock) });
  });

  await page.route('http://localhost:8000/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const isInitializeWithCardToken =
      url.pathname === '/api/v1/payment/payments/initialize/' &&
      request.method() === 'POST' &&
      !!(request.postDataJSON() || {}).card_token;

    if (isInitializeWithCardToken) {
      page.__lastInitializeBody = request.postDataJSON();
      return route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({
          transaction_uuid: 'e2e-fake-tx-1', wompi_id: 'wompi-e2e-fake-1',
          status: 'PENDING', amount_in_cents: 100000, currency: 'COP',
        }),
      });
    }

    if (url.pathname === '/api/v1/payment/payments/initialize/' && request.method() === 'POST') {
      page.__lastInitializeBody = request.postDataJSON();
      // PSE/Otros: se registra el body para verificar que NO lleva card_token,
      // pero NO se deja pasar tal cual -- evita que el frontend intente cargar
      // el widget.js real de Wompi con datos de sesion falsos.
      return route.fulfill({
        status: 200, contentType: 'application/json',
        body: JSON.stringify({
          uuid: 'e2e-fake-tx-2', transaction_uuid: 'e2e-fake-tx-2', amount_in_cents: 100000,
          currency: 'COP', status: 'PENDING', public_key: 'pub_test_fake', integrity_signature: 'fake',
          widget_url: 'https://checkout.wompi.co/widget.js',
        }),
      });
    }

    try {
      const res = await forwardToNginx(
        url.pathname + url.search, request.method(), request.headers(), request.postDataBuffer(),
      );
      await route.fulfill({ status: res.status, headers: res.headers, body: res.body });
    } catch {
      await route.abort('connectionfailed');
    }
  });
}

async function login(page) {
  await page.goto('/login');
  await page.fill('input[type="email"]', ADMIN_EMAIL);
  await page.fill('input[type="password"]', ADMIN_PASSWORD);
  await page.click('button[type="submit"]');
  // Login exitoso navega fuera de /login via Vue Router (pushState, sin load
  // event real) -- se hace polling directo del pathname en vez de waitForURL.
  await page.waitForFunction(() => !location.pathname.startsWith('/login'), { timeout: 10000 });
}

/**
 * ColombianAddressForm.vue exige departamento/ciudad/barrio/direccion
 * completos para que validate() pase -- sin esto submitOrder() corta en
 * silencio con un toast, sin llegar nunca a initialize/. Nombre/email ya
 * vienen prellenados desde authStore.user, no hace falta tocarlos.
 */
async function fillAddressForm(page) {
  const phoneInput = page.getByPlaceholder('3001234567').first();
  if (await phoneInput.count() > 0) await phoneInput.fill('3001234567');

  const departmentSelect = page.locator('select', { hasText: 'Seleccionar departamento' });
  await departmentSelect.selectOption({ label: 'Cundinamarca' });

  const citySelect = page.locator('select', { hasText: 'Seleccionar ciudad' });
  const cityOptions = await citySelect.locator('option').allTextContents();
  const realCity = cityOptions.find((o) => !o.includes('Seleccionar'));
  if (realCity) await citySelect.selectOption({ label: realCity });

  await page.getByPlaceholder('Ej. Chapinero, Poblado').fill('Barrio E2E');
  await page.getByPlaceholder('85, 45A').fill('85');
  await page.getByPlaceholder('15, 82').fill('15');
  await page.getByPlaceholder('25, 40').fill('40');
}

async function ensureCartHasItem(page) {
  const token = await page.evaluate(() => localStorage.getItem('sintel_access'));
  const headers = { authorization: `Bearer ${token}` };

  const cartRes = await forwardToNginx('/api/v1/cart/', 'GET', headers);
  const cart = JSON.parse(cartRes.body.toString());
  if (cart.items?.length > 0) return;

  const productsRes = await forwardToNginx('/api/v1/shop/products/?page_size=1', 'GET', headers);
  const productData = JSON.parse(productsRes.body.toString());
  const product = (productData.results || productData)[0];
  test.skip(!product, 'No hay productos en el catalogo de desarrollo para poblar el carrito.');

  const detailRes = await forwardToNginx(`/api/v1/shop/products/${product.uuid}/`, 'GET', headers);
  const detail = JSON.parse(detailRes.body.toString());
  const variantUuid = detail.variants?.[0]?.uuid;
  test.skip(!variantUuid, 'El producto de prueba no tiene variantes disponibles.');

  const body = Buffer.from(JSON.stringify({ variant_uuid: variantUuid, quantity: 1 }));
  const addRes = await forwardToNginx('/api/v1/cart/add_item/', 'POST', {
    ...headers, 'content-type': 'application/json',
  }, body);
  test.skip(addRes.status >= 300, `No se pudo agregar el item al carrito (status ${addRes.status}).`);
}

test.describe('Checkout Wompi — sub-metodo Tarjeta (ADR-001 Fase 3b)', () => {
  test('pagar con tarjeta nueva no abre el widget de Wompi', async ({ page }) => {
    await setupNetworkBridge(page);
    await login(page);
    await ensureCartHasItem(page);

    await page.goto('/checkout');
    await page.waitForSelector('button:has-text("Pagar")', { timeout: 10000 });
    await fillAddressForm(page);

    // Si la cuenta ya tiene tarjetas guardadas (de verificaciones previas de
    // esta misma sesion), el sub-metodo "Tarjeta" preselecciona la primera en
    // vez de "Agregar tarjeta nueva" -- forzar el camino de tarjeta nueva a
    // proposito, que es lo que este test quiere cubrir.
    const addNewCardOption = page.locator('text=Agregar tarjeta nueva');
    if (await addNewCardOption.count() > 0) await addNewCardOption.click();

    // waitFor explicito (no un count() sincrono) -- el click de arriba dispara
    // un re-render de Vue que puede no haber terminado todavia en el instante
    // en que se evalua la siguiente linea (race condition real encontrada al
    // escribir este spec). Placeholder real de este formulario (distinto del
    // de CustomerCardsView.vue, que si usa "4242 4242...").
    const numberInput = page.getByPlaceholder('Numero de tarjeta');
    await numberInput.waitFor({ state: 'visible', timeout: 5000 });
    await numberInput.fill('4242424242424242');
    await page.locator('input[placeholder="MM"]').fill('12');
    await page.locator('input[placeholder="AA"]').fill('29');
    await page.locator('input[placeholder="CVC"]').fill('123');
    await page.locator('input[placeholder*="titular" i]').fill('Cliente E2E');

    await page.click('button:has-text("Pagar")');
    await page.waitForFunction(() => location.pathname === '/payment/result', { timeout: 15000 });

    // __lastInitializeBody/__lastTokenizedCardId se guardan en los handlers de
    // page.route() -- viven del lado de Node (Playwright), no en window del
    // navegador; se leen directo.
    expect(page.__lastInitializeBody?.card_token).toBe(page.__lastTokenizedCardId);
    expect(await page.locator('iframe[src*="checkout.wompi.co"]').count()).toBe(0);
  });
});

test.describe('Checkout Wompi — sub-metodo PSE/Otros (sin cambios, ADR-001 Fase 3b)', () => {
  test('PSE/Otros nunca envia card_token a initialize/', async ({ page }) => {
    await setupNetworkBridge(page);
    await login(page);
    await ensureCartHasItem(page);

    await page.goto('/checkout');
    await page.waitForSelector('button:has-text("Pagar")', { timeout: 10000 });
    await fillAddressForm(page);

    const pseButton = page.locator('button:has-text("PSE / Otros")');
    await expect(pseButton).toBeVisible({ timeout: 10000 });
    await pseButton.click();

    await expect(page.locator('input[placeholder*="4242"]')).toHaveCount(0);

    await page.click('button:has-text("Pagar")');
    await page.waitForTimeout(2000);

    expect(page.__lastInitializeBody).toBeTruthy();
    expect(page.__lastInitializeBody.card_token).toBeUndefined();
  });
});

test.describe('Panel admin de pagos (ADR-001 Fase 7)', () => {
  test('el switch de feature flag persiste y vuelve a su estado original', async ({ page }) => {
    await setupNetworkBridge(page);
    await login(page);
    await page.goto('/panel/pagos');

    const toggle = page.locator('input[type="checkbox"][role="switch"]');
    await expect(toggle).toBeVisible({ timeout: 10000 });
    const initialState = await toggle.isChecked();

    await toggle.click();
    await page.waitForTimeout(500);
    await expect(toggle).toBeChecked({ checked: !initialState });

    await page.reload();
    await setupNetworkBridge(page); // el reload limpia los route() previos
    await expect(page.locator('input[type="checkbox"][role="switch"]')).toBeChecked({ checked: !initialState });

    await page.locator('input[type="checkbox"][role="switch"]').click();
    await page.waitForTimeout(500);
    await expect(page.locator('input[type="checkbox"][role="switch"]')).toBeChecked({ checked: initialState });
  });
});
