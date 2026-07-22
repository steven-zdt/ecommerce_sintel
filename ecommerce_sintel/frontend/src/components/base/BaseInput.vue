<template>
  <div class="bi-field">
    <label v-if="label" class="bi-label">{{ label }} <span v-if="required" class="text-danger">*</span></label>
    <input
      :value="modelValue"
      :type="type"
      :placeholder="placeholder"
      :maxlength="maxlength"
      :disabled="disabled"
      class="bi-input"
      :class="{ 'is-invalid': error }"
      @input="onInput"
    />
    <div v-if="hint && !error" class="bi-hint">{{ hint }}</div>
    <div v-if="error" class="bi-error">{{ error }}</div>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: [String, Number], default: '' },
  label: { type: String, default: '' },
  type: { type: String, default: 'text' },
  placeholder: { type: String, default: '' },
  maxlength: { type: [String, Number], default: null },
  required: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  hint: { type: String, default: '' },
  error: { type: String, default: '' },
});

const emit = defineEmits(['update:modelValue']);

function onInput(event) {
  const raw = event.target.value;
  emit('update:modelValue', props.type === 'number' ? (raw === '' ? null : Number(raw)) : raw);
}
</script>

<style scoped>
.bi-label { display: block; font-size: .8rem; font-weight: 600; color: #374151; margin-bottom: .3rem; }
.bi-input {
  width: 100%; padding: .5rem .75rem; border: 1px solid #d1d5db; border-radius: 8px;
  font-size: .88rem;
}
.bi-input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,.15); }
.bi-input.is-invalid { border-color: #dc2626; }
.bi-hint { font-size: .75rem; color: #6b7280; margin-top: .25rem; }
.bi-error { font-size: .75rem; color: #dc2626; margin-top: .25rem; }
</style>
