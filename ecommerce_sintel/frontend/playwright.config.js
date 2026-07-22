import { defineConfig, devices } from '@playwright/test';

/**
 * Config para correr specs de Playwright contra el dev server ya corriendo en
 * este contenedor (npm run dev, puerto 5173). No levanta un webServer propio
 * -- el contenedor ecommerce_sintel_frontend ya sirve Vite en 0.0.0.0:5173
 * via docker compose.
 *
 * Dos ubicaciones de specs:
 *   e2e/                 -- specs nuevos (regresion visual, flujos publicos)
 *   .AGENT/load-tests/    -- Fase 8 (2026-07-01), offline-testing.spec.ts
 */
export default defineConfig({
  testDir: '.',
  testMatch: ['e2e/**/*.spec.js', '.AGENT/load-tests/**/*.spec.ts'],
  timeout: 30000,
  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
  },
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
