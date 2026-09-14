<template>
  <div>
    <!-- Banner informativo (solo create) -->
    <div v-if="localMode === 'create'" class="alert border-0 py-2 px-3 mb-4 small" style="background:#eff6ff;border-left:3px solid #3b82f6 !important;border-radius:8px">
      <i class="bi bi-info-circle me-2 text-primary"></i>
      Crea el equipo primero. Luego configura variantes, logistica y costos desde las pestanas.
    </div>

    <form @submit.prevent="localMode === 'create' ? $emit('submit-create') : $emit('submit-update')">
      <div class="mb-3">
        <label class="form-label small fw-bold">Nombre <span class="text-danger">*</span></label>
        <input v-model="form.name" type="text" class="form-control" required :placeholder="localMode === 'create' ? 'Ej: Grua Hidraulica 20T' : 'Nombre del equipo'">
      </div>
      <div class="mb-3">
        <label class="form-label small fw-bold">Descripcion</label>
        <textarea v-model="form.description" class="form-control" rows="3" placeholder="Descripcion del equipo..."></textarea>
      </div>
      <div class="row g-3 mb-3">
        <div class="col-6">
          <label class="form-label small fw-bold">Categoria <span class="text-danger">*</span></label>
          <select v-model="form.category" class="form-select" required>
            <option value="">— Seleccionar —</option>
            <option v-for="cat in categories" :key="cat.uuid" :value="cat.uuid">{{ cat.name }}</option>
          </select>
        </div>
        <div class="col-6">
          <label class="form-label small fw-bold">Marca</label>
          <select v-model="form.brand" class="form-select">
            <option value="">— Sin marca —</option>
            <option v-for="brd in brands" :key="brd.uuid" :value="brd.uuid">{{ brd.name }}</option>
          </select>
        </div>
      </div>
      <div class="row g-3 mb-4">
        <div class="col-6">
          <div class="form-check form-switch">
            <input v-model="form.is_active" class="form-check-input" type="checkbox" :id="`eqActive-${localMode}`">
            <label class="form-check-label small" :for="`eqActive-${localMode}`">Activo</label>
          </div>
        </div>
        <div class="col-6">
          <div class="form-check form-switch">
            <input v-model="form.is_featured" class="form-check-input" type="checkbox" :id="`eqFeatured-${localMode}`">
            <label class="form-check-label small" :for="`eqFeatured-${localMode}`">Destacado</label>
          </div>
        </div>
      </div>

      <div v-if="localMode === 'create'" class="d-flex gap-2">
        <button type="submit" class="btn btn-primary w-100" :disabled="loading">
          <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
          <i v-else class="bi bi-check-lg me-1"></i> Crear Equipo
        </button>
        <button type="button" class="btn btn-light border" @click="$emit('cancel')" :disabled="loading">Cancelar</button>
      </div>
      <button v-else type="submit" class="btn btn-primary w-100" :disabled="loading">
        <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
        Guardar Cambios
      </button>
    </form>
  </div>
</template>

<script setup>
defineProps({
  // Objeto del padre (form) mutado in-place por los v-model de este tab --
  // misma referencia reactiva, el padre lo repuebla por completo al cambiar
  // de item/modo, este tab nunca lo reasigna.
  form: { type: Object, required: true },
  localMode: { type: String, required: true },
  categories: { type: Array, default: () => [] },
  brands: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
});
defineEmits(['submit-create', 'submit-update', 'cancel']);
</script>
