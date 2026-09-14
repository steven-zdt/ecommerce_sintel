<template>
  <div>
    <!-- Info variante principal -->
    <div v-if="firstVariantUuid"
         class="d-flex align-items-center gap-2 mb-3 p-2 rounded-2 border"
         style="background:#f8fafc">
      <i class="bi bi-info-circle text-primary small"></i>
      <span class="small text-muted">
        Asignaciones aplican a la variante principal:
        <code class="text-dark">{{ variants[0]?.sku }}</code>
      </span>
    </div>
    <div v-else class="alert alert-warning border-0 py-2 px-3 mb-3 small">
      <i class="bi bi-exclamation-triangle me-2"></i>
      Crea al menos una variante antes de asignar reglas de costo.
    </div>

    <!-- Header -->
    <div class="d-flex align-items-center justify-content-between mb-3">
      <span class="small text-muted fw-semibold">{{ costRules.length }} regla(s) disponibles</span>
      <button type="button" class="btn btn-sm btn-primary" @click="showCostForm = !showCostForm">
        <i class="bi bi-plus-lg me-1"></i>Nueva Regla
      </button>
    </div>

    <!-- Formulario crear regla de costo -->
    <div v-if="showCostForm" class="card border-0 bg-light p-3 mb-3 rounded-3">
      <h6 class="fw-semibold small mb-3">Nueva Regla de Costo</h6>
      <div class="row g-2 mb-3">
        <div class="col-12">
          <label class="form-label small">Nombre <span class="text-danger">*</span></label>
          <input v-model="costForm.name" type="text" class="form-control form-control-sm"
                 placeholder="Ej: Flete nacional, IVA 19%, Descuento comercial">
        </div>
        <div class="col-6">
          <label class="form-label small">Tipo de costo</label>
          <select v-model="costForm.context" class="form-select form-select-sm">
            <option value="TAX">Impuesto / Cargo</option>
            <option value="DISCOUNT">Descuento</option>
          </select>
        </div>
        <div class="col-6">
          <label class="form-label small">Calculo</label>
          <select v-model="costForm.cost_type" class="form-select form-select-sm">
            <option value="PERCENTAGE">Porcentaje (%)</option>
            <option value="FIXED">Valor fijo ($)</option>
          </select>
        </div>
        <div class="col-6">
          <label class="form-label small">Valor <span class="text-danger">*</span></label>
          <div class="input-group input-group-sm">
            <span class="input-group-text">
              {{ costForm.cost_type === 'PERCENTAGE' ? '%' : '$' }}
            </span>
            <input v-model.number="costForm.value" type="number" step="0.0001" min="0"
                   class="form-control" placeholder="19.0">
          </div>
        </div>
        <div class="col-6">
          <label class="form-label small">Descripcion</label>
          <input v-model="costForm.description" type="text" class="form-control form-control-sm"
                 placeholder="Opcional">
        </div>
        <div class="col-12">
          <div class="form-check form-switch">
            <input class="form-check-input" type="checkbox"
                   v-model="costForm.applies_globally" id="shopCostGlobal">
            <label class="form-check-label small" for="shopCostGlobal">
              Aplicar globalmente a todos los productos
            </label>
          </div>
        </div>
      </div>
      <div class="d-flex gap-2">
        <button type="button" class="btn btn-sm btn-primary"
                @click="onSaveCostRule" :disabled="actionLoading">
          <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>
          Crear Regla
        </button>
        <button type="button" class="btn btn-sm btn-light border"
                @click="showCostForm = false">Cancelar</button>
      </div>
    </div>

    <!-- Lista reglas de costo -->
    <div v-if="costRules.length" class="d-flex flex-column gap-2">
      <div v-for="rule in costRules" :key="rule.uuid"
           class="d-flex align-items-center gap-2 p-2 rounded-3 border"
           :class="rule.is_active ? 'bg-white' : 'bg-light opacity-60'">

        <span class="badge rounded-pill flex-shrink-0"
              :class="rule.context === 'TAX'
                ? 'bg-warning-subtle text-warning border border-warning-subtle'
                : 'bg-success-subtle text-success border border-success-subtle'"
              style="font-size:.65rem;min-width:60px;text-align:center">
          {{ rule.context === 'TAX' ? 'Impuesto' : 'Descuento' }}
        </span>

        <div class="flex-grow-1 min-w-0">
          <div class="fw-semibold small text-truncate">{{ rule.name }}</div>
          <div class="text-muted" style="font-size:.72rem">
            {{ rule.cost_type === 'PERCENTAGE' ? rule.value + '%' : '$' + formatNum(rule.value) }}
            <span v-if="rule.description" class="ms-1 opacity-75">· {{ rule.description }}</span>
            <span v-if="rule.applies_globally" class="ms-1 text-success">· Global</span>
          </div>
        </div>

        <div class="d-flex align-items-center gap-1 flex-shrink-0">
          <button type="button" class="btn btn-link p-0"
                  @click="onToggleCostRule(rule)" :disabled="actionLoading"
                  :title="rule.is_active ? 'Desactivar' : 'Activar'">
            <i :class="rule.is_active
              ? 'bi bi-toggle-on text-success fs-5'
              : 'bi bi-toggle-off text-muted fs-5'"></i>
          </button>
          <button v-if="firstVariantUuid && !rule.applies_globally"
                  type="button"
                  class="btn btn-sm btn-outline-secondary py-0 px-2"
                  style="font-size:.7rem"
                  @click="onAssignCostRule(rule.uuid)"
                  :disabled="actionLoading"
                  title="Asignar a variante principal">
            <i class="bi bi-link-45deg"></i>
          </button>
          <span v-else-if="rule.applies_globally" class="text-success" style="font-size:.75rem">
            <i class="bi bi-check-circle-fill"></i>
          </span>
          <button type="button" class="btn btn-link p-0 text-danger"
                  title="Eliminar regla" @click="onDeleteCostRule(rule)"
                  :disabled="actionLoading">
            <i class="bi bi-trash fs-6"></i>
          </button>
        </div>
      </div>
    </div>

    <div v-else-if="!showCostForm" class="text-center py-4 text-muted">
      <i class="bi bi-tags fs-3 d-block mb-2 opacity-50"></i>
      <p class="small mb-2">Sin reglas de costo. Crea la primera.</p>
      <button type="button" class="btn btn-sm btn-outline-primary" @click="showCostForm = true">
        <i class="bi bi-plus-lg me-1"></i> Crear primera regla
      </button>
    </div>

    <!-- Footer Costos -->
    <div class="d-flex justify-content-end mt-4 pt-2 border-top">
      <button type="button" class="btn btn-light border" @click="$emit('close')">Cerrar</button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useShopAdminStore } from '@/store/shopAdmin';
import { formatNum } from './helpers';

defineEmits(['close']);

const toast = useToast();
const { handleError } = useErrorHandler();
const store = useShopAdminStore();
const { costRules, variants, actionLoading } = storeToRefs(store);

const firstVariantUuid = computed(() => variants.value[0]?.uuid || null);

const showCostForm = ref(false);
const costForm = reactive({
  name: '', context: 'TAX', cost_type: 'PERCENTAGE', value: '', description: '', applies_globally: false,
});

async function fetchCostRules() {
  await store.fetchCostRules();
  if (store.error) toast.error(store.error);
}

async function onSaveCostRule() {
  if (!costForm.name?.trim()) return toast.error('Nombre requerido');
  if (costForm.value === '' || costForm.value === null) return toast.error('Valor requerido');

  const res = await store.createCostRule({ ...costForm, value: String(costForm.value) });
  if (res.ok) {
    await fetchCostRules();
    showCostForm.value = false;
    Object.assign(costForm, {
      name: '', context: 'TAX', cost_type: 'PERCENTAGE',
      value: '', description: '', applies_globally: false,
    });
    toast.success('Regla de costo creada');
  } else {
    handleError(res.error, 'Error al crear regla');
  }
}

async function onToggleCostRule(rule) {
  const res = await store.toggleCostRule(rule);
  if (res.ok) {
    await fetchCostRules();
  } else {
    toast.error('Error al cambiar estado de la regla');
  }
}

async function onDeleteCostRule(rule) {
  if (!confirm(`¿Eliminar la regla "${rule.name}"? Esta accion no se puede deshacer.`)) return;
  const res = await store.deleteCostRule(rule.uuid);
  if (res.ok) {
    await fetchCostRules();
    toast.success('Regla eliminada');
  } else {
    handleError(res.error, 'Error al eliminar la regla');
  }
}

async function onAssignCostRule(ruleUuid) {
  if (!firstVariantUuid.value) return toast.error('Crea una variante primero');
  const res = await store.assignCostRule(ruleUuid, firstVariantUuid.value);
  if (res.ok) {
    toast.success('Regla asignada a la variante principal');
  } else {
    handleError(res.error, 'Ya asignada o error al asignar');
  }
}

onMounted(fetchCostRules);
</script>
