<template>
  <section
    v-if="visibleCards.length"
    class="sr-section"
    :class="`sr-hover--${group.hover || 'lift'}`"
    :style="sectionStyle"
  >
    <div class="container-xl">
      <!-- Encabezado de sección -->
      <div v-if="group.title || group.subtitle" class="sr-header">
        <p v-if="group.subtitle" class="sr-eyebrow">{{ group.subtitle }}</p>
        <h2 class="sr-title">{{ group.title }}</h2>
        <p v-if="group.description" class="sr-desc">{{ group.description }}</p>
      </div>

      <!-- Layout dinámico -->
      <component
        :is="layoutComponent"
        :cards="visibleCards"
        :columns="group.columns || 3"
      />
    </div>

    <!-- Divider -->
    <div v-if="group.divider" class="sr-divider"></div>
  </section>
</template>

<script setup>
import { computed, defineAsyncComponent } from 'vue';
import { useLayoutEngine } from '@/composables/useLayoutEngine';

// Nombres resueltos por useLayoutEngine().resolveGroupLayout() -- unica fuente
// de verdad del mapeo layout_type -> componente (ver GROUP_LAYOUTS).
const COMPONENT_MAP = {
  CardsGrid:        defineAsyncComponent(() => import('@/components/ui/home/cards/CardsGrid.vue')),
  CardsSlider:      defineAsyncComponent(() => import('@/components/ui/home/cards/CardsSlider.vue')),
  TimelineSection:  defineAsyncComponent(() => import('@/components/ui/home/sections/TimelineSection.vue')),
  AccordionSection: defineAsyncComponent(() => import('@/components/ui/home/sections/AccordionSection.vue')),
  TabsSection:      defineAsyncComponent(() => import('@/components/ui/home/sections/TabsSection.vue')),
  LogoStrip:        defineAsyncComponent(() => import('@/components/ui/home/cards/LogoStrip.vue')),
  MarqueeStrip:     defineAsyncComponent(() => import('@/components/ui/home/cards/MarqueeStrip.vue')),
};

const props = defineProps({
  group: { type: Object, required: true },
  cards: { type: Array, default: () => [] },
});

const { buildSectionStyle, resolveGroupLayout } = useLayoutEngine();

const visibleCards = computed(() =>
  props.cards.filter(c => c.is_active !== false && c.group_name === props.group.name)
);

const layoutComponent = computed(() => COMPONENT_MAP[resolveGroupLayout(props.group)] || COMPONENT_MAP.CardsGrid);

const sectionStyle = computed(() => buildSectionStyle(props.group));
</script>

<style scoped>
.sr-section {
  padding: clamp(3rem, 5vw, 5rem) 0;
  width: 100%;
}
.sr-header { text-align: center; margin-bottom: 2.5rem; }
.sr-eyebrow {
  text-transform: uppercase; letter-spacing: .1em;
  font-size: .75rem; font-weight: 700;
  color: #2563eb; margin-bottom: .5rem;
}
.sr-title { font-size: clamp(1.5rem, 3vw, 2.2rem); font-weight: 800; color: #0f172a; margin-bottom: .75rem; }
.sr-desc { color: #64748b; max-width: 560px; margin: 0 auto; font-size: .95rem; line-height: 1.7; }
.sr-divider {
  width: 80%; margin: 2rem auto 0;
  height: 1px; background: linear-gradient(90deg, transparent, #e2e8f0, transparent);
}

/* ── Variantes de hover del grupo (group.hover) ──────────────────────────────── */
/* 'lift' es el comportamiento por defecto de CardItem/ModuleCard, sin override. */
.sr-hover--scale :deep(.ci-root--clickable:hover) { transform: scale(1.04) !important; }
.sr-hover--glow :deep(.ci-root--clickable:hover) {
  transform: none !important;
  box-shadow: 0 0 24px rgba(37,99,235,.35) !important;
}
.sr-hover--none :deep(.ci-root--clickable:hover) { transform: none !important; box-shadow: inherit !important; }
</style>
