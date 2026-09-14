<template>
  <div class="mb-section">
    <div class="mb-section-title"><i class="bi bi-palette me-2"></i>Estilo Visual</div>

    <div class="mb-subsection">Tema rápido</div>
    <div class="mb-theme-grid">
      <button
        v-for="th in THEMES" :key="th.value"
        :class="['mb-theme-card', form.theme === th.value && 'mb-theme-card--active']"
        @click="applyTheme(th.value)"
      >
        <div class="mb-theme-swatch" :style="th.swatch"></div>
        <span>{{ th.label }}</span>
      </button>
    </div>

    <div class="mb-subsection mt-3">Colores</div>
    <div class="mb-grid">
      <div v-for="col in COLOR_FIELDS" :key="col.key" class="mb-field">
        <label class="mb-label">{{ col.label }}</label>
        <div class="d-flex gap-2 align-items-center">
          <input type="color" v-model="form[col.key]" class="mb-color-input">
          <input v-model="form[col.key]" class="mb-input" :placeholder="col.placeholder" style="flex:1">
        </div>
      </div>
    </div>

    <div class="mb-subsection mt-3">Tipografía</div>
    <div class="mb-grid">
      <div class="mb-field">
        <label class="mb-label">Tamaño título (rem)</label>
        <div class="d-flex gap-2 align-items-center">
          <input v-model.number="form.title_size" type="range" min="1" max="5" step="0.25" class="form-range" style="flex:1">
          <span class="mb-range-val">{{ form.title_size }}rem</span>
        </div>
      </div>
      <div class="mb-field">
        <label class="mb-label">Tamaño subtítulo (rem)</label>
        <div class="d-flex gap-2 align-items-center">
          <input v-model.number="form.subtitle_size" type="range" min="0.7" max="2" step="0.1" class="form-range" style="flex:1">
          <span class="mb-range-val">{{ form.subtitle_size }}rem</span>
        </div>
      </div>
      <div class="mb-field">
        <label class="mb-label">Peso tipográfico</label>
        <select v-model="form.font_weight" class="mb-select">
          <option value="400">Normal (400)</option>
          <option value="500">Medium (500)</option>
          <option value="600">Semibold (600)</option>
          <option value="700">Bold (700)</option>
          <option value="800">Extrabold (800)</option>
          <option value="900">Black (900)</option>
        </select>
      </div>
      <div class="mb-field">
        <label class="mb-label">Alineación</label>
        <div class="mb-align-group">
          <button v-for="al in ['left','center','right']" :key="al"
            :class="['mb-align-btn', form.text_align === al && 'active']"
            @click="form.text_align = al">
            <i :class="`bi bi-text-${al}`"></i>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  form: { type: Object, required: true },
});

const THEMES = [
  { value: 'light',     label: 'Claro',      swatch: { background: '#f8fafc', border: '1px solid #e2e8f0' } },
  { value: 'dark',      label: 'Oscuro',     swatch: { background: '#0f172a' } },
  { value: 'gradient',  label: 'Gradiente',  swatch: { background: 'linear-gradient(135deg,#0f172a,#1e3a8a)' } },
  { value: 'glass',     label: 'Glass',      swatch: { background: 'rgba(99,102,241,.18)', border: '1px solid rgba(99,102,241,.3)' } },
  { value: 'minimal',   label: 'Minimal',    swatch: { background: '#fff', border: '1px solid #e2e8f0' } },
  { value: 'corporate', label: 'Corporativo', swatch: { background: '#1d4ed8' } },
];

const THEME_PRESETS = {
  light:     { bg_type: 'color',    bg_color: '#ffffff',               color_text: '#0f172a', color_bg: '#ffffff' },
  dark:      { bg_type: 'color',    bg_color: '#0f172a',               color_text: '#f1f5f9', color_bg: '#0f172a' },
  gradient:  { bg_type: 'gradient', bg_gradient_from: '#0f172a',       bg_gradient_to: '#1e3a8a', color_text: '#ffffff', color_bg: '#0f172a' },
  glass:     { bg_type: 'glass',    bg_color: 'rgba(255,255,255,.08)', color_text: '#ffffff', color_bg: 'transparent' },
  minimal:   { bg_type: 'color',    bg_color: '#ffffff',               color_text: '#374151', color_bg: '#ffffff' },
  corporate: { bg_type: 'gradient', bg_gradient_from: '#1d4ed8',       bg_gradient_to: '#7c3aed', color_text: '#ffffff', color_bg: '#1d4ed8' },
};

const COLOR_FIELDS = [
  { key: 'color_primary',   label: 'Color principal',  placeholder: '#2563eb' },
  { key: 'color_secondary', label: 'Color secundario', placeholder: '#7c3aed' },
  { key: 'color_text',      label: 'Color de texto',   placeholder: '#0f172a' },
  { key: 'color_bg',        label: 'Color de fondo',   placeholder: '#ffffff' },
];

// Muta el objeto `form` en sitio (Object.assign sobre el reactive del shell),
// exactamente igual que la version monolitica.
function applyTheme(value) {
  props.form.theme = value;
  const preset = THEME_PRESETS[value] || {};
  Object.assign(props.form, preset);
}
</script>

<style scoped src="./_shared.css"></style>

<style scoped>
/* ── Themes ──────────────────────────────────────────────────────────────── */
.mb-theme-grid {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.mb-theme-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.35rem;
  padding: 0.5rem 0.6rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  background: none;
  cursor: pointer;
  font-size: 0.72rem;
  font-weight: 500;
  color: #475569;
  transition: border-color .15s;
}
.mb-theme-card:hover   { border-color: #93c5fd; }
.mb-theme-card--active { border-color: #2563eb; color: #2563eb; }
.mb-theme-swatch       { width: 36px; height: 22px; border-radius: 4px; }

/* ── Align group ─────────────────────────────────────────────────────────── */
.mb-align-group { display: flex; gap: 4px; }
.mb-align-btn {
  padding: 0.3rem 0.6rem; border: 1px solid #d1d5db; border-radius: 5px;
  background: none; cursor: pointer; color: #64748b; font-size: 0.9rem;
  transition: background .15s, color .15s;
}
.mb-align-btn.active { background: #2563eb; border-color: #2563eb; color: #fff; }
</style>
