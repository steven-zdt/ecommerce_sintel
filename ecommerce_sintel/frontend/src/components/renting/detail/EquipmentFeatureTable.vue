<template>
  <div v-if="features.length" class="eq-feature-grid">
    <article v-for="feature in features" :key="feature.uuid" class="eq-feature-card">
      <IconRenderer v-if="feature.icon" :icon="feature.icon" extra-class="eq-feature-icon" />
      <div>
        <strong>{{ feature.title }}</strong>
        <span v-if="feature.value">{{ feature.value }}</span>
      </div>
    </article>
  </div>
</template>

<script setup>
import IconRenderer from '@/components/ui/IconRenderer.vue';

defineProps({
  features: { type: Array, default: () => [] },
});
</script>

<style scoped>
.eq-feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: .75rem;
}
.eq-feature-card {
  display: flex; align-items: center; gap: .6rem;
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px;
  padding: .85rem;
}
.eq-feature-icon { color: #2563eb; font-size: 1.3rem; flex-shrink: 0; }
.eq-feature-card strong { display: block; color: #0f172a; font-size: .84rem; font-weight: 800; }
.eq-feature-card span { display: block; color: #64748b; font-size: .8rem; margin-top: .1rem; }
</style>
