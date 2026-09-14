<template>
  <div class="mb-section">
    <div class="mb-section-title"><i class="bi bi-sliders me-2"></i>Información General</div>
    <div class="mb-grid">
      <div v-if="isNew" class="mb-field mb-field--full">
        <label class="mb-label">Clave interna *</label>
        <input v-model="form.module_key" class="mb-input" placeholder="productos, blog, servicios...">
        <span class="mb-hint">Identificador único. Solo letras, números y guiones.</span>
      </div>
      <div class="mb-field">
        <label class="mb-label">Nombre del módulo *</label>
        <input v-model="form.custom_label" class="mb-input" placeholder="Productos destacados">
      </div>
      <div class="mb-field">
        <label class="mb-label">Subtítulo público</label>
        <input v-model="form.public_subtitle" class="mb-input" placeholder="Descripción breve de la sección">
      </div>
      <div class="mb-field mb-field--full">
        <label class="mb-label">Descripción interna</label>
        <textarea v-model="form.description" class="mb-input" rows="2" placeholder="Notas internas..."></textarea>
      </div>
      <div class="mb-field">
        <label class="mb-label">URL destino</label>
        <input v-model="form.custom_url" class="mb-input" placeholder="/tienda">
      </div>
      <div class="mb-field">
        <label class="mb-label">Orden</label>
        <input v-model.number="form.display_order" type="number" class="mb-input" min="0">
      </div>
      <div class="mb-field">
        <label class="mb-label">Items destacados</label>
        <input v-model.number="form.featured_items_limit" type="number" class="mb-input" min="1" max="24">
      </div>
      <div class="mb-field mb-field--full">
        <div class="form-check form-switch">
          <input v-model="form.is_visible" class="form-check-input" type="checkbox" id="mb-visible">
          <label class="form-check-label" for="mb-visible">Visible en la home</label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
// `form` es el objeto reactivo del shell: se muta en sitio (nunca se reasigna),
// que es como Vue comparte estado de objeto entre padre e hijo sin v-model.
defineProps({
  form:  { type: Object,  required: true },
  isNew: { type: Boolean, default: false },
});
</script>

<style scoped src="./_shared.css"></style>
