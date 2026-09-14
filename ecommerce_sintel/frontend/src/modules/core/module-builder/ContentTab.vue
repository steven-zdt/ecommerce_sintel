<template>
  <div class="mb-section">
    <div class="mb-section-title"><i class="bi bi-toggles me-2"></i>Contenido</div>
    <p class="mb-section-sub">Define qué información se muestra en cada elemento.</p>
    <div class="mb-toggle-grid">
      <label v-for="cf in CONTENT_FIELDS" :key="cf.key" class="mb-toggle-row">
        <div class="mb-toggle-info">
          <i :class="['bi', cf.icon]"></i>
          <span>{{ cf.label }}</span>
        </div>
        <div class="form-check form-switch mb-0">
          <input v-model="form[cf.key]" class="form-check-input" type="checkbox">
        </div>
      </label>
    </div>

    <div v-if="form.show_badge" class="mb-grid mt-3">
      <div class="mb-field">
        <label class="mb-label">Texto del badge</label>
        <input v-model="form.badge_text" class="mb-input" placeholder="Nuevo">
      </div>
      <div class="mb-field">
        <label class="mb-label">Color del badge</label>
        <div class="d-flex gap-2 align-items-center">
          <input type="color" v-model="form.badge_color" class="mb-color-input">
          <input v-model="form.badge_color" class="mb-input" style="flex:1">
        </div>
      </div>
    </div>

    <div v-if="form.show_counter" class="mt-3">
      <div class="mb-section-title mb-section-title--sm"><i class="bi bi-graph-up me-2"></i>Estadísticas</div>
      <div v-for="(st, i) in form.stats" :key="i" class="mb-grid mb-stat-row">
        <div class="mb-field">
          <label class="mb-label">Valor</label>
          <input v-model="st.value" class="mb-input" placeholder="+500">
        </div>
        <div class="mb-field">
          <label class="mb-label">Etiqueta</label>
          <input v-model="st.label" class="mb-input" placeholder="Instalaciones">
        </div>
        <button class="mb-btn mb-stat-remove" @click="form.stats.splice(i, 1)"><i class="bi bi-trash"></i></button>
      </div>
      <button class="mb-btn mt-2" @click="form.stats.push({ value: '', label: '' })">
        <i class="bi bi-plus-lg me-1"></i>Agregar estadística
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  form: { type: Object, required: true },
});

const CONTENT_FIELDS = [
  { key: 'show_image',       icon: 'bi-image',            label: 'Imagen' },
  { key: 'show_icon',        icon: 'bi-star',             label: 'Ícono' },
  { key: 'show_title',       icon: 'bi-type-h1',          label: 'Título' },
  { key: 'show_subtitle',    icon: 'bi-type-h2',          label: 'Subtítulo' },
  { key: 'show_description', icon: 'bi-text-paragraph',   label: 'Descripción' },
  { key: 'show_price',       icon: 'bi-currency-dollar',  label: 'Precio' },
  { key: 'show_category',    icon: 'bi-tag',              label: 'Categoría' },
  { key: 'show_button',      icon: 'bi-cursor',           label: 'Botón' },
  { key: 'show_rating',      icon: 'bi-star-half',        label: 'Calificación' },
  { key: 'show_counter',     icon: 'bi-hash',             label: 'Contador' },
  { key: 'show_tags',        icon: 'bi-tags',             label: 'Etiquetas' },
  { key: 'show_badge',       icon: 'bi-award',            label: 'Badge' },
];
</script>

<style scoped src="./_shared.css"></style>

<style scoped>
.mb-section-title--sm { font-size: 0.78rem; border-bottom: none; padding-bottom: 0.25rem; }
.mb-stat-row { grid-template-columns: 1fr 1fr auto; align-items: end; margin-bottom: 0.5rem; }
.mb-stat-remove { color: #ef4444; padding: 0.4rem 0.6rem; }

/* ── Content toggles ─────────────────────────────────────────────────────── */
.mb-toggle-grid { display: flex; flex-direction: column; gap: 0; }
.mb-toggle-row {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0.55rem 0.5rem; cursor: pointer;
  border-bottom: 1px solid #f1f5f9;
  transition: background .12s;
}
.mb-toggle-row:hover { background: #f8fafc; }
.mb-toggle-info { display: flex; align-items: center; gap: 0.5rem; font-size: 0.82rem; color: #374151; }
.mb-toggle-info i { color: #64748b; }
</style>
