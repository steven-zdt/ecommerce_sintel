<template>
  <div class="fp-root">

    <!-- Header -->
    <div class="fp-header">
      <div class="d-flex align-items-center gap-2">
        <i class="bi bi-sliders2 fp-header-icon"></i>
        <span class="fp-header-title">Filtros</span>
      </div>
      <button v-if="hasActive" class="fp-reset-btn" @click="$emit('reset')">
        <i class="bi bi-x-circle me-1"></i>Limpiar
      </button>
    </div>

    <!-- Chips de filtros activos -->
    <div v-if="hasActive" class="fp-active-chips">
      <span v-if="localFilters.categorySlug" class="fp-chip">
        <i class="bi bi-tag me-1"></i>
        {{ categories.find(c => c.slug === localFilters.categorySlug)?.name ?? localFilters.categorySlug }}
        <button class="fp-chip-remove" @click="toggle('categorySlug', localFilters.categorySlug)">
          <i class="bi bi-x"></i>
        </button>
      </span>
      <span v-if="localFilters.brandSlug" class="fp-chip">
        <i class="bi bi-bookmark me-1"></i>
        {{ brands.find(b => b.slug === localFilters.brandSlug)?.name ?? localFilters.brandSlug }}
        <button class="fp-chip-remove" @click="toggle('brandSlug', localFilters.brandSlug)">
          <i class="bi bi-x"></i>
        </button>
      </span>
      <span v-if="localFilters.isFeatured" class="fp-chip fp-chip-feat">
        <i class="bi bi-star-fill me-1"></i>Destacados
        <button class="fp-chip-remove" @click="localFilters.isFeatured = null; emit('change', { ...localFilters })">
          <i class="bi bi-x"></i>
        </button>
      </span>
    </div>

    <div class="fp-divider"></div>

    <!-- Categorías -->
    <div v-if="categories.length" class="fp-section">
      <button class="fp-section-btn" @click="openCat = !openCat">
        <span class="fp-section-label">Categoria</span>
        <i :class="['bi fp-chevron', openCat ? 'bi-chevron-up' : 'bi-chevron-down']"></i>
      </button>
      <div v-show="openCat" class="fp-options">
        <div
          v-for="cat in categories"
          :key="cat.uuid"
          :class="['fp-option', { 'fp-option-active': localFilters.categorySlug === cat.slug }]"
          @click="toggle('categorySlug', cat.slug)"
        >
          <span class="fp-option-dot"></span>
          <span class="fp-option-label">{{ cat.name }}</span>
          <i v-if="localFilters.categorySlug === cat.slug" class="bi bi-check-lg fp-option-check"></i>
        </div>
      </div>
    </div>

    <div class="fp-divider"></div>

    <!-- Marcas / Nivel -->
    <div v-if="brands.length" class="fp-section">
      <button class="fp-section-btn" @click="openBrand = !openBrand">
        <span class="fp-section-label">{{ brandLabel }}</span>
        <i :class="['bi fp-chevron', openBrand ? 'bi-chevron-up' : 'bi-chevron-down']"></i>
      </button>
      <div v-show="openBrand" class="fp-options">
        <div
          v-for="brand in brands"
          :key="brand.uuid"
          :class="['fp-option', { 'fp-option-active': localFilters.brandSlug === brand.slug }]"
          @click="toggle('brandSlug', brand.slug)"
        >
          <span class="fp-option-dot"></span>
          <span class="fp-option-label">{{ brand.name }}</span>
          <i v-if="localFilters.brandSlug === brand.slug" class="bi bi-check-lg fp-option-check"></i>
        </div>
      </div>
    </div>

    <div v-if="showPrice" class="fp-divider"></div>

    <!-- Rango de precio -->
    <div v-if="showPrice" class="fp-section">
      <button class="fp-section-btn" @click="openPrice = !openPrice">
        <span class="fp-section-label">Precio</span>
        <i :class="['bi fp-chevron', openPrice ? 'bi-chevron-up' : 'bi-chevron-down']"></i>
      </button>
      <div v-show="openPrice" class="fp-price-range">
        <div class="fp-price-field">
          <label class="fp-price-label">Mínimo</label>
          <input
            v-model="localFilters.minPrice"
            type="number"
            class="fp-price-input"
            placeholder="$ 0"
            @change="emit('change', { ...localFilters })"
          >
        </div>
        <div class="fp-price-sep">—</div>
        <div class="fp-price-field">
          <label class="fp-price-label">Máximo</label>
          <input
            v-model="localFilters.maxPrice"
            type="number"
            class="fp-price-input"
            placeholder="$ ∞"
            @change="emit('change', { ...localFilters })"
          >
        </div>
      </div>
    </div>

    <div class="fp-divider"></div>

    <!-- Solo destacados — toggle switch -->
    <div class="fp-section fp-toggle-row">
      <div>
        <p class="fp-section-label mb-0">Solo destacados</p>
        <p class="fp-toggle-sub">Productos seleccionados</p>
      </div>
      <label class="fp-toggle-switch">
        <input
          type="checkbox"
          :checked="localFilters.isFeatured === true"
          @change="toggleFeatured"
        >
        <span class="fp-toggle-track"></span>
      </label>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';

const props = defineProps({
  filters: { type: Object, required: true },
  categories: { type: Array, default: () => [] },
  brands: { type: Array, default: () => [] },
  brandLabel: { type: String, default: 'Marca' },
  showPrice: { type: Boolean, default: true },
});

const emit = defineEmits(['change', 'reset']);

const localFilters = ref({ ...props.filters });
const openCat = ref(true);
const openBrand = ref(true);
const openPrice = ref(false);

watch(() => props.filters, (v) => { localFilters.value = { ...v }; }, { deep: true });

const hasActive = computed(() =>
  !!(localFilters.value.categorySlug || localFilters.value.brandSlug
    || localFilters.value.minPrice || localFilters.value.maxPrice
    || localFilters.value.isFeatured)
);

function toggle(key, val) {
  localFilters.value[key] = localFilters.value[key] === val ? '' : val;
  emit('change', { ...localFilters.value });
}

function toggleFeatured(e) {
  localFilters.value.isFeatured = e.target.checked ? true : null;
  emit('change', { ...localFilters.value });
}
</script>

<style scoped>
/* ── Root ───────────────────────────────────────────────────────────────────── */
.fp-root {
  font-size: 0.875rem;
}

/* ── Header ─────────────────────────────────────────────────────────────────── */
.fp-header {
  padding: 1rem 1.1rem 0.75rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.fp-header-icon {
  color: #2563eb;
  font-size: 1rem;
}
.fp-header-title {
  font-weight: 800;
  font-size: 0.9rem;
  color: #0f172a;
  letter-spacing: -0.01em;
}
.fp-reset-btn {
  font-size: 0.72rem;
  font-weight: 600;
  color: #ef4444;
  background: rgba(239,68,68,.08);
  border: 1px solid rgba(239,68,68,.2);
  border-radius: 9999px;
  padding: 0.2rem 0.65rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  transition: background 0.2s;
}
.fp-reset-btn:hover { background: rgba(239,68,68,.15); }

/* ── Active chips ───────────────────────────────────────────────────────────── */
.fp-active-chips {
  padding: 0 1.1rem 0.75rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}
.fp-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  font-size: 0.68rem;
  font-weight: 600;
  background: #eff6ff;
  color: #1d4ed8;
  border: 1px solid #bfdbfe;
  border-radius: 9999px;
  padding: 0.22rem 0.55rem 0.22rem 0.65rem;
}
.fp-chip-feat {
  background: #fefce8;
  color: #a16207;
  border-color: #fde68a;
}
.fp-chip-remove {
  background: none;
  border: none;
  padding: 0;
  color: inherit;
  cursor: pointer;
  opacity: 0.65;
  font-size: 0.85rem;
  line-height: 1;
  margin-left: 0.1rem;
  display: flex;
  align-items: center;
}
.fp-chip-remove:hover { opacity: 1; }

/* ── Divider ────────────────────────────────────────────────────────────────── */
.fp-divider {
  height: 1px;
  background: rgba(0,0,0,.06);
  margin: 0 1.1rem;
}

/* ── Sections ───────────────────────────────────────────────────────────────── */
.fp-section {
  padding: 0.65rem 1.1rem;
}
.fp-section-btn {
  width: 100%;
  background: none;
  border: none;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.1rem 0;
  cursor: pointer;
  color: #0f172a;
}
.fp-section-label {
  font-weight: 700;
  font-size: 0.8rem;
  color: #0f172a;
}
.fp-chevron {
  font-size: 0.75rem;
  color: #64748b;
  transition: transform 0.2s;
}

/* ── Options ────────────────────────────────────────────────────────────────── */
.fp-options {
  margin-top: 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}
.fp-option {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  padding: 0.42rem 0.65rem;
  border-radius: 9px;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
  color: #475569;
}
.fp-option:hover { background: #f1f5f9; color: #0f172a; }
.fp-option-active { background: #eff6ff; color: #2563eb; }

.fp-option-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #cbd5e1;
  flex-shrink: 0;
  transition: background 0.15s;
}
.fp-option-active .fp-option-dot { background: #2563eb; }
.fp-option-label { flex: 1; font-size: 0.82rem; font-weight: 500; }
.fp-option-check { font-size: 0.85rem; color: #2563eb; }

/* ── Price range ────────────────────────────────────────────────────────────── */
.fp-price-range {
  margin-top: 0.7rem;
  display: flex;
  align-items: flex-end;
  gap: 0.5rem;
}
.fp-price-field { flex: 1; display: flex; flex-direction: column; gap: 0.2rem; }
.fp-price-label {
  font-size: 0.65rem;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.fp-price-input {
  width: 100%;
  background: #f8fafc;
  border: 1.5px solid #e2e8f0;
  border-radius: 9px;
  padding: 0.4rem 0.6rem;
  font-size: 0.82rem;
  color: #0f172a;
  transition: border-color 0.18s;
  outline: none;
}
.fp-price-input:focus { border-color: #2563eb; background: #fff; }
.fp-price-sep {
  font-size: 0.8rem;
  color: #94a3b8;
  padding-bottom: 0.45rem;
  flex-shrink: 0;
}

/* ── Toggle switch ──────────────────────────────────────────────────────────── */
.fp-toggle-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.fp-toggle-sub {
  font-size: 0.7rem;
  color: #94a3b8;
  margin: 0.1rem 0 0;
}
.fp-toggle-switch {
  position: relative;
  cursor: pointer;
  flex-shrink: 0;
}
.fp-toggle-switch input { position: absolute; opacity: 0; width: 0; height: 0; }
.fp-toggle-track {
  display: block;
  width: 38px;
  height: 22px;
  border-radius: 999px;
  background: #e2e8f0;
  transition: background 0.22s;
  position: relative;
}
.fp-toggle-track::after {
  content: '';
  position: absolute;
  top: 3px;
  left: 3px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 1px 4px rgba(0,0,0,.2);
  transition: transform 0.22s cubic-bezier(0.34,1.56,0.64,1);
}
.fp-toggle-switch input:checked + .fp-toggle-track {
  background: #2563eb;
}
.fp-toggle-switch input:checked + .fp-toggle-track::after {
  transform: translateX(16px);
}
</style>
