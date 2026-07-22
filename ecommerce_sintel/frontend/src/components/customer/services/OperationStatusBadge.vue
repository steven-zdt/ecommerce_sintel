<template>
  <BaseStatusBadge enum-name="service-operation-statuses" :value="status" />
</template>

<script setup>
import BaseStatusBadge from '@/components/base/BaseStatusBadge.vue';

defineProps({ status: { type: String, required: true } });
</script>
