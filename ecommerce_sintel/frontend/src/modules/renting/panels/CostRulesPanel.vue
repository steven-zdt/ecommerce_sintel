<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-3">
      <h6 class="fw-semibold mb-0">Reglas de Costo de Alquiler</h6>
      <button class="btn btn-sm btn-primary" @click="showCreateModal = true">
        <i class="bi bi-plus-lg me-1"></i> Nueva Regla
      </button>
    </div>

    <!-- Tabla de reglas -->
    <div class="card border-0 shadow-sm">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="bg-light text-muted small text-uppercase">
            <tr>
              <th class="px-3 py-3">Nombre</th>
              <th class="py-3">Contexto</th>
              <th class="py-3">Tipo</th>
              <th class="py-3">Valor</th>
              <th class="py-3 text-center">Activa</th>
              <th class="py-3 text-end px-3">Asignar</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="store.loading">
              <td colspan="6" class="text-center py-4">
                <div class="spinner-border spinner-border-sm text-primary me-2"></div>
                <span class="text-muted">Cargando...</span>
              </td>
            </tr>
            <tr v-else-if="!store.costRules.length">
              <td colspan="6" class="text-center py-4 text-muted">
                <i class="bi bi-tags fs-2 d-block mb-2"></i>
                No existen reglas configuradas para este equipo.
              </td>
            </tr>
            <tr v-for="rule in store.costRules" :key="rule.uuid">
              <td class="px-3 fw-semibold">{{ rule.name }}</td>
              <td>
                <span class="badge rounded-pill" :class="contextBadge(rule.context)">
                  {{ contextLabel(rule.context) }}
                </span>
              </td>
              <td class="text-muted small">{{ rule.cost_type === 'PERCENTAGE' ? 'Porcentaje' : 'Fijo' }}</td>
              <td class="fw-bold">
                {{ rule.cost_type === 'PERCENTAGE' ? rule.value + '%' : formatCOP(rule.value) }}
              </td>
              <td class="text-center">
                <button
                  class="btn btn-link p-0"
                  :title="rule.is_active ? 'Desactivar' : 'Activar'"
                  @click="toggleActive(rule)"
                  :disabled="store.actionLoading"
                >
                  <i :class="rule.is_active ? 'bi bi-toggle-on text-success fs-5' : 'bi bi-toggle-off text-muted fs-5'"></i>
                </button>
              </td>
              <td class="text-end px-3">
                <button
                  v-if="variantUuid"
                  class="btn btn-sm btn-outline-secondary"
                  @click="assignRule(rule.uuid)"
                  :disabled="store.actionLoading"
                  title="Asignar a variante principal"
                >
                  <i class="bi bi-link-45deg me-1"></i> Asignar
                </button>
                <span v-else class="text-muted small">—</span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal crear regla -->
    <CostRuleFormModal
      v-if="showCreateModal"
      :equipment-uuid="props.equipmentUuid"
      @success="onRuleCreated"
      @close="showCreateModal = false"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRentingPricingAdminStore } from '@/store/rentingAdmin/pricing';
import { useToast } from '@/composables/useToast';
import CostRuleFormModal from '../CostRuleFormModal.vue';

const props = defineProps({
  equipmentUuid: { type: String, required: true },
  variantUuid: { type: String, default: null },
});

const store = useRentingPricingAdminStore();
const toast = useToast();
const showCreateModal = ref(false);

function formatCOP(value) {
  if (!value) return '—';
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', minimumFractionDigits: 0 }).format(value);
}

function contextLabel(ctx) {
  const map = { TAX: 'IVA', DISCOUNT: 'Descuento', DEPOSIT: 'Depósito', INSURANCE: 'Seguro', SURCHARGE: 'Recargo' };
  return map[ctx] || ctx;
}

function contextBadge(ctx) {
  const map = {
    TAX: 'bg-warning-subtle text-warning',
    DISCOUNT: 'bg-success-subtle text-success',
    DEPOSIT: 'bg-info-subtle text-info',
    INSURANCE: 'bg-primary-subtle text-primary',
    SURCHARGE: 'bg-danger-subtle text-danger',
  };
  return map[ctx] || 'bg-secondary-subtle text-secondary';
}

async function toggleActive(rule) {
  if (rule.is_active) {
    const result = await store.deactivateCostRule(rule.uuid);
    if (result.ok) toast.success('Regla desactivada.');
    else toast.error(result.error);
  } else {
    const result = await store.updateCostRule(rule.uuid, { is_active: true });
    if (result.ok) toast.success('Regla activada.');
    else toast.error(result.error);
  }
}

async function assignRule(ruleUuid) {
  if (!props.variantUuid) return;
  const result = await store.assignCostRule(ruleUuid, props.variantUuid);
  if (result.ok) toast.success('Regla asignada a la variante.');
  else toast.error(result.error);
}

async function onRuleCreated() {
  showCreateModal.value = false;
  toast.success('Regla de costo creada.');
  await store.fetchCostRules(props.equipmentUuid);
}

onMounted(() => store.fetchCostRules(props.equipmentUuid));
</script>
