<template>
  <div class="mb-section">
    <div class="mb-section-title"><i class="bi bi-grid-3x3 me-2"></i>Distribución</div>
    <div class="mb-subsection">Columnas (desktop)</div>
    <div class="mb-cols-picker">
      <button v-for="n in [1,2,3,4,5,6]" :key="n"
        :class="['mb-col-btn', form.columns === n && 'active']"
        @click="form.columns = n">
        <div class="mb-col-vis">
          <div v-for="i in n" :key="i" class="mb-col-bar"></div>
        </div>
        <span>{{ n }}</span>
      </button>
    </div>
    <div class="mb-grid mt-3">
      <div class="mb-field">
        <label class="mb-label">Espaciado (padding)</label>
        <select v-model="form.padding" class="mb-select">
          <option value="none">Sin padding</option>
          <option value="sm">Pequeño</option>
          <option value="normal">Normal</option>
          <option value="lg">Grande</option>
          <option value="xl">Extra grande</option>
        </select>
      </div>
      <div class="mb-field">
        <label class="mb-label">Gap entre items (rem)</label>
        <input v-model.number="form.gap" type="number" class="mb-input" min="0" max="4" step="0.25">
      </div>
      <div class="mb-field">
        <label class="mb-label">Altura mínima (px)</label>
        <input v-model="form.min_height" class="mb-input" placeholder="Sin mínimo">
      </div>
      <div class="mb-field">
        <label class="mb-label">Ancho máximo (px)</label>
        <input v-model="form.max_width" class="mb-input" placeholder="Sin máximo">
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  form: { type: Object, required: true },
});
</script>

<style scoped src="./_shared.css"></style>
