<template>
  <section v-if="loading || visibleModules.length" class="mps-root">
    <MarketplaceBackground
      v-if="sectionBg.type !== 'none'"
      class="mps-section-bg"
      :type="sectionBg.type"
      :image="sectionBg.image"
      :video-src="sectionBg.videoSrc"
      :video-src-webm="sectionBg.videoSrcWebm"
      :poster="sectionBg.poster"
      :parallax="sectionBg.parallax"
    />

    <div class="mps-inner container-xl">
      <MarketplaceHeader
        :title="headerProps.title"
        :subtitle="headerProps.subtitle"
        :description="headerProps.description"
        :cta-text="headerProps.ctaText"
        :cta-url="headerProps.ctaUrl"
        :cta-target="headerProps.ctaTarget"
      />

      <div v-if="loading" class="mps-skeleton">
        <LoadingSkeleton v-for="n in 4" :key="n" height="260px" radius="20px" />
      </div>

      <template v-else>
        <MarketplaceCarousel
          ref="carouselRef"
          :cards="visibleModules"
          :items-desktop="carouselCfg.items_desktop"
          :items-tablet="carouselCfg.items_tablet"
          :items-mobile="carouselCfg.items_mobile"
          :autoplay="carouselCfg.autoplay"
          :loop="carouselCfg.loop"
          :speed="carouselCfg.speed"
          :pause-on-hover="carouselCfg.pause_on_hover"
          :pause-on-touch="carouselCfg.pause_on_touch"
          :pause-on-focus="carouselCfg.pause_on_focus"
          :show-arrows="carouselCfg.show_arrows"
          @slide-change="activeIndex = $event"
        >
          <template #card="{ card }">
            <MarketplaceCard :module="card" />
          </template>
        </MarketplaceCarousel>

        <MarketplaceIndicators
          v-if="carouselCfg.show_indicators"
          :total="visibleModules.length"
          :active-index="activeIndex"
          @select="onIndicatorSelect"
        />
      </template>
    </div>
  </section>
</template>

<script setup>
/**
 * MarketplaceShowcase — orquestador (reemplaza HomeModulesBelt/ModuleGrid.vue
 * dentro de HomeRenderer.vue). Unicamente orquesta: resuelve la config
 * compartida desde `modules` y conecta Header + Background + Carousel/Card +
 * Indicators. Ninguna logica de scroll/video/parallax vive aqui -- eso ya
 * esta en los componentes hijos (Fases 3-8).
 *
 * Contrato de datos: mismo shape que ya devuelve GET core/home-feed/ para
 * `modules` (key/label/url/icon/color/is_visible/background_image/
 * display_type/layout_config) -- sin cambios de API (Fase 14).
 *
 * Resolucion de config compartida (carousel/header/section_background):
 * se lee del PRIMER modulo visible que traiga esa clave en su
 * layout_config -- mismo patron que ModuleGrid.vue ya usaba para
 * columns/columns_tablet/columns_mobile (ver Fase 1, ModuleGrid.vue:36-44).
 * No es una convencion nueva.
 */
import { ref, computed } from 'vue';
import MarketplaceBackground from './MarketplaceBackground.vue';
import MarketplaceHeader from './MarketplaceHeader.vue';
import MarketplaceCarousel from './MarketplaceCarousel.vue';
import MarketplaceCard from './MarketplaceCard.vue';
import MarketplaceIndicators from './MarketplaceIndicators.vue';
import LoadingSkeleton from '@/components/ui/landing/LoadingSkeleton.vue';

const props = defineProps({
  modules: { type: Array,   default: () => [] },
  loading: { type: Boolean, default: false },
});

const visibleModules = computed(() => props.modules.filter((m) => m.is_visible !== false));

function firstConfig(key) {
  const withCfg = visibleModules.value.find((m) => m.layout_config && m.layout_config[key]);
  return (withCfg?.layout_config || {})[key] || {};
}

const carouselCfg = computed(() => {
  const c = firstConfig('carousel');
  return {
    items_desktop:   c.items_desktop ?? 6,
    items_tablet:    c.items_tablet ?? 3,
    items_mobile:    c.items_mobile ?? 1.2,
    autoplay:        c.autoplay ?? false,
    loop:            c.loop ?? true,
    speed:           c.speed ?? 40,
    pause_on_hover:  c.pause_on_hover !== false,
    pause_on_touch:  c.pause_on_touch !== false,
    pause_on_focus:  c.pause_on_focus !== false,
    show_arrows:     c.show_arrows !== false,
    show_indicators: c.show_indicators !== false,
  };
});

const headerCfg = computed(() => firstConfig('header'));
const headerProps = computed(() => ({
  title:       headerCfg.value.title || '',
  subtitle:    headerCfg.value.subtitle || '',
  description: headerCfg.value.description || '',
  ctaText:     headerCfg.value.cta_text || '',
  ctaUrl:      headerCfg.value.cta_url || '',
  ctaTarget:   headerCfg.value.cta_target || '_self',
}));

const sectionBgCfg = computed(() => firstConfig('section_background'));
const sectionBg = computed(() => ({
  type:          sectionBgCfg.value.type || 'none',
  image:         sectionBgCfg.value.image || '',
  videoSrc:      sectionBgCfg.value.video_url || '',
  videoSrcWebm:  sectionBgCfg.value.video_url_webm || '',
  poster:        sectionBgCfg.value.poster || '',
  parallax:      sectionBgCfg.value.parallax || false,
}));

const carouselRef = ref(null);
const activeIndex = ref(0);
function onIndicatorSelect(i) {
  carouselRef.value?.scrollToIndex(i);
}
</script>

<style scoped>
.mps-root {
  position: relative;
  padding: clamp(2.5rem, 5vw, 4rem) 0;
  overflow: hidden;
}
.mps-section-bg { z-index: 0; }
.mps-inner { position: relative; z-index: 1; }

.mps-skeleton {
  display: flex;
  gap: 1.25rem;
  overflow: hidden;
}
.mps-skeleton > :deep(*) { flex: 0 0 260px; }
</style>
