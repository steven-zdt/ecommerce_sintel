<template>
  <RouterLink :to="offer.item_url || '/tienda'" class="foc-card text-decoration-none">
    <!-- Badge descuento -->
    <div class="foc-badge">
      <span class="foc-badge-num">-{{ Math.round(offer.discount_percentage || 0) }}%</span>
      <span class="foc-badge-label">OFF</span>
    </div>

    <!-- Imagen -->
    <div class="foc-img-wrap">
      <img
        v-if="offer.item_thumbnail"
        :src="offer.item_thumbnail"
        :alt="offer.item_name"
        class="foc-img"
        loading="lazy"
      >
      <div v-else class="foc-img-placeholder">
        <i class="bi bi-tag-fill"></i>
      </div>
    </div>

    <!-- Info -->
    <div class="foc-body">
      <p class="foc-item-name">{{ offer.item_name }}</p>
      <p class="foc-offer-name">{{ offer.name }}</p>
      <CountdownTimer :seconds-remaining="offer.seconds_remaining ?? 0" />
    </div>

    <!-- Arrow -->
    <div class="foc-arrow">
      <i class="bi bi-arrow-right"></i>
    </div>
  </RouterLink>
</template>

<script setup>
import { RouterLink } from 'vue-router';
import CountdownTimer from './CountdownTimer.vue';

defineProps({
  offer: { type: Object, required: true },
});
</script>

<style scoped>
.foc-card {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: rgba(255,255,255,.055);
  border: 1px solid rgba(255,255,255,.09);
  border-radius: 16px;
  padding: 1rem 1.1rem;
  position: relative;
  overflow: hidden;
  transition:
    background 0.22s ease,
    border-color 0.22s ease,
    transform 0.3s cubic-bezier(0.16,1,0.3,1);
}
.foc-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(249,115,22,.06), transparent 60%);
  opacity: 0;
  transition: opacity 0.22s;
}
.foc-card:hover {
  background: rgba(255,255,255,.09);
  border-color: rgba(249,115,22,.3);
  transform: translateY(-3px);
}
.foc-card:hover::before { opacity: 1; }

/* ── Badge ──────────────────────────────────────────────────────────────────── */
.foc-badge {
  position: absolute;
  top: 0.55rem;
  left: 0.65rem;
  background: linear-gradient(135deg, #f97316, #ef4444);
  border-radius: 8px;
  padding: 0.15rem 0.45rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  line-height: 1;
  min-width: 44px;
  text-align: center;
  box-shadow: 0 2px 8px rgba(239,68,68,.35);
}
.foc-badge-num {
  font-size: 0.85rem;
  font-weight: 800;
  color: #fff;
}
.foc-badge-label {
  font-size: 0.54rem;
  font-weight: 700;
  color: rgba(255,255,255,.85);
  letter-spacing: 1px;
}

/* ── Imagen ─────────────────────────────────────────────────────────────────── */
.foc-img-wrap {
  width: 74px;
  height: 74px;
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
  background: rgba(255,255,255,.07);
  display: flex;
  align-items: center;
  justify-content: center;
}
.foc-img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.foc-img-placeholder {
  font-size: 1.75rem;
  color: rgba(255,255,255,.22);
}

/* ── Body ───────────────────────────────────────────────────────────────────── */
.foc-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.foc-item-name {
  font-size: 0.9rem;
  font-weight: 700;
  color: #f1f5f9;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.foc-offer-name {
  font-size: 0.72rem;
  color: rgba(255,255,255,.42);
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ── Arrow ──────────────────────────────────────────────────────────────────── */
.foc-arrow {
  flex-shrink: 0;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: rgba(255,255,255,.08);
  border: 1px solid rgba(255,255,255,.12);
  display: flex;
  align-items: center;
  justify-content: center;
  color: rgba(255,255,255,.45);
  font-size: 0.85rem;
  transition: background 0.22s, color 0.22s, transform 0.22s;
}
.foc-card:hover .foc-arrow {
  background: #f97316;
  color: #fff;
  border-color: #f97316;
  transform: translateX(3px);
}
</style>
