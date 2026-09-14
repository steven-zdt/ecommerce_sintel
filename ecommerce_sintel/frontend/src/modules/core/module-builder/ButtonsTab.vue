<template>
  <div class="mb-section">
    <div class="mb-section-title"><i class="bi bi-cursor me-2"></i>Botones CTA</div>
    <div class="mb-grid">
      <div class="mb-field">
        <label class="mb-label">Texto del botón</label>
        <input v-model="form.btn_text" class="mb-input" placeholder="Ver más">
      </div>
      <div class="mb-field">
        <label class="mb-label">Color</label>
        <div class="d-flex gap-2 align-items-center">
          <input type="color" v-model="form.btn_color" class="mb-color-input">
          <input v-model="form.btn_color" class="mb-input" style="flex:1">
        </div>
      </div>
      <div class="mb-field">
        <label class="mb-label">Ícono Bootstrap</label>
        <input v-model="form.btn_icon" class="mb-input" placeholder="bi-arrow-right">
      </div>
      <div class="mb-field">
        <label class="mb-label">Estilo</label>
        <div class="mb-btn-style-group">
          <button v-for="s in ['filled','outline','ghost','minimal']" :key="s"
            :class="['mb-btn-style-opt', form.btn_style === s && 'active']"
            @click="form.btn_style = s">
            {{ s }}
          </button>
        </div>
      </div>
      <div class="mb-field">
        <label class="mb-label">Posición</label>
        <select v-model="form.btn_position" class="mb-select">
          <option value="bottom">Abajo</option>
          <option value="top">Arriba</option>
          <option value="inline">Inline</option>
          <option value="overlay">Overlay</option>
        </select>
      </div>
      <div class="mb-field">
        <label class="mb-label">Apertura</label>
        <select v-model="form.btn_target" class="mb-select">
          <option value="_self">Misma pestaña</option>
          <option value="_blank">Nueva pestaña</option>
        </select>
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

<style scoped>
/* ── Button style picker ─────────────────────────────────────────────────── */
.mb-btn-style-group { display: flex; gap: 4px; flex-wrap: wrap; }
.mb-btn-style-opt {
  padding: 0.25rem 0.55rem; border: 1px solid #d1d5db; border-radius: 5px;
  background: none; cursor: pointer; font-size: 0.72rem; color: #64748b;
  text-transform: capitalize; transition: background .12s;
}
.mb-btn-style-opt:hover  { background: #f1f5f9; }
.mb-btn-style-opt.active { background: #2563eb; border-color: #2563eb; color: #fff; }
</style>
