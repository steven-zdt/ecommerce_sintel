<template>
  <div class="acc-skeleton" :class="{ 'acc-skeleton--grid': layout === 'grid' }">
    <LoadingSkeleton
      v-for="n in count"
      :key="n"
      :height="height"
      radius="14px"
      width="100%"
    />
  </div>
</template>

<script setup>
import LoadingSkeleton from '@/components/ui/landing/LoadingSkeleton.vue';

/**
 * Wrapper de "Mi Cuenta" sobre el unico skeleton real del proyecto
 * (components/ui/landing/LoadingSkeleton.vue) -- reemplaza las 6 copias de
 * `.skeleton`/`@keyframes shimmer` que existian por archivo.
 */
defineProps({
  count: { type: Number, default: 3 },
  height: { type: String, default: '110px' },
  layout: { type: String, default: 'list' }, // 'list' | 'grid'
});
</script>

<style scoped>
.acc-skeleton {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.acc-skeleton--grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}
</style>
