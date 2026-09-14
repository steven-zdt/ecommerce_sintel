# HOME_MODULE_URLS.md — Auditoría de URLs

**Fecha:** 2026-08-06. Fase 3 del brief de auditoría "Home Config → Módulos". Solo lectura, cero
cambios de código.

## Resolución real de URLs (`MarketplaceCard.vue:2-8`)

```html
<RouterLink :to="isExternal ? '/' : (module.url || '/')" custom v-slot="{ navigate, href }">
  <a :href="isExternal ? module.url : href"
     :target="isExternal ? '_blank' : undefined"
     ...>
```

```js
isExternal = /^https?:\/\//.test(module.url || '')
```

Mismo patrón replicado en `MarketplaceHeader.vue:7-9` para el CTA de cabecera de sección.

## Hallazgos

1. **No hay `#`, `javascript:void(0)` ni links rotos por diseño.** El fallback cuando `module.url`
   está vacío es `'/'` (home), no un placeholder roto. Esto es correcto como comportamiento
   defensivo, pero **silencioso**: si el admin deja la URL vacía, la tarjeta apunta a la home sin
   ninguna advertencia visible en el panel de que "esta tarjeta no lleva a ningún lado
   específico".

2. **No existe un campo `url_type` (interno/externo/ancla) en el modelo ni en el formulario.**
   La distinción interno/externo se **infiere** por regex sobre el propio valor de la URL
   (`/^https?:\/\//`). Esto significa:
   - Una URL interna correcta debe escribirse como ruta relativa (`/tienda`, `/servicios/...`)
     para que `isExternal` sea `false` y use `RouterLink` (navegación SPA sin recarga).
   - Si el admin escribe una URL absoluta de este mismo dominio (`https://sintel.net.co/tienda`),
     el sistema la trata como **externa**: abre en `_blank` con recarga completa de página, en vez
     de navegación SPA — funcionalmente correcto pero subóptimo (pierde el estado de la SPA,
     fuerza un full reload).
   - No hay soporte para anclas (`#seccion`) como tipo de URL explícito — un valor `#algo`
     tampoco matchea el regex `https?://`, así que se trataría como "interna" y `RouterLink`
     probablemente no resolvería la navegación a un ancla dentro de la misma vista correctamente
     (no verificado en runtime, es una inferencia de código, ver Fase 10 para confirmación visual).

3. **No hay validación de formato de URL en el admin.** `GeneralTab.vue:24` (`custom_url`) es un
   input de texto libre sin `type="url"` ni validación de patrón — el admin puede guardar
   cualquier string. El backend (`HomeModuleConfigInputSerializer`, `custom_url` línea 325-339 de
   `core/api/serializers.py`) tampoco lo valida como URL, solo como texto. Un typo (`htps://...`,
   espacios, etc.) se guarda sin error y produce un link roto silencioso en producción.

4. **Target inconsistente entre campos del mismo formulario.** El CTA de cabecera
   (`MultimediaTab.vue:63-66`, campo `header.cta_target`) y los botones (`ButtonsTab.vue:41-44`,
   campo `btn_target`) sí tienen selector explícito `_self`/`_blank`. La URL principal del módulo
   (`custom_url`) **no tiene ese selector** — su target se infiere automáticamente por el regex,
   sin que el admin pueda forzar `_blank` en una URL interna o `_self` en una externa aunque lo
   necesite (p. ej. un enlace externo de confianza que se quiera abrir en la misma pestaña).

## Recomendación (no ejecutada en esta fase — requiere aprobación, ver HOME_MODULE_REFACTOR.md)

Agregar un campo explícito `url_type` (`INTERNA`/`EXTERNA`/`ANCLA`) al modelo `HomeModuleConfig`
y al formulario (select junto al input de URL), con:
- Validación de formato según el tipo elegido (ruta que empiece con `/` para interna, URL absoluta
  válida con esquema `http(s)://` para externa, `#slug` para ancla).
- El target ya no se infiere por regex — se deriva del `url_type` explícito (interna=SPA sin
  target, externa=selector `_self`/`_blank` visible en el form, ancla=scroll sin nueva pestaña).
- Esto es un cambio de **modelo + migración + serializer + formulario admin + lógica de
  `MarketplaceCard.vue`** — no es solo frontend. Se detalla como ítem propio del roadmap de
  remediación, con impacto y riesgo evaluados antes de tocar código de producción.
