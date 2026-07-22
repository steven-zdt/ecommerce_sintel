<template>
  <div v-if="modelValue" class="legal-modal" @click.self="close">
    <div class="legal-modal__box">
      <div class="d-flex justify-content-between align-items-center mb-2 legal-modal__header">
        <h2 class="h5 fw-bold mb-0">{{ doc.title }}</h2>
        <button type="button" class="btn-close" @click="close"></button>
      </div>
      <p class="text-muted small mb-3">Ultima actualizacion: {{ doc.updated }}</p>

      <div class="legal-modal__body small">
        <p class="disclaimer">
          <i class="bi bi-info-circle-fill me-1"></i>
          Documento base elaborado conforme a la Ley 1480 de 2011 (Estatuto del Consumidor),
          Ley 1581 de 2012 (proteccion de datos) y Ley 527 de 1999 (comercio electronico).
          Sujeto a revision por un abogado antes de considerarse definitivo.
        </p>

        <section v-for="(section, i) in doc.sections" :key="i" class="legal-section">
          <h3 v-if="section.heading" class="legal-section__heading">{{ section.heading }}</h3>
          <p v-for="(p, j) in section.paragraphs" :key="j" v-html="p"></p>
          <ul v-if="section.list" class="legal-section__list">
            <li v-for="(item, k) in section.list" :key="k" v-html="item"></li>
          </ul>
        </section>
      </div>

      <button type="button" class="btn btn-primary w-100 mt-3" @click="close">Entendido</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { LEGAL_DOCS } from './legalDocs';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  docType: { type: String, required: true }, // 'terminos' | 'privacidad' | 'garantia' | 'devoluciones' | 'autorizacion'
});
const emit = defineEmits(['update:modelValue']);

const doc = computed(() => LEGAL_DOCS[props.docType] || LEGAL_DOCS.terminos);

function close() {
  emit('update:modelValue', false);
}
</script>

<style scoped>
.legal-modal {
  position: fixed; inset: 0; z-index: 1050;
  background: rgba(15, 23, 42, .5);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.legal-modal__box {
  background: #fff; border-radius: 16px; padding: 28px;
  width: 100%; max-width: 680px;
  max-height: 85vh; overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,.25);
}
.legal-modal__header { position: sticky; top: -28px; background: #fff; padding-top: 4px; z-index: 1; }
.disclaimer {
  background: #fff8e6; border: 1px solid #ffe8a3; border-radius: 8px;
  padding: 10px 12px; color: #8a6100; margin-bottom: 1.25rem;
}
.legal-section { margin-bottom: 1.25rem; }
.legal-section__heading {
  font-size: .95rem; font-weight: 700; color: #0f172a;
  margin-bottom: .5rem;
}
.legal-section p { color: #475569; line-height: 1.55; margin-bottom: .5rem; }
.legal-section__list { color: #475569; line-height: 1.55; padding-left: 1.2rem; }
.legal-section__list li { margin-bottom: .35rem; }
</style>
