<template>
  <BaseHorizontalCard
    :image="equipment.image || ''"
    image-fit="contain"
    placeholder-icon="bi-truck"
    placeholder-bg="linear-gradient(135deg, #faf5ff, #f3e8ff)"
    placeholder-color="#c4b5fd"
    :title="equipment.name"
    :description="equipment.description || ''"
    accent-color="#7c3aed"
    accent-shadow="rgba(124,58,237,.09)"
    accent-border="#ddd6fe"
    @view="emit('view', equipment)"
  >
    <template #image-badge>
      <span v-if="equipment.is_featured" class="ehc-feat-badge">
        <i class="bi bi-star-fill me-1"></i>Destacado
      </span>
    </template>

    <template #tags>
      <p v-if="categoryName" class="ehc-category">{{ categoryName }}</p>
    </template>

    <template #badges>
      <div class="ehc-meta">
        <span v-if="brandName" class="ehc-meta-item">
          <i class="bi bi-building me-1"></i>{{ brandName }}
        </span>
      </div>
      <div class="ehc-badges">
        <span v-if="equipment.is_active" class="ehc-avail ehc-avail-ok">
          <i class="bi bi-check-circle me-1"></i>Disponible
        </span>
        <span v-else class="ehc-avail ehc-avail-out">
          <i class="bi bi-x-circle me-1"></i>No disponible
        </span>
      </div>
    </template>

    <template #price>
      <div v-if="hasPricePerDay" class="ehc-price-main">
        <span class="ehc-price-value">{{ fmtCOP(pricePerDay) }}</span>
        <span class="ehc-price-unit">/ dia</span>
      </div>
      <div v-if="hasPricePerHour" class="ehc-price-hour">
        {{ fmtCOP(pricePerHour) }} / hora
      </div>
      <div v-if="!hasPricePerDay && !hasPricePerHour" class="ehc-price-convenir">
        Precio a convenir
      </div>
    </template>

    <template #actions>
      <button class="ehc-btn-primary" :disabled="!equipment.is_active" @click="emit('quote', equipment)">
        <i class="bi bi-truck me-1"></i>Solicitar alquiler
      </button>
      <button class="ehc-btn-secondary" @click="emit('view', equipment)">
        <i class="bi bi-eye me-1"></i>Ver equipo
      </button>
    </template>
  </BaseHorizontalCard>
</template>

<script setup>
import { computed } from 'vue';
import BaseHorizontalCard from '@/components/base/BaseHorizontalCard.vue';

const props = defineProps({
  equipment: { type: Object, required: true },
});

const emit = defineEmits(['view', 'quote']);

const defaultVariant = computed(() =>
  props.equipment.variants?.find(v => v.is_default) || props.equipment.variants?.[0] || {}
);

const pricePerDay   = computed(() => parseFloat(defaultVariant.value.rental_price_per_day  || 0));
const pricePerHour  = computed(() => parseFloat(defaultVariant.value.rental_price_per_hour || 0));
const hasPricePerDay  = computed(() => pricePerDay.value  > 0);
const hasPricePerHour = computed(() => pricePerHour.value > 0);
const categoryName  = computed(() => props.equipment.category_name  || props.equipment.category?.name  || null);
const brandName     = computed(() => props.equipment.brand_name      || props.equipment.brand?.name      || null);

const fmtCOP = (n) => new Intl.NumberFormat('es-CO', {
  style: 'currency', currency: 'COP', maximumFractionDigits: 0,
}).format(n);
</script>

<style scoped>
.ehc-feat-badge {
  position: absolute; top: 0.5rem; left: 0.5rem;
  background: rgba(245,158,11,.9); color: #78350f;
  font-size: 0.62rem; font-weight: 700; border-radius: 9999px;
  padding: 0.18rem 0.5rem; display: inline-flex; align-items: center;
  backdrop-filter: blur(4px);
}
.ehc-category {
  font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 1px; color: #64748b; margin: 0 0 0.3rem;
}
.ehc-meta { margin-bottom: 0.6rem; }
.ehc-meta-item { font-size: 0.75rem; color: #94a3b8; }
.ehc-badges { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.ehc-avail {
  font-size: 0.68rem; font-weight: 600; border-radius: 9999px;
  padding: 0.2rem 0.6rem; display: inline-flex; align-items: center;
}
.ehc-avail-ok  { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.ehc-avail-out { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }

.ehc-price-main { display: flex; align-items: baseline; gap: 0.3rem; }
.ehc-price-value { font-size: 1.25rem; font-weight: 800; color: #7c3aed; line-height: 1; }
.ehc-price-unit { font-size: 0.8rem; color: #94a3b8; font-weight: 500; }
.ehc-price-hour { font-size: 0.78rem; color: #64748b; }
.ehc-price-convenir { font-size: 0.82rem; color: #94a3b8; font-style: italic; }

.ehc-btn-primary {
  font-size: 0.82rem; font-weight: 600; color: #fff;
  background: linear-gradient(135deg, #7c3aed, #6d28d9);
  border: none; border-radius: 9999px; padding: 0.55rem 0.9rem; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: transform 0.22s ease, box-shadow 0.22s ease;
  box-shadow: 0 2px 10px rgba(124,58,237,.3);
}
.ehc-btn-primary:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 5px 14px rgba(124,58,237,.4); }
.ehc-btn-primary:disabled { background: #e2e8f0; color: #94a3b8; box-shadow: none; cursor: not-allowed; }
.ehc-btn-secondary {
  font-size: 0.78rem; font-weight: 600; color: #7c3aed;
  background: rgba(124,58,237,.07); border: 1px solid rgba(124,58,237,.2);
  border-radius: 9999px; padding: 0.45rem 0.9rem; cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: background 0.2s;
}
.ehc-btn-secondary:hover { background: rgba(124,58,237,.14); }

@media (max-width: 575px) {
  .ehc-price-value { font-size: 1rem; }
}
</style>
