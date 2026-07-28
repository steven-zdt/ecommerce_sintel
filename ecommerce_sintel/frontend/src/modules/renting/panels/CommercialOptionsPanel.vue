<template>
  <div>
    <h6 class="fw-semibold mb-3">Plazos de Comodato</h6>

    <div class="card border-0 shadow-sm p-4">
      <p class="text-muted small mb-3">
        Activa los plazos que el cliente podra elegir al solicitar este equipo
        en comodato. Un plazo inactivo no aparece en el selector del wizard.
      </p>

      <div v-if="store.loading" class="text-center py-3">
        <div class="spinner-border spinner-border-sm text-primary"></div>
      </div>

      <div v-else class="d-flex flex-wrap gap-2">
        <button
          v-for="term in TERM_CHOICES"
          :key="term.value"
          type="button"
          class="btn btn-sm term-toggle"
          :class="isEnabled(term.value) ? 'btn-primary' : 'btn-outline-secondary'"
          :disabled="store.actionLoading"
          @click="toggleTerm(term.value)"
        >
          <i :class="isEnabled(term.value) ? 'bi bi-check-circle-fill me-1' : 'bi bi-circle me-1'"></i>
          {{ term.label }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useRentingCatalogAdminStore } from '@/store/rentingAdmin/catalog';
import { useToast } from '@/composables/useToast';

const props = defineProps({
  equipmentUuid: { type: String, required: true },
});

const store = useRentingCatalogAdminStore();
const toast = useToast();

const TERM_CHOICES = [
  { value: 6, label: '6 meses' },
  { value: 12, label: '12 meses' },
  { value: 18, label: '18 meses' },
  { value: 24, label: '24 meses' },
  { value: 36, label: '36 meses' },
];

function findOption(termMonths) {
  return store.commercialOptions.find(
    (o) => o.modality === 'COMODATO' && o.term_months === termMonths
  );
}

function isEnabled(termMonths) {
  return !!findOption(termMonths)?.is_enabled;
}

async function toggleTerm(termMonths) {
  const current = findOption(termMonths);
  const result = await store.upsertCommercialOption(props.equipmentUuid, {
    modality: 'COMODATO',
    term_months: termMonths,
    is_enabled: !current?.is_enabled,
  });
  if (result.ok) {
    toast.success('Plazo actualizado.');
  } else {
    toast.error(result.error);
  }
}

onMounted(() => store.fetchCommercialOptions(props.equipmentUuid));
</script>

<style scoped>
.term-toggle {
  min-width: 100px;
}
</style>
