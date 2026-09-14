<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-3">
      <div>
        <p class="text-muted small mb-0">Define SKU, precio/dia, precio/hora y stock disponible.</p>
      </div>
      <button
        type="button"
        class="btn btn-sm btn-primary"
        @click="openVariantForm"
        :disabled="showVariantForm"
      >
        <i class="bi bi-plus-lg me-1"></i> Nueva Variante
      </button>
    </div>

    <!-- Form nueva variante -->
    <div v-if="showVariantForm" class="card border-0 bg-light p-3 mb-3 rounded-3">
      <h6 class="fw-semibold small mb-3">{{ editingVariant ? 'Editar Variante' : 'Nueva Variante' }}</h6>
      <div class="row g-2 mb-3">
        <div class="col-12">
          <label class="form-label small">SKU <span class="text-danger">*</span></label>
          <input
            v-model="vForm.sku"
            type="text"
            class="form-control form-control-sm"
            placeholder="Ej: GA110-STD"
          >
        </div>
        <div class="col-6">
          <label class="form-label small">Precio / Dia</label>
          <div class="input-group input-group-sm">
            <span class="input-group-text">$</span>
            <input v-model.number="vForm.rental_price_per_day" type="number" step="0.01" min="0" class="form-control" placeholder="0.00">
          </div>
        </div>
        <div class="col-6">
          <label class="form-label small">Precio / Hora</label>
          <div class="input-group input-group-sm">
            <span class="input-group-text">$</span>
            <input v-model.number="vForm.rental_price_per_hour" type="number" step="0.01" min="0" class="form-control" placeholder="0.00">
          </div>
        </div>
        <div class="col-6">
          <label class="form-label small">Stock</label>
          <input v-model.number="vForm.stock" type="number" min="0" class="form-control form-control-sm" placeholder="0">
        </div>
        <div class="col-6 d-flex align-items-end pb-1">
          <div class="form-check form-switch ms-1">
            <input v-model="vForm.is_active" class="form-check-input" type="checkbox" id="vActive">
            <label class="form-check-label small" for="vActive">Activa</label>
          </div>
        </div>
      </div>
      <div class="d-flex gap-2">
        <button type="button" class="btn btn-sm btn-primary" @click="saveVariant" :disabled="vLoading">
          <span v-if="vLoading" class="spinner-border spinner-border-sm me-1"></span>
          {{ editingVariant ? 'Guardar' : 'Agregar' }}
        </button>
        <button type="button" class="btn btn-sm btn-light border" @click="cancelVariantForm">Cancelar</button>
      </div>
    </div>

    <!-- Lista variantes -->
    <div v-if="variants.length" class="list-group list-group-flush">
      <div v-for="v in variants" :key="v.uuid" class="list-group-item px-0 py-2">
        <div class="d-flex align-items-start justify-content-between gap-2">
          <div class="flex-grow-1">
            <div class="d-flex align-items-center gap-2">
              <code class="small fw-bold text-dark">{{ v.sku }}</code>
              <span
                class="badge rounded-pill"
                :class="v.stock > 0 ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'"
                style="font-size:.65rem"
              >{{ v.stock }} und</span>
              <span v-if="!v.is_active" class="badge bg-secondary-subtle text-secondary" style="font-size:.65rem">Inactiva</span>
              <span v-if="v.uuid === variants[0]?.uuid && variants.length > 1" class="badge bg-primary-subtle text-primary" style="font-size:.65rem">Principal</span>
            </div>
            <div class="text-muted mt-1" style="font-size:.75rem">
              <span v-if="v.rental_price_per_day"><i class="bi bi-calendar3 me-1"></i>{{ formatCOP(v.rental_price_per_day) }}/dia</span>
              <span v-if="v.rental_price_per_day && v.rental_price_per_hour" class="mx-2">·</span>
              <span v-if="v.rental_price_per_hour"><i class="bi bi-clock me-1"></i>{{ formatCOP(v.rental_price_per_hour) }}/hora</span>
            </div>
          </div>
          <div class="btn-group btn-group-sm flex-shrink-0">
            <button type="button" class="btn btn-light border-end" @click="startEditVariant(v)" title="Editar">
              <i class="bi bi-pencil text-primary"></i>
            </button>
            <button type="button" class="btn btn-light" @click="onDeleteVariant(v)" :disabled="vLoading" title="Eliminar">
              <i class="bi bi-trash text-danger"></i>
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-else-if="!showVariantForm" class="text-center py-4 text-muted">
      <i class="bi bi-layers fs-3 d-block mb-2 opacity-50"></i>
      <p class="small mb-2">Sin variantes registradas.</p>
      <button type="button" class="btn btn-sm btn-outline-primary" @click="openVariantForm">
        <i class="bi bi-plus-lg me-1"></i> Crear primera variante
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { formatCOP as formatCOPBase } from '@/utils/money';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';

const props = defineProps({
  // Array del padre (mismo estado que necesitan Marketing/Costos/badge de
  // pestanas) -- este tab lo puebla llamando a props.actions.fetchVariants,
  // pero nunca lo muta directamente el mismo.
  variants: { type: Array, required: true },
  actions: { type: Object, required: true },
});

const toast = useToast();
const { handleError } = useErrorHandler();

const vLoading = ref(false);
const showVariantForm = ref(false);
const editingVariant = ref(null);
const vForm = ref({ sku: '', rental_price_per_day: null, rental_price_per_hour: null, stock: 0, is_active: true });

function formatCOP(value) {
  if (value == null || value === '') return null;
  return formatCOPBase(value, { withSymbol: true });
}

function openVariantForm() {
  editingVariant.value = null;
  vForm.value = { sku: '', rental_price_per_day: null, rental_price_per_hour: null, stock: 0, is_active: true };
  showVariantForm.value = true;
}

function startEditVariant(v) {
  editingVariant.value = v;
  vForm.value = {
    sku: v.sku,
    rental_price_per_day: v.rental_price_per_day ? parseFloat(v.rental_price_per_day) : null,
    rental_price_per_hour: v.rental_price_per_hour ? parseFloat(v.rental_price_per_hour) : null,
    stock: v.stock,
    is_active: v.is_active,
  };
  showVariantForm.value = true;
}

function cancelVariantForm() {
  showVariantForm.value = false;
  editingVariant.value = null;
  vForm.value = { sku: '', rental_price_per_day: null, rental_price_per_hour: null, stock: 0, is_active: true };
}

async function saveVariant() {
  if (!vForm.value.sku?.trim()) return toast.error('SKU es requerido');
  if (!vForm.value.rental_price_per_day && !vForm.value.rental_price_per_hour) {
    return toast.error('Ingresa precio por dia o por hora');
  }
  vLoading.value = true;
  try {
    const payload = {
      sku: vForm.value.sku,
      rental_price_per_day: vForm.value.rental_price_per_day || null,
      rental_price_per_hour: vForm.value.rental_price_per_hour || null,
      stock: vForm.value.stock || 0,
      is_active: vForm.value.is_active,
    };
    if (editingVariant.value) {
      await props.actions.updateVariant(editingVariant.value.uuid, payload);
      toast.success('Variante actualizada');
    } else {
      await props.actions.createVariant(payload);
      toast.success('Variante agregada');
    }
    cancelVariantForm();
  } catch (e) {
    handleError(e, 'Error al guardar variante');
  } finally {
    vLoading.value = false;
  }
}

async function onDeleteVariant(v) {
  vLoading.value = true;
  try {
    await props.actions.deleteVariant(v.uuid);
    toast.success('Variante eliminada');
  } catch {
    toast.error('No se pudo eliminar la variante');
  } finally {
    vLoading.value = false;
  }
}

onMounted(() => props.actions.fetchVariants());
</script>
