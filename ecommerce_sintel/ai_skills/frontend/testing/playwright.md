---
description: Playwright instalado y formalizado 2026-07-11. Suite pre-existente (.AGENT/load-tests/offline-testing.spec.ts, Fase 8 2026-07-01) corre pero tiene bugs reales nunca antes detectados porque nunca se habia ejecutado.
metadata:
  domain: testing
  status: instalado-suite-preexistente-con-bugs-reales
---

# Playwright — estado real

**Instalado 2026-07-11** (`@playwright/test` + Chromium con deps, `frontend/playwright.config.js`).
Corre contra el dev server real (`ecommerce_sintel_frontend`, puerto 5173) dentro del mismo
contenedor — no hace falta levantar un `webServer` propio en la config.

```bash
docker exec ecommerce_sintel_frontend npx playwright test              # todos los specs
docker exec ecommerce_sintel_frontend npx playwright test -g "Scenario 1"  # uno especifico
docker exec ecommerce_sintel_frontend npx playwright show-report       # reporte HTML
```

## Hallazgo importante: la suite pre-existente nunca se habia corrido

`.AGENT/load-tests/offline-testing.spec.ts` (10 escenarios, ver
`.AGENT/doc/PHASE8_OFFLINE_TESTING.md`, 2026-07-01) prueba el fallback de 4 capas de `useEnums.ts`
(memoria → localStorage → API → catalogo hardcodeado). Se escribio pero **`@playwright/test`
nunca se instalo** hasta ahora — la doc de esa fase la marcaba "✅ Production Readiness" sin
haberse ejecutado nunca.

Al correrla por primera vez (2026-07-11): **1 de 10 escenarios pasa.** Los 9 que fallan tienen
bugs reales en el spec, no en la app:

- **Causa principal:** navega a `/panel/marketing` y `/panel/orders` (rutas admin) sin hacer
  login primero — la app redirige a `/login`, asi que los textos de enum que el test busca
  (`text=Creado`, `text=Pagado`) nunca aparecen. El spec nunca contemplo autenticacion.
- **Causa secundaria:** varios escenarios llaman `page.evaluate(() => localStorage...)` **antes**
  de `page.goto(...)` — en `about:blank` el acceso a `localStorage` lanza `SecurityError` en
  Chromium. Orden de operaciones incorrecto en el spec original.

**No se arreglaron los 9 escenarios** — es un esfuerzo de debugging separado (necesita un fixture
de login reutilizable + revisar cada escenario) fuera del alcance de "formalizar Playwright". Ver
[../editor/architecture_audit.md](../editor/architecture_audit.md) si se decide retomarlo.

## Uso previo documentado (verificacion manual puntual)

Durante [[project_renting_availability_engine_phase2]], Playwright se uso de forma ad-hoc en el
scratchpad de la sesion (no en el repo) para navegar el wizard de renta y encontrar un bug real de
`emit` en Vue. Ese patron sigue siendo valido para verificacion puntual via `/verify` o `/run`,
independiente de la suite formal.

## Ver tambien

- [visual_regression.md](visual_regression.md)
- `frontend/.AGENT/doc/PHASE8_OFFLINE_TESTING.md` — contexto original del spec
- Skill `/verify` del harness — para verificacion puntual sin depender de la suite instalada
