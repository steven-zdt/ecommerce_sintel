<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-4">
      <div>
        <h4 class="fw-bold mb-0">Costos Adicionales</h4>
        <p class="text-muted small mb-0">Motor de precios: impuestos, descuentos, transporte y mas.</p>
      </div>
      <button class="btn btn-primary rounded-pill px-3" @click="openCreate">
        <i class="bi bi-plus-lg me-1"></i> Nuevo Costo
      </button>
    </div>

    <!-- KPI Cards -->
    <div class="row g-3 mb-4">
      <div class="col-md-4">
        <div class="card border-0 shadow-sm text-center p-3">
          <div class="small text-muted mb-1">Total Costos</div>
          <div class="h3 fw-bold text-primary mb-0">{{ costs.length }}</div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card border-0 shadow-sm text-center p-3">
          <div class="small text-muted mb-1">Activos</div>
          <div class="h3 fw-bold text-success mb-0">{{ activeCosts }}</div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card border-0 shadow-sm text-center p-3">
          <div class="small text-muted mb-1">Globales</div>
          <div class="h3 fw-bold text-warning mb-0">{{ globalCosts }}</div>
        </div>
      </div>
    </div>

    <!-- Filter by context -->
    <div class="d-flex gap-2 mb-3 flex-wrap">
      <button
        v-for="tab in contextTabs"
        :key="tab.key"
        type="button"
        :class="['btn btn-sm', activeCtx === tab.key ? 'btn-primary' : 'btn-outline-secondary']"
        @click="activeCtx = tab.key"
      >
        {{ tab.label }}
        <span :class="['badge rounded-pill ms-1', activeCtx === tab.key ? 'bg-white text-primary' : 'bg-secondary-subtle text-secondary']">
          {{ tabCount(tab.key) }}
        </span>
      </button>
    </div>

    <!-- Table -->
    <div class="card border-0 shadow-sm overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="bg-light small text-uppercase fw-semibold">
            <tr>
              <th class="px-4 py-3">Nombre</th>
              <th class="py-3">Contexto</th>
              <th class="py-3">Tipo</th>
              <th class="py-3 text-end">Valor</th>
              <th class="py-3 text-center">Alcance</th>
              <th class="py-3 text-center">Estado</th>
              <th class="py-3 text-end px-4">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="7" class="text-center py-5">
                <div class="spinner-border spinner-border-sm text-primary"></div>
              </td>
            </tr>
            <tr v-else-if="!filteredCosts.length">
              <td colspan="7" class="text-center py-5 text-muted">Sin costos adicionales configurados.</td>
            </tr>
            <tr v-for="cost in filteredCosts" :key="cost.uuid" :class="{ 'opacity-50': !cost.is_active }">
              <td class="px-4">
                <div class="fw-semibold text-dark">{{ cost.name }}</div>
                <div v-if="cost.description" class="text-muted smaller text-truncate" style="max-width: 220px;">{{ cost.description }}</div>
              </td>
              <td>
                <span class="badge rounded-pill" :class="ctxBadge(cost.context)">
                  {{ cost.context_display }}
                </span>
              </td>
              <td>
                <span class="badge bg-secondary-subtle text-secondary rounded-pill text-uppercase smaller">
                  {{ cost.cost_type_display }}
                </span>
              </td>
              <td class="text-end fw-semibold">
                <span v-if="cost.cost_type === 'PERCENTAGE'">{{ cost.value }}%</span>
                <span v-else>${{ Number(cost.value).toFixed(2) }}</span>
              </td>
              <td class="text-center">
                <span v-if="cost.applies_globally" class="badge bg-primary-subtle text-primary rounded-pill">Global</span>
                <span v-else class="badge bg-light text-muted rounded-pill">Especifico</span>
              </td>
              <td class="text-center">
                <span class="badge rounded-pill" :class="cost.is_active ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'">
                  {{ cost.is_active ? 'Activo' : 'Inactivo' }}
                </span>
              </td>
              <td class="text-end px-4">
                <div class="d-flex gap-2 justify-content-end">
                  <button class="btn btn-sm btn-light border" title="Editar" @click="openEdit(cost)">
                    <i class="bi bi-pencil"></i>
                  </button>
                  <button
                    v-if="cost.is_active"
                    class="btn btn-sm btn-outline-danger"
                    title="Desactivar"
                    :disabled="deactivating === cost.uuid"
                    @click="deactivate(cost)"
                  >
                    <span v-if="deactivating === cost.uuid" class="spinner-border spinner-border-sm"></span>
                    <i v-else class="bi bi-slash-circle"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal Form -->
    <AdditionalCostForm
      v-if="showForm"
      :cost="editTarget"
      @saved="onSaved"
      @close="showForm = false"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import AdditionalCostForm from './AdditionalCostForm.vue';

const api = useApi();

const costs      = ref([]);
const loading    = ref(false);
const showForm   = ref(false);
const editTarget = ref(null);
const deactivating = ref(null);
const activeCtx  = ref('ALL');

const contextTabs = [
  { key: 'ALL',         label: 'Todos' },
  { key: 'TAX',         label: 'Impuesto' },
  { key: 'DISCOUNT',    label: 'Descuento' },
  { key: 'TRANSPORT',   label: 'Transporte' },
  { key: 'LOGISTICS',   label: 'Logistica' },
  { key: 'OPERATIONAL', label: 'Operacional' },
  { key: 'SETUP',       label: 'Configuracion' },
];

const filteredCosts = computed(() =>
  activeCtx.value === 'ALL'
    ? costs.value
    : costs.value.filter(c => c.context === activeCtx.value)
);

const activeCosts = computed(() => costs.value.filter(c => c.is_active).length);
const globalCosts = computed(() => costs.value.filter(c => c.applies_globally).length);

function tabCount(key) {
  if (key === 'ALL') return costs.value.length;
  return costs.value.filter(c => c.context === key).length;
}

function ctxBadge(ctx) {
  const map = {
    TAX:         'bg-info-subtle text-info',
    DISCOUNT:    'bg-success-subtle text-success',
    TRANSPORT:   'bg-warning-subtle text-warning',
    LOGISTICS:   'bg-primary-subtle text-primary',
    OPERATIONAL: 'bg-secondary-subtle text-secondary',
    SETUP:       'bg-purple-subtle text-purple',
  };
  return map[ctx] || 'bg-secondary-subtle text-secondary';
}

async function fetchCosts() {
  loading.value = true;
  try {
    const { data } = await api.get('dashboard/additional-costs/');
    costs.value = data.results ?? data;
  } catch (e) {
    console.error('Error al cargar costos adicionales:', e);
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  editTarget.value = null;
  showForm.value   = true;
}

function openEdit(cost) {
  editTarget.value = cost;
  showForm.value   = true;
}

async function deactivate(cost) {
  if (!confirm(`Desactivar "${cost.name}"?`)) return;
  deactivating.value = cost.uuid;
  try {
    await api.post(`dashboard/additional-costs/${cost.uuid}/deactivate/`);
    await fetchCosts();
  } catch (e) {
    console.error('Error al desactivar:', e);
  } finally {
    deactivating.value = null;
  }
}

function onSaved() {
  showForm.value = false;
  fetchCosts();
}

onMounted(fetchCosts);
</script>
