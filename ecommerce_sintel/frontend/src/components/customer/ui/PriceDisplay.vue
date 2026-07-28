<template>
  <div class="price-display">
    <!-- Precio con descuento activo -->
    <template v-if="hasActiveDiscount">
      <div class="d-flex align-items-baseline gap-2 flex-wrap">
        <span class="price-original text-muted text-decoration-line-through small">
          {{ fmt(price) }}
        </span>
        <span class="price-current text-danger fw-bold">
          {{ fmt(discountedPrice) }}
        </span>
        <span v-if="mode === 'per-day'" class="price-unit text-muted">/día</span>
        <span v-else-if="mode === 'per-hour'" class="price-unit text-muted">/hora</span>
      </div>
      <div v-if="discountEnd" class="discount-badge mt-1">
        <i class="bi bi-clock me-1"></i>Oferta hasta {{ fmtDate(discountEnd) }}
      </div>
    </template>

    <!-- Precio normal -->
    <template v-else>
      <div class="d-flex align-items-baseline gap-2">
        <span :class="['price-current fw-bold', size === 'lg' ? 'fs-4' : size === 'sm' ? 'small' : '']">
          {{ price ? fmt(price) : cotizar ? 'Cotizar' : 'Consultar' }}
        </span>
        <span v-if="mode === 'per-day'" class="price-unit text-muted small">/día</span>
        <span v-else-if="mode === 'per-hour'" class="price-unit text-muted small">/hora</span>
      </div>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { formatCOP } from '@/utils/money';

const props = defineProps({
  price: { type: [String, Number], default: null },
  discountedPrice: { type: [String, Number], default: null },
  discountStart: { type: String, default: null },
  discountEnd: { type: String, default: null },
  mode: { type: String, default: 'final' }, // 'final' | 'per-day' | 'per-hour'
  size: { type: String, default: 'md' },    // 'sm' | 'md' | 'lg'
  cotizar: { type: Boolean, default: false },
});

const hasActiveDiscount = computed(() => {
  if (!props.discountedPrice || !props.discountStart || !props.discountEnd) return false;
  const now = new Date();
  return now >= new Date(props.discountStart) && now <= new Date(props.discountEnd);
});

const fmt = (val) => formatCOP(val, { withSymbol: true });
const fmtDate = (iso) => new Date(iso).toLocaleDateString('es-CO');
</script>

<style scoped>
.price-current { color: #1e40af; }
.price-unit { font-size: .8rem; }
.discount-badge {
  display: inline-block;
  font-size: .72rem;
  color: #dc2626;
  background: #fef2f2;
  padding: 2px 8px;
  border-radius: 20px;
  border: 1px solid #fecaca;
}
</style>
