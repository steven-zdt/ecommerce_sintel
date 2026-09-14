<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-3">
      <p class="text-muted small mb-0">Gestiona los precios, duraciones y complejidades de este servicio.</p>
      <button type="button" class="btn btn-sm btn-primary" @click="openNewVariantForm"
              :disabled="showVariantForm && !editingVar">
        <i class="bi bi-plus-lg me-1"></i>Nueva Variante
      </button>
    </div>

    <!-- Formulario nueva variante (modal-like) -->
    <div v-if="showVariantForm && !editingVar" class="card border-0 bg-light p-3 mb-3 rounded-3">
      <h6 class="fw-semibold small mb-3">Nueva Variante</h6>

      <div class="d-flex gap-3 mb-2" style="font-size:.82rem">
        <div class="form-check">
          <input v-model="newVar.pricing_strategy" class="form-check-input" type="radio" value="FIXED" id="nvPFixed">
          <label class="form-check-label" for="nvPFixed">Precio fijo</label>
        </div>
        <div class="form-check">
          <input v-model="newVar.pricing_strategy" class="form-check-input" type="radio" value="HOURLY" id="nvPHourly">
          <label class="form-check-label" for="nvPHourly">Por horas</label>
        </div>
        <div class="form-check">
          <input v-model="newVar.pricing_strategy" class="form-check-input" type="radio" value="DAILY" id="nvPDaily">
          <label class="form-check-label" for="nvPDaily">Por dias</label>
        </div>
      </div>

      <div class="row g-2 mb-2">
        <template v-if="newVar.pricing_strategy === 'FIXED'">
          <div class="col-12">
            <label class="form-label smaller mb-1 fw-semibold">Precio fijo (COP)</label>
            <div class="input-group input-group-sm">
              <span class="input-group-text">$</span>
              <input v-model.number="newVar.fixed_price" type="number" step="100" min="0"
                     class="form-control" placeholder="0">
            </div>
          </div>
        </template>
        <template v-else>
          <div class="col-6">
            <label class="form-label smaller mb-1 fw-semibold">
              {{ newVar.pricing_strategy === 'DAILY' ? 'Dias estimados' : 'Horas estimadas' }}
            </label>
            <input v-model.number="newVar.estimated_hours" type="number" step="0.5" min="0.5"
                   class="form-control form-control-sm">
          </div>
          <div class="col-6">
            <label class="form-label smaller mb-1 fw-semibold">Complejidad</label>
            <input v-model.number="newVar.complexity_factor" type="number" step="0.1" min="0.1"
                   class="form-control form-control-sm" placeholder="1.0">
          </div>
          <div class="col-6">
            <label class="form-label smaller mb-1">
              Min. ({{ newVar.pricing_strategy === 'DAILY' ? 'd' : 'h' }})
            </label>
            <input v-model.number="newVar.min_duration" type="number" step="0.5" min="0"
                   class="form-control form-control-sm" placeholder="Sin minimo">
          </div>
          <div class="col-6">
            <label class="form-label smaller mb-1">
              Max. ({{ newVar.pricing_strategy === 'DAILY' ? 'd' : 'h' }})
            </label>
            <input v-model.number="newVar.max_duration" type="number" step="0.5" min="0"
                   class="form-control form-control-sm" placeholder="Sin maximo">
          </div>
        </template>

        <!-- Capacidad simultanea -->
        <div class="col-12 mt-1">
          <label class="form-label smaller mb-1 fw-semibold d-flex align-items-center gap-1">
            Capacidad simultanea
            <span class="badge bg-info-subtle text-info border border-info-subtle"
                  style="font-size:.6rem;cursor:help"
                  title="Cuantos servicios de este tipo se pueden atender al mismo tiempo.">
              ?
            </span>
          </label>
          <input v-model.number="newVar.simultaneous_capacity" type="number" min="1" step="1"
                 class="form-control form-control-sm" placeholder="1">
        </div>
      </div>

      <div class="d-flex align-items-center justify-content-between pt-2 border-top mt-1">
        <div class="d-flex gap-3 mb-0">
          <div class="form-check mb-0">
            <input v-model="newVar.is_default" type="checkbox" class="form-check-input" id="nvDefault">
            <label class="form-check-label smaller" for="nvDefault">Por defecto</label>
          </div>
          <div class="form-check form-switch mb-0">
            <input v-model="newVar.is_active" type="checkbox" class="form-check-input" id="nvActive" role="switch">
            <label class="form-check-label smaller" for="nvActive">
              <span :class="newVar.is_active ? 'text-success fw-semibold' : 'text-danger fw-semibold'">
                {{ newVar.is_active ? 'Activa' : 'Inactiva' }}
              </span>
            </label>
          </div>
        </div>
        <div class="d-flex gap-2">
          <button type="button" class="btn btn-sm btn-light border" @click="cancelVariantForm">Cancelar</button>
          <button type="button" class="btn btn-sm btn-primary" @click="addVariant" :disabled="varLoading">
            <span v-if="varLoading" class="spinner-border spinner-border-sm me-1"></span>
            Guardar
          </button>
        </div>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="variantsLoading" class="text-center py-4">
      <div class="spinner-border spinner-border-sm text-primary"></div>
    </div>

    <!-- Empty state -->
    <div v-else-if="!variants.length && !showVariantForm" class="text-center py-4 text-muted">
      <i class="bi bi-layers fs-3 d-block mb-2 opacity-50"></i>
      <p class="small mb-2">Sin variantes. Agrega la primera.</p>
    </div>

    <!-- Tabla de variantes (simplificada) -->
    <div v-else-if="variants.length" class="d-flex flex-column gap-2">
      <div v-for="v in variants" :key="v.uuid" class="border rounded-3 overflow-hidden p-3">

        <!-- Modo edicion -->
        <div v-if="editingVar?.uuid === v.uuid" class="bg-light">
          <h6 class="fw-semibold small mb-3">Editando: <code>{{ v.sku }}</code></h6>

          <div class="d-flex gap-3 mb-2" style="font-size:.82rem">
            <div class="form-check">
              <input v-model="editingVar.pricing_strategy" class="form-check-input" type="radio"
                     value="FIXED" :id="'evPF-'+v.uuid">
              <label class="form-check-label" :for="'evPF-'+v.uuid">Precio fijo</label>
            </div>
            <div class="form-check">
              <input v-model="editingVar.pricing_strategy" class="form-check-input" type="radio"
                     value="HOURLY" :id="'evPH-'+v.uuid">
              <label class="form-check-label" :for="'evPH-'+v.uuid">Por horas</label>
            </div>
            <div class="form-check">
              <input v-model="editingVar.pricing_strategy" class="form-check-input" type="radio"
                     value="DAILY" :id="'evPD-'+v.uuid">
              <label class="form-check-label" :for="'evPD-'+v.uuid">Por dias</label>
            </div>
          </div>

          <div class="row g-2 mb-2">
            <template v-if="editingVar.pricing_strategy === 'FIXED'">
              <div class="col-12">
                <label class="form-label smaller mb-1 fw-semibold">Precio fijo (COP)</label>
                <div class="input-group input-group-sm">
                  <span class="input-group-text">$</span>
                  <input v-model.number="editingVar.fixed_price" type="number" step="100" class="form-control">
                </div>
              </div>
            </template>
            <template v-else>
              <div class="col-6">
                <label class="form-label smaller mb-1 fw-semibold">
                  {{ editingVar.pricing_strategy === 'DAILY' ? 'Dias estimados' : 'Horas estimadas' }}
                </label>
                <input v-model.number="editingVar.estimated_hours" type="number" step="0.5" min="0.5"
                       class="form-control form-control-sm">
              </div>
              <div class="col-6">
                <label class="form-label smaller mb-1 fw-semibold">Complejidad</label>
                <input v-model.number="editingVar.complexity_factor" type="number" step="0.1" min="0.1"
                       class="form-control form-control-sm">
              </div>
              <div class="col-6">
                <label class="form-label smaller mb-1">
                  Min. ({{ editingVar.pricing_strategy === 'DAILY' ? 'd' : 'h' }})
                </label>
                <input v-model.number="editingVar.min_duration" type="number" step="0.5" min="0"
                       class="form-control form-control-sm" placeholder="Sin minimo">
              </div>
              <div class="col-6">
                <label class="form-label smaller mb-1">
                  Max. ({{ editingVar.pricing_strategy === 'DAILY' ? 'd' : 'h' }})
                </label>
                <input v-model.number="editingVar.max_duration" type="number" step="0.5" min="0"
                       class="form-control form-control-sm" placeholder="Sin maximo">
              </div>
            </template>

            <!-- Capacidad (edit) -->
            <div class="col-12 mt-1">
              <label class="form-label smaller mb-1 fw-semibold">Capacidad simultanea</label>
              <input v-model.number="editingVar.simultaneous_capacity" type="number" min="1" step="1"
                     class="form-control form-control-sm" placeholder="1">
            </div>
          </div>

          <div class="d-flex align-items-center justify-content-between pt-2 border-top mt-1">
            <div class="d-flex gap-3 mb-0">
              <div class="form-check mb-0">
                <input v-model="editingVar.is_default" type="checkbox" class="form-check-input" :id="'evDef-'+v.uuid">
                <label class="form-check-label smaller" :for="'evDef-'+v.uuid">Por defecto</label>
              </div>
              <div class="form-check form-switch mb-0">
                <input v-model="editingVar.is_active" type="checkbox" class="form-check-input" :id="'evAct-'+v.uuid" role="switch">
                <label class="form-check-label smaller" :for="'evAct-'+v.uuid">
                  <span :class="editingVar.is_active ? 'text-success fw-semibold' : 'text-danger fw-semibold'">
                    {{ editingVar.is_active ? 'Activa' : 'Inactiva' }}
                  </span>
                </label>
              </div>
            </div>
            <div class="d-flex gap-2">
              <button type="button" class="btn btn-sm btn-light border"
                      @click="editingVar = null; showVariantForm = false">
                Cancelar
              </button>
              <button type="button" class="btn btn-sm btn-warning text-dark fw-medium"
                      @click="saveVariant" :disabled="varLoading">
                <span v-if="varLoading" class="spinner-border spinner-border-sm me-1"></span>
                Guardar
              </button>
            </div>
          </div>
        </div>

        <!-- Modo vista -->
        <div v-else>
          <div class="d-flex align-items-start justify-content-between gap-2">
            <div class="flex-grow-1">
              <div class="d-flex align-items-center gap-2 flex-wrap">
                <code class="fw-bold text-dark">{{ v.sku }}</code>
                <span v-if="v.is_default"
                      class="badge bg-primary-subtle text-primary border border-primary-subtle smaller">Default</span>
                <span class="badge rounded-pill smaller"
                      :class="v.pricing_strategy === 'FIXED'
                        ? 'bg-success-subtle text-success'
                        : 'bg-info-subtle text-info'">
                  {{ v.pricing_strategy === 'FIXED' ? 'Fijo' : v.pricing_strategy === 'DAILY' ? 'Diario' : 'Horario' }}
                </span>
                <!-- Plan "Manual Pricing Engine" FASE 29 -- indicador de pricing_source manual -->
                <span v-if="v.is_manual_pricing" class="badge rounded-pill smaller bg-primary-subtle text-primary border border-primary-subtle">
                  <i class="bi bi-hand-index-thumb me-1"></i>{{ manualPricingLabel(v) }}
                </span>
                <span class="badge rounded-pill smaller"
                      :class="v.is_active ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'">
                  <i :class="v.is_active ? 'bi bi-check-circle me-1' : 'bi bi-x-circle me-1'"></i>
                  {{ v.is_active ? 'Activa' : 'Inactiva' }}
                </span>
              </div>

              <div class="mt-1">
                <span v-if="v.pricing_strategy === 'FIXED'" class="fw-bold text-dark">
                  ${{ formatNum(v.fixed_price) }} COP
                </span>
                <span v-else class="fw-bold text-dark">
                  ~${{ formatNum(v.calculated_price) }}
                  <span class="text-muted fw-normal smaller">
                    ({{ v.estimated_hours }}{{ v.pricing_strategy === 'DAILY' ? 'd' : 'h' }}
                    &times; {{ v.complexity_factor }})
                  </span>
                </span>
                <span v-if="v.pricing_strategy !== 'FIXED' && (v.min_duration || v.max_duration)"
                      class="text-muted smaller ms-1">
                  [{{ v.min_duration || 0 }}&ndash;{{ v.max_duration || '&infin;' }}
                  {{ v.pricing_strategy === 'DAILY' ? 'd' : 'h' }}]
                </span>
              </div>

              <!-- Desglose price_info -->
              <div v-if="v.price_info"
                   class="mt-2 p-2 rounded-2 border" style="background:#f8fafc;font-size:.72rem">
                <div class="d-flex justify-content-between text-muted mb-1">
                  <span>Mano de obra</span>
                  <span class="fw-semibold text-dark">${{ formatNum(v.price_info.labor_cost) }}</span>
                </div>
                <div v-if="v.price_info.material_cost > 0"
                     class="d-flex justify-content-between text-muted mb-1">
                  <span>Materiales</span>
                  <span>${{ formatNum(v.price_info.material_cost) }}</span>
                </div>
                <div v-if="v.price_info.iva_amount > 0"
                     class="d-flex justify-content-between text-muted mb-1">
                  <span>IVA ({{ Number(v.price_info.iva_rate).toFixed(0) }}%)</span>
                  <span>+${{ formatNum(v.price_info.iva_amount) }}</span>
                </div>
                <div class="d-flex justify-content-between border-top mt-1 pt-1 fw-bold text-dark">
                  <span>Total estimado</span>
                  <span class="text-primary">${{ formatNum(v.price_info.total_price || v.price_info.total) }}</span>
                </div>
              </div>
            </div>

            <!-- Acciones -->
            <div class="btn-group btn-group-sm flex-shrink-0">
              <button type="button" class="btn btn-light border-end"
                      @click="viewPriceHistory(v)" title="Historial de precios">
                <i class="bi bi-clock-history text-secondary" style="font-size:.75rem"></i>
              </button>
              <button type="button" class="btn btn-light border-end"
                      @click="startEditVar(v)" title="Editar">
                <i class="bi bi-pencil text-primary" style="font-size:.75rem"></i>
              </button>
              <button type="button" class="btn btn-light border-end"
                      @click="duplicateVariant(v)" :disabled="varLoading" title="Duplicar">
                <i class="bi bi-copy text-info" style="font-size:.75rem"></i>
              </button>
              <button type="button" class="btn btn-light"
                      @click="deleteVariant(v)" :disabled="varLoading" title="Eliminar">
                <i class="bi bi-trash text-danger" style="font-size:.75rem"></i>
              </button>
            </div>
          </div>
        </div>

      </div>
    </div>

    <div class="d-flex justify-content-end mt-4 pt-2 border-top">
      <button type="button" class="btn btn-light border" @click="$emit('close')">Cerrar</button>
    </div>

    <!-- ===================================================================
         MODAL: Historial de Precios
    =================================================================== -->
    <div v-if="selectedVariantForHistory" class="modal-backdrop fade show" style="z-index:1060"
         @click="closePriceHistory"></div>
    <div v-if="selectedVariantForHistory" class="modal fade show d-block" tabindex="-1" style="z-index:1070">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content shadow-lg border-0">
          <div class="modal-header bg-light border-bottom py-3">
            <div>
              <h6 class="modal-title fw-bold mb-0 text-dark">Historial de Precios</h6>
              <span class="text-muted smaller">SKU:
                <strong class="text-primary">{{ selectedVariantForHistory.sku }}</strong>
              </span>
            </div>
            <button type="button" class="btn-close" @click="closePriceHistory"></button>
          </div>
          <div class="modal-body py-4" style="max-height:400px;overflow-y:auto">
            <div v-if="historyLoading" class="text-center py-4">
              <div class="spinner-border spinner-border-sm text-primary me-2"></div>
              <span class="text-muted small">Cargando historial...</span>
            </div>
            <div v-else-if="!priceHistory.length" class="text-muted small text-center py-4">
              <i class="bi bi-clock-history fs-3 d-block mb-2 opacity-50"></i>
              Sin cambios de precio registrados.
            </div>
            <div v-else class="timeline-container">
              <div v-for="h in priceHistory" :key="h.uuid" class="timeline-item">
                <div class="timeline-marker"></div>
                <!-- Plan "Manual Pricing Engine" FASE 24 -- ServicePricingCommands.
                     set_manual_pricing() genera un tipo de entrada distinto
                     (pricing_source_old/new, sin old_price/new_price) al que ya
                     generaba update_variant() para fixed_price. Sin esta rama, una
                     entrada de cambio de fuente de precio se mostraba como
                     "$0 -> $0" (old_price/new_price siempre null en esas filas). -->
                <template v-if="h.pricing_source_new">
                  <div class="d-flex align-items-center justify-content-between mb-1">
                    <span class="badge bg-primary-subtle text-primary border border-primary-subtle fw-bold">
                      <i class="bi bi-hand-index-thumb me-1"></i>{{ pricingSourceLabel(h.pricing_source_new) }}
                    </span>
                    <span class="text-muted smaller fw-medium">{{ formatDate(h.created_at) }}</span>
                  </div>
                  <div class="text-muted smaller mt-2">
                    <div>Fuente anterior: <del class="text-danger">{{ pricingSourceLabel(h.pricing_source_old) }}</del></div>
                    <div v-if="h.unit_price_new">Tarifa: <strong class="text-dark">${{ formatNum(h.unit_price_new) }}</strong></div>
                    <div v-if="h.project_price_new">Precio proyecto: <strong class="text-dark">${{ formatNum(h.project_price_new) }}</strong></div>
                    <div v-if="h.reason" class="mt-1 fst-italic">
                      <i class="bi bi-chat-left-text me-1"></i>{{ h.reason }}
                    </div>
                    <div v-if="h.changed_by_email" class="mt-1 d-flex align-items-center gap-1">
                      <i class="bi bi-person text-muted"></i>
                      Modificado por: <span class="fw-semibold text-dark">{{ h.changed_by_email }}</span>
                    </div>
                  </div>
                </template>
                <template v-else>
                  <div class="d-flex align-items-center justify-content-between mb-1">
                    <span class="badge bg-primary-subtle text-primary border border-primary-subtle fw-bold">
                      ${{ formatNum(h.new_price) }}
                    </span>
                    <span class="text-muted smaller fw-medium">{{ formatDate(h.created_at) }}</span>
                  </div>
                  <div class="text-muted smaller mt-2">
                    <div>Precio anterior: <del class="text-danger">${{ formatNum(h.old_price) }}</del></div>
                    <div v-if="h.changed_by_email" class="mt-1 d-flex align-items-center gap-1">
                      <i class="bi bi-person text-muted"></i>
                      Modificado por: <span class="fw-semibold text-dark">{{ h.changed_by_email }}</span>
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>
          <div class="modal-footer bg-light border-top p-2 d-flex justify-content-end">
            <button type="button" class="btn btn-sm btn-secondary px-3" @click="closePriceHistory">Cerrar</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useTechnicalServicesStore } from '@/store/technicalServicesAdmin/services';
import { useToast } from '@/composables/useToast';
import { formatCOP } from '@/utils/money';
import { cleanNum } from './helpers';

const props = defineProps({
  serviceUuid: { type: String, default: '' },
});
defineEmits(['close']);

const toast = useToast();
const store = useTechnicalServicesStore();
const { variants } = storeToRefs(store);

const variantsLoading = ref(false);
const varLoading = ref(false);
const showVariantForm = ref(false);
const editingVar = ref(null);

const emptyNewVar = () => ({
  pricing_strategy: 'FIXED', fixed_price: '',
  estimated_hours: 1, complexity_factor: 1,
  min_duration: '', max_duration: '',
  simultaneous_capacity: 1,
  is_default: false, is_active: true,
});
const newVar = ref(emptyNewVar());

const selectedVariantForHistory = ref(null);
const priceHistory = ref([]);
const historyLoading = ref(false);

async function fetchVariants() {
  if (!props.serviceUuid) return;
  variantsLoading.value = true;
  try {
    await store.fetchVariants(props.serviceUuid);
  } catch {
    toast.error('Error al cargar variantes');
  } finally {
    variantsLoading.value = false;
  }
}

function openNewVariantForm() {
  editingVar.value = null;
  newVar.value = emptyNewVar();
  showVariantForm.value = true;
}

function cancelVariantForm() {
  showVariantForm.value = false;
  editingVar.value = null;
  newVar.value = emptyNewVar();
}

async function addVariant() {
  const nv = newVar.value;
  const isFixed = nv.pricing_strategy === 'FIXED';
  if (isFixed && !nv.fixed_price) return toast.error('Precio fijo requerido');
  if (!isFixed && !nv.estimated_hours) return toast.error('Horas/dias estimados requeridos');

  varLoading.value = true;
  try {
    const res = await store.createVariant({
      service: props.serviceUuid,
      pricing_strategy: nv.pricing_strategy || 'FIXED',
      fixed_price: isFixed ? (cleanNum(nv.fixed_price) || null) : null,
      estimated_hours: !isFixed ? (cleanNum(nv.estimated_hours) || 1) : 1,
      complexity_factor: !isFixed ? (cleanNum(nv.complexity_factor) || 1) : 1,
      min_duration: !isFixed ? cleanNum(nv.min_duration) : null,
      max_duration: !isFixed ? cleanNum(nv.max_duration) : null,
      simultaneous_capacity: nv.simultaneous_capacity || 1,
      is_default: nv.is_default,
    });
    if (!res.ok) throw new Error(res.error);
    toast.success('Variante agregada');
    cancelVariantForm();
    await fetchVariants();
  } catch (e) {
    toast.error(e.message || 'Error al agregar variante');
  } finally {
    varLoading.value = false;
  }
}

function startEditVar(v) {
  editingVar.value = {
    uuid: v.uuid,
    sku: v.sku,
    pricing_strategy: v.pricing_strategy || (v.fixed_price ? 'FIXED' : 'HOURLY'),
    fixed_price: v.fixed_price ? parseFloat(v.fixed_price) : '',
    estimated_hours: v.estimated_hours ? parseFloat(v.estimated_hours) : 1,
    complexity_factor: v.complexity_factor ? parseFloat(v.complexity_factor) : 1,
    min_duration: v.min_duration ? parseFloat(v.min_duration) : '',
    max_duration: v.max_duration ? parseFloat(v.max_duration) : '',
    simultaneous_capacity: v.simultaneous_capacity ? parseInt(v.simultaneous_capacity) : 1,
    is_default: v.is_default,
    is_active: v.is_active !== undefined ? v.is_active : true,
  };
  showVariantForm.value = true;
}

async function saveVariant() {
  if (!editingVar.value) return;
  varLoading.value = true;
  try {
    const ev = editingVar.value;
    const isFixed = ev.pricing_strategy === 'FIXED';
    const res = await store.updateVariant(ev.uuid, props.serviceUuid, {
      pricing_strategy: ev.pricing_strategy || 'FIXED',
      fixed_price: isFixed ? (cleanNum(ev.fixed_price) || null) : null,
      estimated_hours: !isFixed ? (cleanNum(ev.estimated_hours) || 1) : 1,
      complexity_factor: !isFixed ? (cleanNum(ev.complexity_factor) || 1) : 1,
      min_duration: !isFixed ? cleanNum(ev.min_duration) : null,
      max_duration: !isFixed ? cleanNum(ev.max_duration) : null,
      simultaneous_capacity: ev.simultaneous_capacity || 1,
      is_default: ev.is_default,
    });
    if (!res.ok) throw new Error(res.error);
    toast.success('Variante actualizada');
    editingVar.value = null;
    showVariantForm.value = false;
    await fetchVariants();
  } catch (e) {
    toast.error(e.message || 'Error al actualizar variante');
  } finally {
    varLoading.value = false;
  }
}

async function deleteVariant(v) {
  varLoading.value = true;
  try {
    const res = await store.deleteVariant(v.uuid, props.serviceUuid);
    if (!res.ok) throw new Error(res.error);
    toast.success('Variante eliminada');
    await fetchVariants();
  } catch (e) {
    toast.error(e.message || 'Error al eliminar la variante');
  } finally {
    varLoading.value = false;
  }
}

async function duplicateVariant(v) {
  varLoading.value = true;
  try {
    const isFixed = v.pricing_strategy === 'FIXED';
    const res = await store.createVariant({
      service: props.serviceUuid,
      pricing_strategy: v.pricing_strategy || 'FIXED',
      fixed_price: isFixed ? (cleanNum(v.fixed_price) || null) : null,
      estimated_hours: !isFixed ? (cleanNum(v.estimated_hours) || 1) : 1,
      complexity_factor: !isFixed ? (cleanNum(v.complexity_factor) || 1) : 1,
      min_duration: !isFixed ? cleanNum(v.min_duration) : null,
      max_duration: !isFixed ? cleanNum(v.max_duration) : null,
      simultaneous_capacity: v.simultaneous_capacity || 1,
      is_default: false,
      is_active: v.is_active !== false,
    });
    if (!res.ok) throw new Error(res.error);
    toast.success('Variante duplicada');
    await fetchVariants();
  } catch (e) {
    toast.error(e.message || 'Error al duplicar la variante');
  } finally {
    varLoading.value = false;
  }
}

async function viewPriceHistory(v) {
  selectedVariantForHistory.value = v;
  historyLoading.value = true;
  priceHistory.value = [];
  try {
    const data = await store.fetchVariantsPriceHistory(v.uuid);
    priceHistory.value = data;
  } catch {
    toast.error('Error al cargar el historial de precios');
    selectedVariantForHistory.value = null;
  } finally {
    historyLoading.value = false;
  }
}

function closePriceHistory() {
  selectedVariantForHistory.value = null;
  priceHistory.value = [];
}

const formatNum = (val) => {
  if (val == null || val === '') return '0';
  return formatCOP(val);
};

const MANUAL_PRICING_LABELS = {
  MANUAL_PROJECT: 'Manual por proyecto',
  MANUAL_GENERAL: 'Manual general',
  MANUAL_HOURLY: 'Manual por horas',
};
function manualPricingLabel(v) {
  return MANUAL_PRICING_LABELS[v.pricing_source] || 'Manual';
}

// Plan "Manual Pricing Engine" FASE 24 -- etiqueta para entradas de
// ServicePriceHistory generadas por ServicePricingCommands.set_manual_pricing()
// (pricing_source_old/new), distinto de manualPricingLabel() de arriba (que lee
// de una ServiceVariant real, no de una fila de historial).
const PRICING_SOURCE_HISTORY_LABELS = {
  AUTOMATIC: 'Automático',
  MANUAL_PROJECT: 'Manual — Proyecto completo',
  MANUAL_GENERAL: 'Manual — Precio general',
  MANUAL_HOURLY: 'Manual — Por horas',
};
function pricingSourceLabel(source) {
  return PRICING_SOURCE_HISTORY_LABELS[source] || source || 'Sin definir';
}

const formatDate = (val) => {
  if (!val) return '';
  return new Date(val).toLocaleString('es-CO', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
};

onMounted(fetchVariants);
</script>

<style scoped>
.smaller { font-size: 0.78rem; }
.timeline-container { position: relative; padding-left: 1rem; }
.timeline-item {
  position: relative;
  padding-bottom: 1.5rem;
  border-left: 2px dashed #e2e8f0;
  padding-left: 1.5rem;
}
.timeline-item:last-child { border-left: none; padding-bottom: 0; }
.timeline-marker {
  position: absolute; left: -6px; top: 4px;
  width: 10px; height: 10px;
  border-radius: 50%;
  background-color: #3b82f6;
  border: 2px solid #fff;
}
</style>
