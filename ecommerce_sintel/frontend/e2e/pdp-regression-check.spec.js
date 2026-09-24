/**
 * Regresion cross-vertical (mision "Remodelar PDP", 2026-09-16, seccion 39 del
 * brief): BaseGallery.vue (opt-in prop `lightbox`, default false) y
 * PublicDetailView.vue son compartidos por Shop/Renting/Services -- este spec
 * guarda que un cambio futuro en cualquiera de los dos no rompa las otras 2
 * verticales sin que se note. Ver AUDITORIA/PRODUCT_DETAIL_PDP_REDESIGN.md.
 */
import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }) => {
  await page.route('http://localhost:8000/**', (route) => {
    route.continue({ url: route.request().url().replace('localhost:8000', 'django:8000') });
  });
});

test('Renting detail (comparte BaseGallery/PublicDetailView) sin errores de consola', async ({ page }) => {
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
  await page.goto('/alquiler/6f02beb4-4144-411e-9941-6a3ab1521d36');
  await page.waitForLoadState('networkidle');
  await expect(page.locator('.bv-gallery-main').first()).toBeVisible();
  expect(errors, errors.join(' | ')).toEqual([]);
});

test('Services detail sin errores de consola', async ({ page }) => {
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
  await page.goto('/servicios/ee85d731-825a-4660-8e15-152015a514f4');
  await page.waitForLoadState('networkidle');
  expect(errors, errors.join(' | ')).toEqual([]);
});

test('Catalogo de tienda carga sin errores de consola', async ({ page }) => {
  const errors = [];
  page.on('console', (msg) => { if (msg.type() === 'error') errors.push(msg.text()); });
  await page.goto('/tienda');
  await page.waitForLoadState('networkidle');
  expect(errors, errors.join(' | ')).toEqual([]);
});
