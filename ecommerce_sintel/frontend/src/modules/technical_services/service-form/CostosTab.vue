<template>
  <div class="pb-4">
    <div v-if="variants.length" class="row g-2 mb-3">
      <div class="col-12 col-md-6">
        <label class="form-label small fw-semibold mb-1">Variante a cotizar</label>
        <select v-model="selectedCostVariantUuid" class="form-select form-select-sm">
          <option v-for="v in variants" :key="v.uuid" :value="v.uuid">
            {{ v.sku }} · {{ v.pricing_strategy }}
          </option>
        </select>
      </div>
      <div class="col-6 col-md-3">
        <label class="form-label small fw-semibold mb-1">Duración (opcional)</label>
        <input v-model.number="selectedCostDuration" type="number" min="0.5" step="0.5"
               class="form-control form-control-sm" placeholder="Usar default">
      </div>
      <div class="col-6 col-md-3">
        <label class="form-label small fw-semibold mb-1">Descuento %</label>
        <input v-model.number="selectedCostDiscount" type="number" min="0" max="100" step="0.1"
               class="form-control form-control-sm" placeholder="0">
      </div>
    </div>

    <PricingSourceCard
      v-if="selectedVariant"
      :key="selectedVariant.uuid"
      :variant="selectedVariant"
      :service-uuid="serviceUuid"
      @saved="pricingRefreshKey += 1"
    />

    <div v-if="variants.length" class="mb-3">
      <CostCalculationPanel
        :key="pricingRefreshKey"
        :variant-uuid="selectedCostVariantUuid"
        :duration="cleanNum(selectedCostDuration)"
        :discount="cleanNum(selectedCostDiscount)"
      />
    </div>

    <div v-else class="alert alert-warning border-0 py-2 px-3 mb-3 small">
      <i class="bi bi-exclamation-triangle me-2"></i>
      Crea al menos una variante para ver los detalles de costos.
    </div>

    <div class="d-flex justify-content-end pt-2 border-top">
      <button type="button" class="btn btn-light border" @click="$emit('close')">Cerrar</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useTechnicalServicesStore } from '@/store/technicalServicesAdmin/services';
import { cleanNum } from './helpers';
import CostCalculationPanel from '../CostCalculationPanel.vue';
import PricingSourceCard from './PricingSourceCard.vue';

const props = defineProps({
  serviceUuid: { type: String, default: '' },
});
defineEmits(['close']);

const store = useTechnicalServicesStore();
const { variants } = storeToRefs(store);

// Lazy-mount de pestanas (P5, ServiceForm.vue, 2026-08-14): antes esta pestana
// asumia implicitamente que VariantsTab.vue ya habia poblado `store.variants`
// (ambas montaban siempre juntas via v-show). Con v-if lazy eso ya no esta
// garantizado -- el admin puede abrir "Costos" sin haber visitado nunca
// "Variantes" en esta sesion de edicion, mostrando datos vacios o de otro
// servicio. Se hace el mismo fetch que VariantsTab.vue.onMounted para que esta
// pestana sea autosuficiente, sin depender del orden de visita.
onMounted(() => {
  if (props.serviceUuid) store.fetchVariants(props.serviceUuid);
});

const selectedCostVariantUuid = ref('');
const selectedCostDuration = ref(null);
const selectedCostDiscount = ref(null);
// Plan "Manual Pricing Engine" FASE 9 -- forzar re-fetch de CostCalculationPanel
// (pide GET quotation/ real al backend) despues de guardar un cambio de
// pricing_source, en vez de calcular una vista previa en el cliente.
const pricingRefreshKey = ref(0);

// Replica el comportamiento original: solo autoselecciona la primera variante
// si aun no hay ninguna elegida -- no se resetea al cambiar de item (quirk
// preexistente, no un bug, no se "corrige" aqui).
watch(variants, (v) => {
  if (!selectedCostVariantUuid.value && v.length) {
    selectedCostVariantUuid.value = v[0].uuid;
  }
}, { immediate: true });

const selectedVariant = computed(() => variants.value.find((v) => v.uuid === selectedCostVariantUuid.value) || null);

watch(selectedVariant, () => {
  pricingRefreshKey.value += 1;
});
</script>
