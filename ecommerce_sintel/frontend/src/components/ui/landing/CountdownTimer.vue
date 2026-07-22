<template>
  <div class="ct-root" :class="{ 'ct-urgent': remaining < 3600 && remaining > 0 }">
    <svg class="ct-icon" width="12" height="12" viewBox="0 0 24 24" fill="none">
      <circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2"/>
      <path d="M12 6v6l4 2" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
    </svg>
    <span class="ct-time">{{ formatted }}</span>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue';

const props = defineProps({
  secondsRemaining: { type: Number, default: 0 },
});

const remaining = ref(props.secondsRemaining);
let timer = null;

onMounted(() => {
  if (remaining.value > 0) {
    timer = setInterval(() => {
      remaining.value = Math.max(0, remaining.value - 1);
    }, 1000);
  }
});
onUnmounted(() => { if (timer) clearInterval(timer); });

const formatted = computed(() => {
  const s = remaining.value;
  if (s <= 0) return 'Expirado';
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const sec = s % 60;
  if (h >= 24) {
    const d = Math.floor(h / 24);
    return `${d}d ${h % 24}h`;
  }
  return [h, m, sec].map(n => String(n).padStart(2, '0')).join(':');
});
</script>

<style scoped>
.ct-root {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.78rem;
  font-weight: 600;
  color: #94a3b8;
  background: rgba(255,255,255,.06);
  border-radius: 6px;
  padding: 0.2rem 0.5rem;
  transition: color 0.3s, background 0.3s;
}
.ct-urgent {
  color: #f87171;
  background: rgba(248,113,113,.12);
}
.ct-icon { flex-shrink: 0; }
.ct-time { font-variant-numeric: tabular-nums; }
</style>
