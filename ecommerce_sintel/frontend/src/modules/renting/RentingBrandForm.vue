<template>
  <BaseBrandForm
    :item="item"
    :mode="mode"
    endpoint="dashboard/renting-brands"
    name-placeholder="Ej: Caterpillar, Volvo"
    @success="$emit('success')"
    @cancel="$emit('cancel')"
  />
</template>

<script setup>
import BaseBrandForm from '@/components/base/BaseBrandForm.vue';

defineProps({
  item: { type: Object, default: null },
  mode: { type: String, default: 'create' },
});
defineEmits(['success', 'cancel']);
</script>
