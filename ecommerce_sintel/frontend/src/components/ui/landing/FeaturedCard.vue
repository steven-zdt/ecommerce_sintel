<template>
  <RouterLink :to="item.item_url || '/'" class="fc-card text-decoration-none">
    <!-- Imagen -->
    <div class="fc-img-wrap">
      <img
        v-if="item.thumbnail"
        :src="item.thumbnail"
        :alt="item.name"
        class="fc-img"
        loading="lazy"
      >
      <div v-else class="fc-img-placeholder">
        <i :class="['bi', typeIcon]"></i>
      </div>

      <!-- Badges -->
      <span v-if="item.is_featured" class="fc-badge fc-badge-star">
        <i class="bi bi-star-fill"></i> Destacado
      </span>
      <span v-if="typeBadge" class="fc-badge" :class="typeBadgeClass">
        {{ typeBadge }}
      </span>

      <!-- CTA overlay en hover -->
      <div class="fc-hover-cta">
        <span>Ver detalle</span>
        <i class="bi bi-arrow-right"></i>
      </div>
    </div>

    <!-- Info -->
    <div class="fc-body">
      <span v-if="item.category_name" class="fc-category">{{ item.category_name }}</span>
      <p class="fc-name">{{ item.name }}</p>
      <div class="fc-footer">
        <span class="fc-price">{{ priceLabel }}</span>
        <span v-if="priceSuffix" class="fc-suffix">{{ priceSuffix }}</span>
      </div>
    </div>
  </RouterLink>
</template>

<script setup>
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import { formatCOP } from '@/utils/money';

const props = defineProps({
  item: { type: Object, required: true },
  type: { type: String, default: 'product' },
});

const typeIcon = computed(() => ({
  product: 'bi-box-seam',
  rental:  'bi-truck',
  service: 'bi-tools',
}[props.type] ?? 'bi-grid'));

const typeBadge = computed(() => ({
  rental:  'Alquiler',
  service: 'Servicio',
}[props.type] ?? ''));

const typeBadgeClass = computed(() => ({
  rental:  'fc-badge-rental',
  service: 'fc-badge-service',
}[props.type] ?? ''));

const priceLabel = computed(() => {
  if (!props.item.min_price) return 'Consultar';
  return formatCOP(props.item.min_price, { withSymbol: true });
});

const priceSuffix = computed(() =>
  props.type === 'rental' ? '/dia' : ''
);
</script>

<style scoped>
.fc-card {
  display: flex;
  flex-direction: column;
  background: #fff;
  border: 1px solid rgba(0,0,0,.07);
  border-radius: 18px;
  overflow: hidden;
  transition:
    transform 0.35s cubic-bezier(0.16,1,0.3,1),
    box-shadow 0.35s ease,
    border-color 0.22s ease;
  box-shadow: 0 2px 8px rgba(0,0,0,.05);
}
.fc-card:hover {
  transform: translateY(-7px);
  box-shadow: 0 16px 40px rgba(0,0,0,.1), 0 4px 12px rgba(0,0,0,.06);
  border-color: #bfdbfe;
}

/* ── Imagen ─────────────────────────────────────────────────────────────────── */
.fc-img-wrap {
  position: relative;
  width: 100%;
  padding-top: 62%;
  overflow: hidden;
  background: #f8fafc;
}
.fc-img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
  transition: transform 0.5s ease;
}
.fc-card:hover .fc-img { transform: scale(1.06); }
.fc-img-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2rem;
  color: #cbd5e1;
}

/* ── CTA hover overlay ──────────────────────────────────────────────────────── */
.fc-hover-cta {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(0deg, rgba(37,99,235,.85) 0%, transparent 100%);
  padding: 1.5rem 0.85rem 0.65rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.8rem;
  font-weight: 600;
  color: #fff;
  opacity: 0;
  transform: translateY(8px);
  transition: opacity 0.28s ease, transform 0.28s cubic-bezier(0.16,1,0.3,1);
}
.fc-card:hover .fc-hover-cta {
  opacity: 1;
  transform: translateY(0);
}

/* ── Badges ─────────────────────────────────────────────────────────────────── */
.fc-badge {
  position: absolute;
  top: 0.55rem;
  font-size: 0.6rem;
  font-weight: 700;
  border-radius: 9999px;
  padding: 0.2rem 0.55rem;
  color: #fff;
  display: flex;
  align-items: center;
  gap: 0.2rem;
}
.fc-badge-star {
  left: 0.55rem;
  background: rgba(245,158,11,.95);
  color: #78350f;
}
.fc-badge-rental {
  right: 0.55rem;
  background: #0ea5e9;
}
.fc-badge-service {
  right: 0.55rem;
  background: #8b5cf6;
}

/* ── Body ───────────────────────────────────────────────────────────────────── */
.fc-body {
  flex: 1;
  padding: 0.9rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}
.fc-category {
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #64748b;
}
.fc-name {
  font-size: 0.88rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.fc-footer {
  display: flex;
  align-items: baseline;
  gap: 0.2rem;
  margin-top: auto;
  padding-top: 0.5rem;
}
.fc-price {
  font-size: 1rem;
  font-weight: 800;
  color: #2563eb;
}
.fc-suffix {
  font-size: 0.7rem;
  color: #64748b;
}
</style>
