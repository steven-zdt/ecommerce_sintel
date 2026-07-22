<template>
  <div class="hour-selector">
    <label class="field">
      <span>Hora de entrega *</span>
      <input
        type="time"
        :value="deliveryTime"
        :disabled="disabled"
        @input="emit('update:delivery-time', $event.target.value)"
      >
    </label>
    <label class="field">
      <span>Hora de recogida *</span>
      <input
        type="time"
        :value="pickupTime"
        :disabled="disabled"
        @input="emit('update:pickup-time', $event.target.value)"
      >
    </label>
    <p v-if="invalidRange" class="field-error wide">La hora de recogida debe ser posterior a la hora de entrega.</p>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  deliveryTime: { type: String, default: '' },
  pickupTime: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(['update:delivery-time', 'update:pickup-time']);

const invalidRange = computed(() =>
  !!props.deliveryTime && !!props.pickupTime && props.pickupTime <= props.deliveryTime
);
</script>

<style scoped>
.hour-selector { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
.field { display: grid; gap: .38rem; }
.field > span { font-size: .78rem; font-weight: 700; color: #475569; }
.field input { width: 100%; border: 1.5px solid #dddbe5; border-radius: 12px; padding: .78rem .85rem; background: #fff; outline: none; }
.field input:focus { border-color: #7c3aed; box-shadow: 0 0 0 3px #ede9fe; }
.field input:disabled { background: #f1f5f9; color: #94a3b8; }
.wide { grid-column: 1 / -1; }
.field-error { color: #be123c; font-size: .75rem; margin: 0; }
</style>
