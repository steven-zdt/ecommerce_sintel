<template>
  <template v-for="section in visibleSections" :key="section.uuid">
    <section
      v-if="section.blocks.length"
      :class="['fb-section', `fb-section--${section.theme}`]"
      :style="sectionStyle(section)"
    >
      <div v-if="section.background_type === 'image' && section.background_image" class="fb-section__bg">
        <img :src="section.background_image" alt="" loading="lazy">
      </div>
      <div v-if="section.overlay_enabled" class="fb-section__overlay" :style="{ opacity: (section.overlay_opacity ?? 45) / 100 }"></div>

      <div class="fb-section__inner container-xl">
        <div v-if="section.title || section.subtitle || section.description" class="fb-section__header">
          <p v-if="section.subtitle" class="fb-section__eyebrow">{{ section.subtitle }}</p>
          <h2 v-if="section.title" class="fb-section__title">{{ section.title }}</h2>
          <p v-if="section.description" class="fb-section__desc">{{ section.description }}</p>
        </div>

        <FeatureBannerBlock v-for="block in section.blocks" :key="block.uuid" :block="block" />
      </div>
    </section>
  </template>
</template>

<script setup>
/**
 * FeatureBannerRenderer — orquestador de secciones "Feature Banner" (mismo rol
 * que MarketplaceShowcase.vue para Modulos). El filtrado de visibilidad real
 * ya ocurre en el backend (FeatureBannerSectionSelector.list_active_with_blocks(),
 * a diferencia de HomeFeedSelector.get_module_configs()) -- este componente
 * solo aplica un filtro defensivo adicional por si el caller (preview del
 * builder) pasa el estado completo sin filtrar.
 */
import { computed } from 'vue';
import FeatureBannerBlock from './FeatureBannerBlock.vue';

const props = defineProps({
  sections: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
});

const visibleSections = computed(() =>
  props.sections
    .filter((s) => s.is_visible !== false)
    .map((s) => ({ ...s, blocks: (s.blocks || []).filter((b) => b.is_active !== false) }))
);

function sectionStyle(section) {
  if (section.background_type === 'gradient') {
    return { background: `linear-gradient(135deg, ${section.background_gradient_from || '#0f172a'}, ${section.background_gradient_to || '#1e3a8a'})` };
  }
  if (section.background_type === 'color' && section.background_color) {
    return { background: section.background_color };
  }
  return {};
}
</script>

<style scoped>
.fb-section {
  position: relative;
  overflow: hidden;
}
.fb-section__bg { position: absolute; inset: 0; z-index: 0; }
.fb-section__bg img { width: 100%; height: 100%; object-fit: cover; }
.fb-section__overlay { position: absolute; inset: 0; background: #000; z-index: 1; }
.fb-section__inner { position: relative; z-index: 2; padding: clamp(2.5rem, 5vw, 4rem) 0; }

.fb-section__header { max-width: 640px; margin: 0 auto clamp(1.5rem, 3vw, 2.5rem); text-align: center; }
.fb-section__eyebrow { font-size: .75rem; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; color: var(--fb-accent, #2563eb); margin: 0 0 .4rem; }
.fb-section__title { font-size: clamp(1.6rem, 3.5vw, 2.4rem); font-weight: 800; margin: 0 0 .6rem; color: var(--fb-text, #0f172a); }
.fb-section__desc { color: var(--fb-text-muted, #64748b); margin: 0; }

/* ── Padding por seccion (HomeCardGroup.PADDING_CHOICES, mismos valores) ──── */
.fb-section { padding-block: 0; }

/* ── Temas: 5 combinaciones predefinidas de color de texto/acento ─────────── */
.fb-section--light  { --fb-text: #0f172a; --fb-text-muted: #64748b; --fb-accent: #2563eb; --fb-media-placeholder: #e2e8f0; }
.fb-section--dark    { --fb-text: #f8fafc; --fb-text-muted: #94a3b8; --fb-accent: #60a5fa; --fb-media-placeholder: #1e293b; background-color: #0f172a; }
.fb-section--corporate { --fb-text: #0f172a; --fb-text-muted: #475569; --fb-accent: #0f172a; --fb-media-placeholder: #e2e8f0; }
.fb-section--minimal { --fb-text: #18181b; --fb-text-muted: #71717a; --fb-accent: #18181b; --fb-media-placeholder: #f4f4f5; }
.fb-section--glass   { --fb-text: #f8fafc; --fb-text-muted: #cbd5e1; --fb-accent: #93c5fd; --fb-media-placeholder: rgba(255,255,255,.08); }
</style>
