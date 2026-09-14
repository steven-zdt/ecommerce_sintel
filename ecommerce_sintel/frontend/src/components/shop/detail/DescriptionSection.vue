<template>
  <div>
    <p :class="['dsx-text', { 'dsx-clamped': clamped }]" style="white-space:pre-wrap">{{ text }}</p>
    <button v-if="isLong" type="button" class="dsx-toggle" @click="expanded = !expanded">
      {{ expanded ? 'Leer menos' : 'Leer mas' }}
      <i :class="['bi', expanded ? 'bi-chevron-up' : 'bi-chevron-down']"></i>
    </button>
  </div>
</template>

<script setup>
/**
 * DescriptionSection.vue -- bloque de texto colapsable, reusado 3 veces en
 * ShopDetailContent.vue (Descripcion general / Alcance / Garantia -- Fase 4,
 * reingenieria PDP 2026-08-05). Resuelve el hallazgo de la Fase 1 (auditoria):
 * la descripcion no tenia limite de longitud ni colapso.
 *
 * Solo maneja el texto -- el wrapper .detail-section/.section-head lo pone el
 * padre (mismo markup que el resto de secciones de la PDP), para no duplicar
 * ese CSS aqui.
 */
import { ref, computed } from 'vue';

const props = defineProps({
  text: { type: String, default: '' },
  maxLength: { type: Number, default: 600 },
});

const expanded = ref(false);
const isLong = computed(() => (props.text || '').length > props.maxLength);
const clamped = computed(() => isLong.value && !expanded.value);
</script>

<style scoped>
.dsx-text {
  font-size: .92rem;
  line-height: 1.75;
  color: #374151;
  margin: 0;
}
.dsx-clamped {
  display: -webkit-box;
  -webkit-line-clamp: 6;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.dsx-toggle {
  background: none;
  border: none;
  color: #2563eb;
  font-weight: 700;
  font-size: .82rem;
  padding: .5rem 0 0;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: .3rem;
}
.dsx-toggle:hover { text-decoration: underline; }
</style>
