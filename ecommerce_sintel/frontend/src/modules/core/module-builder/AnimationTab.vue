<template>
  <div class="mb-section">
    <div class="mb-section-title"><i class="bi bi-stars me-2"></i>Animaciones</div>
    <div class="mb-anim-grid">
      <button
        v-for="a in ANIMATIONS" :key="a.value"
        :class="['mb-anim-card', form.animation_type === a.value && 'active']"
        @click="form.animation_type = a.value"
      >
        <i :class="['bi', a.icon]"></i>
        <span>{{ a.label }}</span>
      </button>
    </div>
    <div class="mb-grid mt-3">
      <div class="mb-field">
        <label class="mb-label">Duración (ms)</label>
        <div class="d-flex gap-2 align-items-center">
          <input v-model.number="form.animation_duration" type="range" min="100" max="2000" step="100" class="form-range" style="flex:1">
          <span class="mb-range-val">{{ form.animation_duration }}ms</span>
        </div>
      </div>
      <div class="mb-field">
        <label class="mb-label">Delay (ms)</label>
        <div class="d-flex gap-2 align-items-center">
          <input v-model.number="form.animation_delay" type="range" min="0" max="1000" step="50" class="form-range" style="flex:1">
          <span class="mb-range-val">{{ form.animation_delay }}ms</span>
        </div>
      </div>
      <div class="mb-field">
        <label class="mb-label">Repetir</label>
        <div class="form-check form-switch mt-1">
          <input v-model="form.animation_repeat" class="form-check-input" type="checkbox" id="mb-anim-repeat">
          <label class="form-check-label" for="mb-anim-repeat">Repetir animación</label>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ANIMATIONS } from '@/constants/animations';

defineProps({
  form: { type: Object, required: true },
});
</script>

<style scoped src="./_shared.css"></style>

<style scoped>
/* ── Animations ──────────────────────────────────────────────────────────── */
.mb-anim-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.5rem; }
.mb-anim-card {
  display: flex; flex-direction: column; align-items: center; gap: 0.3rem;
  padding: 0.6rem 0.4rem; border: 2px solid #e2e8f0; border-radius: 8px;
  background: #f8fafc; cursor: pointer; font-size: 0.7rem; color: #64748b;
  transition: border-color .15s;
}
.mb-anim-card:hover  { border-color: #93c5fd; background: #eff6ff; }
.mb-anim-card.active { border-color: #2563eb; background: #eff6ff; color: #2563eb; }
.mb-anim-card i { font-size: 1.2rem; }
</style>
