<template>
  <div v-if="loading || packages.length" class="pkg-selector">
    <div v-if="loading" class="pkg-selector-loading">
      <span class="spinner-border spinner-border-sm text-warning"></span>
    </div>

    <template v-else>
      <h5 class="fw-bold mb-3">Personaliza tu paquete <span class="fw-normal text-muted small">(opcional)</span></h5>
      <div class="pkg-selector-grid">
        <ServicePackageCard
          v-for="pkg in packages"
          :key="pkg.uuid"
          :pkg="pkg"
          :selected="selectedPackage?.uuid === pkg.uuid"
          selectable
          @select="selectPackage"
        />
      </div>

      <div v-if="selectedPackage" class="pkg-selector-detail">
        <div v-if="selectedPackage.included_items?.length" class="pkg-selector-section">
          <h4>Que incluye este paquete</h4>
          <PackageIncludedList :items="selectedPackage.included_items" />
        </div>

        <div v-if="selectedPackage.additional_costs?.length" class="pkg-selector-section">
          <h4>Costos adicionales opcionales</h4>
          <div class="pkg-selector-costs">
            <PackageAdditionalCostCard
              v-for="cost in selectedPackage.additional_costs"
              :key="cost.uuid"
              :cost="cost"
              :selected="isCostSelected(cost)"
              :quantity="quantityFor(cost)"
              @toggle="(checked) => toggleCost(cost, checked)"
              @quantity-change="(qty) => setQuantity(cost, qty)"
            />
          </div>
        </div>

        <PackageCostBreakdown v-if="breakdown" :breakdown="breakdown" />
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import ServicePackageCard from './ServicePackageCard.vue';
import PackageIncludedList from './PackageIncludedList.vue';
import PackageAdditionalCostCard from './PackageAdditionalCostCard.vue';
import PackageCostBreakdown from './PackageCostBreakdown.vue';

const props = defineProps({
  serviceUuid: { type: String, required: true },
  variantUuid: { type: String, default: '' },
  duration: { type: [Number, String], default: null },
  initialPackageUuid: { type: String, default: '' },
});
const emit = defineEmits(['selection-change', 'packages-loaded']);

const api = useApi();
const loading = ref(true);
const packages = ref([]);
const selectedPackage = ref(null);
const selectedCosts = ref(new Map()); // uuid -> { cost, quantity }
const breakdown = ref(null);

async function fetchPackages() {
  loading.value = true;
  try {
    const res = await api.get(`services/services/${props.serviceUuid}/packages/`);
    packages.value = res.data || [];
    emit('packages-loaded', packages.value);
    const preselected = props.initialPackageUuid
      ? packages.value.find((p) => p.uuid === props.initialPackageUuid)
      : null;
    const defaultPkg = preselected || packages.value.find((p) => p.is_default) || packages.value[0] || null;
    if (defaultPkg) selectPackage(defaultPkg);
  } catch {
    packages.value = [];
  } finally {
    loading.value = false;
  }
}

function selectPackage(pkg) {
  selectedPackage.value = pkg;
  const next = new Map();
  for (const cost of pkg.additional_costs || []) {
    if (cost.is_required || cost.is_default) {
      next.set(cost.uuid, { cost, quantity: 1 });
    }
  }
  selectedCosts.value = next;
  refreshQuote();
}

function isCostSelected(cost) {
  return selectedCosts.value.has(cost.uuid);
}
function quantityFor(cost) {
  return selectedCosts.value.get(cost.uuid)?.quantity || 1;
}
function toggleCost(cost, checked) {
  const next = new Map(selectedCosts.value);
  if (checked) next.set(cost.uuid, { cost, quantity: 1 });
  else next.delete(cost.uuid);
  selectedCosts.value = next;
  refreshQuote();
}
function setQuantity(cost, quantity) {
  const next = new Map(selectedCosts.value);
  if (next.has(cost.uuid)) next.set(cost.uuid, { cost, quantity });
  selectedCosts.value = next;
  refreshQuote();
}

const selectedCostsList = computed(() => Array.from(selectedCosts.value.values()));

async function refreshQuote() {
  if (!selectedPackage.value) return;
  try {
    const res = await api.post(`services/services/${props.serviceUuid}/quote-package/`, {
      package_uuid: selectedPackage.value.uuid,
      variant_uuid: props.variantUuid || undefined,
      duration: props.duration || undefined,
      additional_costs: selectedCostsList.value.map((entry) => ({
        additional_cost_uuid: entry.cost.uuid,
        quantity: entry.quantity,
      })),
    });
    breakdown.value = res.data;
  } catch {
    breakdown.value = null;
  }
  emit('selection-change', {
    package: selectedPackage.value,
    additionalCosts: selectedCostsList.value,
    breakdown: breakdown.value,
  });
}

watch(() => [props.variantUuid, props.duration], refreshQuote);
watch(() => props.serviceUuid, fetchPackages);

onMounted(fetchPackages);

defineExpose({ hasPackages: computed(() => packages.value.length > 0) });
</script>

<style scoped>
.pkg-selector-loading { display: flex; justify-content: center; padding: 2rem 0; }
.pkg-selector-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 1rem;
}
.pkg-selector-detail { margin-top: 1.25rem; display: flex; flex-direction: column; gap: 1.1rem; }
.pkg-selector-section h4 { color: #0f172a; font-size: .92rem; font-weight: 800; margin: 0 0 .6rem; }
.pkg-selector-costs { display: flex; flex-direction: column; gap: .6rem; }
</style>
