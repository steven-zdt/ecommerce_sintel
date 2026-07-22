<template>
  <section v-if="loading || items.length" class="fs-root">
    <!-- Header con eyebrow, título y "Ver todos" -->
    <div class="fs-header">
      <div class="fs-header-left">
        <div class="fs-type-dot" :style="`background: ${typeColor}`"></div>
        <div>
          <p v-if="eyebrow" class="fs-eyebrow">{{ eyebrow }}</p>
          <h2 class="fs-title" v-html="renderedTitle"></h2>
        </div>
      </div>
      <RouterLink :to="link" class="fs-link">
        {{ linkLabel || 'Ver todos' }}
        <i class="bi bi-arrow-right ms-1"></i>
      </RouterLink>
    </div>

    <!-- Carousel / Grid -->
    <FeaturedCarousel :items="items" :type="type" :loading="loading" />
  </section>
</template>

<script setup>
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import FeaturedCarousel from './FeaturedCarousel.vue';

const props = defineProps({
  eyebrow:   { type: String,  default: '' },
  title:     { type: String,  required: true },
  link:      { type: String,  default: '/' },
  linkLabel: { type: String,  default: 'Ver todos' },
  items:     { type: Array,   default: () => [] },
  type:      { type: String,  default: 'product' },
  loading:   { type: Boolean, default: false },
});

const renderedTitle = computed(() =>
  props.title.replace(/\*(.*?)\*/g, '<em>$1</em>')
);

const typeColor = computed(() => ({
  product: '#2563eb',
  rental:  '#0ea5e9',
  service: '#8b5cf6',
}[props.type] ?? '#2563eb'));
</script>

<style scoped>
.fs-root { width: 100%; }

/* ── Header ─────────────────────────────────────────────────────────────────── */
.fs-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
  gap: 0.5rem;
}
.fs-header-left {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.fs-type-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 0 3px rgba(37,99,235,.15);
}

.fs-eyebrow {
  font-size: 0.65rem;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #64748b;
  margin: 0 0 0.1rem;
}
.fs-title {
  font-size: clamp(1.15rem, 2.2vw, 1.5rem);
  font-weight: 700;
  color: #0f172a;
  margin: 0;
  line-height: 1.2;
}

.fs-link {
  font-size: 0.82rem;
  font-weight: 600;
  color: #2563eb;
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  white-space: nowrap;
  transition: gap 0.15s, opacity 0.15s;
}
.fs-link:hover { text-decoration: underline; }
.fs-title :deep(em) {
  font-style: normal;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
</style>
