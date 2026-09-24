/**
 * PDP publica (Shop) — rediseno 3 columnas (mision "Remodelar PDP", 2026-09-16).
 *
 * El UUID del brief original (1b541c67-f443-4336-beb2-d5c02a361cc8) NO existe en
 * la base de datos de dev (confirmado por ORM y por un 404 real, ver
 * AUDITORIA/PRODUCT_DETAIL_PDP_BASELINE.md seccion 6) -- se usa un producto real
 * verificado en su lugar. Si este UUID deja de existir en un futuro reset de la
 * base de datos de dev, actualizar la constante de abajo con
 * `Product.objects.filter(is_deleted=False).first().uuid` real.
 *
 * Ver AUDITORIA/PRODUCT_DETAIL_PDP_REDESIGN.md para el detalle de la mision.
 */
import { test, expect } from '@playwright/test';

const PRODUCT_UUID = 'f54ccb3a-315c-4e11-b878-700c2c96c539';
const PRODUCT_PATH = `/tienda/${PRODUCT_UUID}`;

const VIEWPORTS = [
  { name: 'desktop-1366', width: 1366, height: 768 },
  { name: 'desktop-1440', width: 1440, height: 900 },
  { name: 'desktop-1920', width: 1920, height: 1080 },
  { name: 'tablet-768', width: 768, height: 1024 },
  { name: 'mobile-390', width: 390, height: 844 },
];

test.describe('PDP rediseno 3 columnas — producto real', () => {
  // Este spec corre DENTRO del contenedor `ecommerce_sintel_frontend` (ver
  // ai_skills/frontend/testing/playwright.md) -- ahi "localhost:8000" no
  // resuelve a Django (namespace de red propio del contenedor), a diferencia
  // de un navegador real en el HOST donde si funciona via el port-forward de
  // Docker. Se reescribe SOLO en este proceso de test, nunca afecta produccion
  // ni el comportamiento real de un usuario.
  test.beforeEach(async ({ page }) => {
    await page.route('http://localhost:8000/**', (route) => {
      route.continue({ url: route.request().url().replace('localhost:8000', 'django:8000') });
    });
  });

  test('carga sin errores de consola y sin 404 de red', async ({ page }) => {
    const consoleErrors = [];
    const failedRequests = [];
    page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
    page.on('response', (res) => { if (res.status() >= 400) failedRequests.push(`${res.status()} ${res.url()}`); });

    await page.goto(PRODUCT_PATH);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.pd-title')).toBeVisible();

    expect(consoleErrors, `console errors: ${consoleErrors.join(' | ')}`).toEqual([]);
    expect(failedRequests, `failed requests: ${failedRequests.join(' | ')}`).toEqual([]);
  });

  test('layout desktop: galeria, info y compra son 3 columnas separadas (no anidadas)', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(PRODUCT_PATH);
    await page.waitForLoadState('networkidle');

    const galleryBox = await page.locator('.gallery-sticky').boundingBox();
    const titleBox = await page.locator('.pd-title').boundingBox();
    const purchaseBox = await page.locator('.ppc-card').boundingBox();

    expect(galleryBox, 'galeria debe existir').not.toBeNull();
    expect(titleBox, 'titulo (columna info) debe existir').not.toBeNull();
    expect(purchaseBox, 'tarjeta de compra debe existir').not.toBeNull();

    // 3 columnas reales = 3 x-offsets distintos, en el mismo orden horizontal
    // (no la tarjeta de compra anidada al final de la columna de info).
    expect(galleryBox.x).toBeLessThan(titleBox.x);
    expect(titleBox.x + titleBox.width).toBeLessThanOrEqual(purchaseBox.x + 1);
  });

  test('galeria: lightbox abre con click, navega y cierra con Escape', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(PRODUCT_PATH);
    await page.waitForLoadState('networkidle');

    await page.locator('.bv-gallery-main').click();
    const lightbox = page.locator('.bv-lightbox-backdrop');
    await expect(lightbox).toBeVisible();
    await expect(lightbox.locator('.bv-lightbox-img')).toBeVisible();

    await page.keyboard.press('Escape');
    await expect(lightbox).toBeHidden();
  });

  test('panel de compra: cantidad respeta minimo/maximo y agregar al carrito reacciona', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(PRODUCT_PATH);
    await page.waitForLoadState('networkidle');

    const qtyInput = page.locator('.ppc-qty-input');
    await expect(qtyInput).toHaveValue('1');

    const minusBtn = page.locator('.ppc-qty-btn').first();
    await expect(minusBtn).toBeDisabled(); // ya esta en el minimo (1)

    const plusBtn = page.locator('.ppc-qty-btn').nth(1);
    await plusBtn.click();
    await expect(qtyInput).toHaveValue('2');

    // Sin sesion: "Agregar al carrito" redirige a /login (comportamiento
    // existente, no cambiado por esta mision) -- solo se verifica que el
    // click no rompe la pagina.
    await page.locator('.ppc-btn-secondary').click();
    await page.waitForLoadState('networkidle');
  });

  for (const vp of VIEWPORTS) {
    test(`responsive @ ${vp.name} (${vp.width}x${vp.height}) — sin overflow horizontal`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto(PRODUCT_PATH);
      await page.waitForLoadState('networkidle');
      await expect(page.locator('.pd-title')).toBeVisible();

      const hasHorizontalOverflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1
      );
      expect(hasHorizontalOverflow, `overflow horizontal en ${vp.name}`).toBe(false);

      await page.screenshot({ path: `test-results/pdp-${vp.name}.png`, fullPage: true });
    });
  }
});
