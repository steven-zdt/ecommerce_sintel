---
description: Regresion visual implementada 2026-07-11 — un caso real (pantalla de login) via Playwright toHaveScreenshot(), no una suite exhaustiva.
metadata:
  domain: testing
  status: instalado-un-caso
---

# Visual regression — estado real

**Implementado 2026-07-11, con un caso real**, sobre la misma instalacion de Playwright que
[playwright.md](playwright.md). No hay Percy/Chromatic ni servicio externo — usa el mecanismo
nativo de Playwright (`toHaveScreenshot()`, comparacion pixel a pixel contra un baseline PNG
versionado en el repo).

## Caso implementado — `e2e/visual-regression.spec.js`

```js
import { test, expect } from '@playwright/test';

test('pantalla de login no cambia visualmente', async ({ page }) => {
  await page.goto('/login');
  await page.waitForLoadState('networkidle');
  await expect(page).toHaveScreenshot('login.png', { maxDiffPixelRatio: 0.02 });
});
```

**Por que `/login` y no otra pantalla:** es la unica ruta publica sin dependencia de datos reales
de API (no llama `core/home-feed/`, no requiere sesion) — la mas estable posible para un primer
caso. Las rutas admin (`/panel/*`) necesitan login primero (ver gap de auth en
[playwright.md](playwright.md)); las rutas customer publicas (Home/Landing) dependen de datos
variables del backend (banners, ofertas flash) que harian el snapshot inestable entre corridas.

## Comandos

```bash
# Generar/actualizar el baseline (commitear el PNG resultante)
docker exec ecommerce_sintel_frontend npx playwright test visual-regression --update-snapshots

# Verificar contra el baseline (falla si hay diferencia > 2% de pixeles)
docker exec ecommerce_sintel_frontend npx playwright test visual-regression
```

Baseline commiteado en `e2e/visual-regression.spec.js-snapshots/login-chromium-linux.png` — el
sufijo `-chromium-linux` es especifico de browser+OS; si CI corre en otro OS, generar el baseline
ahi tambien (Playwright nombra el archivo automaticamente por plataforma).

## Limitaciones honestas

- **Un solo caso**, no una suite. Extender a otras pantallas publicas es sencillo (mismo patron),
  pero pantallas admin requieren primero resolver el gap de autenticacion en Playwright (ver
  [playwright.md](playwright.md#hallazgo-importante-la-suite-pre-existente-nunca-se-habia-corrido)).
- Snapshots son sensibles a fuente/renderizado del SO — el baseline se genero en el contenedor
  Linux (`ecommerce_sintel_frontend`), no en Windows host. Correrlo fuera de ese contenedor
  probablemente falle por diferencias de renderizado, no por regresiones reales.
- `.gitignore` excluye `test-results/`/`playwright-report/` (artefactos de corrida) pero **no**
  la carpeta `*-snapshots/` (son los baselines, deben commitearse).

## Ver tambien

- [playwright.md](playwright.md) — instalacion base, config compartida (`playwright.config.js`)
