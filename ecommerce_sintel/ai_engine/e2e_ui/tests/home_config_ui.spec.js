// ═══════════════════════════════════════════════════════════════════════
// TEST E2E UI — Home Config → Home Publica (http://localhost:5173/)
//
// Sincroniza las operaciones del script API con la UI del navegador:
//  1. Crea banner / modulo / tarjeta via API (igual que e2e_home_config_test.ps1)
//  2. Abre http://localhost:5173/ y verifica que cada item aparece en pantalla
//  3. Actualiza cada item y verifica la actualizacion en el browser
//  4. Limpia via API y verifica que desaparecen de la UI
//
// Ejecutar: cd ai_engine/e2e_ui && npx playwright test --headed
// ═══════════════════════════════════════════════════════════════════════

import { test, expect, request } from '@playwright/test';

const API     = 'http://localhost:8000/api/v1';
const UI      = 'http://localhost:5173';
const EMAIL   = 'admin@sintel.com';
const PASS    = 'Sintel@Admin2026';
const TAG     = `E2E_UI_${Date.now()}`;

// ── Helpers de API ──────────────────────────────────────────────────────────
async function getToken(apiCtx) {
  const r = await apiCtx.post(`${API}/auth/login/`, {
    data: { email: EMAIL, password: PASS },
  });
  expect(r.ok(), `Login fallido: ${await r.text()}`).toBeTruthy();
  const body = await r.json();
  return body.tokens.access;
}

async function apiPost(apiCtx, token, path, data) {
  const r = await apiCtx.post(`${API}${path}`, {
    data,
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok()) {
    const txt = await r.text();
    throw new Error(`POST ${path} → ${r.status()} ${txt}`);
  }
  return r.json();
}

async function apiPatch(apiCtx, token, path, data) {
  const r = await apiCtx.patch(`${API}${path}`, {
    data,
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok()) throw new Error(`PATCH ${path} → ${r.status()} ${await r.text()}`);
  return r.json();
}

async function apiDelete(apiCtx, token, path) {
  const r = await apiCtx.delete(`${API}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!r.ok()) throw new Error(`DELETE ${path} → ${r.status()} ${await r.text()}`);
}

// ── Setup compartido ─────────────────────────────────────────────────────────
let token;
let bannerUuid, moduleUuid, moduleKey, cardUuid;

test.beforeAll(async ({ playwright }) => {
  const apiCtx = await playwright.request.newContext();
  token = await getToken(apiCtx);
  await apiCtx.dispose();
});

// ════════════════════════════════════════════════════════════════════════════
//  SUITE A — BANNERS
// ════════════════════════════════════════════════════════════════════════════
test.describe('A — Banners', () => {

  test('A1: crear banner via API y aparecer inmediatamente en /', async ({ page, playwright }) => {
    const apiCtx = await playwright.request.newContext();

    // Crear banner
    const banner = await apiPost(apiCtx, token, '/dashboard/home-config/banners/create/', {
      title:         `${TAG} Banner Playwright`,
      subtitle:      'Subtitulo del banner E2E UI',
      link_url:      '/tienda',
      link_label:    'Ver catalogo',
      display_order: 99,
      is_active:     true,
    });
    bannerUuid = banner.uuid;

    await apiCtx.dispose();

    // Abrir home publica y esperar que cargue
    await page.goto(UI);
    await page.waitForLoadState('networkidle');

    // El carousel debe estar presente
    const bannerSection = page.locator('#homeBannerCarousel');
    await expect(bannerSection).toBeVisible({ timeout: 8000 });

    // El banner puede estar en un slide no-activo (display_order: 99 → último slide).
    // Verificamos que el contenido existe en el DOM del carousel (attached),
    // independientemente de si el slide es el activo en este momento.
    const bannerTitle = page.locator('#homeBannerCarousel .banner-title').filter({ hasText: `${TAG} Banner Playwright` });
    await expect(bannerTitle.first()).toBeAttached({ timeout: 5000 });

    // Subtitulo y CTA también en el DOM del carousel
    const bannerSub = page.locator('#homeBannerCarousel .banner-sub').filter({ hasText: 'Subtitulo del banner E2E UI' });
    await expect(bannerSub.first()).toBeAttached();

    const cta = page.locator('#homeBannerCarousel .banner-content a').filter({ hasText: 'Ver catalogo' });
    await expect(cta.first()).toBeAttached();
  });

  test('A2: actualizar banner → cambio visible en UI sin recargar forzado', async ({ page, playwright }) => {
    test.skip(!bannerUuid, 'A1 no creo el banner');
    const apiCtx = await playwright.request.newContext();

    await apiPatch(apiCtx, token, `/dashboard/home-config/banners/${bannerUuid}/`, {
      subtitle: 'Subtitulo ACTUALIZADO por Playwright',
    });
    await apiCtx.dispose();

    // Recargar la home (simula usuario que regresa)
    await page.goto(UI);
    await page.waitForLoadState('networkidle');

    const updatedSub = page.locator('#homeBannerCarousel .banner-sub').filter({ hasText: 'Subtitulo ACTUALIZADO por Playwright' });
    await expect(updatedSub.first()).toBeAttached({ timeout: 5000 });
  });

  test('A3: desactivar banner → desaparece de la UI', async ({ page, playwright }) => {
    test.skip(!bannerUuid, 'A1 no creo el banner');
    const apiCtx = await playwright.request.newContext();

    await apiPatch(apiCtx, token, `/dashboard/home-config/banners/${bannerUuid}/`, { is_active: false });
    await apiCtx.dispose();

    await page.goto(UI);
    await page.waitForLoadState('networkidle');

    // El titulo del banner NO debe aparecer
    const bannerTitle = page.locator('#homeBannerCarousel .banner-title').filter({ hasText: `${TAG} Banner Playwright` });
    await expect(bannerTitle).not.toBeAttached({ timeout: 5000 });
  });

});

// ════════════════════════════════════════════════════════════════════════════
//  SUITE B — MODULOS
// ════════════════════════════════════════════════════════════════════════════
test.describe('B — Modulos', () => {

  test('B1: crear modulo personalizado → aparece en seccion "Nuestros servicios"', async ({ page, playwright }) => {
    const apiCtx = await playwright.request.newContext();
    moduleKey = `e2e_ui_${Date.now()}`;

    const mod = await apiPost(apiCtx, token, '/dashboard/home-config/modules/create/', {
      module_key:           moduleKey,
      custom_label:         `${TAG} Modulo UI`,
      custom_icon:          'bi-cpu',
      custom_url:           '/e2e-ui-test',
      custom_color:         '#7c3aed',
      display_order:        99,
      featured_items_limit: 4,
      is_visible:           true,
    });
    moduleUuid = mod.uuid;
    await apiCtx.dispose();

    await page.goto(UI);
    await page.waitForLoadState('networkidle');

    // La seccion de modulos debe contener el label del nuevo modulo
    const modLabel = page.locator('.module-label', { hasText: `${TAG} Modulo UI` });
    await expect(modLabel).toBeVisible({ timeout: 5000 });

    // La tarjeta del modulo scoped por label unico para evitar colisiones con runs anteriores
    const modLink = page.locator('a.module-card').filter({ has: page.locator('.module-label', { hasText: `${TAG} Modulo UI` }) });
    await expect(modLink.first()).toBeVisible();
  });

  test('B2: actualizar label del modulo → refleja en UI', async ({ page, playwright }) => {
    test.skip(!moduleUuid, 'B1 no creo el modulo');
    const apiCtx = await playwright.request.newContext();

    await apiPatch(apiCtx, token, `/dashboard/home-config/modules/${moduleUuid}/`, {
      custom_label: `${TAG} Modulo ACTUALIZADO`,
    });
    await apiCtx.dispose();

    await page.goto(UI);
    await page.waitForLoadState('networkidle');

    const updLabel = page.locator('.module-label', { hasText: `${TAG} Modulo ACTUALIZADO` });
    await expect(updLabel).toBeVisible({ timeout: 5000 });
  });

  test('B3: ocultar modulo (is_visible=false) → desaparece de la seccion', async ({ page, playwright }) => {
    test.skip(!moduleUuid, 'B1 no creo el modulo');
    const apiCtx = await playwright.request.newContext();

    await apiPatch(apiCtx, token, `/dashboard/home-config/modules/${moduleUuid}/`, {
      is_visible: false,
    });
    await apiCtx.dispose();

    await page.goto(UI);
    await page.waitForLoadState('networkidle');

    const hiddenLabel = page.locator('.module-label', { hasText: `${TAG} Modulo ACTUALIZADO` });
    await expect(hiddenLabel).not.toBeVisible({ timeout: 5000 });
  });

});

// ════════════════════════════════════════════════════════════════════════════
//  SUITE C — TARJETAS INFORMATIVAS
// ════════════════════════════════════════════════════════════════════════════
test.describe('C — Tarjetas informativas', () => {

  test('C1: crear tarjeta → aparece en seccion de tarjetas en la home', async ({ page, playwright }) => {
    const apiCtx = await playwright.request.newContext();

    const card = await apiPost(apiCtx, token, '/dashboard/home-cards/create/', {
      title:            `${TAG} Tarjeta UI`,
      subtitle:         'Subtitulo tarjeta Playwright',
      description:      'Descripcion generada por Playwright E2E',
      group_name:       'E2E_UI_GROUP',
      icon_class:       'bi-lightning',
      background_color: '#059669',
      redirect_url:     '/servicios',
      display_order:    99,
      is_active:        true,
    });
    cardUuid = card.uuid;
    await apiCtx.dispose();

    await page.goto(UI);
    await page.waitForLoadState('networkidle');

    // La tarjeta debe aparecer en la seccion de cards — usamos el enlace como scope unico
    const cardLink = page.locator('a.flat-card').filter({ has: page.locator('.fc-title', { hasText: `${TAG} Tarjeta UI` }) });
    await expect(cardLink.first()).toBeVisible({ timeout: 5000 });

    // El subtitulo scoped al mismo card para evitar colisiones con tarjetas de otras ejecuciones
    const cardSub = cardLink.locator('.fc-subtitle', { hasText: 'Subtitulo tarjeta Playwright' });
    await expect(cardSub).toBeVisible();

    // El encabezado del grupo debe aparecer
    const groupHeader = page.locator('.section-label', { hasText: 'E2E_UI_GROUP' });
    await expect(groupHeader).toBeVisible();
  });

  test('C2: actualizar titulo → refleja en UI', async ({ page, playwright }) => {
    test.skip(!cardUuid, 'C1 no creo la tarjeta');
    const apiCtx = await playwright.request.newContext();

    await apiPatch(apiCtx, token, `/dashboard/home-cards/${cardUuid}/`, {
      title: `${TAG} Tarjeta ACTUALIZADA`,
    });
    await apiCtx.dispose();

    await page.goto(UI);
    await page.waitForLoadState('networkidle');

    const updTitle = page.locator('.fc-title', { hasText: `${TAG} Tarjeta ACTUALIZADA` });
    await expect(updTitle).toBeVisible({ timeout: 5000 });
  });

  test('C3: desactivar tarjeta → desaparece de la UI', async ({ page, playwright }) => {
    test.skip(!cardUuid, 'C1 no creo la tarjeta');
    const apiCtx = await playwright.request.newContext();

    await apiPatch(apiCtx, token, `/dashboard/home-cards/${cardUuid}/`, { is_active: false });
    await apiCtx.dispose();

    await page.goto(UI);
    await page.waitForLoadState('networkidle');

    const hiddenTitle = page.locator('.fc-title', { hasText: `${TAG} Tarjeta ACTUALIZADA` });
    await expect(hiddenTitle).not.toBeVisible({ timeout: 5000 });
  });

});

// ════════════════════════════════════════════════════════════════════════════
//  SUITE D — PANEL ADMIN (panel/home-config → refleja en /)
// ════════════════════════════════════════════════════════════════════════════
test.describe('D — Admin panel -> Home publica', () => {

  test('D1: login en panel admin y navegar a home-config', async ({ page }) => {
    // Login via UI
    await page.goto(`${UI}/login`);
    await page.waitForLoadState('networkidle');

    await page.fill('input[type="email"]', EMAIL);
    await page.fill('input[type="password"]', PASS);
    await page.click('button[type="submit"]');

    // Esperar redireccion al panel
    await page.waitForURL(/\/panel/, { timeout: 10000 });
    await expect(page).toHaveURL(/\/panel/);
  });

  test('D2: panel home-config carga los 4 tabs (Modulos, Banners, Tarjetas, Footer)', async ({ page }) => {
    // Login
    await page.goto(`${UI}/login`);
    await page.waitForLoadState('networkidle');
    await page.fill('input[type="email"]', EMAIL);
    await page.fill('input[type="password"]', PASS);
    await page.click('button[type="submit"]');
    await page.waitForURL(/\/panel/, { timeout: 10000 });

    // Navegar a home-config
    await page.goto(`${UI}/panel/home-config`);
    await page.waitForLoadState('networkidle');

    // Los 4 tabs deben estar presentes
    await expect(page.locator('.nav-link', { hasText: 'Modulos' })).toBeVisible();
    await expect(page.locator('.nav-link', { hasText: 'Banners' })).toBeVisible();
    await expect(page.locator('.nav-link', { hasText: 'Tarjetas' })).toBeVisible();
    await expect(page.locator('.nav-link', { hasText: 'Footer' })).toBeVisible();

    // El boton "Nuevo Modulo" debe estar disponible (tab activo por defecto)
    await expect(page.locator('button', { hasText: 'Nuevo Modulo' })).toBeVisible();
  });

  test('D3: crear modulo desde panel → aparece inmediatamente en /', async ({ page, playwright }) => {
    const apiCtx = await playwright.request.newContext();
    // Limpiar modulo si quedó de test anterior
    let cleanupUuid = null;

    try {
      // Login
      await page.goto(`${UI}/login`);
      await page.waitForLoadState('networkidle');
      await page.fill('input[type="email"]', EMAIL);
      await page.fill('input[type="password"]', PASS);
      await page.click('button[type="submit"]');
      await page.waitForURL(/\/panel/, { timeout: 10000 });

      // Ir a home-config
      await page.goto(`${UI}/panel/home-config`);
      await page.waitForLoadState('networkidle');

      // Abrir modal "Nuevo Modulo"
      await page.click('button:has-text("Nuevo Modulo")');
      await expect(page.locator('.modal-backdrop-custom')).toBeVisible({ timeout: 3000 });

      // Llenar formulario del modal
      const panelKey = `panel_e2e_${Date.now()}`;
      await page.fill('input[placeholder*="blog"]', panelKey);
      await page.fill('input[placeholder*="Blog, Eventos"]', `${TAG} Panel Modulo`);
      await page.fill('input[placeholder*="bi-grid"]', 'bi-stars');
      await page.fill('input[placeholder*="/blog"]', '/panel-e2e-test');

      // Guardar
      await page.click('button:has-text("Crear modulo")');
      await page.waitForTimeout(1000);

      // Obtener UUID del modulo recien creado para limpieza
      const allMods = await apiCtx.get(`${API}/dashboard/home-config/modules/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const modsData = await allMods.json();
      const newMod = modsData.find(m => m.module_key === panelKey);
      if (newMod) cleanupUuid = newMod.uuid;

      // Ir a home publica y verificar
      await page.goto(UI);
      await page.waitForLoadState('networkidle');

      const modLabel = page.locator('.module-label', { hasText: `${TAG} Panel Modulo` });
      await expect(modLabel).toBeVisible({ timeout: 5000 });

    } finally {
      // Limpieza
      if (cleanupUuid) {
        try {
          await apiDelete(apiCtx, token, `/dashboard/home-config/modules/${cleanupUuid}/delete/`);
        } catch (_) {}
      }
      await apiCtx.dispose();
    }
  });

});

// ════════════════════════════════════════════════════════════════════════════
//  SUITE E — LIMPIEZA Y ESTADO FINAL
// ════════════════════════════════════════════════════════════════════════════
test.describe('E — Limpieza', () => {

  test('E1: eliminar banner → no aparece en UI', async ({ page, playwright }) => {
    test.skip(!bannerUuid, 'Sin banner que limpiar');
    const apiCtx = await playwright.request.newContext();

    await apiDelete(apiCtx, token, `/dashboard/home-config/banners/${bannerUuid}/delete/`);
    await apiCtx.dispose();

    await page.goto(UI);
    await page.waitForLoadState('networkidle');

    const deletedTitle = page.locator('#homeBannerCarousel .banner-title').filter({ hasText: `${TAG} Banner Playwright` });
    await expect(deletedTitle).not.toBeAttached({ timeout: 5000 });
  });

  test('E2: eliminar modulo → no aparece en UI', async ({ page, playwright }) => {
    test.skip(!moduleUuid, 'Sin modulo que limpiar');
    const apiCtx = await playwright.request.newContext();

    await apiDelete(apiCtx, token, `/dashboard/home-config/modules/${moduleUuid}/delete/`);
    await apiCtx.dispose();

    await page.goto(UI);
    await page.waitForLoadState('networkidle');

    // Ni el label original ni el actualizado deben aparecer
    const deletedLabel = page.locator('.module-label').filter({ hasText: TAG });
    await expect(deletedLabel).not.toBeVisible({ timeout: 5000 });
  });

  test('E3: eliminar tarjeta → no aparece en UI', async ({ page, playwright }) => {
    test.skip(!cardUuid, 'Sin tarjeta que limpiar');
    const apiCtx = await playwright.request.newContext();

    await apiDelete(apiCtx, token, `/dashboard/home-cards/${cardUuid}/delete/`);
    await apiCtx.dispose();

    await page.goto(UI);
    await page.waitForLoadState('networkidle');

    const deletedCard = page.locator('.fc-title').filter({ hasText: TAG });
    await expect(deletedCard).not.toBeVisible({ timeout: 5000 });
  });

  test('E4: home publica carga sin errores JS en consola', async ({ page }) => {
    const jsErrors = [];
    page.on('pageerror', err => jsErrors.push(err.message));

    await page.goto(UI);
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(1500);

    // Puede haber warnings de Vue pero no errores de runtime
    const criticalErrors = jsErrors.filter(e =>
      !e.includes('Warning') && !e.includes('[Vue warn]')
    );
    expect(criticalErrors, `Errores JS en consola: ${criticalErrors.join(', ')}`).toHaveLength(0);
  });

});
