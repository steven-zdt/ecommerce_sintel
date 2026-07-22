<template>
  <div class="otp-row" @paste="onPaste">
    <input
      v-for="i in length"
      :key="i"
      :ref="el => { if (el) otpRefs[i - 1] = el }"
      v-model="otpDigits[i - 1]"
      type="text"
      inputmode="numeric"
      maxlength="1"
      class="otp-box"
      :class="{ 'is-invalid': !!error }"
      :disabled="disabled"
      :aria-label="`Dígito ${i} de ${length}`"
      :aria-invalid="!!error"
      @input="onOtpInput(i - 1, $event)"
      @keydown="onOtpKeydown(i - 1, $event)"
    >
  </div>
</template>

<script setup>
import { reactive, ref, watch } from 'vue';

const props = defineProps({
  modelValue: { type: String, default: '' },
  error: { type: String, default: '' },
  length: { type: Number, default: 6 },
  disabled: { type: Boolean, default: false },
});

const emit = defineEmits(['update:modelValue']);

const otpDigits = reactive(Array.from({ length: props.length }, () => ''));
const otpRefs = ref([]);

function emitValue() {
  emit('update:modelValue', otpDigits.join(''));
}

function onOtpInput(index, event) {
  const val = event.target.value.replace(/\D/g, '');
  otpDigits[index] = val.slice(-1);
  emitValue();
  if (val && index < props.length - 1) otpRefs.value[index + 1]?.focus();
}

function onOtpKeydown(index, event) {
  if (event.key === 'Backspace' && !otpDigits[index] && index > 0) {
    otpRefs.value[index - 1]?.focus();
  }
}

function onPaste(event) {
  const text = event.clipboardData?.getData('text') || '';
  const digits = text.replace(/\D/g, '').slice(0, props.length);
  digits.split('').forEach((d, i) => { otpDigits[i] = d; });
  emitValue();
  if (digits.length === props.length) otpRefs.value[props.length - 1]?.focus();
  event.preventDefault();
}

function clear() {
  for (let i = 0; i < props.length; i++) otpDigits[i] = '';
  emitValue();
  otpRefs.value[0]?.focus();
}

// Si el padre resetea modelValue externamente (ej. tras cambiar de paso), reflejarlo.
watch(() => props.modelValue, (val) => {
  if (val === '') clear();
});

defineExpose({ clear });
</script>

<style scoped>
.otp-row { display: flex; gap: 10px; justify-content: center; }
.otp-box {
  width: 52px; height: 60px; text-align: center;
  font-size: 1.5rem; font-weight: 700;
  border: 2px solid #d1d5db; border-radius: 12px;
  outline: none; transition: border-color .15s, box-shadow .15s;
}
.otp-box:focus      { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,.15); }
.otp-box.is-invalid { border-color: #dc3545; box-shadow: 0 0 0 3px rgba(220,53,69,.12); }
.otp-box:disabled   { background: #f3f4f6; cursor: not-allowed; }
</style>
