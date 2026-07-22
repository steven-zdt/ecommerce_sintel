---
description: Convenciones de loading, empty y error state — spinners, skeletons y disabled states.
metadata:
  domain: ux
  supersedes: FRONTEND_UI_RULES.md (secciones dispersas 5.3/5.9), consolidado nuevo
---

# Loading, Empty & Error states

## 1. Loading en tabla

```html
<tr v-if="loading">
  <td colspan="N" class="text-center py-5">
    <div class="spinner-border text-primary" role="status"></div>
    <div class="mt-2 text-muted small">Cargando...</div>
  </td>
</tr>
```

## 2. Empty state en tabla

```html
<tr v-else-if="items.length === 0">
  <td colspan="N" class="text-center py-5 text-muted">No se encontraron registros.</td>
</tr>
```

## 3. Loading en boton de submit

```html
<button type="submit" class="btn btn-primary w-100" :disabled="loading">
  <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
  {{ mode === 'create' ? 'Crear' : 'Guardar Cambios' }}
</button>
```

## 4. Loading de accion puntual (delete/aprobar/etc.)

Patron `actionLoading` separado del `loading` general de la lista, para no bloquear toda la
tabla mientras una sola fila procesa una accion:

```html
<button class="btn btn-sm btn-danger" @click="executeDelete(item)" :disabled="actionLoading">
  <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>
  Confirmar
</button>
```

## 5. Skeleton (solo landing publica)

`LoadingSkeleton` (`@/components/ui/landing/LoadingSkeleton.vue`) — shimmer configurable con
props `width`, `height`, `radius`, `dark`, `count`, `gap`, `inline`. Es el unico skeleton real del
proyecto; no existe un skeleton generico para el panel admin (usa `spinner-border` en su lugar).
Ver [../components/cards.md](../components/cards.md#31-primitivos-reutilizables-en-cualquier-contexto).

## 6. Error state

Para errores de llamada async puntuales, el patron sigue siendo reactivo via `toast.error(...)`
en el `catch` (ver
[../ux/enterprise_ux.md](enterprise_ux.md#2-contrato-de-errores--obligatorio-en-toda-llamada-async)).

Para errores de render que rompen un componente completo (excepciones no capturadas en
`<script setup>`/template), `@/components/ui/ErrorBoundary.vue` (2026-07-11) envuelve
`<RouterView>` en `AppShell.vue` y `CustomerLayout.vue` via `onErrorCaptured()` — muestra un
fallback con "Reintentar"/"Ir al inicio" en vez de dejar la SPA en blanco. `<Suspense>` envuelve
el mismo `<RouterView>` para mostrar un `spinner-border` mientras se descarga el chunk de la ruta
(lazy loading), en vez de un flash en blanco.

No hay manejo generico de 404/500 de API a nivel de router (ej. una vista de detalle con uuid
invalido) — verificar el componente puntual, no asumir que existe.

## 7. Offline / retry

Implementado en `useApi.js` (2026-07-11), en el mismo interceptor de response que maneja el
refresh de JWT en 401:

- Errores de red (`!error.response`, es decir la request nunca llego al servidor) en peticiones
  **GET** se reintentan automaticamente hasta 2 veces con backoff corto (500ms, 1500ms) antes de
  fallar — cubre blips de conexion transitorios.
- **POST/PATCH/DELETE nunca se reintentan automaticamente** — reintentar una escritura de red
  cuyo resultado se desconoce es inseguro (riesgo de duplicar side-effects, especialmente en
  pagos — ver `payment/CLAUDE.md`). El usuario debe reintentar manualmente via la UI.
- El error rechazado se anota con `error.isNetworkError = true` y
  `error.isOffline = !navigator.onLine` — **sin** alterar el mensaje ni el flujo. El
  `catch { toast.error(...) }` de cada caller sigue funcionando exactamente igual; usar estas
  flags solo si un componente puntual quiere un mensaje mas especifico
  (`e.isOffline ? 'Sin conexion a internet' : 'Error de red'`).
- No se agrego un toast generico en el interceptor a proposito — hacerlo duplicaria el toast que
  cada caller ya muestra en su propio catch (ver
  [enterprise_ux.md](enterprise_ux.md#2-contrato-de-errores--obligatorio-en-toda-llamada-async)).
