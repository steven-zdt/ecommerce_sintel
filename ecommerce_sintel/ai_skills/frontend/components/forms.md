---
description: Patrones de formulario — labels, inputs de precio, contadores SEO, tabs, botones y manejo de errores DRF a toast.
metadata:
  domain: components
  supersedes: FRONTEND_UI_RULES.md (seccion 5.8-5.13), FRONTEND_OFFCANVAS_SKILL.md (seccion 7, 8)
---

# Forms

## Label de formulario

```html
<!-- Campo requerido -->
<label class="form-label small fw-bold">Nombre <span class="text-danger">*</span></label>
<input v-model="form.name" type="text" class="form-control" required>

<!-- Campo con texto de ayuda -->
<div class="form-text">Texto explicativo.</div>

<!-- Switch activo/inactivo -->
<div class="mb-3 form-check form-switch">
  <input v-model="form.is_active" class="form-check-input" type="checkbox" id="switchId">
  <label class="form-check-label small" for="switchId">Campo Activo</label>
</div>
```

## Botones de formulario (dentro del offcanvas)

```html
<div class="d-flex gap-2 mt-4">
  <button type="submit" class="btn btn-primary w-100" :disabled="loading">
    <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
    {{ mode === 'create' ? 'Crear' : 'Guardar Cambios' }}
  </button>
  <button type="button" class="btn btn-light border" @click="$emit('cancel')" :disabled="loading">Cancelar</button>
</div>
```

## Tabs dentro del offcanvas

```html
<ul class="nav nav-tabs nav-fill mb-3" style="font-size:.85rem">
  <li class="nav-item">
    <button type="button" class="nav-link" :class="{ active: tab === 'general' }" @click="tab = 'general'">
      <i class="bi bi-folder me-1"></i>General
    </button>
  </li>
  <li class="nav-item">
    <button type="button" class="nav-link" :class="{ active: tab === 'seo' }" @click="tab = 'seo'">
      <i class="bi bi-search me-1"></i>SEO
    </button>
  </li>
</ul>
<div v-show="tab === 'general'"> ... </div>
<div v-show="tab === 'seo'"> ... </div>
```

Reset al abrir: `watch(() => props.item, () => { tab.value = 'general'; }, { immediate: true });`

## Input de precio

```html
<div class="input-group">
  <span class="input-group-text">$</span>
  <input v-model="form.price" type="number" step="0.01" min="0.01" class="form-control" required>
</div>
```

Formato de display (no de input): ver
[../design_system/typography.md](../design_system/typography.md#2-formato-de-datos-en-ui).

## Contador de caracteres SEO

```html
<!-- meta_title — max 70 -->
<div class="form-text d-flex justify-content-between">
  <span>Recomendado: 50-70 caracteres.</span>
  <span :class="form.meta_title.length > 60 ? 'text-warning' : 'text-muted'">{{ form.meta_title.length }}/70</span>
</div>

<!-- meta_description — max 160 -->
<div class="form-text d-flex justify-content-between">
  <span>Recomendado: 120-160 caracteres.</span>
  <span :class="form.meta_description.length > 145 ? 'text-warning' : 'text-muted'">{{ form.meta_description.length }}/160</span>
</div>
```

## `btn-xs` — micro botones en variantes

```css
/* Agregar en <style scoped> cuando se necesite */
.btn-xs { padding: 0.1rem 0.35rem; font-size: 0.75rem; line-height: 1.3; }
```

## Manejo de errores DRF → toast

```js
const msg = e.response?.data?.detail            // error global
         || e.response?.data?.name?.[0]         // error de campo 'name'
         || e.response?.data?.non_field_errors?.[0]
         || 'Error al guardar';
toast.error(msg);
```

Regla: **try/catch con `toast.error(...)` en toda llamada async**, sin excepcion.

## Validacion declarativa — `vee-validate` + `yup`

**Regla:** solo usar este patron para formularios con reglas de validacion no triviales (varios
campos interdependientes, validacion async, mensajes de error por campo con estado
touched/dirty). Para formularios simples (la mayoria de los CRUD offcanvas del panel), el patron
liviano de [offcanvas.md](offcanvas.md) (`required` nativo de HTML + error de DRF a toast) sigue
siendo el default — no migrar formularios existentes sin necesidad real.

Unico uso real hoy: `composables/useFormValidation.js` (usado por
`modules/marketing/CampaignForm.vue`). **Siempre `.js`, nunca `.ts`** — el proyecto es JS puro,
sin excepcion (ver [../architecture/vue_patterns.md](../architecture/vue_patterns.md#1-regla-no-negociable)).

```js
// composables/useFormValidation.js
import { useForm } from 'vee-validate';
import * as yup from 'yup';
import { computed } from 'vue';

export const campaignValidationSchema = yup.object({
  title: yup.string().required('El titulo es requerido').min(3).max(100),
  content: yup.string().required().min(10).max(500),
  channels: yup.array().of(yup.string()).min(1, 'Selecciona al menos un canal').required(),
  scheduled_at: yup.string().required().test('is-future', 'Debe ser en el futuro', (v) => v && new Date(v) > new Date()),
});

export function useFormValidation(validationSchema) {
  const { handleSubmit, values, errors, meta, resetForm, setFieldValue, setFieldTouched } = useForm({
    validationSchema,
    initialValues: { /* ... */ },
  });
  // computed: hasErrors, isValid | funciones: getErrorMessage(field), touchField(field),
  // touchAllFields(), reset(), setValues(obj)
  // onSubmit = handleSubmit(validCallback, invalidCallback) — invalidCallback llama touchAllFields()
  //            para mostrar los errores solo despues del primer intento de submit
  return { values, errors, meta, /* ...helpers */ };
}
```

Uso en el componente (`<script setup>`):

```vue
<script setup>
import { useFormValidation, campaignValidationSchema } from '@/composables/useFormValidation';

const { values, campaignForm, onSubmit } = useFormValidation(campaignValidationSchema);

const submit = onSubmit(async (formValues) => {
  await api.post('dashboard/marketing/campaigns/', formValues);
});
</script>

<template>
  <input v-model="campaignForm.title.value" class="form-control" :class="{ 'is-invalid': campaignForm.titleTouched.value && campaignForm.titleError.value }">
  <div v-if="campaignForm.titleTouched.value" class="invalid-feedback">{{ campaignForm.titleError.value }}</div>
</template>
```

Clases Bootstrap de estado (`is-invalid`/`is-valid`) via helper `getFieldClasses(fieldState, touched)`
exportado del mismo composable — no reinventar la logica de clases en cada componente.

## Ver tambien

- [offcanvas.md](offcanvas.md) — contrato completo del Form component, flujo watch/submit
