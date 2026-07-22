---
description: Vitest instalado y funcionando desde 2026-07-11. Primer test real en useToast.
metadata:
  domain: testing
  status: instalado
---

# Vitest — estado real

**Instalado 2026-07-11.** `vitest` + `@vue/test-utils` + `jsdom` en `devDependencies`. Config en
`vite.config.js` (bloque `test`, `environment: 'jsdom'`, `globals: true` — no hace falta
`import { describe, it, expect } from 'vitest'` en cada archivo, aunque tambien funciona
importarlos explicitamente).

```bash
npm test          # vitest run — una pasada, exit code para CI
npm run test:watch  # vitest — modo watch
```

`exclude: ['**/.AGENT/**']` en el bloque `test` — necesario porque
`.AGENT/load-tests/offline-testing.spec.ts` es un spec de **Playwright**
(`import { test } from '@playwright/test'`), no de Vitest; sin la exclusion, Vitest lo recoge por
el glob por defecto `**/*.spec.ts` y falla al no poder resolver `@playwright/test` como test
runner de Vitest. Ver [playwright.md](playwright.md).

## Convencion de archivos de test

`{archivo}.test.js` junto al archivo que testea (no una carpeta `__tests__/` separada) — mismo
principio de colocacion que el resto del proyecto (`Form.vue` junto a `List.vue`, no en carpetas
por tipo).

## Primer test real — `composables/useToast.test.js`

Elegido como primer ejemplo por ser un composable puro (sin llamadas a `useApi()`/axios, sin
montar un componente Vue) — prueba directa de `add`/`remove`/auto-dismiss con `vi.useFakeTimers()`
para el `setTimeout` de 4000ms. 5 tests, corren en ~10ms.

```js
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { useToast } from './useToast';

describe('useToast', () => {
  beforeEach(() => {
    const { toasts } = useToast();
    toasts.value = []; // el ref es a nivel de modulo, persiste entre tests
  });

  it('agrega un toast de exito con el tipo correcto', () => {
    const { toasts, success } = useToast();
    success('Producto creado');
    expect(toasts.value[0]).toMatchObject({ message: 'Producto creado', type: 'success' });
  });
  // ... ver archivo completo para los 5 tests
});
```

## Mock de `useApi()` — pendiente de un caso real

`useApi()` es un singleton Axios real (no mockeado). Para testear un composable/componente que lo
usa, mockear el modulo completo:

```js
vi.mock('@/composables/useApi', () => ({
  default: () => ({
    get: vi.fn().mockResolvedValue({ data: { results: [], count: 0 } }),
    post: vi.fn().mockResolvedValue({ data: {} }),
  }),
}));
```

No hay todavia un test real que use este patron (el primer test elegido, `useToast`, no llama a
la API) — documentado como receta para el siguiente test que lo necesite, no verificado en un
caso real.

## Ver tambien

- [playwright.md](playwright.md) — e2e, tambien instalado 2026-07-11
- [../editor/architecture_audit.md](../editor/architecture_audit.md)
