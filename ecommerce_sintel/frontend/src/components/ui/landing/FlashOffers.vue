<template>
  <section v-if="loading || offers.length" ref="el" class="fo-root">
    <div class="container-xl">
      <!-- Header -->
      <div class="fo-header">
        <div class="fo-header-left">
          <span class="fo-pulse"></span>
          <div>
            <p class="fo-label">
              <i class="bi bi-lightning-charge-fill me-1"></i>Ofertas del momento
            </p>
            <p class="fo-sub">Descuentos por tiempo limitado</p>
          </div>
        </div>
        <RouterLink to="/tienda" class="fo-link">
          Ver todas <i class="bi bi-arrow-right ms-1"></i>
        </RouterLink>
      </div>

      <!-- Skeleton -->
      <div v-if="loading" class="fo-grid">
        <div v-for="n in 3" :key="n" class="fo-skeleton"></div>
      </div>

      <!-- Cards -->
      <div v-else class="fo-grid">
        <FlashOfferCard
          v-for="(offer, i) in offers"
          :key="offer.uuid"
          :offer="offer"
          :style="`transition-delay: ${i * 80}ms`"
          class="fo-card-reveal"
          :class="{ 'fo-card-visible': sectionVisible }"
        />
      </div>
    </div>
  </section>
</template>

<script setup>
import { RouterLink } from 'vue-router';
import FlashOfferCard from './FlashOfferCard.vue';
import { useScrollReveal } from '@/composables/useScrollReveal';

defineProps({
  offers:  { type: Array,   default: () => [] },
  loading: { type: Boolean, default: false },
});

const { el, visible: sectionVisible } = useScrollReveal({ threshold: 0.08 });
</script>

<style scoped>
/* ── Section ────────────────────────────────────────────────────────────────── */
.fo-root {
  background: #080d1a;
  padding: clamp(3rem, 6vw, 5rem) 0;
  width: 100%;
}

/* ── Header ─────────────────────────────────────────────────────────────────── */
.fo-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 1.75rem;
}
.fo-header-left {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}
.fo-pulse {
  display: flex;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: #f97316;
  flex-shrink: 0;
  box-shadow: 0 0 0 0 rgba(249,115,22,.7);
  animation: fo-pulse 1.5s infinite ease-out;
}
@keyframes fo-pulse {
  0%   { box-shadow: 0 0 0 0 rgba(249,115,22,.7); }
  70%  { box-shadow: 0 0 0 10px rgba(249,115,22,0); }
  100% { box-shadow: 0 0 0 0 rgba(249,115,22,0); }
}
.fo-label {
  font-size: 1rem;
  font-weight: 700;
  color: #f97316;
  margin: 0 0 0.1rem;
}
.fo-sub {
  font-size: 0.75rem;
  color: rgba(255,255,255,.38);
  margin: 0;
}
.fo-link {
  font-size: 0.82rem;
  font-weight: 600;
  color: rgba(255,255,255,.6);
  text-decoration: none;
  transition: color 0.18s;
}
.fo-link:hover { color: #f97316; }

/* ── Grid ───────────────────────────────────────────────────────────────────── */
.fo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
}

/* ── Skeleton ───────────────────────────────────────────────────────────────── */
.fo-skeleton {
  height: 108px;
  border-radius: 16px;
  background: linear-gradient(90deg,
    rgba(255,255,255,.05) 25%,
    rgba(255,255,255,.1) 50%,
    rgba(255,255,255,.05) 75%
  );
  background-size: 800px 100%;
  animation: fo-shimmer 1.5s infinite linear;
}
@keyframes fo-shimmer {
  0%   { background-position: -800px 0; }
  100% { background-position: 800px 0; }
}

/* ── Card reveal animation ──────────────────────────────────────────────────── */
.fo-card-reveal {
  opacity: 0;
  transform: translateX(20px);
  transition: opacity 0.55s cubic-bezier(0.16,1,0.3,1),
              transform 0.55s cubic-bezier(0.16,1,0.3,1);
}
.fo-card-visible {
  opacity: 1;
  transform: translateX(0);
}

/* ── Mobile ─────────────────────────────────────────────────────────────────── */
@media (max-width: 575px) {
  .fo-grid { grid-template-columns: 1fr; }
}
</style>
