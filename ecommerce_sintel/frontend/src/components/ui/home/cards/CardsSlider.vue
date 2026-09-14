<template>
  <div class="cs-root">
    <MarketplaceCarousel
      ref="carouselRef"
      :cards="visibleCards"
      :items-desktop="columns"
      :items-tablet="columnsTablet"
      :items-mobile="columnsMobile"
      :gap="gap"
      :autoplay="autoplay"
      :loop="loop"
      :speed="speed"
      :show-arrows="showArrows"
      @slide-change="activeIndex = $event"
    >
      <template #card="{ card }">
        <CardItem :card="card" :visible="true" />
      </template>
    </MarketplaceCarousel>

    <MarketplaceIndicators
      v-if="showIndicators"
      :total="visibleCards.length"
      :active-index="activeIndex"
      @select="onIndicatorSelect"
    />
  </div>
</template>

<script setup>
/**
 * CardsSlider — reutiliza MarketplaceCarousel.vue/MarketplaceIndicators.vue (el
 * mismo carrusel ya probado en MarketplaceShowcase.vue para Modulos) en vez de un
 * tercer carrusel dedicado a Card Group. Mismo wiring exacto (carouselRef,
 * activeIndex, scrollToIndex, evento slide-change) -- ver
 * MarketplaceShowcase.vue para la referencia.
 *
 * Mantiene el nombre de componente y el layout_type='slider' -> CardsSlider ya
 * mapeado en useLayoutEngine.js (GROUP_LAYOUTS): cero cambio de contrato con
 * SectionRenderer.vue.
 */
import { ref, computed } from 'vue';
import CardItem from './CardItem.vue';
import MarketplaceCarousel from '@/components/ui/showcase/MarketplaceCarousel.vue';
import MarketplaceIndicators from '@/components/ui/showcase/MarketplaceIndicators.vue';

const props = defineProps({
  cards: { type: Array, default: () => [] },
  // Config de carrusel -- viene de HomeCardGroup (ver SectionRenderer.vue).
  group: { type: Object, default: () => ({}) },
});

const visibleCards = computed(() => props.cards.filter(c => c.is_active !== false));

const columns       = computed(() => props.group.columns || 3);
const columnsTablet = computed(() => props.group.columns_tablet || 2);
const columnsMobile = computed(() => props.group.columns_mobile || 1.2);
const gap           = computed(() => Number(props.group.gap ?? 1.25));
const autoplay      = computed(() => props.group.carousel_autoplay || false);
const loop          = computed(() => props.group.carousel_loop !== false);
const speed          = computed(() => props.group.carousel_speed || 40);
const showArrows     = computed(() => props.group.show_arrows !== false);
const showIndicators = computed(() => props.group.show_indicators !== false);

const carouselRef = ref(null);
const activeIndex = ref(0);
function onIndicatorSelect(i) {
  carouselRef.value?.scrollToIndex(i);
}
</script>

<style scoped>
.cs-root { position: relative; }
</style>
