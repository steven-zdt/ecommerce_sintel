<template>
  <div class="bi-field">
    <label v-if="label" class="bi-label">{{ label }}</label>
    <input type="file" :accept="accept" class="bi-input" @change="onChange" />
    <img v-if="previewUrl" :src="previewUrl" class="bu-preview mt-2" alt="" />
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, default: '' },
  accept: { type: String, default: 'image/*' },
  previewUrl: { type: String, default: null },
});

const emit = defineEmits(['file-selected']);

function onChange(event) {
  const file = event.target.files?.[0];
  if (file) emit('file-selected', file);
}
</script>

<style scoped>
.bi-label { display: block; font-size: .8rem; font-weight: 600; color: #374151; margin-bottom: .3rem; }
.bi-input {
  width: 100%; padding: .5rem .75rem; border: 1px solid #d1d5db; border-radius: 8px;
  font-size: .88rem;
}
.bi-input:focus { outline: none; border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59,130,246,.15); }
.bu-preview { max-height: 60px; max-width: 100%; border-radius: 6px; display: block; }
</style>
