/**
 * PDP publica (Renting) — rediseno 3 columnas, Fase 2 (mision "Remodelar PDP
 * Renting", 2026-09-16). Alcance de esta fase: solo layout, con los datos que
 * YA trae `unified/detail/?module=renting` -- sin selector de variante, sin
 * fechas, sin chequeo de disponibilidad por periodo (Fase 3 aparte).
 *
 * El UUID del brief (d443139b-7b94-4c41-9fed-9e96c409ac7f) NO existe en dev
 * (confirmado por ORM, ver AUDITORIA/RENTING_DETAIL_BASELINE.md seccion 0).
 * Se usa un equipo real con contenido rico ("Grua Hidraulica 20T Demo", 2
 * imagenes, 2 variantes, precio dia+hora) -- este mismo equipo tenia un bug
 * real de backend (thumbnail vacio de un RentalVideo rompia la serializacion
 * con un 500) encontrado y corregido en esta misma sesion
 * (renting/services/presenters.py).
 */
import { test, expect } from '@playwright/test';

const EQUIPMENT_UUID = '693e2d7e-b260-4206-9058-4566b08e4e6a';
const EQUIPMENT_PATH = `/alquiler/${EQUIPMENT_UUID}`;

const VIEWPORTS = [
  { name: 'desktop-1366', width: 1366, height: 768 },
  { name: 'desktop-1440', width: 1440, height: 900 },
  { name: 'desktop-1920', width: 1920, height: 1080 },
  { name: 'tablet-768', width: 768, height: 1024 },
  { name: 'mobile-390', width: 390, height: 844 },
];

test.describe('PDP Renting rediseno 3 columnas — equipo real', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('http://localhost:8000/**', (route) => {
      route.continue({ url: route.request().url().replace('localhost:8000', 'django:8000') });
    });
  });

  test('carga sin errores de consola y sin requests fallidos', async ({ page }) => {
    const consoleErrors = [];
    const failedRequests = [];
    page.on('console', (msg) => { if (msg.type() === 'error') consoleErrors.push(msg.text()); });
    page.on('response', (res) => { if (res.status() >= 400) failedRequests.push(`${res.status()} ${res.url()}`); });

    await page.goto(EQUIPMENT_PATH);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.equipment-title')).toBeVisible();

    expect(consoleErrors, consoleErrors.join(' | ')).toEqual([]);
    expect(failedRequests, failedRequests.join(' | ')).toEqual([]);
  });

  test('layout desktop: 3 columnas reales (galeria, info, panel de reserva)', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(EQUIPMENT_PATH);
    await page.waitForLoadState('networkidle');

    const galleryBox = await page.locator('.gallery-sticky').boundingBox();
    const titleBox = await page.locator('.equipment-title').boundingBox();
    const panelBox = await page.locator('.package-panel').boundingBox();

    expect(galleryBox).not.toBeNull();
    expect(titleBox).not.toBeNull();
    expect(panelBox).not.toBeNull();

    expect(galleryBox.x).toBeLessThan(titleBox.x);
    expect(titleBox.x + titleBox.width).toBeLessThanOrEqual(panelBox.x + 1);
  });

  test('panel de reserva: muestra precio por dia y por hora, disponibilidad y CTA al wizard', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(EQUIPMENT_PATH);
    await page.waitForLoadState('networkidle');

    const panel = page.locator('.package-panel');
    await expect(panel.locator('.rental-price-value').first()).toContainText('$');
    await expect(panel).toContainText('/ dia');
    await expect(panel).toContainText('/ hora');
    await expect(panel).toContainText('Disponibilidad');

    const cta = panel.locator('.reserve-btn');
    await expect(cta).toBeVisible();
    await expect(cta).toHaveAttribute('href', `/alquiler/${EQUIPMENT_UUID}/solicitar`);
    await cta.click();
    // Sin sesion: la ruta del wizard exige auth (meta.requiresAuth) y el guard
    // real redirige a /login -- comportamiento preexistente correcto, no algo
    // que esta mision deba cambiar. `waitForURL` espera la navegacion real
    // (el guard es async), a diferencia de `waitForLoadState('networkidle')`
    // que puede resolver antes de que el guard termine.
    await page.waitForURL(/\/(login|alquiler\/.+\/solicitar)/);
    expect(page.url()).toMatch(/\/(login|alquiler\/.+\/solicitar)/);
  });

  test('galeria: lightbox abre con click y cierra con Escape (reuso del BaseGallery de Shop)', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto(EQUIPMENT_PATH);
    await page.waitForLoadState('networkidle');

    await page.locator('.bv-gallery-main').click();
    const lightbox = page.locator('.bv-lightbox-backdrop');
    await expect(lightbox).toBeVisible();
    await page.keyboard.press('Escape');
    await expect(lightbox).toBeHidden();
  });

  for (const vp of VIEWPORTS) {
    test(`responsive @ ${vp.name} (${vp.width}x${vp.height}) — sin overflow horizontal`, async ({ page }) => {
      await page.setViewportSize({ width: vp.width, height: vp.height });
      await page.goto(EQUIPMENT_PATH);
      await page.waitForLoadState('networkidle');
      await expect(page.locator('.equipment-title')).toBeVisible();

      const hasHorizontalOverflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1
      );
      expect(hasHorizontalOverflow, `overflow horizontal en ${vp.name}`).toBe(false);

      await page.screenshot({ path: `test-results/renting-pdp-${vp.name}.png`, fullPage: true });
    });
  }
});
