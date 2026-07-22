<template>
  <div v-if="modelValue" class="stm-modal" @click.self="$emit('update:modelValue', false)">
    <div class="stm-modal__box">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <h2 class="h5 fw-bold mb-0">{{ title }}</h2>
        <button type="button" class="btn-close" @click="$emit('update:modelValue', false)"></button>
      </div>
      <div class="stm-modal__body small text-muted">
        <p class="text-warning-emphasis fw-semibold small">
          <i class="bi bi-exclamation-triangle-fill me-1"></i>
          Contenido de referencia -- pendiente de aprobacion legal definitiva.
        </p>
        <p style="white-space:pre-line">{{ placeholderText }}</p>
      </div>
      <button type="button" class="btn btn-violet w-100 mt-3" @click="$emit('update:modelValue', false)">Entendido</button>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  docType: {
    type: String,
    required: true,
    // 'condiciones' | 'cancelacion' | 'reprogramacion' | 'garantias' | 'responsabilidades' | 'datos'
  },
});
defineEmits(['update:modelValue']);

const TEXTS = {
  condiciones: {
    title: 'Condiciones del Servicio',
    body: 'La ejecucion del servicio tecnico contratado esta sujeta a la disponibilidad real del '
      + 'profesional asignado y a las condiciones de acceso al sitio informadas por el cliente. '
      + 'El costo final puede ajustarse tras la evaluacion tecnica presencial si las condiciones '
      + 'reales difieren de lo declarado en la solicitud.',
  },
  cancelacion: {
    title: 'Politica de Cancelacion',
    body: 'El cliente puede cancelar su solicitud de servicio sin costo antes de que un profesional '
      + 'sea asignado. Una vez asignado un profesional o confirmada una visita, la cancelacion '
      + 'podra generar un cargo administrativo segun el tiempo de anticipacion con el que se '
      + 'informe la cancelacion.',
  },
  reprogramacion: {
    title: 'Politica de Reprogramacion',
    body: 'La fecha y hora de la visita tecnica pueden reprogramarse de mutuo acuerdo entre el '
      + 'cliente y el equipo de Sintel, sujeto a disponibilidad. Si el cliente no se encuentra '
      + 'disponible en la fecha confirmada, Sintel podra proponer una nueva fecha sin costo '
      + 'adicional en la primera reprogramacion.',
  },
  garantias: {
    title: 'Garantias',
    body: 'Todos los trabajos ejecutados por profesionales de Sintel cuentan con garantia sobre la '
      + 'mano de obra por el periodo indicado en la ficha del servicio. Los materiales e insumos '
      + 'utilizados conservan la garantia otorgada por su fabricante.',
  },
  responsabilidades: {
    title: 'Responsabilidades',
    body: 'El cliente es responsable de suministrar informacion veraz sobre el estado del sitio y '
      + 'de garantizar el acceso seguro al lugar donde se ejecutara el servicio. Sintel es '
      + 'responsable de la correcta ejecucion tecnica del servicio contratado por el profesional '
      + 'asignado.',
  },
  datos: {
    title: 'Tratamiento de Datos Personales',
    body: 'Sintel trata tus datos personales conforme a la Ley 1581 de 2012 y sus decretos '
      + 'reglamentarios, con el fin de gestionar tu solicitud de servicio, coordinar la visita '
      + 'tecnica y prestarte soporte postventa. Puedes conocer, actualizar, rectificar y solicitar '
      + 'la supresion de tus datos en cualquier momento contactando a nuestro equipo de soporte.',
  },
};

const title = computed(() => TEXTS[props.docType]?.title || 'Documento legal');
const placeholderText = computed(() => TEXTS[props.docType]?.body || '');
</script>

<style scoped>
.stm-modal {
  position: fixed; inset: 0; z-index: 1060;
  background: rgba(15, 23, 42, .5);
  display: flex; align-items: center; justify-content: center;
  padding: 20px;
}
.stm-modal__box {
  background: #fff; border-radius: 16px; padding: 28px;
  width: 100%; max-width: 480px;
  max-height: 80vh; overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,.25);
}
.btn-violet { background: #7c3aed; color: #fff; border: none; }
.btn-violet:hover { background: #6d28d9; color: #fff; }
</style>
