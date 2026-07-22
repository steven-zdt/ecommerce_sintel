<template>
  <RouterLink :to="isExternal ? '/' : (module.url || '/')" custom v-slot="{ navigate, href }">
    <a
      ref="el"
      :href="isExternal ? module.url : href"
      :target="isExternal ? '_blank' : undefined"
      :rel="isExternal ? 'noopener noreferrer' : undefined"
      @click="isExternal ? undefined : navigate"
      class="mc-card text-decoration-none"
      :class="[revealClass, { 'mc-visible': visible }]"
      :style="cardStyle"
    >
      <!-- Imagen de fondo -->
      <div
        v-if="show.image && module.background_image"
        class="mc-bg"
        :style="`background-image: url('${module.background_image}')`"
      ></div>

      <!-- Overlay base (legibilidad) + overlay configurable del admin -->
      <div class="mc-overlay"></div>
      <div v-if="overlayStyle" class="mc-overlay-custom" :style="overlayStyle"></div>

      <!-- Badge -->
      <span v-if="show.badge && badge.text" class="mc-badge" :style="{ background: badge.color || '#f59e0b' }">
        {{ badge.text }}
      </span>

      <div class="mc-body" :style="{ textAlign: layoutConfig.text_align || 'center' }">
        <div v-if="show.icon" class="mc-icon-wrap">
          <IconRenderer :icon="module.icon || 'bi-grid'" extra-class="mc-icon" />
        </div>

        <p v-if="show.title" class="mc-label">{{ module.label }}</p>
        <p v-if="show.subtitle && layoutConfig.public_subtitle" class="mc-subtitle">{{ layoutConfig.public_subtitle }}</p>
        <p v-if="show.description && layoutConfig.description" class="mc-description">{{ layoutConfig.description }}</p>

        <div v-if="show.counter && stats.length" class="mc-stats">
          <AnimatedCounter v-for="(s, i) in stats" :key="i" :value="s.value" :label="s.label" />
        </div>

        <span v-if="show.button" class="mc-cta" :style="ctaStyle">
          {{ button.text || 'Ver más' }}
          <IconRenderer v-if="button.icon" :icon="button.icon" />
        </span>
      </div>
    </a>
  </RouterLink>
</template>

<script setup>
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import { useLayoutEngine } from '@/composables/useLayoutEngine';
import { useScrollReveal, resolveRevealClass } from '@/composables/useScrollReveal';
import AnimatedCounter from './AnimatedCounter.vue';
import IconRenderer from '@/components/ui/IconRenderer.vue';

const props = defineProps({
  module:  { type: Object,  required: true },
  visible: { type: Boolean, default: false },
});

const { resolveModuleBackgroundStyle, resolveModuleOverlayStyle } = useLayoutEngine();

const isExternal = computed(() => /^https?:\/\//.test(props.module.url || ''));

const layoutConfig = computed(() => props.module.layout_config || {});
// Defaults alineados con DEFAULT_FORM de ModuleBuilderModal.vue: modulos sin
// configuracion previa (layout_config={}) deben verse igual que antes (icono+label).
const show = computed(() => {
  const s = layoutConfig.value.show || {};
  return {
    image: s.image !== false,
    icon: s.icon !== false,
    title: s.title !== false,
    subtitle: s.subtitle !== false,
    description: s.description !== false,
    button: s.button === true,
    counter: s.counter === true,
    badge: s.badge === true,
  };
});
const badge  = computed(() => layoutConfig.value.badge  || {});
const button = computed(() => layoutConfig.value.button || {});
const stats  = computed(() => Array.isArray(layoutConfig.value.stats) ? layoutConfig.value.stats.filter(s => s.value) : []);
const animation = computed(() => layoutConfig.value.animation || {});

const { el, visible: ownVisible } = useScrollReveal({ threshold: 0.1 });
const revealClass = computed(() => resolveRevealClass(animation.value.type));

const cardStyle = computed(() => {
  const bgStyle = resolveModuleBackgroundStyle(layoutConfig.value);
  return {
    '--mc': props.module.color || '#2563eb',
    background: bgStyle.background || undefined,
    backdropFilter: bgStyle.backdropFilter,
    transitionDuration: `${animation.value.duration || 600}ms`,
    transitionDelay: `${animation.value.delay || 0}ms`,
  };
});

const overlayStyle = computed(() => resolveModuleOverlayStyle(layoutConfig.value));

const ctaStyle = computed(() => ({
  background: button.value.style === 'outline' || button.value.style === 'ghost' ? 'transparent' : (button.value.color || '#2563eb'),
  color: button.value.style === 'outline' ? (button.value.color || '#2563eb') : '#fff',
  border: button.value.style === 'outline' ? `1px solid ${button.value.color || '#2563eb'}` : 'none',
}));

// Visibilidad efectiva: propia (scroll reveal individual) o forzada por el padre (skeleton->grid).
const visible = computed(() => props.visible || ownVisible.value);
</script>

<style scoped>
.mc-card {
  position: relative;
  border-radius: 18px;
  overflow: hidden;
  background: var(--mc, #2563eb);
  min-height: 220px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  opacity: 0;
  transform: translateY(28px);
  transition-property: opacity, transform, box-shadow;
  transition-timing-function: cubic-bezier(0.16,1,0.3,1);
  box-shadow: 0 2px 10px rgba(0,0,0,.08);
  will-change: transform, opacity;
}
.mc-card.mc-visible {
  opacity: 1;
  transform: translateY(0);
}
.mc-card:hover {
  transform: translateY(-7px) scale(1.02);
  box-shadow: 0 16px 40px rgba(0,0,0,.16), 0 0 0 1px var(--mc) inset;
}
.mc-card.mc-visible:hover {
  transform: translateY(-7px) scale(1.02);
}

/* ── Variantes de reveal (animation.type del Constructor Visual) ─────────────── */
.sr-zoom { transform: scale(0.85); }
.sr-zoom.mc-visible { transform: scale(1); }
.sr-zoom.mc-visible:hover { transform: scale(1.02) translateY(-7px); }
.sr-flip { transform: rotateY(35deg); }
.sr-flip.mc-visible { transform: rotateY(0); }
.sr-rotate { transform: rotate(-6deg) translateY(28px); }
.sr-rotate.mc-visible { transform: rotate(0) translateY(0); }
.sr-bounce.mc-visible { animation: mc-bounce 0.7s cubic-bezier(0.34,1.56,0.64,1); }
.sr-parallax { transform: translateY(50px); }
.sr-parallax.mc-visible { transform: translateY(0); }
@keyframes mc-bounce {
  0%   { transform: translateY(28px); opacity: 0; }
  60%  { transform: translateY(-10px); opacity: 1; }
  100% { transform: translateY(0); }
}

/* ── Fondo imagen ───────────────────────────────────────────────────────────── */
.mc-bg {
  position: absolute;
  inset: 0;
  background-size: cover;
  background-position: center;
  transition: transform 0.5s ease;
}
.mc-card:hover .mc-bg { transform: scale(1.06); }

/* ── Overlays ───────────────────────────────────────────────────────────────── */
.mc-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(170deg, rgba(0,0,0,.12) 0%, rgba(0,0,0,.48) 100%);
}
.mc-overlay-custom {
  position: absolute;
  inset: 0;
}

/* ── Badge ──────────────────────────────────────────────────────────────────── */
.mc-badge {
  position: absolute;
  top: 0.75rem;
  right: 0.75rem;
  z-index: 3;
  font-size: 0.68rem;
  font-weight: 700;
  color: #fff;
  padding: 0.2rem 0.6rem;
  border-radius: 999px;
  box-shadow: 0 2px 8px rgba(0,0,0,.2);
}

/* ── Cuerpo ─────────────────────────────────────────────────────────────────── */
.mc-body {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1.5rem 1.25rem;
  width: 100%;
}
.mc-icon-wrap {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  background: rgba(255,255,255,.18);
  border: 1px solid rgba(255,255,255,.28);
  backdrop-filter: blur(6px);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.3s cubic-bezier(0.34,1.56,0.64,1), background 0.22s ease;
}
.mc-card:hover .mc-icon-wrap {
  transform: scale(1.12);
  background: rgba(255,255,255,.28);
}
.mc-icon { font-size: 1.3rem; color: #fff; }

.mc-label {
  font-size: 1rem;
  font-weight: 700;
  color: #fff;
  margin: 0;
  text-shadow: 0 1px 4px rgba(0,0,0,.3);
  line-height: 1.2;
}
.mc-subtitle {
  font-size: 0.82rem;
  font-weight: 500;
  color: rgba(255,255,255,.88);
  margin: 0;
}
.mc-description {
  font-size: 0.78rem;
  color: rgba(255,255,255,.78);
  margin: 0;
  line-height: 1.4;
}
.mc-stats {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 0.25rem;
}
.mc-stats :deep(.ac-value) { font-size: 1.3rem; -webkit-text-fill-color: #fff; background: none; }
.mc-stats :deep(.ac-label) { color: rgba(255,255,255,.72); }
.mc-cta {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.78rem;
  font-weight: 700;
  padding: 0.4rem 0.9rem;
  border-radius: 999px;
  margin-top: 0.35rem;
}

/* ── Responsive ─────────────────────────────────────────────────────────────── */
@media (min-width: 992px) {
  .mc-card { min-height: 260px; }
}
</style>
