<template>
  <div class="mpo-root" :class="{ 'mpo-root--glass': glass }" :style="rootStyle">
    <slot />
  </div>
</template>

<script setup>
/**
 * MarketplaceOverlay — panel de contenido superpuesto (Fase 5).
 *
 * Dos modos:
 *  - glass=true:  glassmorphism real (backdrop-filter blur+saturate sobre
 *    un tinte translucido del color de acento) -- el panel premium de
 *    contenido que flota sobre MarketplaceBackground.
 *  - glass=false + opacity>0: tinte solido plano (equivalente al overlay
 *    fijo que ya usaba ModuleCard.vue para legibilidad de texto sobre imagen).
 */
import { computed } from 'vue';

const props = defineProps({
  color:   { type: String,  default: '#000000' },
  opacity: { type: Number,  default: 0 },   // 0-100, tinte solido cuando glass=false
  glass:   { type: Boolean, default: false },
  blur:    { type: Number,  default: 14 },  // px, backdrop-filter cuando glass=true
});

function hexToRgba(hex, alpha) {
  const h = String(hex || '#000000').replace('#', '');
  const full = h.length === 3 ? h.split('').map((c) => c + c).join('') : h;
  const int = parseInt(full, 16) || 0;
  const r = (int >> 16) & 255, g = (int >> 8) & 255, b = int & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

const rootStyle = computed(() => {
  if (props.glass) {
    return {
      background: hexToRgba(props.color, 0.14),
      backdropFilter: `blur(${props.blur}px) saturate(160%)`,
      WebkitBackdropFilter: `blur(${props.blur}px) saturate(160%)`,
    };
  }
  if (props.opacity > 0) {
    return { background: hexToRgba(props.color, Math.min(props.opacity, 100) / 100) };
  }
  return {};
});
</script>

<style scoped>
.mpo-root {
  position: relative;
  z-index: 2;
  width: 100%;
  height: 100%;
}
.mpo-root--glass {
  border: 1px solid rgba(255,255,255,.16);
}
</style>
