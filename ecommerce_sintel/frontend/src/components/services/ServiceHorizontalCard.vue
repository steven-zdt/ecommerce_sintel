<template>
  <BaseHorizontalCard
    :image="primaryImage || ''"
    image-fit="cover"
    placeholder-bg="linear-gradient(135deg, #fffbeb, #fef3c7)"
    placeholder-color="#d97706"
    :title="service.name"
    :description="service.description || ''"
    accent-color="#d97706"
    accent-shadow="rgba(217,119,6,.1)"
    accent-border="#fde68a"
    @view="emit('view', service)"
  >
    <template #placeholder-icon>
      <div class="shc-placeholder-icon">
        <i :class="['bi', service.icon_class || 'bi-tools']"></i>
      </div>
    </template>

    <template #image-badge>
      <span v-if="service.is_featured" class="shc-feat-badge">
        <i class="bi bi-star-fill me-1"></i>Destacado
      </span>
    </template>

    <template #tags>
      <div class="shc-tags">
        <span v-if="categoryName" class="shc-tag shc-tag-cat">{{ categoryName }}</span>
        <span v-if="levelName" class="shc-tag shc-tag-level">
          <i class="bi bi-person-badge me-1"></i>{{ levelName }}
        </span>
      </div>
    </template>

    <template #price>
      <div v-if="minPrice !== null">
        <span class="shc-price-from">Desde</span>
        <span class="shc-price-value">{{ fmtCOP(minPrice) }}</span>
      </div>
      <div v-else class="shc-price-cotizar">
        <i class="bi bi-file-earmark-text me-1"></i>A cotizar
      </div>
      <p class="shc-price-hint">Segun evaluacion tecnica</p>
    </template>

    <template #actions>
      <button class="shc-btn-primary" @click="emit('quote', service)">
        <i class="bi bi-file-earmark-text me-1"></i>Solicitar servicio
      </button>
      <button class="shc-btn-secondary" @click="emit('view', service)">
        <i class="bi bi-eye me-1"></i>Ver detalle
      </button>
    </template>
  </BaseHorizontalCard>
</template>

<script setup>
import { computed } from 'vue';
import BaseHorizontalCard from '@/components/base/BaseHorizontalCard.vue';
import { formatCOP } from '@/utils/money';
import { resolvePrimaryImage } from '@/utils/media';

const props = defineProps({ service: { type: Object, required: true } });
const emit = defineEmits(['view', 'quote']);

// Auditoria Enterprise de Imagenes (2026-08-04): logica de "elegir imagen principal"
// centralizada en resolvePrimaryImage() -- antes reimplementada identicamente 4 veces.
const primaryImage = computed(() => resolvePrimaryImage(props.service.images));

const categoryName = computed(() => props.service.category?.name || null);
const levelName    = computed(() => props.service.level?.name    || null);

const minPrice = computed(() => {
  const variants = props.service.variants;
  if (!variants?.length) return null;
  const prices = variants
    .map(v => v.calculated_price)
    .filter(p => p != null && parseFloat(p) > 0)
    .map(p => parseFloat(p));
  return prices.length ? Math.min(...prices) : null;
});

const fmtCOP = (n) => formatCOP(n, { withSymbol: true });
</script>

<style scoped>
.shc-placeholder-icon {
  width: 52px; height: 52px; border-radius: 14px;
  background: rgba(217,119,6,.12); border: 1.5px solid rgba(217,119,6,.2);
  display: flex; align-items: center; justify-content: center;
  font-size: 1.4rem; color: #d97706;
}
.shc-feat-badge {
  position: absolute; top: 0.5rem; left: 0.5rem;
  background: rgba(245,158,11,.9); color: #78350f;
  font-size: 0.62rem; font-weight: 700; border-radius: 9999px;
  padding: 0.18rem 0.5rem; display: inline-flex; align-items: center;
  backdrop-filter: blur(4px);
}
.shc-tags { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 0.5rem; }
.shc-tag {
  font-size: 0.65rem; font-weight: 700; border-radius: 9999px;
  padding: 0.18rem 0.55rem; display: inline-flex; align-items: center;
}
.shc-tag-cat   { background: #fffbeb; color: #92400e; border: 1px solid #fde68a; }
.shc-tag-level { background: #f8fafc; color: #64748b; border: 1px solid #e2e8f0; }

.shc-price-from { font-size: 0.72rem; color: #94a3b8; display: block; }
.shc-price-value { font-size: 1.25rem; font-weight: 800; color: #d97706; line-height: 1; display: block; }
.shc-price-cotizar {
  font-size: 0.82rem; font-weight: 600; color: #d97706;
  background: rgba(217,119,6,.08); border: 1px solid rgba(217,119,6,.18);
  border-radius: 9999px; padding: 0.25rem 0.7rem; display: inline-flex; align-items: center;
}
.shc-price-hint { font-size: 0.7rem; color: #94a3b8; margin: 0.15rem 0 0; display: flex; align-items: center; gap: 0.25rem; }

.shc-btn-primary {
  font-size: 0.82rem; font-weight: 600; color: #fff;
  background: linear-gradient(135deg, #d97706, #b45309);
  border: none; border-radius: 9999px; padding: 0.55rem 0.9rem; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: transform 0.22s ease, box-shadow 0.22s ease;
  box-shadow: 0 2px 10px rgba(217,119,6,.3);
}
.shc-btn-primary:hover { transform: translateY(-1px); box-shadow: 0 5px 14px rgba(217,119,6,.4); }
.shc-btn-secondary {
  font-size: 0.78rem; font-weight: 600; color: #d97706;
  background: rgba(217,119,6,.07); border: 1px solid rgba(217,119,6,.2);
  border-radius: 9999px; padding: 0.45rem 0.9rem; cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: background 0.2s;
}
.shc-btn-secondary:hover { background: rgba(217,119,6,.14); }

@media (max-width: 575px) {
  .shc-price-value { font-size: 1rem; }
}
</style>
