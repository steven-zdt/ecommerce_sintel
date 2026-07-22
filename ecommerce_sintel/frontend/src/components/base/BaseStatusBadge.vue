<template>
  <span class="badge" :class="badgeClass">
    <i v-if="iconClass" :class="['bi', iconClass]"></i>
    {{ label }}
  </span>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue';
import { useEnums } from '@/composables/useEnums';

const props = defineProps({
  enumName: { type: String, required: true },
  value: { type: String, default: '' },
  showIcon: { type: Boolean, default: false },
  fallbackClass: { type: String, default: 'bg-secondary-subtle text-secondary' },
});

const enums = useEnums();

// Algunos enums (ej. service-operation-statuses, shipment-statuses) no estan en
// el catalogo estatico de fallback de useEnums.ts y su cache interno es un Map
// plano, no reactivo -- sin este flag local, el badge no se actualiza tras
// resolver ensure() de forma asincrona.
const loaded = ref(false);
onMounted(async () => {
  await enums.ensure(props.enumName);
  loaded.value = true;
});

const label = computed(() => {
  loaded.value;
  return enums.label(props.enumName, props.value, props.value);
});
const badgeClass = computed(() => {
  loaded.value;
  return enums.cssClass(props.enumName, props.value, props.fallbackClass);
});
const iconClass = computed(() => {
  loaded.value;
  return props.showIcon ? enums.icon(props.enumName, props.value, '') : '';
});
</script>
