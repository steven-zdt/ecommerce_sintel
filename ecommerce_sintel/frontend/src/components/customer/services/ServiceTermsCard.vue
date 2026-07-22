<template>
  <div class="stc-card">
    <div class="stc-header">
      <i class="bi bi-file-earmark-text me-2 text-violet"></i>
      <span>Terminos y condiciones del servicio</span>
    </div>
    <div class="stc-body">
      <p class="text-muted small mb-3">
        Antes de continuar, revisa y acepta las condiciones que aplican a tu solicitud de servicio tecnico:
      </p>
      <div class="d-flex flex-wrap gap-2 mb-3">
        <button v-for="doc in DOCS" :key="doc.key" type="button" class="btn btn-sm btn-outline-secondary" @click="openModal = doc.key">
          <i :class="doc.icon" class="me-1"></i>{{ doc.label }}
        </button>
      </div>
      <div class="form-check d-flex align-items-start gap-2">
        <input
          class="form-check-input mt-1 flex-shrink-0"
          type="checkbox"
          id="serviceTermsAccept"
          :checked="modelValue"
          @change="$emit('update:modelValue', $event.target.checked)"
        >
        <label class="form-check-label small" for="serviceTermsAccept">
          He leido y acepto los <strong>Terminos y Condiciones</strong>, la
          <strong>Politica de Cancelacion</strong>, la <strong>Politica de Reprogramacion</strong>,
          las <strong>Garantias</strong>, las <strong>Responsabilidades</strong> del servicio y el
          <strong>Tratamiento de mis Datos Personales</strong>.
          <span class="text-danger">*</span>
        </label>
      </div>
    </div>

    <ServiceTermsModal
      :model-value="!!openModal"
      :doc-type="openModal || 'condiciones'"
      @update:model-value="openModal = null"
    />
  </div>
</template>

<script setup>
import { ref } from 'vue';
import ServiceTermsModal from './ServiceTermsModal.vue';

defineProps({
  modelValue: { type: Boolean, default: false },
});
defineEmits(['update:modelValue']);

const openModal = ref(null);

const DOCS = [
  { key: 'condiciones',        label: 'Condiciones del servicio', icon: 'bi bi-clipboard-check' },
  { key: 'cancelacion',        label: 'Cancelacion',              icon: 'bi bi-x-circle' },
  { key: 'reprogramacion',     label: 'Reprogramacion',            icon: 'bi bi-calendar2-week' },
  { key: 'garantias',          label: 'Garantias',                icon: 'bi bi-shield-check' },
  { key: 'responsabilidades',  label: 'Responsabilidades',        icon: 'bi bi-person-check' },
  { key: 'datos',              label: 'Tratamiento de datos',      icon: 'bi bi-lock' },
];
</script>

<style scoped>
.stc-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 14px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,.04); }
.stc-header { display: flex; align-items: center; padding: 14px 20px; background: #f9fafb; border-bottom: 1px solid #e5e7eb; font-weight: 700; font-size: .9rem; }
.stc-body { padding: 16px 20px; }
.text-violet { color: #7c3aed !important; }
</style>
