<template>
  <RouterLink :to="isExternal ? '/' : (module.url || '/')" custom v-slot="{ navigate, href }">
    <a
      ref="el"
      :href="isExternal ? module.url : href"
      :target="isExternal ? '_blank' : undefined"
      :rel="isExternal ? 'noopener noreferrer' : undefined"
      @click="isExternal ? undefined : navigate($event)"
      class="mps-card-root text-decoration-none"
      :class="[revealClass, { 'mps-card-root--visible': visible }]"
      :style="cardStyle"
    >
      <MarketplaceBackground
        :type="media.type"
        :image="module.background_image || media.image"
        :video-src="media.video_url"
        :video-src-webm="media.video_url_webm"
        :poster="media.poster || module.background_image"
        :color="module.color || '#2563eb'"
        :loop="media.loop !== false"
        :overlay="overlayCfg.enabled"
        :overlay-color="overlayCfg.color"
        :overlay-opacity="overlayCfg.opacity"
        :blur="media.blur || 0"
        :parallax="false"
      />

      <span v-if="show.badge && badge.text" class="mps-badge" :style="{ background: badge.color || '#f59e0b' }">
        {{ badge.text }}
      </span>

      <MarketplaceOverlay class="mps-body-wrap" :glass="!!media.glass" :color="module.color">
        <div class="mps-body" :style="{ textAlign: layoutConfig.text_align || 'center' }">
          <div v-if="show.icon" class="mps-icon-wrap">
            <IconRenderer :icon="module.icon || 'bi-grid'" extra-class="mps-icon" />
          </div>

          <p v-if="show.title" class="mps-title">{{ module.label }}</p>
          <p v-if="show.subtitle && layoutConfig.public_subtitle" class="mps-subtitle">{{ layoutConfig.public_subtitle }}</p>
          <p v-if="show.description && layoutConfig.description" class="mps-description">{{ layoutConfig.description }}</p>

          <MarketplaceStats v-if="show.counter && stats.length" :stats="stats" />

          <span v-if="show.button" class="mps-cta" :class="{ 'mps-cta--top': button.position === 'top' }" :style="ctaStyle">
            {{ button.text || 'Ver más' }}
            <i :class="['bi', button.icon || 'bi-arrow-right', 'mps-cta-icon']"></i>
          </span>
        </div>
      </MarketplaceOverlay>
    </a>
  </RouterLink>
</template>

<script setup>
/**
 * MarketplaceCard — card premium (Fase 5). Reemplaza a ModuleCard.vue como
 * unidad visual dentro de MarketplaceCarousel.vue (ver scoped slot `card`).
 *
 * Mismo contrato de datos que ModuleCard.vue (module.layout_config.show/
 * badge/button/stats/animation) -- retrocompatible con modulos ya
 * configurados en el Home Builder, mas la rama nueva `layout_config.media`
 * (Fase 3/10: video/imagen/blur/glass por card).
 *
 * No recibe un prop `active` para controlar el autoplay del video: se
 * decidio no duplicar aqui el IntersectionObserver que ya trae
 * MarketplaceBackground.vue (pausa/reproduce solo, mirando su propia
 * visibilidad) -- agregar un segundo observer redundante violaria la Fase 11
 * (reducir consumo, no duplicar trabajo).
 */
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import { useLayoutEngine } from '@/composables/useLayoutEngine';
import { useScrollReveal, resolveRevealClass } from '@/composables/useScrollReveal';
import MarketplaceBackground from './MarketplaceBackground.vue';
import MarketplaceOverlay from './MarketplaceOverlay.vue';
import MarketplaceStats from './MarketplaceStats.vue';
import IconRenderer from '@/components/ui/IconRenderer.vue';

const props = defineProps({
  module: { type: Object, required: true },
});

const { resolveModuleOverlayStyle } = useLayoutEngine();

const isExternal = computed(() => /^https?:\/\//.test(props.module.url || ''));

const layoutConfig = computed(() => props.module.layout_config || {});

// Defaults alineados con ModuleCard.vue: un modulo sin layout_config previo
// debe seguir viendose igual (icono+label), no romperse.
const show = computed(() => {
  const s = layoutConfig.value.show || {};
  return {
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
const stats  = computed(() => Array.isArray(layoutConfig.value.stats) ? layoutConfig.value.stats.filter((s) => s.value) : []);
const animation = computed(() => layoutConfig.value.animation || {});

// ── Fondo multimedia (Fase 3/10) ──────────────────────────────────────────────
// [CORREGIDO 2026-08-06] `m.type` casi siempre tiene un valor real ('color' es
// el default de fabrica de ModuleBuilderModal.vue -- se guarda en CADA save(),
// no solo cuando el admin elige video/imagen a proposito), asi que `m.type ||
// fallback` nunca caia al fallback: un modulo con `background_image` subida
// (tab "Imagen") pero `media.type` congelado en 'color' desde antes de subirla
// mostraba igual el color solido, con la imagen real huerfana en el backend.
// Regla: solo 'video' es una eleccion inequivoca (trae su propia URL); si no
// es video y hay background_image, esa imagen gana sobre el default 'color'.
const media = computed(() => {
  const m = layoutConfig.value.media || {};
  const hasBgImage = !!props.module.background_image;
  const type = m.type === 'video' ? 'video' : (hasBgImage ? 'image' : (m.type || 'color'));
  return {
    type,
    image: m.image || '',
    video_url: m.video_url || '',
    video_url_webm: m.video_url_webm || '',
    poster: m.poster || '',
    loop: m.loop,
    blur: m.blur || 0,
    glass: m.glass || false,
  };
});

// Overlay oscuro para legibilidad -- por defecto activo si hay imagen/video
// (mismo criterio visual que el `.mc-overlay` fijo de ModuleCard.vue), pero
// ahora configurable via layout_config.overlay.
const overlayCfg = computed(() => {
  const o = layoutConfig.value.overlay;
  if (o) {
    return { enabled: o.enabled !== false, color: o.color || '#000000', opacity: o.opacity ?? 45 };
  }
  // Fallback legado: usa resolveModuleOverlayStyle (bg.overlay/overlay_opacity)
  // para no romper modulos configurados antes de esta fase.
  const legacy = resolveModuleOverlayStyle(layoutConfig.value);
  return legacy
    ? { enabled: true, color: '#000000', opacity: (layoutConfig.value.background?.overlay_opacity ?? 45) }
    : { enabled: media.value.type !== 'color', color: '#000000', opacity: 45 };
});

const { el, visible: ownVisible } = useScrollReveal({ threshold: 0.1 });
const revealClass = computed(() => resolveRevealClass(animation.value.type));
const visible = computed(() => ownVisible.value);

const cardStyle = computed(() => ({
  '--mps-accent': props.module.color || '#2563eb',
  transitionDuration: `${animation.value.duration || 600}ms`,
  transitionDelay: `${animation.value.delay || 0}ms`,
}));

// button.style (ButtonsTab.vue): filled (default) / outline / ghost / minimal.
// filled y outline ya funcionaban -- ghost y minimal antes colapsaban en esas
// dos ramas (sin distincion visual real). Ahora las 4 quedan distinguibles:
// outline = borde solido, ghost = sin borde ni fondo (solo texto+icono con
// color de acento), minimal = igual que ghost pero sin el padding de pildora
// (texto inline, mas discreto).
const ctaStyle = computed(() => {
  const style = button.value.style || 'filled';
  const color = button.value.color || '#2563eb';
  if (style === 'outline') {
    return { background: 'transparent', color, border: `1px solid ${color}` };
  }
  if (style === 'ghost') {
    return { background: 'transparent', color, border: 'none' };
  }
  if (style === 'minimal') {
    return { background: 'transparent', color, border: 'none', padding: '0', borderRadius: '0' };
  }
  return { background: color, color: '#fff', border: 'none' };
});
</script>

<style scoped>
.mps-card-root {
  position: relative;
  display: flex;
  border-radius: 20px;
  overflow: hidden;
  min-height: 240px;
  height: 100%;
  cursor: pointer;
  opacity: 0;
  transform: translateY(24px);
  transition-property: opacity, transform, box-shadow;
  transition-timing-function: cubic-bezier(0.16,1,0.3,1);
  box-shadow: 0 2px 14px rgba(15,23,42,.08);
  will-change: transform, opacity;
}
.mps-card-root--visible { opacity: 1; transform: translateY(0); }

/* ── Hover: escala ligera + sombra mas profunda + glow muy suave del acento ── */
.mps-card-root:hover {
  transform: translateY(-6px) scale(1.015);
  box-shadow:
    0 20px 40px rgba(15,23,42,.16),
    0 0 0 1px rgba(255,255,255,.06) inset,
    0 0 32px -8px var(--mps-accent, #2563eb);
}
.mps-card-root--visible:hover { transform: translateY(-6px) scale(1.015); }

/* ── Variantes de reveal (comparten sr-* con ModuleCard/CardItem) ───────────── */
.sr-zoom { transform: scale(0.88); }
.sr-zoom.mps-card-root--visible { transform: scale(1); }
.sr-zoom.mps-card-root--visible:hover { transform: scale(1.015) translateY(-6px); }
.sr-flip { transform: rotateY(30deg); }
.sr-flip.mps-card-root--visible { transform: rotateY(0); }
.sr-rotate { transform: rotate(-5deg) translateY(24px); }
.sr-rotate.mps-card-root--visible { transform: rotate(0) translateY(0); }
.sr-bounce.mps-card-root--visible { animation: mps-bounce 0.7s cubic-bezier(0.34,1.56,0.64,1); }
.sr-parallax { transform: translateY(44px); }
.sr-parallax.mps-card-root--visible { transform: translateY(0); }
@keyframes mps-bounce {
  0%   { transform: translateY(24px); opacity: 0; }
  60%  { transform: translateY(-8px); opacity: 1; }
  100% { transform: translateY(0); }
}

/* ── Badge ──────────────────────────────────────────────────────────────────── */
.mps-badge {
  position: absolute;
  top: 0.85rem;
  right: 0.85rem;
  z-index: 3;
  font-size: 0.66rem;
  font-weight: 700;
  color: #fff;
  padding: 0.22rem 0.65rem;
  border-radius: 999px;
  box-shadow: 0 2px 8px rgba(0,0,0,.2);
}

/* ── Panel de contenido (glass o plano, ver MarketplaceOverlay.vue) ──────────── */
.mps-body-wrap {
  margin-top: auto;
  display: flex;
  align-items: flex-end;
}
.mps-body {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.55rem;
  padding: 1.5rem 1.25rem;
  width: 100%;
}

/* ── Ícono: microinteraccion de hover (escala + rotacion sutil) ──────────────── */
.mps-icon-wrap {
  width: 50px;
  height: 50px;
  border-radius: 15px;
  background: rgba(255,255,255,.16);
  border: 1px solid rgba(255,255,255,.26);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.35s cubic-bezier(0.34,1.56,0.64,1), background 0.25s ease;
}
.mps-card-root:hover .mps-icon-wrap {
  transform: scale(1.12) rotate(-4deg);
  background: rgba(255,255,255,.26);
}
.mps-icon { font-size: 1.3rem; color: #fff; }

.mps-title {
  font-size: 1.02rem;
  font-weight: 700;
  color: #fff;
  margin: 0;
  text-shadow: 0 1px 6px rgba(0,0,0,.35);
  line-height: 1.25;
}
.mps-subtitle { font-size: 0.82rem; font-weight: 500; color: rgba(255,255,255,.88); margin: 0; }
.mps-description { font-size: 0.78rem; color: rgba(255,255,255,.78); margin: 0; line-height: 1.45; }

/* ── CTA: microinteraccion (flecha se desliza a la derecha en hover) ─────────── */
.mps-cta {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  font-weight: 700;
  padding: 0.42rem 0.95rem;
  border-radius: 999px;
  margin-top: 0.3rem;
}
.mps-cta-icon { transition: transform 0.25s cubic-bezier(0.16,1,0.3,1); }
.mps-card-root:hover .mps-cta-icon { transform: translateX(3px); }

/* button.position === 'top' (ButtonsTab.vue) -- reordena dentro del mismo
   flex column, sin duplicar markup ni tocar el resto del layout. */
.mps-cta--top { order: -1; margin-top: 0; margin-bottom: 0.3rem; }

/* ── Responsive ───────────────────────────────────────────────────────────── */
@media (min-width: 992px) {
  .mps-card-root { min-height: 280px; }
}

@media (prefers-reduced-motion: reduce) {
  .mps-card-root, .mps-icon-wrap, .mps-cta-icon { transition: none !important; }
}
</style>
