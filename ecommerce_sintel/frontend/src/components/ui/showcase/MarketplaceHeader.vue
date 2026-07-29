<template>
  <div v-if="hasContent" class="mps-head" :style="{ textAlign }">
    <p v-if="subtitle" class="mps-head-eyebrow" :style="{ color: accentColor }">{{ subtitle }}</p>
    <h2 v-if="title" class="mps-head-title" :style="{ color: colorText }">{{ title }}</h2>
    <p v-if="description" class="mps-head-desc" :style="{ color: colorText }">{{ description }}</p>

    <RouterLink v-if="ctaText && ctaUrl" :to="isExternalCta ? '/' : ctaUrl" custom v-slot="{ navigate, href }">
      <a
        :href="isExternalCta ? ctaUrl : href"
        :target="ctaTarget !== '_self' ? ctaTarget : undefined"
        :rel="ctaTarget === '_blank' ? 'noopener noreferrer' : undefined"
        class="mps-head-cta"
        @click="onCtaClick($event, isExternalCta ? undefined : navigate)"
      >
        {{ ctaText }}
        <i class="bi bi-arrow-right mps-head-cta-icon"></i>
      </a>
    </RouterLink>
  </div>
</template>

<script setup>
/**
 * MarketplaceHeader — encabezado editorial de la seccion (Fase 6).
 * Todo el contenido llega por props, editable desde el Home Builder
 * (layout_config.header del primer modulo visible -- ver contrato de Fase 2
 * §2.3). Sin contenido configurado, no renderiza nada (hasContent).
 */
import { computed } from 'vue';
import { RouterLink } from 'vue-router';

const props = defineProps({
  title:       { type: String, default: '' },
  subtitle:    { type: String, default: '' },
  description: { type: String, default: '' },
  ctaText:     { type: String, default: '' },
  ctaUrl:      { type: String, default: '' },
  ctaTarget:   { type: String, default: '_self' },
  textAlign:   { type: String, default: 'center' },
  colorText:   { type: String, default: '#0a0f1e' },
  accentColor: { type: String, default: '#2563eb' },
});

const emit = defineEmits(['cta-click']);

const hasContent = computed(() =>
  !!(props.title || props.subtitle || props.description || (props.ctaText && props.ctaUrl))
);
const isExternalCta = computed(() => /^https?:\/\//.test(props.ctaUrl || ''));

function onCtaClick(e, navigate) {
  emit('cta-click');
  navigate?.(e);
}
</script>

<style scoped>
.mps-head {
  max-width: 720px;
  margin: 0 auto clamp(2rem, 4vw, 3rem);
  padding: 0 1rem;
}
.mps-head-eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.78rem;
  font-weight: 700;
  margin-bottom: 0.6rem;
}
.mps-head-title {
  font-size: clamp(1.6rem, 3.4vw, 2.5rem);
  font-weight: 800;
  line-height: 1.15;
  margin-bottom: 0.85rem;
}
.mps-head-desc {
  font-size: 1rem;
  opacity: 0.72;
  line-height: 1.65;
  margin-bottom: 1.4rem;
}
.mps-head-cta {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.88rem;
  font-weight: 700;
  color: #0a0f1e;
  text-decoration: none;
  padding: 0.6rem 1.3rem;
  border-radius: 999px;
  border: 1px solid rgba(10,15,30,.14);
  transition: transform 220ms cubic-bezier(0.16,1,0.3,1), border-color 220ms ease, background 220ms ease;
}
.mps-head-cta:hover {
  transform: translateY(-2px);
  border-color: rgba(10,15,30,.28);
  background: rgba(10,15,30,.03);
}
.mps-head-cta-icon { transition: transform 220ms cubic-bezier(0.16,1,0.3,1); }
.mps-head-cta:hover .mps-head-cta-icon { transform: translateX(3px); }

@media (prefers-reduced-motion: reduce) {
  .mps-head-cta, .mps-head-cta-icon { transition: none !important; }
}
</style>
