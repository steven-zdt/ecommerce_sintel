<template>
  <div class="mb-3">
    <div class="form-check mb-2">
      <input v-model="form.acepta_politica_tratamiento_datos" class="form-check-input" type="checkbox"
        id="consent-politica" :class="{ 'is-invalid': errors.acepta_politica_tratamiento_datos }">
      <label class="form-check-label small" for="consent-politica">
        Acepto la <a href="#" @click.prevent="openModal = 'politica'">Politica de Tratamiento de Datos Personales</a>
        <span class="text-danger">*</span>
      </label>
      <div class="invalid-feedback">{{ errors.acepta_politica_tratamiento_datos }}</div>
    </div>
    <div class="form-check mb-2">
      <input v-model="form.acepta_autorizacion_tratamiento_datos" class="form-check-input" type="checkbox"
        id="consent-autorizacion" :class="{ 'is-invalid': errors.acepta_autorizacion_tratamiento_datos }">
      <label class="form-check-label small" for="consent-autorizacion">
        Autorizo el <a href="#" @click.prevent="openModal = 'autorizacion'">tratamiento de mis datos personales</a>
        <span class="text-danger">*</span>
      </label>
      <div class="invalid-feedback">{{ errors.acepta_autorizacion_tratamiento_datos }}</div>
    </div>
    <div class="form-check">
      <input v-model="form.acepta_terminos_condiciones" class="form-check-input" type="checkbox"
        id="consent-terminos" :class="{ 'is-invalid': errors.acepta_terminos_condiciones }">
      <label class="form-check-label small" for="consent-terminos">
        Acepto los <a href="#" @click.prevent="openModal = 'terminos'">Terminos y Condiciones</a>
        <span class="text-danger">*</span>
      </label>
      <div class="invalid-feedback">{{ errors.acepta_terminos_condiciones }}</div>
    </div>
  </div>

  <LegalTextModal
    :model-value="!!openModal"
    :doc-type="openModal || 'politica'"
    @update:model-value="openModal = null"
  />
</template>

<script setup>
import { ref } from 'vue';
import LegalTextModal from './LegalTextModal.vue';

defineProps({
  form: { type: Object, required: true },
  errors: { type: Object, required: true },
});

const openModal = ref(null);
</script>
