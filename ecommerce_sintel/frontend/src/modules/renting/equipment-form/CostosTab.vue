<template>
  <div>
    <!-- Info variante principal -->
    <div v-if="firstVariantUuid" class="d-flex align-items-center gap-2 mb-3 p-2 rounded-2 border" style="background:#f8fafc">
      <i class="bi bi-info-circle text-primary small"></i>
      <span class="small text-muted">Las asignaciones aplican a la variante principal:
        <code class="text-dark">{{ variants[0]?.sku }}</code>
      </span>
    </div>
    <div v-else class="alert alert-warning border-0 py-2 px-3 mb-3 small">
      <i class="bi bi-exclamation-triangle me-2"></i>
      Registra al menos una variante en la pestana "Variantes" para poder asignar reglas.
    </div>

    <!-- Header -->
    <div class="d-flex align-items-center justify-content-between mb-3">
      <span class="small text-muted fw-semibold">{{ costRules.length }} regla(s) definidas</span>
      <button
        type="button"
        class="btn btn-sm btn-primary"
        @click="showCostForm = !showCostForm"
      >
        <i class="bi bi-plus-lg me-1"></i> Nueva Regla
      </button>
    </div>

    <!-- Formulario crear regla -->
    <div v-if="showCostForm" class="card border-0 bg-light p-3 mb-3 rounded-3">
      <h6 class="fw-semibold small mb-3">Nueva Regla de Costo</h6>
      <div class="row g-2 mb-3">
        <div class="col-12">
          <label class="form-label small">Nombre <span class="text-danger">*</span></label>
          <input v-model="costForm.name" type="text" class="form-control form-control-sm" placeholder="Ej: IVA 19%, Seguro basico...">
        </div>
        <div class="col-6">
          <label class="form-label small">Contexto</label>
          <select v-model="costForm.context" class="form-select form-select-sm">
            <option value="TAX">IVA / Impuesto</option>
            <option value="DISCOUNT">Descuento</option>
            <option value="DEPOSIT">Deposito</option>
            <option value="INSURANCE">Seguro</option>
            <option value="SURCHARGE">Recargo</option>
          </select>
        </div>
        <div class="col-6">
          <label class="form-label small">Tipo</label>
          <select v-model="costForm.cost_type" class="form-select form-select-sm">
            <option value="PERCENTAGE">Porcentaje (%)</option>
            <option value="FIXED">Valor Fijo ($)</option>
          </select>
        </div>
        <div class="col-6">
          <label class="form-label small">Valor <span class="text-danger">*</span></label>
          <div class="input-group input-group-sm">
            <span class="input-group-text">{{ costForm.cost_type === 'PERCENTAGE' ? '%' : '$' }}</span>
            <input v-model.number="costForm.value" type="number" step="0.0001" min="0" class="form-control" placeholder="19.0">
          </div>
        </div>
        <div class="col-6">
          <label class="form-label small">Descripcion</label>
          <input v-model="costForm.description" type="text" class="form-control form-control-sm" placeholder="Opcional">
        </div>
      </div>
      <div class="d-flex gap-2">
        <button type="button" class="btn btn-sm btn-primary" @click="onSaveCostRule" :disabled="costLoading">
          <span v-if="costLoading" class="spinner-border spinner-border-sm me-1"></span>
          Crear Regla
        </button>
        <button type="button" class="btn btn-sm btn-light border" @click="showCostForm = false">Cancelar</button>
      </div>
    </div>

    <!-- Lista reglas -->
    <div v-if="costRules.length" class="d-flex flex-column gap-2">
      <div
        v-for="rule in costRules"
        :key="rule.uuid"
        class="d-flex align-items-center gap-2 p-2 rounded-3 border"
        :class="rule.is_active ? 'bg-white' : 'bg-light opacity-60'"
      >
        <span
          class="badge rounded-pill flex-shrink-0"
          :class="contextBadge(rule.context)"
          style="font-size:.65rem;min-width:56px;text-align:center"
        >{{ contextLabel(rule.context) }}</span>

        <div class="flex-grow-1 min-w-0">
          <div class="fw-semibold small text-truncate">{{ rule.name }}</div>
          <div class="text-muted" style="font-size:.72rem">
            {{ rule.cost_type === 'PERCENTAGE' ? rule.value + '%' : formatCOP(rule.value) }}
          </div>
        </div>

        <div class="d-flex align-items-center gap-1 flex-shrink-0">
          <!-- Toggle activa -->
          <button
            type="button"
            class="btn btn-link p-0"
            :title="rule.is_active ? 'Desactivar' : 'Activar'"
            @click="onToggleCostRule(rule)"
            :disabled="costLoading"
          >
            <i
              :class="rule.is_active ? 'bi bi-toggle-on text-success fs-5' : 'bi bi-toggle-off text-muted fs-5'"
            ></i>
          </button>

          <!-- Reasignar a variante (por si se desvinculo) -->
          <button
            v-if="firstVariantUuid"
            type="button"
            class="btn btn-sm btn-outline-secondary py-0 px-2"
            style="font-size:.7rem"
            @click="onAssignCostRule(rule.uuid)"
            :disabled="costLoading"
            title="Asignar a variante principal"
          >
            <i class="bi bi-link-45deg"></i>
          </button>

          <!-- Eliminar -->
          <button
            type="button"
            class="btn btn-link p-0 text-danger"
            title="Eliminar regla"
            @click="onDeleteCostRule(rule)"
            :disabled="costLoading"
          >
            <i class="bi bi-trash fs-6"></i>
          </button>
        </div>
      </div>
    </div>

    <div v-else-if="!showCostForm" class="text-center py-4 text-muted">
      <i class="bi bi-tags fs-3 d-block mb-2 opacity-50"></i>
      <p class="small mb-2">No existen reglas configuradas para este equipo.</p>
      <button type="button" class="btn btn-sm btn-outline-primary" @click="showCostForm = true">
        <i class="bi bi-plus-lg me-1"></i> Crear primera regla
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { formatCOP as formatCOPBase } from '@/utils/money';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const props = defineProps({
  // Array del padre (compartido con el badge de la pestana en la barra de
  // tabs) -- este tab lo puebla vía props.actions, nunca lo muta el mismo.
  costRules: { type: Array, required: true },
  // Solo lectura -- viene del padre (compartido con la pestana Variantes).
  variants: { type: Array, required: true },
  actions: { type: Object, required: true },
});

const toast = useToast();
const { handleError } = useErrorHandler();

const firstVariantUuid = computed(() => props.variants[0]?.uuid || null);

function formatCOP(value) {
  if (value == null || value === '') return null;
  return formatCOPBase(value, { withSymbol: true });
}

const costLoading = ref(false);
const showCostForm = ref(false);
const costForm = reactive({
  name: '', context: 'TAX', cost_type: 'PERCENTAGE', value: '', description: '',
});

async function onSaveCostRule() {
  if (!costForm.name?.trim()) return toast.error('Nombre requerido');
  if (!costForm.value && costForm.value !== 0) return toast.error('Valor requerido');
  costLoading.value = true;
  try {
    await props.actions.saveCostRule({ ...costForm, value: String(costForm.value) });
    showCostForm.value = false;
    Object.assign(costForm, {
      name: '', context: 'TAX', cost_type: 'PERCENTAGE', value: '', description: '',
    });
    toast.success('Regla de costo creada');
  } catch (e) {
    handleError(e, 'Error al crear regla');
  } finally {
    costLoading.value = false;
  }
}

async function onToggleCostRule(rule) {
  costLoading.value = true;
  try {
    await props.actions.toggleCostRule(rule);
  } catch {
    toast.error('Error al cambiar estado de la regla');
  } finally {
    costLoading.value = false;
  }
}

async function onDeleteCostRule(rule) {
  if (!confirm(`¿Eliminar la regla "${rule.name}"? Esta accion no se puede deshacer.`)) return;
  costLoading.value = true;
  try {
    await props.actions.deleteCostRule(rule);
    toast.success('Regla eliminada');
  } catch (e) {
    handleError(e, 'Error al eliminar la regla');
  } finally {
    costLoading.value = false;
  }
}

async function onAssignCostRule(ruleUuid) {
  if (!firstVariantUuid.value) return toast.error('Registra una variante primero');
  costLoading.value = true;
  try {
    await props.actions.assignCostRule(ruleUuid, firstVariantUuid.value);
    toast.success('Regla asignada a la variante principal');
  } catch (e) {
    handleError(e, 'Ya asignada o error al asignar');
  } finally {
    costLoading.value = false;
  }
}

function contextLabel(ctx) {
  const map = { TAX: 'IVA', DISCOUNT: 'Descuento', DEPOSIT: 'Deposito', INSURANCE: 'Seguro', SURCHARGE: 'Recargo' };
  return map[ctx] || ctx;
}

function contextBadge(ctx) {
  const map = {
    TAX: 'bg-warning-subtle text-warning border border-warning-subtle',
    DISCOUNT: 'bg-success-subtle text-success border border-success-subtle',
    DEPOSIT: 'bg-info-subtle text-info border border-info-subtle',
    INSURANCE: 'bg-primary-subtle text-primary border border-primary-subtle',
    SURCHARGE: 'bg-danger-subtle text-danger border border-danger-subtle',
  };
  return map[ctx] || 'bg-secondary-subtle text-secondary';
}

onMounted(() => props.actions.fetchCostRules());
</script>
