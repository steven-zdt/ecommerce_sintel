<template>
  <div class="hsl-root">
    <HeroBackground
      :image="banner.image || ''"
      :video="banner.video || ''"
      :bg-color="banner.background_color || ''"
    />

    <div class="container-xl hsl-content">
      <div class="row align-items-center hsl-row">
        <!-- Texto principal -->
        <div class="col-lg-7">
          <div class="hsl-text">
            <span class="hsl-eyebrow">{{ banner.eyebrow || appConfigStore.brand.site_name }}</span>
            <!-- El carrusel monta todos los slides en el DOM a la vez (Bootstrap solo
                 oculta los inactivos con CSS) -- solo el primero debe ser <h1>, el resto
                 <h2>, o la pagina termina con varios <h1> simultaneos (hallazgo F10). -->
            <component :is="isFirst ? 'h1' : 'h2'" class="hsl-title">{{ banner.title || defaultTitle }}</component>
            <p v-if="banner.subtitle || defaultSubtitle" class="hsl-subtitle">
              {{ banner.subtitle || defaultSubtitle }}
            </p>
            <HeroCTA
              :primary-label="banner.link_label || 'Explorar catalogo'"
              :primary-url="banner.link_url || '/tienda'"
              :ghost-label="banner.cta_ghost_label || 'Solicitar cotizacion'"
              :ghost-url="banner.cta_ghost_url || '/cotizar'"
            />
          </div>
        </div>

        <!-- Panel flotante decorativo (solo desktop, solo primer slide sin imagen) -->
        <div
          v-if="showGlassPanel"
          class="col-lg-5 d-none d-lg-flex justify-content-end"
        >
          <div class="hsl-glass-panel">
            <div class="row g-3">
              <div v-for="feat in features" :key="feat.label" class="col-6">
                <div class="hsl-feat-card">
                  <div class="hsl-feat-icon">
                    <i :class="['bi', feat.icon]"></i>
                  </div>
                  <span class="hsl-feat-label">{{ feat.label }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import HeroBackground from './HeroBackground.vue';
import HeroCTA from './HeroCTA.vue';
import { useAppConfigStore } from '@/store/appConfig';

// White-label F7 (2026-08-14): antes 'Sintel Technology' hardcodeado como
// fallback del eyebrow -- ver AUDITORIA/WHITE_LABEL/WHITE_LABEL_FRONTEND_AUDIT.md.
const appConfigStore = useAppConfigStore();

const props = defineProps({
  banner:   { type: Object,  required: true },
  isFirst:  { type: Boolean, default: false },
});

const defaultTitle    = 'Tecnologia para *tu empresa*';
const defaultSubtitle = 'Equipos, servicios y soluciones tecnologicas en un solo lugar.';

const showGlassPanel = computed(() =>
  props.isFirst && !props.banner.image && !props.banner.video
);

const features = [
  { label: 'Tienda Online',      icon: 'bi-shop' },
  { label: 'Alquiler Equipos',   icon: 'bi-truck' },
  { label: 'Servicios Tecnicos', icon: 'bi-tools' },
  { label: 'Cotizaciones Pro',   icon: 'bi-file-earmark-text' },
];
</script>

<style scoped>
/* ── Root: ocupa todo el slide ──────────────────────────────────────────────── */
.hsl-root {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: inherit;
}

/* ── Content layer ──────────────────────────────────────────────────────────── */
.hsl-content {
  position: relative;
  z-index: 2;
  height: 100%;
}
.hsl-row {
  min-height: inherit;
  height: 100%;
  padding-top: 2rem;
  padding-bottom: 1.5rem;
}

/* ── Texto ──────────────────────────────────────────────────────────────────── */
.hsl-text { color: #fff; }

.hsl-eyebrow {
  display: inline-block;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  background: rgba(255,255,255,.1);
  border: 1px solid rgba(255,255,255,.2);
  border-radius: 9999px;
  padding: 0.25rem 0.9rem;
  margin-bottom: 0.6rem;
  color: rgba(255,255,255,.88);
}

.hsl-title {
  font-size: clamp(1.6rem, 3.4vw, 2.75rem);
  font-weight: 800;
  line-height: 1.15;
  text-shadow: 0 2px 16px rgba(0,0,0,.35);
  margin: 0 0 0.6rem;
}

.hsl-subtitle {
  font-size: clamp(0.85rem, 1.4vw, 1rem);
  color: rgba(255,255,255,.78);
  line-height: 1.5;
  text-shadow: 0 1px 4px rgba(0,0,0,.25);
  max-width: 520px;
  margin: 0;
}

/* ── Glass panel flotante ───────────────────────────────────────────────────── */
.hsl-glass-panel {
  background: rgba(255,255,255,.08);
  border: 1px solid rgba(255,255,255,.16);
  border-radius: 24px;
  backdrop-filter: blur(16px) saturate(160%);
  -webkit-backdrop-filter: blur(16px) saturate(160%);
  padding: 2rem;
  max-width: 320px;
  width: 100%;
  box-shadow: 0 24px 64px rgba(0,0,0,.28);
  animation: hsl-float 4s ease-in-out infinite;
}
@keyframes hsl-float {
  0%, 100% { transform: translateY(0); }
  50%       { transform: translateY(-14px); }
}

.hsl-feat-card {
  background: rgba(255,255,255,.09);
  border: 1px solid rgba(255,255,255,.13);
  border-radius: 14px;
  padding: 1rem 0.75rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  text-align: center;
  transition: background 0.22s;
}
.hsl-feat-card:hover { background: rgba(255,255,255,.18); }

.hsl-feat-icon {
  width: 40px;
  height: 40px;
  background: rgba(255,255,255,.14);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.1rem;
  color: #fff;
}
.hsl-feat-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: rgba(255,255,255,.85);
  line-height: 1.2;
}
</style>
