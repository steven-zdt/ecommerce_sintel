<template>
  <div
    ref="el"
    class="sh-root"
    :class="[`sh-${align}`, { 'sh-dark': dark, 'sh-visible': visible }]"
  >
    <span v-if="eyebrow" class="sh-eyebrow">{{ eyebrow }}</span>
    <h2 class="sh-title" v-html="renderedTitle"></h2>
    <p v-if="subtitle" class="sh-subtitle">{{ subtitle }}</p>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useScrollReveal } from '@/composables/useScrollReveal';

const props = defineProps({
  eyebrow:  { type: String,  default: '' },
  title:    { type: String,  required: true },
  subtitle: { type: String,  default: '' },
  align:    { type: String,  default: 'left' },
  dark:     { type: Boolean, default: false },
});

const renderedTitle = computed(() =>
  props.title.replace(/\*(.*?)\*/g, '<em>$1</em>')
);

const { el, visible } = useScrollReveal({ threshold: 0.15 });
</script>

<style scoped>
.sh-root {
  margin-bottom: 2rem;
  opacity: 0;
  transform: translateY(20px);
  transition: opacity 0.6s ease,
              transform 0.6s cubic-bezier(0.16,1,0.3,1);
}
.sh-root.sh-visible {
  opacity: 1;
  transform: translateY(0);
}
.sh-center { text-align: center; }
.sh-left   { text-align: left; }

.sh-eyebrow {
  display: inline-flex;
  align-items: center;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: #2563eb;
  background: rgba(37,99,235,.09);
  border: 1px solid rgba(37,99,235,.18);
  border-radius: 9999px;
  padding: 0.25rem 0.85rem;
  margin-bottom: 0.75rem;
}
.sh-dark .sh-eyebrow {
  color: #7dd3fc;
  background: rgba(125,211,252,.1);
  border-color: rgba(125,211,252,.22);
}

.sh-title {
  font-size: clamp(1.75rem, 3.5vw, 2.75rem);
  font-weight: 700;
  line-height: 1.2;
  color: #0a0f1e;
  margin: 0 0 0.6rem;
}
.sh-dark .sh-title { color: #f1f5f9; }

.sh-title :deep(em) {
  font-style: normal;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.sh-subtitle {
  font-size: 1rem;
  color: #475569;
  line-height: 1.65;
  margin: 0;
  max-width: 560px;
}
.sh-dark .sh-subtitle { color: rgba(255,255,255,.55); }
.sh-center .sh-subtitle { margin: 0 auto; }
</style>
