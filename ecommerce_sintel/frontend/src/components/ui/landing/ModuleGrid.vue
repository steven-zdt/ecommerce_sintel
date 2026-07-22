<template>
  <section v-if="loading || visibleModules.length" class="mg-root">
    <!-- Skeleton -->
    <div v-if="loading" class="mg-grid" :style="gridStyle">
      <LoadingSkeleton v-for="n in 4" :key="n" height="220px" radius="18px" />
    </div>

    <!-- Cards -->
    <div v-else class="mg-grid" :style="gridStyle">
      <ModuleCard
        v-for="m in visibleModules"
        :key="m.key"
        :module="m"
      />
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue';
import ModuleCard from './ModuleCard.vue';
import LoadingSkeleton from './LoadingSkeleton.vue';

const props = defineProps({
  modules: { type: Array,   default: () => [] },
  loading: { type: Boolean, default: false },
});

const visibleModules = computed(() =>
  props.modules.filter(m => m.is_visible !== false)
);

// Toma columns/columns_tablet/columns_mobile del primer modulo que los
// configuro via el Constructor Visual; si ninguno lo hizo, usa el default
// premium (4 / 2 / 1) en vez del belt fijo de iconos de 140px.
const columnsConfig = computed(() => {
  const withConfig = props.modules.find(m => m.layout_config && m.layout_config.columns);
  const lc = withConfig?.layout_config || {};
  return {
    desktop: lc.columns || 4,
    tablet: lc.columns_tablet || 2,
    mobile: lc.columns_mobile || 1,
  };
});

const gridStyle = computed(() => ({
  '--mg-cols-mobile': columnsConfig.value.mobile,
  '--mg-cols-tablet': columnsConfig.value.tablet,
  '--mg-cols-desktop': columnsConfig.value.desktop,
}));
</script>

<style scoped>
.mg-root { width: 100%; }

/* ── Grid ───────────────────────────────────────────────────────────────────── */
.mg-grid {
  display: grid;
  grid-template-columns: repeat(var(--mg-cols-mobile, 1), 1fr);
  gap: 1.25rem;
}

/* ── Responsive ─────────────────────────────────────────────────────────────── */
@media (min-width: 576px) {
  .mg-grid { grid-template-columns: repeat(var(--mg-cols-tablet, 2), 1fr); }
}
@media (min-width: 992px) {
  .mg-grid { grid-template-columns: repeat(var(--mg-cols-desktop, 4), 1fr); }
}
</style>
