/**
 * Regresion visual — primer caso real (2026-07-11).
 *
 * Usa /login porque es la unica pantalla publica, sin dependencias de datos de
 * API (no llama a core/home-feed/ ni requiere estado de sesion), lo que la hace
 * estable entre corridas. Rutas admin (/panel/*) requieren login primero (ver
 * ai_skills/frontend/testing/playwright.md) y rutas customer publicas
 * (Home/Landing) dependen de datos reales del backend, mas fragiles como
 * primera prueba de este mecanismo.
 *
 * Generar/actualizar el baseline:
 *   npx playwright test visual-regression --update-snapshots
 * Verificar contra el baseline:
 *   npx playwright test visual-regression
 */
import { test, expect } from '@playwright/test';

test.describe('Regresion visual', () => {
  test('pantalla de login no cambia visualmente', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveScreenshot('login.png', { maxDiffPixelRatio: 0.02 });
  });
});
