<template>
  <div v-if="items.length" class="pkg-included-grid">
    <article v-for="item in items" :key="item.uuid" class="pkg-included-card">
      <IconRenderer :icon="item.icon" fallback="bi-check-circle" extra-class="pkg-included-icon" />
      <div>
        <strong>{{ item.title }}</strong>
        <p v-if="item.description">{{ item.description }}</p>
      </div>
    </article>
  </div>
</template>

<script setup>
import IconRenderer from '@/components/ui/IconRenderer.vue';

defineProps({
  items: { type: Array, default: () => [] },
});
</script>

<style scoped>
.pkg-included-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: .65rem;
}
.pkg-included-card {
  display: flex; gap: .55rem; align-items: flex-start;
  background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 12px; padding: .75rem;
}
.pkg-included-icon { color: #16a34a; font-size: 1.1rem; margin-top: .1rem; flex-shrink: 0; }
.pkg-included-card strong { display: block; color: #14532d; font-size: .84rem; }
.pkg-included-card p { color: #4d7c5f; font-size: .76rem; margin: .15rem 0 0; }
</style>
