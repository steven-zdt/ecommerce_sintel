<template>
  <div class="mb-section">
    <div class="mb-section-title"><i class="bi bi-paint-bucket me-2"></i>Fondo</div>
    <div class="mb-bg-type-grid">
      <button v-for="bg in BG_TYPES" :key="bg.value"
        :class="['mb-bg-card', form.bg_type === bg.value && 'active']"
        @click="form.bg_type = bg.value">
        <div :class="['mb-bg-swatch', `mb-bg-swatch--${bg.value}`]"></div>
        <span>{{ bg.label }}</span>
      </button>
    </div>
    <div class="mb-grid mt-3">
      <template v-if="form.bg_type === 'color'">
        <div class="mb-field mb-field--full">
          <label class="mb-label">Color de fondo</label>
          <div class="d-flex gap-2 align-items-center">
            <input type="color" v-model="form.bg_color" class="mb-color-input">
            <input v-model="form.bg_color" class="mb-input" style="flex:1">
          </div>
        </div>
      </template>
      <template v-else-if="form.bg_type === 'gradient'">
        <div class="mb-field">
          <label class="mb-label">Color inicial</label>
          <div class="d-flex gap-2 align-items-center">
            <input type="color" v-model="form.bg_gradient_from" class="mb-color-input">
            <input v-model="form.bg_gradient_from" class="mb-input" style="flex:1">
          </div>
        </div>
        <div class="mb-field">
          <label class="mb-label">Color final</label>
          <div class="d-flex gap-2 align-items-center">
            <input type="color" v-model="form.bg_gradient_to" class="mb-color-input">
            <input v-model="form.bg_gradient_to" class="mb-input" style="flex:1">
          </div>
        </div>
        <div class="mb-field mb-field--full">
          <label class="mb-label">Vista previa</label>
          <div class="mb-gradient-preview" :style="{ background: `linear-gradient(135deg, ${form.bg_gradient_from}, ${form.bg_gradient_to})` }"></div>
        </div>
      </template>
      <template v-else-if="form.bg_type === 'glass'">
        <div class="mb-field mb-field--full">
          <label class="mb-label">Color base (hex con alpha)</label>
          <div class="d-flex gap-2 align-items-center">
            <input type="color" v-model="form.bg_color" class="mb-color-input">
            <input v-model="form.bg_color" class="mb-input" style="flex:1">
          </div>
        </div>
      </template>
      <template v-else-if="form.bg_type === 'pattern'">
        <div class="mb-field mb-field--full">
          <label class="mb-label">Patrón</label>
          <div class="mb-pattern-grid">
            <button v-for="p in PATTERNS" :key="p.value"
              :class="['mb-pattern-btn', form.bg_pattern === p.value && 'active']"
              :style="p.style"
              @click="form.bg_pattern = p.value">
            </button>
          </div>
        </div>
      </template>
      <div class="mb-field mb-field--full">
        <div class="form-check form-switch">
          <input v-model="form.bg_overlay" class="form-check-input" type="checkbox" id="mb-overlay">
          <label class="form-check-label" for="mb-overlay">Activar overlay oscuro</label>
        </div>
      </div>
      <div v-if="form.bg_overlay" class="mb-field">
        <label class="mb-label">Opacidad overlay (%)</label>
        <div class="d-flex gap-2 align-items-center">
          <input v-model.number="form.bg_overlay_opacity" type="range" min="0" max="100" class="form-range" style="flex:1">
          <span class="mb-range-val">{{ form.bg_overlay_opacity }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  form: { type: Object, required: true },
});

const BG_TYPES = [
  { value: 'color',    label: 'Color sólido' },
  { value: 'gradient', label: 'Gradiente' },
  { value: 'glass',    label: 'Glass' },
  { value: 'pattern',  label: 'Patrón' },
];

const PATTERNS = [
  { value: 'dots',     style: { backgroundImage: 'radial-gradient(#94a3b8 1px, transparent 1px)', backgroundSize: '10px 10px', background: '#f8fafc' } },
  { value: 'grid',     style: { backgroundImage: 'linear-gradient(#e2e8f0 1px, transparent 1px), linear-gradient(90deg, #e2e8f0 1px, transparent 1px)', backgroundSize: '14px 14px', background: '#f8fafc' } },
  { value: 'diagonal', style: { backgroundImage: 'repeating-linear-gradient(45deg, #e2e8f0 0, #e2e8f0 1px, transparent 0, transparent 50%)', backgroundSize: '10px 10px', background: '#f8fafc' } },
];
</script>

<style scoped src="./_shared.css"></style>

<style scoped>
/* ── Gradient preview ────────────────────────────────────────────────────── */
.mb-gradient-preview { height: 48px; border-radius: 8px; border: 1px solid rgba(0,0,0,.08); }

/* ── Background type picker ──────────────────────────────────────────────── */
.mb-bg-type-grid { display: flex; gap: 0.5rem; flex-wrap: wrap; }
.mb-bg-card {
  display: flex; flex-direction: column; align-items: center; gap: 0.35rem;
  padding: 0.5rem 0.7rem; border: 2px solid #e2e8f0; border-radius: 8px;
  background: none; cursor: pointer; font-size: 0.72rem; color: #64748b;
  transition: border-color .15s;
}
.mb-bg-card:hover  { border-color: #93c5fd; }
.mb-bg-card.active { border-color: #2563eb; color: #2563eb; }
.mb-bg-swatch { width: 40px; height: 24px; border-radius: 5px; }
.mb-bg-swatch--color    { background: #f1f5f9; border: 1px solid #e2e8f0; }
.mb-bg-swatch--gradient { background: linear-gradient(135deg, #0f172a, #1e3a8a); }
.mb-bg-swatch--glass    { background: rgba(99,102,241,.15); border: 1px solid rgba(99,102,241,.3); backdrop-filter: blur(4px); }
.mb-bg-swatch--pattern  { background-image: radial-gradient(#94a3b8 1px, transparent 1px); background-size: 6px 6px; background-color: #f8fafc; }

/* Pattern picker */
.mb-pattern-grid { display: flex; gap: 0.5rem; }
.mb-pattern-btn {
  width: 56px; height: 38px; border-radius: 6px; border: 2px solid #e2e8f0; cursor: pointer;
  transition: border-color .15s;
}
.mb-pattern-btn:hover  { border-color: #93c5fd; }
.mb-pattern-btn.active { border-color: #2563eb; }
</style>
