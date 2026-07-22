<template>
  <div v-if="items.length" class="bv-faq-list">
    <div v-for="item in items" :key="item.key" class="bv-faq-item" :class="{ open: openKey === item.key }">
      <button type="button" class="bv-faq-question" @click="toggle(item.key)">
        <span>{{ item.question }}</span>
        <i class="bi" :class="openKey === item.key ? 'bi-dash-lg' : 'bi-plus-lg'"></i>
      </button>
      <div v-show="openKey === item.key" class="bv-faq-answer">{{ item.answer }}</div>
    </div>
  </div>
</template>

<script setup>
/**
 * BaseAccordion.vue -- fusion de renting/detail/EquipmentFAQ.vue (button+icono
 * plus/menos) y services/detail/ServiceFAQAccordion.vue (native <details>),
 * Fase 2 del PLAN_MAESTRO_FRONTEND_DESIGN_SYSTEM_Y_FORMULARIOS.md §2.1. Se
 * adopto el patron de boton+icono (permite forzar solo 1 abierto a la vez,
 * el nativo <details> no lo permite sin JS extra) como el unico. `items`
 * acepta cualquiera de las 2 formas de clave que ya existian en produccion
 * (`{uuid,question,answer}` de Renting o `{q,a}` de Services) via `normalize()`,
 * asi ningun consumidor tiene que remapear su computed existente.
 */
import { ref, computed } from 'vue';

const props = defineProps({
  items: { type: Array, default: () => [] }, // [{question,answer}] | [{uuid,question,answer}] | [{q,a}]
  accentColor: { type: String, default: '#7c3aed' },
});

const normalized = computed(() => props.items.map((item, index) => ({
  key: item.uuid || item.key || `${item.question || item.q}-${index}`,
  question: item.question ?? item.q ?? '',
  answer: item.answer ?? item.a ?? '',
})));

const openKey = ref(normalized.value[0]?.key ?? null);

function toggle(key) {
  openKey.value = openKey.value === key ? null : key;
}

defineExpose({ items: normalized });
</script>

<style scoped>
.bv-faq-list { display: flex; flex-direction: column; gap: .5rem; }
.bv-faq-item { border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; background: #fff; }
.bv-faq-question {
  width: 100%; display: flex; align-items: center; justify-content: space-between;
  gap: .75rem; padding: .85rem 1rem; background: none; border: 0; text-align: left;
  color: #0f172a; font-size: .86rem; font-weight: 750; cursor: pointer;
}
.bv-faq-item.open .bv-faq-question { color: v-bind(accentColor); }
.bv-faq-answer { padding: 0 1rem .9rem; color: #64748b; font-size: .82rem; line-height: 1.6; }
</style>
