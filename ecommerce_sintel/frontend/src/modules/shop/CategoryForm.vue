<template>
  <BaseCategoryForm
    :item="item"
    :mode="mode"
    endpoint="dashboard/categories"
    has-image
    has-seo
    name-placeholder="Ej: Electronicos"
    @success="$emit('success')"
    @cancel="$emit('cancel')"
  />
</template>

<script setup>
import BaseCategoryForm from '@/components/base/BaseCategoryForm.vue';

defineProps({
  item: { type: Object, default: null },
  mode: { type: String, default: 'create' },
});
defineEmits(['success', 'cancel']);
</script>
