<template>
  <div ref="el" class="ac-root">
    <span class="ac-value">{{ prefix }}{{ isNumeric ? displayValue : rawText }}{{ suffix || textSuffix }}</span>
    <span class="ac-label">{{ label }}</span>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';

const props = defineProps({
  // Numero puro (uso historico, calculado en frontend) o texto libre editado
  // por el admin en el Constructor Visual (ej. "+500", "24/7") -- en ese caso
  // se anima solo la parte numerica y se conserva el resto tal cual se escribio.
  value:  { type: [Number, String], required: true },
  label:  { type: String, default: '' },
  suffix: { type: String, default: '' },
});

const el = ref(null);
const displayValue = ref(0);

const parsed = computed(() => {
  if (typeof props.value === 'number') {
    return { prefix: '', target: props.value, textSuffix: '', isNumeric: true, rawText: '' };
  }
  const match = String(props.value).match(/^([+-]?)(\d[\d.,]*)(.*)$/);
  if (!match) {
    return { prefix: '', target: 0, textSuffix: '', isNumeric: false, rawText: String(props.value) };
  }
  const [, sign, digits, rest] = match;
  return { prefix: sign, target: Number(digits.replace(/[.,]/g, '')), textSuffix: rest, isNumeric: true, rawText: '' };
});

const prefix     = computed(() => parsed.value.prefix);
const textSuffix = computed(() => parsed.value.textSuffix);
const isNumeric  = computed(() => parsed.value.isNumeric);
const rawText    = computed(() => parsed.value.rawText);

function easeOutExpo(t) {
  return t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
}

function animateCount(target, duration = 1600) {
  const start = performance.now();
  function step(now) {
    const elapsed = now - start;
    const progress = Math.min(elapsed / duration, 1);
    displayValue.value = Math.round(easeOutExpo(progress) * target);
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

onMounted(() => {
  const obs = new IntersectionObserver(
    ([e]) => {
      if (e.isIntersecting) {
        if (isNumeric.value) animateCount(parsed.value.target);
        obs.disconnect();
      }
    },
    { threshold: 0.4 }
  );
  if (el.value) obs.observe(el.value);
});
</script>

<style scoped>
.ac-root {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.25rem;
  padding: 1rem 1.5rem;
}
.ac-value {
  font-size: clamp(1.75rem, 3.5vw, 2.75rem);
  font-weight: 800;
  color: #0a0f1e;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  background: linear-gradient(135deg, #2563eb, #06b6d4);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.ac-label {
  font-size: 0.8rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.8px;
}
</style>
