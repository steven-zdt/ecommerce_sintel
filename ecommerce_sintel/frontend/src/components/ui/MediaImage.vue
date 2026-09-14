<template>
  <div class="mi-wrap" :style="wrapStyle">
    <img
      v-if="resolvedSrc && !hasError"
      :src="resolvedSrc"
      :alt="alt"
      :width="width"
      :height="height"
      loading="lazy"
      decoding="async"
      class="mi-img"
      :class="{ 'mi-img-loaded': isLoaded }"
      @load="onLoad"
      @error="onError"
    >
    <div v-if="resolvedSrc && !hasError && !isLoaded" class="mi-skeleton" aria-hidden="true"></div>
    <div v-if="!resolvedSrc || hasError" class="mi-placeholder" role="img" :aria-label="alt || 'Sin imagen disponible'">
      <slot name="placeholder">
        <i :class="['bi', placeholderIcon]"></i>
      </slot>
    </div>
  </div>
</template>

<script setup>
/**
 * MediaImage.vue -- componente generico de imagen (Auditoria Enterprise de Imagenes, 2026-08-04).
 * Reemplaza el <img>/placeholder manual repetido en cada card de Shop/Renting/Technical Services
 * (BaseHorizontalCard, ItemCard, ServiceCard, bloques "relacionados") -- mismo componente para
 * los 3 modulos en vez de ProductImage/EquipmentImage/ServiceImage triplicados, ya que su
 * necesidad real (lazy+decode, skeleton mientras carga, fallback a placeholder si no hay imagen
 * o si falla la carga, alt siempre presente) es identica en los 3.
 *
 * Acepta la fuente de 2 formas segun el consumidor:
 * - `images` (Array): resuelve la imagen principal via resolvePrimaryImage() (is_primary primero,
 *   si no el primer item). Uso tipico: cards de catalogo con `product.images`/`equipment.images`/
 *   `service.images`.
 * - `src` (String): URL ya resuelta por el backend (ej. `equipment.image_url` en bloques
 *   "relacionados", `item.thumbnail` en Home). Si ambas props vienen, `src` tiene prioridad.
 */
import { ref, computed, watch } from 'vue';
import { resolvePrimaryImage, resolveMediaUrl } from '@/utils/media';

const props = defineProps({
  images: { type: Array, default: () => [] },
  src: { type: String, default: '' },
  alt: { type: String, default: '' },
  placeholderIcon: { type: String, default: 'bi-image' },
  placeholderBg: { type: String, default: '#f8fafc' },
  placeholderColor: { type: String, default: '#94a3b8' },
  imageFit: { type: String, default: 'cover' }, // 'cover' | 'contain'
  width: { type: [Number, String], default: null },
  height: { type: [Number, String], default: null },
});

const hasError = ref(false);
const isLoaded = ref(false);

const resolvedSrc = computed(() => resolveMediaUrl(props.src) || resolvePrimaryImage(props.images));

// Si el componente se reutiliza para otro item (mismo nodo, v-for con :key estable pero fuente
// distinta) el estado de error/carga previo no debe sobrevivir a la nueva imagen.
watch(resolvedSrc, () => {
  hasError.value = false;
  isLoaded.value = false;
});

function onLoad() {
  isLoaded.value = true;
}
function onError() {
  // Fase 9: nunca romper la card -- cae al placeholder en vez de mostrar el icono
  // de imagen rota nativo del navegador (gap presente en el 100% de las cards antes de esto).
  hasError.value = true;
}

const wrapStyle = computed(() => ({
  '--mi-bg': props.placeholderBg,
  '--mi-color': props.placeholderColor,
  '--mi-fit': props.imageFit,
}));
</script>

<style scoped>
.mi-wrap {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
  background: var(--mi-bg);
}

.mi-img {
  width: 100%;
  height: 100%;
  object-fit: var(--mi-fit);
  display: block;
  opacity: 0;
  transition: opacity .25s ease;
}
.mi-img-loaded { opacity: 1; }

.mi-skeleton {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 50%, #f1f5f9 75%);
  background-size: 200% 100%;
  animation: mi-shimmer 1.4s ease-in-out infinite;
}

.mi-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--mi-color);
  font-size: 2rem;
}

@keyframes mi-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

@media (prefers-reduced-motion: reduce) {
  .mi-img { transition: none; }
  .mi-skeleton { animation: none; }
}
</style>
