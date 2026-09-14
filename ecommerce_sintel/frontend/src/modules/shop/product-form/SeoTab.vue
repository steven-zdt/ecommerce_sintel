<template>
  <div>
    <div class="rounded-3 px-3 py-2 mb-3 small" style="background:#eff6ff;border-left:3px solid #3b82f6">
      <i class="bi bi-info-circle me-1"></i>
      Mejoran el posicionamiento en buscadores (Google, Bing).
    </div>
    <div class="mb-3">
      <label class="form-label small fw-semibold">Titulo SEO</label>
      <input v-model="form.meta_title" type="text" class="form-control" maxlength="70"
             placeholder="Titulo optimizado para buscadores">
      <div class="form-text d-flex justify-content-between">
        <span>50–70 caracteres recomendado.</span>
        <span :class="form.meta_title.length > 60 ? 'text-warning' : 'text-muted'">{{ form.meta_title.length }}/70</span>
      </div>
    </div>
    <div class="mb-3">
      <label class="form-label small fw-semibold">Meta Descripcion</label>
      <textarea v-model="form.meta_description" class="form-control" rows="3" maxlength="160"
                placeholder="Descripcion breve para buscadores..."></textarea>
      <div class="form-text d-flex justify-content-between">
        <span>120–160 caracteres recomendado.</span>
        <span :class="form.meta_description.length > 145 ? 'text-warning' : 'text-muted'">{{ form.meta_description.length }}/160</span>
      </div>
    </div>
    <div v-if="localMode === 'edit'" class="d-flex gap-2">
      <button type="button" class="btn btn-primary flex-grow-1" @click="$emit('submit')" :disabled="actionLoading">
        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-2"></span>
        Guardar SEO
      </button>
      <button type="button" class="btn btn-light border" @click="$emit('close')">Cerrar</button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  // Mismo objeto `form` que GeneralTab.vue (mutado in-place) -- un solo
  // submit guarda ambos tabs a la vez (General + SEO son un solo formulario
  // dividido en 2 pestanas por conveniencia de UI).
  form: { type: Object, required: true },
  localMode: { type: String, required: true },
  actionLoading: { type: Boolean, default: false },
});
defineEmits(['submit', 'close']);
</script>
