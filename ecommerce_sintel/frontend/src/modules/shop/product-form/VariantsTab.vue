<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <p class="text-muted small mb-0">Precio, descuento, stock y dimensiones logisticas por variante.</p>
      <button type="button" class="btn btn-sm btn-primary" @click="openNewVariantForm"
              :disabled="showVariantForm && !editingVariant">
        <i class="bi bi-plus-lg me-1"></i>Nueva Variante
      </button>
    </div>

    <!-- ── FORMULARIO NUEVA VARIANTE ── -->
    <div v-if="showVariantForm && !editingVariant" class="card border-0 bg-light p-3 mb-3 rounded-3">
      <h6 class="fw-semibold small mb-3">Nueva Variante</h6>

      <!-- Stock -->
      <div class="row g-2 mb-2">
        <div class="col-4">
          <label class="form-label smaller mb-1 fw-semibold">Stock</label>
          <input v-model.number="newVariant.stock" type="number" min="0" class="form-control form-control-sm"
                 placeholder="0">
        </div>
        <div class="col-8 d-flex align-items-end pb-1">
          <div class="form-check form-switch ms-1">
            <input v-model="newVariant.is_default" type="checkbox" class="form-check-input" id="nvDefault">
            <label class="form-check-label smaller" for="nvDefault">Variante por defecto</label>
          </div>
        </div>
      </div>

      <!-- Precio base + Precio oferta -->
      <div class="row g-2 mb-2">
        <div class="col-6">
          <label class="form-label smaller mb-1 fw-semibold">Precio base <span class="text-danger">*</span></label>
          <div class="input-group input-group-sm">
            <span class="input-group-text">$</span>
            <input v-model.number="newVariant.price" type="number" step="0.01" min="0.01" class="form-control"
                   placeholder="0.00">
          </div>
        </div>
        <div class="col-6">
          <label class="form-label smaller mb-1 fw-semibold">Precio con descuento</label>
          <div class="input-group input-group-sm">
            <span class="input-group-text">$</span>
            <input v-model.number="newVariant.discounted_price" type="number" step="0.01" min="0"
                   class="form-control" placeholder="Opcional">
          </div>
        </div>
      </div>

      <!-- Periodo de descuento temporal -->
      <div class="row g-2 mb-2">
        <div class="col-6">
          <label class="form-label smaller mb-1">Descuento desde</label>
          <input v-model="newVariant.discount_start_date" type="datetime-local"
                 class="form-control form-control-sm">
        </div>
        <div class="col-6">
          <label class="form-label smaller mb-1">Descuento hasta</label>
          <input v-model="newVariant.discount_end_date" type="datetime-local"
                 class="form-control form-control-sm">
        </div>
      </div>

      <!-- Atributos dinamicos -->
      <div class="mb-2">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <label class="form-label smaller mb-0 fw-semibold">Atributos</label>
          <button type="button" class="btn btn-xs btn-outline-secondary" @click="addAttrRow(newVariant)">
            <i class="bi bi-plus"></i> Atributo
          </button>
        </div>
        <div v-for="(row, i) in newVariant.attrRows" :key="i" class="row g-1 mb-1">
          <div class="col-5">
            <input v-model="row.key" type="text" class="form-control form-control-sm"
                   placeholder="Ej: Color">
          </div>
          <div class="col-5">
            <input v-model="row.value" type="text" class="form-control form-control-sm"
                   placeholder="Ej: Rojo">
          </div>
          <div class="col-2">
            <button type="button" class="btn btn-xs btn-light border w-100"
                    @click="removeAttrRow(newVariant, i)">
              <i class="bi bi-x text-danger"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Logistica / Transporte -->
      <p class="smaller fw-semibold text-muted mb-1 mt-2">
        <i class="bi bi-truck me-1"></i>Logistica / Transporte
      </p>
      <div class="row g-2 mb-2">
        <div class="col-3">
          <label class="form-label smaller mb-1">Peso (kg)</label>
          <input v-model.number="newVariant.weight" type="number" step="0.01" min="0"
                 class="form-control form-control-sm" placeholder="0.00">
        </div>
        <div class="col-3">
          <label class="form-label smaller mb-1">Largo (cm)</label>
          <input v-model.number="newVariant.length" type="number" step="0.01" min="0"
                 class="form-control form-control-sm" placeholder="0.00">
        </div>
        <div class="col-3">
          <label class="form-label smaller mb-1">Ancho (cm)</label>
          <input v-model.number="newVariant.width" type="number" step="0.01" min="0"
                 class="form-control form-control-sm" placeholder="0.00">
        </div>
        <div class="col-3">
          <label class="form-label smaller mb-1">Alto (cm)</label>
          <input v-model.number="newVariant.height" type="number" step="0.01" min="0"
                 class="form-control form-control-sm" placeholder="0.00">
        </div>
      </div>

      <!-- Impuestos del sistema -->
      <div v-if="taxes.length" class="mb-3 p-2 rounded-2 border" style="background:#f8fafc">
        <p class="smaller fw-semibold text-muted mb-1">
          <i class="bi bi-percent me-1 text-primary"></i>Impuestos activos del sistema
          <span class="fw-normal">(se aplican automaticamente al precio efectivo)</span>
        </p>
        <div class="d-flex flex-wrap gap-1">
          <span v-for="tax in taxes" :key="tax.uuid"
                class="badge bg-primary-subtle text-primary border border-primary-subtle"
                style="font-size:.7rem">
            {{ tax.name }} &middot;
            {{ tax.tax_type === 'percentage' ? tax.value + '%' : '$' + formatNum(tax.value) }}
          </span>
        </div>
        <div class="mt-1" style="font-size:.68rem;color:#6b7280">
          Para impuestos y descuentos personalizados por variante, usa la pestana <strong>Costos</strong>.
        </div>
      </div>

      <div class="d-flex gap-2">
        <button type="button" class="btn btn-sm btn-primary" @click="addVariant" :disabled="actionLoading">
          <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>
          Guardar Variante
        </button>
        <button type="button" class="btn btn-sm btn-light border" @click="cancelVariantForm">Cancelar</button>
      </div>
    </div>

    <!-- ── LISTA DE VARIANTES ── -->
    <div v-if="variantsLoading" class="text-center py-4">
      <div class="spinner-border spinner-border-sm text-primary"></div>
    </div>

    <div v-else-if="!variants.length && !showVariantForm" class="text-center py-4 text-muted">
      <i class="bi bi-layers fs-3 d-block mb-2 opacity-50"></i>
      <p class="small mb-2">Sin variantes. Agrega la primera con el boton.</p>
    </div>

    <div v-else-if="variants.length" class="d-flex flex-column gap-2">
      <div v-for="v in variants" :key="v.uuid" class="border rounded-3 overflow-hidden">

        <!-- MODO EDICION INLINE -->
        <div v-if="editingVariant?.uuid === v.uuid" class="p-3 bg-light">
          <h6 class="fw-semibold small mb-3">Editando: <code>{{ v.sku }}</code></h6>

          <div class="row g-2 mb-2">
            <div class="col-4">
              <label class="form-label smaller mb-1 fw-semibold">Stock</label>
              <input v-model.number="editingVariant.stock" type="number" min="0"
                     class="form-control form-control-sm">
            </div>
            <div class="col-8 d-flex align-items-end pb-1">
              <div class="form-check form-switch ms-1">
                <input v-model="editingVariant.is_default" type="checkbox"
                       class="form-check-input" :id="'edf-' + v.uuid">
                <label class="form-check-label smaller" :for="'edf-' + v.uuid">Default</label>
              </div>
            </div>
          </div>

          <div class="row g-2 mb-2">
            <div class="col-6">
              <label class="form-label smaller mb-1 fw-semibold">Precio base <span class="text-danger">*</span></label>
              <div class="input-group input-group-sm">
                <span class="input-group-text">$</span>
                <input v-model.number="editingVariant.price" type="number" step="0.01" min="0.01"
                       class="form-control">
              </div>
            </div>
            <div class="col-6">
              <label class="form-label smaller mb-1 fw-semibold">Precio con descuento</label>
              <div class="input-group input-group-sm">
                <span class="input-group-text">$</span>
                <input v-model.number="editingVariant.discounted_price" type="number" step="0.01"
                       min="0" class="form-control" placeholder="Opcional">
              </div>
            </div>
          </div>

          <div class="row g-2 mb-2">
            <div class="col-6">
              <label class="form-label smaller mb-0">Descuento desde</label>
              <input v-model="editingVariant.discount_start_date" type="datetime-local"
                     class="form-control form-control-sm">
            </div>
            <div class="col-6">
              <label class="form-label smaller mb-0">Descuento hasta</label>
              <input v-model="editingVariant.discount_end_date" type="datetime-local"
                     class="form-control form-control-sm">
            </div>
          </div>

          <!-- Atributos edicion -->
          <div class="mb-2">
            <div class="d-flex justify-content-between align-items-center mb-1">
              <label class="form-label smaller mb-0 fw-semibold">Atributos</label>
              <button type="button" class="btn btn-xs btn-outline-secondary"
                      @click="addAttrRow(editingVariant)">
                <i class="bi bi-plus"></i>
              </button>
            </div>
            <div v-for="(row, i) in editingVariant.attrRows" :key="i" class="row g-1 mb-1">
              <div class="col-5">
                <input v-model="row.key" type="text" class="form-control form-control-sm"
                       placeholder="Nombre">
              </div>
              <div class="col-5">
                <input v-model="row.value" type="text" class="form-control form-control-sm"
                       placeholder="Valor">
              </div>
              <div class="col-2">
                <button type="button" class="btn btn-xs btn-light border w-100"
                        @click="removeAttrRow(editingVariant, i)">
                  <i class="bi bi-x text-danger"></i>
                </button>
              </div>
            </div>
          </div>

          <!-- Logistica edicion -->
          <p class="smaller fw-semibold text-muted mb-1 mt-2">
            <i class="bi bi-truck me-1"></i>Logistica / Transporte
          </p>
          <div class="row g-1 mb-2">
            <div class="col-3">
              <label class="form-label smaller mb-0">Peso (kg)</label>
              <input v-model.number="editingVariant.weight" type="number" step="0.01" min="0"
                     class="form-control form-control-sm">
            </div>
            <div class="col-3">
              <label class="form-label smaller mb-0">Largo (cm)</label>
              <input v-model.number="editingVariant.length" type="number" step="0.01" min="0"
                     class="form-control form-control-sm">
            </div>
            <div class="col-3">
              <label class="form-label smaller mb-0">Ancho (cm)</label>
              <input v-model.number="editingVariant.width" type="number" step="0.01" min="0"
                     class="form-control form-control-sm">
            </div>
            <div class="col-3">
              <label class="form-label smaller mb-0">Alto (cm)</label>
              <input v-model.number="editingVariant.height" type="number" step="0.01" min="0"
                     class="form-control form-control-sm">
            </div>
          </div>

          <!-- Impuestos activos -->
          <div v-if="taxes.length" class="mb-3 p-2 rounded-2 border" style="background:#f8fafc">
            <p class="smaller fw-semibold text-muted mb-1">
              <i class="bi bi-percent me-1 text-primary"></i>Impuestos del sistema
            </p>
            <div class="d-flex flex-wrap gap-1">
              <span v-for="tax in taxes" :key="tax.uuid"
                    class="badge bg-primary-subtle text-primary border border-primary-subtle"
                    style="font-size:.68rem">
                {{ tax.name }} &middot;
                {{ tax.tax_type === 'percentage' ? tax.value + '%' : '$' + formatNum(tax.value) }}
              </span>
            </div>
          </div>

          <div class="d-flex gap-2">
            <button type="button" class="btn btn-sm btn-primary" @click="saveVariant"
                    :disabled="actionLoading">
              <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>
              Guardar Variante
            </button>
            <button type="button" class="btn btn-sm btn-light border"
                    @click="editingVariant = null; showVariantForm = false">
              Cancelar
            </button>
          </div>
        </div>

        <!-- MODO VISTA -->
        <div v-else class="p-3">
          <div class="d-flex align-items-start justify-content-between gap-2">
            <div class="flex-grow-1">

              <!-- Encabezado -->
              <div class="d-flex align-items-center gap-2 flex-wrap">
                <code class="fw-bold text-dark">{{ v.sku }}</code>
                <span v-if="v.is_default"
                      class="badge bg-primary-subtle text-primary border smaller">Default</span>
                <span class="badge rounded-pill smaller"
                      :class="v.stock > 0
                        ? 'bg-success-subtle text-success'
                        : 'bg-danger-subtle text-danger'">
                  {{ v.stock }} un.
                </span>
                <span v-if="isDiscountActive(v)"
                      class="badge bg-warning-subtle text-warning border smaller">
                  <i class="bi bi-clock me-1"></i>Descuento activo
                </span>
              </div>

              <!-- Precios -->
              <div class="mt-1 d-flex align-items-center gap-2">
                <span class="fw-bold text-dark">${{ formatNum(v.price) }}</span>
                <span v-if="v.discounted_price" class="text-success fw-semibold smaller">
                  <i class="bi bi-arrow-down-short"></i>${{ formatNum(v.discounted_price) }}
                  <span class="text-muted fw-normal">oferta</span>
                </span>
              </div>

              <!-- Desglose financiero price_info -->
              <div v-if="v.price_info"
                   class="mt-2 p-2 rounded-2 border" style="background:#f8fafc;font-size:.72rem">
                <div class="d-flex justify-content-between text-muted mb-1">
                  <span>Precio base</span>
                  <span class="fw-semibold text-dark">${{ formatNum(v.price_info.base_price) }}</span>
                </div>
                <div v-if="v.price_info.has_discount"
                     class="d-flex justify-content-between text-success mb-1">
                  <span><i class="bi bi-tag me-1"></i>Precio oferta activo</span>
                  <span class="fw-semibold">${{ formatNum(v.price_info.discounted_price) }}</span>
                </div>
                <template v-if="v.price_info.applied_taxes?.length">
                  <div v-for="tax in v.price_info.applied_taxes" :key="tax.name"
                       class="d-flex justify-content-between text-muted">
                    <span>
                      <i class="bi bi-percent me-1"></i>{{ tax.name }}
                      ({{ tax.rate }}{{ tax.tax_type === 'percentage' ? '%' : '$' }})
                    </span>
                    <span>+${{ formatNum(tax.amount) }}</span>
                  </div>
                </template>
                <div class="d-flex justify-content-between border-top mt-1 pt-1 fw-bold text-dark">
                  <span>Precio final con imp.</span>
                  <span class="text-primary">${{ formatNum(v.price_info.final_price_net) }}</span>
                </div>
              </div>

              <!-- Dimensiones logisticas -->
              <div v-if="v.weight || v.length || v.width || v.height"
                   class="mt-1 text-muted" style="font-size:.72rem">
                <i class="bi bi-truck me-1"></i>
                <template v-if="v.weight">{{ v.weight }} kg</template>
                <template v-if="v.length">
                  &nbsp;&middot;&nbsp;{{ v.length }}x{{ v.width }}x{{ v.height }} cm
                </template>
              </div>

              <!-- Atributos -->
              <div v-if="Object.keys(v.attributes || {}).length"
                   class="mt-1 d-flex flex-wrap gap-1">
                <span v-for="(val, key) in v.attributes" :key="key"
                      class="badge bg-secondary-subtle text-secondary border smaller">
                  {{ key }}: {{ val }}
                </span>
              </div>

            </div>

            <!-- Acciones -->
            <div class="btn-group btn-group-sm flex-shrink-0">
              <button type="button" class="btn btn-light border-end"
                      @click="startEditVariant(v)" title="Editar">
                <i class="bi bi-pencil text-primary" style="font-size:.75rem"></i>
              </button>
              <button type="button" class="btn btn-light"
                      @click="onDeleteVariant(v)" :disabled="actionLoading" title="Eliminar">
                <i class="bi bi-trash text-danger" style="font-size:.75rem"></i>
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>

    <!-- Footer Variantes -->
    <div class="d-flex justify-content-end mt-4 pt-2 border-top">
      <button type="button" class="btn btn-light border" @click="$emit('close')">Cerrar</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useShopAdminStore } from '@/store/shopAdmin';
import { formatNum } from './helpers';

const props = defineProps({
  productUuid: { type: String, required: true },
});
const emit = defineEmits(['close', 'saved']);

const toast = useToast();
const { handleError } = useErrorHandler();
const store = useShopAdminStore();
const { variants, variantsLoading, actionLoading, activeTaxes: taxes } = storeToRefs(store);

const showVariantForm = ref(false);
const editingVariant = ref(null);

const emptyNewVariant = () => ({
  price: null, discounted_price: null, stock: 0, is_default: false,
  discount_start_date: '', discount_end_date: '',
  attrRows: [],
  weight: null, length: null, width: null, height: null,
});
const newVariant = ref(emptyNewVariant());

const attrsToRows = (attrs) => Object.entries(attrs || {}).map(([key, value]) => ({ key, value }));
const rowsToAttrs = (rows) => Object.fromEntries(
  rows.filter(r => r.key?.trim()).map(r => [r.key.trim(), r.value])
);
const addAttrRow = (target) => target.attrRows.push({ key: '', value: '' });
const removeAttrRow = (target, i) => target.attrRows.splice(i, 1);

const toLocalDT = (iso) => iso ? iso.substring(0, 16) : '';
const fromLocalDT = (local) => local ? local + ':00' : null;

const cleanNum = (val) => {
  if (val === '' || val === null || val === undefined) return null;
  if (typeof val === 'number' && Number.isNaN(val)) return null;
  return val;
};

const isDiscountActive = (v) => {
  if (!v.discounted_price) return false;
  const now = new Date();
  return (
    (!v.discount_start_date || now >= new Date(v.discount_start_date)) &&
    (!v.discount_end_date || now <= new Date(v.discount_end_date))
  );
};

async function fetchVariants() {
  if (!props.productUuid) return;
  await store.fetchVariants(props.productUuid);
  if (store.error) toast.error(store.error);
}

function openNewVariantForm() {
  editingVariant.value = null;
  newVariant.value = emptyNewVariant();
  showVariantForm.value = true;
}
function cancelVariantForm() {
  showVariantForm.value = false;
  editingVariant.value = null;
  newVariant.value = emptyNewVariant();
}

async function addVariant() {
  const nv = newVariant.value;
  if (!nv.price || Number(nv.price) <= 0) return toast.error('Precio base requerido (> 0)');

  const res = await store.createVariant(props.productUuid, {
    price: nv.price,
    discounted_price: cleanNum(nv.discounted_price),
    stock: cleanNum(nv.stock) ?? 0,
    is_default: nv.is_default,
    attributes: rowsToAttrs(nv.attrRows),
    discount_start_date: fromLocalDT(nv.discount_start_date),
    discount_end_date: fromLocalDT(nv.discount_end_date),
    weight: cleanNum(nv.weight),
    length: cleanNum(nv.length),
    width: cleanNum(nv.width),
    height: cleanNum(nv.height),
  });
  if (res.ok) {
    toast.success('Variante agregada');
    cancelVariantForm();
    await fetchVariants();
  } else {
    handleError(res.error, 'Error al agregar variante');
  }
}

function startEditVariant(v) {
  editingVariant.value = {
    ...v,
    price: parseFloat(v.price) || null,
    discounted_price: v.discounted_price ? parseFloat(v.discounted_price) : null,
    stock: v.stock ?? 0,
    discount_start_date: toLocalDT(v.discount_start_date),
    discount_end_date: toLocalDT(v.discount_end_date),
    attrRows: attrsToRows(v.attributes),
  };
  showVariantForm.value = true;
}

async function saveVariant() {
  if (!editingVariant.value) return;
  const ev = editingVariant.value;
  const res = await store.updateVariant(props.productUuid, ev.uuid, {
    price: ev.price,
    discounted_price: cleanNum(ev.discounted_price),
    stock: cleanNum(ev.stock) ?? 0,
    is_default: ev.is_default,
    attributes: rowsToAttrs(ev.attrRows),
    discount_start_date: fromLocalDT(ev.discount_start_date),
    discount_end_date: fromLocalDT(ev.discount_end_date),
    weight: cleanNum(ev.weight),
    length: cleanNum(ev.length),
    width: cleanNum(ev.width),
    height: cleanNum(ev.height),
  });
  if (res.ok) {
    toast.success('Variante actualizada');
    editingVariant.value = null;
    showVariantForm.value = false;
    await fetchVariants();
    emit('saved');
  } else {
    handleError(res.error, 'Error al actualizar variante');
  }
}

async function onDeleteVariant(v) {
  const res = await store.deleteVariant(props.productUuid, v.uuid);
  if (res.ok) {
    toast.success('Variante eliminada');
    await fetchVariants();
  } else {
    toast.error('Error al eliminar la variante');
  }
}

onMounted(fetchVariants);
</script>

<style scoped>
.smaller { font-size: 0.78rem; }
.btn-xs {
  padding: 0.1rem 0.35rem;
  font-size: 0.75rem;
  line-height: 1.3;
}
</style>
