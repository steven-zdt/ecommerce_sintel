<template>
  <i :class="resolvedClass" :style="sizeStyle"></i>
</template>

<script setup>
/**
 * Renderiza un icono de Bootstrap Icons (unica libreria instalada en el
 * proyecto) validando si la clase existe antes de pintarla. Bootstrap Icons
 * es CSS puro (el glifo viaja en el `content` del pseudo-elemento `::before`,
 * sin registro JS), asi que la unica forma de saber si una clase `bi-*` es
 * real es medirla en el DOM -- no hay lista propia que mantener, y detecta
 * automaticamente `icon_class` guardados en BD con nombres invalidos/viejos.
 */
import { ref, computed, watchEffect } from 'vue';

const props = defineProps({
  icon:       { type: String, default: '' },
  fallback:   { type: String, default: 'bi-question-circle' },
  extraClass: { type: String, default: '' },
  size:       { type: String, default: '' },
});

const validityCache = new Map();

function normalizeIconClass(value) {
  if (!value) return '';
  return value.split(' ').find((c) => c.startsWith('bi-')) || '';
}

function iconClassExists(iconClass) {
  if (!iconClass) return false;
  if (validityCache.has(iconClass)) return validityCache.get(iconClass);
  const probe = document.createElement('i');
  probe.className = `bi ${iconClass}`;
  probe.style.cssText = 'position:absolute;visibility:hidden;pointer-events:none;';
  document.body.appendChild(probe);
  const content = window.getComputedStyle(probe, '::before').content;
  document.body.removeChild(probe);
  const exists = !!content && content !== 'none' && content !== '""';
  validityCache.set(iconClass, exists);
  return exists;
}

const activeIconClass = ref(props.fallback);

watchEffect(() => {
  const normalized = normalizeIconClass(props.icon);
  activeIconClass.value = iconClassExists(normalized) ? normalized : props.fallback;
});

const resolvedClass = computed(() => ['bi', activeIconClass.value, props.extraClass]);
const sizeStyle = computed(() => (props.size ? { fontSize: props.size } : {}));
</script>
