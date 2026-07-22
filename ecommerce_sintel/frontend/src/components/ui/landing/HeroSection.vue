<template>
  <!-- Skeleton -->
  <div v-if="loading" class="hs-skeleton">
    <div class="hs-sk-overlay">
      <div class="hs-sk-text">
        <div class="hs-sk-pill"></div>
        <div class="hs-sk-title"></div>
        <div class="hs-sk-sub"></div>
        <div class="hs-sk-btns">
          <div class="hs-sk-btn"></div>
          <div class="hs-sk-btn hs-sk-btn-ghost"></div>
        </div>
      </div>
    </div>
  </div>

  <!-- Carousel con banners de BD -->
  <section v-else-if="banners.length" class="hs-section">
    <div
      id="heroBannerCarousel"
      class="carousel slide carousel-fade hs-carousel"
      data-bs-ride="carousel"
      data-bs-interval="5500"
    >
      <!-- Indicadores pill -->
      <div v-if="banners.length > 1" class="carousel-indicators hs-indicators">
        <button
          v-for="(b, i) in banners"
          :key="b.uuid"
          type="button"
          data-bs-target="#heroBannerCarousel"
          :data-bs-slide-to="i"
          :class="{ active: i === 0 }"
          :aria-current="i === 0 ? 'true' : undefined"
        ></button>
      </div>

      <!-- Slides -->
      <div class="carousel-inner hs-inner">
        <div
          v-for="(b, i) in banners"
          :key="b.uuid"
          class="carousel-item hs-item"
          :class="{ active: i === 0 }"
        >
          <HeroSlide :banner="b" :is-first="i === 0" />
        </div>
      </div>

      <!-- Controles -->
      <template v-if="banners.length > 1">
        <button
          class="carousel-control-prev hs-ctrl"
          type="button"
          data-bs-target="#heroBannerCarousel"
          data-bs-slide="prev"
        >
          <div class="hs-ctrl-btn"><i class="bi bi-chevron-left"></i></div>
        </button>
        <button
          class="carousel-control-next hs-ctrl"
          type="button"
          data-bs-target="#heroBannerCarousel"
          data-bs-slide="next"
        >
          <div class="hs-ctrl-btn"><i class="bi bi-chevron-right"></i></div>
        </button>
      </template>
    </div>
  </section>

  <!-- Fallback: sin banners -->
  <section v-else class="hs-section hs-static">
    <HeroSlide
      :banner="{ title: 'Tecnologia para *tu empresa*', subtitle: 'Equipos, servicios y soluciones tecnologicas en un solo lugar. Instalacion profesional certificada en toda Colombia.' }"
      :is-first="true"
    />
  </section>
</template>

<script setup>
import HeroSlide from './HeroSlide.vue';

defineProps({
  banners: { type: Array,   default: () => [] },
  loading: { type: Boolean, default: false },
});
</script>

<style scoped>
/* ── Skeleton ───────────────────────────────────────────────────────────────── */
.hs-skeleton {
  height: 48vh;
  min-height: 288px;
  background: linear-gradient(135deg, #080d1a 0%, #0d1f4a 55%, #0f2460 100%);
  position: relative;
  overflow: hidden;
}
.hs-skeleton::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg,
    transparent 0%,
    rgba(255,255,255,.04) 40%,
    transparent 100%
  );
  background-size: 800px 100%;
  animation: hs-sk-shine 1.8s infinite linear;
}
@keyframes hs-sk-shine {
  0%   { background-position: -800px 0; }
  100% { background-position: 800px 0; }
}
.hs-sk-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  padding: 0 max(1.5rem, calc((100% - 1320px)/2 + 1.5rem));
}
.hs-sk-text { display: flex; flex-direction: column; gap: 1rem; max-width: 520px; }
.hs-sk-pill {
  height: 22px; width: 140px;
  border-radius: 9999px;
  background: rgba(255,255,255,.1);
}
.hs-sk-title {
  height: 56px; width: 100%;
  border-radius: 10px;
  background: rgba(255,255,255,.12);
}
.hs-sk-sub {
  height: 20px; width: 80%;
  border-radius: 6px;
  background: rgba(255,255,255,.07);
}
.hs-sk-btns { display: flex; gap: 0.75rem; margin-top: 0.5rem; }
.hs-sk-btn {
  height: 44px; width: 160px;
  border-radius: 9999px;
  background: rgba(37,99,235,.4);
}
.hs-sk-btn-ghost {
  background: rgba(255,255,255,.1);
}

/* ── Section ────────────────────────────────────────────────────────────────── */
.hs-section { width: 100%; }
.hs-carousel { width: 100%; }
.hs-inner,
.hs-item,
.hs-static {
  min-height: 48vh;
  height: 48vh;
}
@media (max-width: 767px) {
  .hs-inner, .hs-item, .hs-static { height: auto; min-height: 51svh; }
}

/* ── Indicadores ────────────────────────────────────────────────────────────── */
.hs-indicators {
  bottom: 1.5rem;
  gap: 6px;
  margin: 0;
}
.hs-indicators [data-bs-slide-to] {
  width: 8px !important;
  height: 8px !important;
  border-radius: 9999px !important;
  background: rgba(255,255,255,.4) !important;
  border: none !important;
  opacity: 1 !important;
  transition: width 0.28s ease, background 0.2s !important;
  margin: 0 !important;
}
.hs-indicators .active {
  width: 28px !important;
  background: #fff !important;
}

/* ── Controles ──────────────────────────────────────────────────────────────── */
.hs-ctrl { width: 52px; opacity: 1; }
.hs-ctrl-btn {
  width: 44px;
  height: 44px;
  background: rgba(255,255,255,.12);
  border: 1px solid rgba(255,255,255,.22);
  border-radius: 50%;
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  color: #fff;
  transition: background 0.22s;
}
.hs-ctrl:hover .hs-ctrl-btn { background: rgba(255,255,255,.26); }
</style>
