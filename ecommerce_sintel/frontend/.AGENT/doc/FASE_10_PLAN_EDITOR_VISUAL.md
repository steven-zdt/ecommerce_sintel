# Fase 10: Editor Visual (Home Builder) — Plan de Implementación

**Estado:** ✓ COMPLETADO (2026-07-29)  
**Complejidad:** Media (modificación de un formulario modal existente, sin backend)  
**Riesgo:** Bajo (cambios son aditivos a `layout_config`, estructura ya existe)

---

## Objetivo

Extender `ModuleBuilderModal.vue` para que los administradores puedan configurar desde el Home Builder:
1. **Media por card** (video, blur, glass)
2. **Carousel (scroll horizontal)** — items, autoplay, loop, speed, pauses, arrows, dots
3. **Header de sección** — título, subtítulo, descripción, CTA
4. **Fondo de sección** — tipo, imagen, video, parallax

Todos estos datos ya se guardan en `layout_config` (JSONField) — esta fase es **UI pura**, sin cambios backend.

---

## Plan de Ejecución

### Paso 1: Analizar estructura actual de ModuleBuilderModal.vue

**Archivo:** `src/modules/core/ModuleBuilderModal.vue`  
**Líneas clave a verificar:**
- Línea ~595: Array `TABS` — definición de pestañas actuales (General, Presentación, Estilo, Icon, Imagen, Distribución, Animaciones, Contenido, Botones, Fondo, Responsive)
- Línea ~700: Función `DEFAULT_FORM()` — valores por defecto de `form` (el modelo reactivo)
- Línea ~780: Función `loadModule(mod)` — población de form desde un módulo existente
- Línea ~868: `configPayload` computed — lo que se envía al backend

**Decisión:** Dado que ya hay 11 tabs (muchos), agrupar los **4 nuevos campos en 2 tabs nuevas:**
- Tab 12: "Carrusel" (`carousel`) — items_desktop/tablet/mobile, autoplay, loop, speed, pauses, arrows, dots
- Tab 13: "Multimedia" (`media`, `header`, `section_background`) — agrupar los 3 para evitar explosión de tabs

O alternativamente, si prefieres máxima separación:
- Tab 12: "Carrusel"
- Tab 13: "Fondo Multimedia" (video/imagen por card)
- Tab 14: "Encabezado"
- Tab 15: "Fondo de Sección"

**Recomendación:** Opción 1 (2 tabs nuevas) para mantener el modal manejable. Los administradores pueden encontrar todo relativo a "scroll horizontal" en Carrusel, y todo "multimedia" en Multimedia.

### Paso 2: Agregar Tab 12 — "Carrusel"

**Ubicación en template:** Después de tab `responsive` (línea ~501), agregar:

```html
<!-- Tab 12: CAROUSEL -->
<button class="mb-tab" @click="activeTab = 'carousel'">
  <i class="bi bi-arrows-move"></i>
  <span>Carrusel</span>
</button>
```

**Ubicación en TABS array (línea ~595):**

```javascript
{ id: 'carousel', icon: 'bi-arrows-move', label: 'Carrusel' },
```

**Ubicación en template body (después de responsive section, línea ~501):**

```html
<!-- S12: CAROUSEL -->
<div v-show="activeTab === 'carousel'" class="mb-section">
  <div class="mb-section-title"><i class="bi bi-arrows-move me-2"></i>Configuración del Carrusel</div>
  <p class="mb-section-sub">Scroll horizontal, autoplay, velocidad y controles.</p>

  <div class="mb-subsection">Número de items visibles</div>
  <div class="mb-responsive-grid">
    <div v-for="dev in DEVICES" :key="dev.key" class="mb-responsive-device">
      <div class="mb-responsive-device__label"><i :class="['bi', dev.icon]"></i> {{ dev.label }}</div>
      <div class="mb-cols-picker mb-cols-picker--sm">
        <button v-for="n in [1,2,3,4,5,6]" :key="n"
          :class="['mb-col-btn mb-col-btn--sm', carouselCfg[carouselKey(dev.key)] === n && 'active']"
          @click="carouselCfg[carouselKey(dev.key)] = n">
          {{ n }}
        </button>
      </div>
    </div>
  </div>

  <div class="mb-grid mt-3">
    <div class="mb-field">
      <label class="mb-label">Velocidad autoplay (px/s)</label>
      <input v-model.number="carouselCfg.speed" type="number" class="mb-input" min="10" max="200" step="10">
    </div>
    <div class="mb-field">
      <label class="mb-label">Velocidad (en segundos)</label>
      <div class="form-check form-switch">
        <input v-model="carouselCfg.autoplay" class="form-check-input" type="checkbox" id="mb-autoplay">
        <label class="form-check-label" for="mb-autoplay">Autoplay activado</label>
      </div>
    </div>
    <div class="mb-field">
      <div class="form-check form-switch">
        <input v-model="carouselCfg.loop" class="form-check-input" type="checkbox" id="mb-loop">
        <label class="form-check-label" for="mb-loop">Loop infinito</label>
      </div>
    </div>
    <div class="mb-field">
      <div class="form-check form-switch">
        <input v-model="carouselCfg.pause_on_hover" class="form-check-input" type="checkbox" id="mb-pause-hover">
        <label class="form-check-label" for="mb-pause-hover">Pausar en hover</label>
      </div>
    </div>
    <div class="mb-field">
      <div class="form-check form-switch">
        <input v-model="carouselCfg.pause_on_touch" class="form-check-input" type="checkbox" id="mb-pause-touch">
        <label class="form-check-label" for="mb-pause-touch">Pausar en touch</label>
      </div>
    </div>
    <div class="mb-field">
      <div class="form-check form-switch">
        <input v-model="carouselCfg.pause_on_focus" class="form-check-input" type="checkbox" id="mb-pause-focus">
        <label class="form-check-label" for="mb-pause-focus">Pausar en foco</label>
      </div>
    </div>
    <div class="mb-field">
      <div class="form-check form-switch">
        <input v-model="carouselCfg.show_arrows" class="form-check-input" type="checkbox" id="mb-arrows">
        <label class="form-check-label" for="mb-arrows">Mostrar flechas</label>
      </div>
    </div>
    <div class="mb-field">
      <div class="form-check form-switch">
        <input v-model="carouselCfg.show_indicators" class="form-check-input" type="checkbox" id="mb-indicators">
        <label class="form-check-label" for="mb-indicators">Mostrar indicadores (dots)</label>
      </div>
    </div>
  </div>
</div>
```

**En `<script setup>`:**

```javascript
const carouselCfg = reactive({
  items_desktop:   6,
  items_tablet:    3,
  items_mobile:    1.2,
  autoplay:        false,
  loop:            true,
  speed:           40,
  pause_on_hover:  true,
  pause_on_touch:  true,
  pause_on_focus:  true,
  show_arrows:     true,
  show_indicators: true,
});
function carouselKey(deviceKey) {
  return { 'columns': 'items_desktop', 'columns_tablet': 'items_tablet', 'columns_mobile': 'items_mobile' }[deviceKey];
}
```

**En `DEFAULT_FORM()`:**

```javascript
carousel: {
  items_desktop:   6,
  items_tablet:    3,
  items_mobile:    1.2,
  autoplay:        false,
  loop:            true,
  speed:           40,
  pause_on_hover:  true,
  pause_on_touch:  true,
  pause_on_focus:  true,
  show_arrows:     true,
  show_indicators: true,
}
```

**En `loadModule(mod)`:**

```javascript
const carouselCfg = lc.carousel || {};
Object.assign(form, DEFAULT_FORM(), {
  // ... existing fields ...
  carousel: {
    items_desktop:   carouselCfg.items_desktop ?? 6,
    items_tablet:    carouselCfg.items_tablet ?? 3,
    items_mobile:    carouselCfg.items_mobile ?? 1.2,
    autoplay:        carouselCfg.autoplay ?? false,
    loop:            carouselCfg.loop ?? true,
    speed:           carouselCfg.speed ?? 40,
    pause_on_hover:  carouselCfg.pause_on_hover !== false,
    pause_on_touch:  carouselCfg.pause_on_touch !== false,
    pause_on_focus:  carouselCfg.pause_on_focus !== false,
    show_arrows:     carouselCfg.show_arrows !== false,
    show_indicators: carouselCfg.show_indicators !== false,
  }
});
```

**En `configPayload` computed:**

```javascript
carousel: {
  items_desktop:   form.carousel.items_desktop,
  items_tablet:    form.carousel.items_tablet,
  items_mobile:    form.carousel.items_mobile,
  autoplay:        form.carousel.autoplay,
  loop:            form.carousel.loop,
  speed:           form.carousel.speed,
  pause_on_hover:  form.carousel.pause_on_hover,
  pause_on_touch:  form.carousel.pause_on_touch,
  pause_on_focus:  form.carousel.pause_on_focus,
  show_arrows:     form.carousel.show_arrows,
  show_indicators: form.carousel.show_indicators,
}
```

### Paso 3: Agregar Tab 13 — "Multimedia"

Similar a Paso 2, agregar una pestaña que abarque:

**Sección 1: Media por Card (Fase 3/10)**
```html
<div class="mb-subsection">Fondo de Card</div>
<div class="mb-grid">
  <div class="mb-field">
    <label class="mb-label">Tipo de fondo</label>
    <select v-model="mediaCfg.type" class="mb-select">
      <option value="color">Color sólido</option>
      <option value="image">Imagen</option>
      <option value="video">Video</option>
      <option value="none">Ninguno</option>
    </select>
  </div>
  <div v-if="mediaCfg.type === 'video'" class="mb-field mb-field--full">
    <label class="mb-label">URL del video (MP4)</label>
    <input v-model="mediaCfg.video_url" class="mb-input" placeholder="https://...">
  </div>
  <div v-if="mediaCfg.type === 'video'" class="mb-field mb-field--full">
    <label class="mb-label">URL del video (WebM)</label>
    <input v-model="mediaCfg.video_url_webm" class="mb-input" placeholder="https://... (opcional)">
  </div>
  <div v-if="mediaCfg.type === 'video'" class="mb-field mb-field--full">
    <label class="mb-label">Poster (imagen de preview)</label>
    <input v-model="mediaCfg.poster" class="mb-input" placeholder="https://...">
  </div>
  <div class="mb-field">
    <label class="mb-label">Blur (px)</label>
    <input v-model.number="mediaCfg.blur" type="number" class="mb-input" min="0" max="20" step="1">
  </div>
  <div class="mb-field mb-field--full">
    <div class="form-check form-switch">
      <input v-model="mediaCfg.glass" class="form-check-input" type="checkbox" id="mb-media-glass">
      <label class="form-check-label" for="mb-media-glass">Glassmorphism</label>
    </div>
  </div>
</div>
```

**Sección 2: Header de Sección**
```html
<div class="mb-subsection mt-3">Encabezado de Sección</div>
<div class="mb-grid">
  <div class="mb-field mb-field--full">
    <label class="mb-label">Título</label>
    <input v-model="headerCfg.title" class="mb-input" placeholder="El ecosistema Sintel">
  </div>
  <div class="mb-field mb-field--full">
    <label class="mb-label">Subtítulo</label>
    <input v-model="headerCfg.subtitle" class="mb-input" placeholder="Marketplace">
  </div>
  <div class="mb-field mb-field--full">
    <label class="mb-label">Descripción</label>
    <textarea v-model="headerCfg.description" class="mb-input" rows="2" placeholder="Detalle sobre esta sección..."></textarea>
  </div>
  <div class="mb-field">
    <label class="mb-label">CTA - Texto</label>
    <input v-model="headerCfg.cta_text" class="mb-input" placeholder="Explorar todo">
  </div>
  <div class="mb-field">
    <label class="mb-label">CTA - URL</label>
    <input v-model="headerCfg.cta_url" class="mb-input" placeholder="/tienda">
  </div>
  <div class="mb-field">
    <label class="mb-label">CTA - Target</label>
    <select v-model="headerCfg.cta_target" class="mb-select">
      <option value="_self">Misma pestaña</option>
      <option value="_blank">Nueva pestaña</option>
    </select>
  </div>
</div>
```

**Sección 3: Fondo de Sección**
```html
<div class="mb-subsection mt-3">Fondo de Sección Completa</div>
<div class="mb-grid">
  <div class="mb-field">
    <label class="mb-label">Tipo</label>
    <select v-model="sectionBgCfg.type" class="mb-select">
      <option value="none">Ninguno</option>
      <option value="image">Imagen</option>
      <option value="video">Video</option>
      <option value="color">Color sólido</option>
    </select>
  </div>
  <div v-if="sectionBgCfg.type === 'image' || sectionBgCfg.type === 'video'" class="mb-field mb-field--full">
    <label class="mb-label">URL de media</label>
    <input v-model="sectionBgCfg.video_url" class="mb-input" placeholder="https://...">
  </div>
  <div v-if="sectionBgCfg.type === 'video'" class="mb-field mb-field--full">
    <label class="mb-label">Poster</label>
    <input v-model="sectionBgCfg.poster" class="mb-input" placeholder="https://...">
  </div>
  <div class="mb-field mb-field--full">
    <div class="form-check form-switch">
      <input v-model="sectionBgCfg.parallax" class="form-check-input" type="checkbox" id="mb-section-parallax">
      <label class="form-check-label" for="mb-section-parallax">Efecto Parallax</label>
    </div>
  </div>
</div>
```

### Paso 4: Integración en `configPayload`

Agregar las 3 nuevas ramas (media, header, section_background) al objeto que se guarda.

### Paso 5: Pruebas en Home Builder

1. Abrir un módulo existente en `HomeConfigView.vue`
2. Verificar que las pestañas nuevas aparecen
3. Configurar valores de prueba
4. Guardar
5. Verificar en el inspector que `layout_config` contiene las nuevas claves

### Paso 6: Documentación

Actualizar `MARKETPLACE_SHOWCASE_IMPLEMENTATION.md` con:
- Screenshots del Home Builder con las nuevas tabs
- Ejemplo de `layout_config` guardado con todos los campos nuevos

---

## Archivos a Modificar

| Archivo | Cambios | LOC |
|---------|---------|-----|
| `src/modules/core/ModuleBuilderModal.vue` | Agregar tabs, campos, lógica | ~250 |

**Total de cambios:** ~250 líneas (aditivas, sin borrar nada existente).

---

## Notas Importantes

1. **Sin cambios backend:** El backend `HomeModuleConfig` ya soporta `layout_config` JSONField arbitrario — no requiere migración.
2. **Retrocompatibilidad:** Los campos nuevos son todos opcionales — módulos sin ellos caen a defaults en los componentes.
3. **Vista previa:** `ModuleBuilderModal.vue` ya tiene un `mb-preview` incorporado (`lines ~506-556`) — se actualizará automáticamente cuando cambies los valores en el form.
4. **Validación:** No se requiere validación server-side especial — el backend acepta cualquier JSON válido.

---

## Orden de Ejecución

```
1. Agregar TABS array → agregar 'carousel' y 'multimedia'
2. Agregar DEFAULT_FORM() → agregar carousel/media/header/section_background ramas
3. Agregar loadModule(mod) → parsear las nuevas claves desde un módulo existente
4. Agregar template sections → las 2 tabs nuevas en el markup
5. Agregar configPayload computed → incluir las nuevas ramas
6. Test en Home Builder
7. Documentar
```

---

## Próximas Fases Después de Fase 10

### Fase 11: Optimización CPU/GPU ✓ (verificar código, sin cambios)
### Fase 12: Accesibilidad Completa (código ya hecho, audit final)
### Fase 13: SEO (código ya hecho, lighthouse check)
### Fase 14: API Contract ✓ (sin cambios, confirmado)
### Fase 15: Testing (unit tests)
### Fase 16: Producción (deploy)

