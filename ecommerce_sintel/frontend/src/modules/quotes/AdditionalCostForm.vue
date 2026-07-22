<template>
  <div class="modal d-block" tabindex="-1" style="background: rgba(0,0,0,.45);">
    <div class="modal-dialog modal-lg modal-dialog-centered modal-dialog-scrollable">
      <div class="modal-content border-0 shadow">

        <div class="modal-header border-bottom">
          <h5 class="modal-title fw-bold">
            {{ isEdit ? 'Editar Costo Adicional' : 'Nuevo Costo Adicional' }}
          </h5>
          <button type="button" class="btn-close" @click="$emit('close')"></button>
        </div>

        <div class="modal-body p-4">
          <form @submit.prevent="submit">

            <!-- Nombre y descripcion -->
            <div class="row g-3 mb-3">
              <div class="col-md-6">
                <label class="form-label fw-semibold small">Nombre <span class="text-danger">*</span></label>
                <input v-model="form.name" type="text" class="form-control" :class="{ 'is-invalid': errors.name }" placeholder="Ej: IVA 19%" required />
                <div v-if="errors.name" class="invalid-feedback">{{ errors.name }}</div>
              </div>
              <div class="col-md-6">
                <label class="form-label fw-semibold small">Descripcion</label>
                <input v-model="form.description" type="text" class="form-control" placeholder="Descripcion opcional" />
              </div>
            </div>

            <!-- Tipo y contexto -->
            <div class="row g-3 mb-3">
              <div class="col-md-4">
                <label class="form-label fw-semibold small">Tipo de Costo <span class="text-danger">*</span></label>
                <select v-model="form.cost_type" class="form-select" :class="{ 'is-invalid': errors.cost_type }" required>
                  <option value="">-- Seleccionar --</option>
                  <option value="FIXED">Fijo ($)</option>
                  <option value="PERCENTAGE">Porcentaje (%)</option>
                </select>
                <div v-if="errors.cost_type" class="invalid-feedback">{{ errors.cost_type }}</div>
              </div>
              <div class="col-md-4">
                <label class="form-label fw-semibold small">Contexto <span class="text-danger">*</span></label>
                <select v-model="form.context" class="form-select" :class="{ 'is-invalid': errors.context }" required>
                  <option value="">-- Seleccionar --</option>
                  <option value="TAX">Impuesto</option>
                  <option value="DISCOUNT">Descuento</option>
                  <option value="TRANSPORT">Transporte</option>
                  <option value="LOGISTICS">Logistica</option>
                  <option value="OPERATIONAL">Operacional</option>
                  <option value="SETUP">Configuracion</option>
                </select>
                <div v-if="errors.context" class="invalid-feedback">{{ errors.context }}</div>
              </div>
              <div class="col-md-4">
                <label class="form-label fw-semibold small">
                  Valor <span class="text-danger">*</span>
                  <span v-if="form.cost_type === 'PERCENTAGE'" class="text-muted">(0–100)</span>
                  <span v-else-if="form.cost_type === 'FIXED'" class="text-muted">($)</span>
                </label>
                <div class="input-group">
                  <span v-if="form.cost_type === 'PERCENTAGE'" class="input-group-text">%</span>
                  <span v-else class="input-group-text">$</span>
                  <input
                    v-model="form.value"
                    type="number"
                    step="0.0001"
                    min="0"
                    :max="form.cost_type === 'PERCENTAGE' ? 100 : undefined"
                    class="form-control"
                    :class="{ 'is-invalid': errors.value }"
                    required
                  />
                  <div v-if="errors.value" class="invalid-feedback">{{ errors.value }}</div>
                </div>
              </div>
            </div>

            <!-- Opciones -->
            <div class="row g-3 mb-3">
              <div class="col-md-6">
                <div class="form-check form-switch">
                  <input v-model="form.applies_globally" class="form-check-input" type="checkbox" id="globalSwitch" />
                  <label class="form-check-label fw-semibold small" for="globalSwitch">
                    Aplicar a todos los productos (global)
                  </label>
                  <div class="text-muted" style="font-size: .75rem;">
                    Si esta activo, se suma automaticamente a cualquier producto sin asignacion especifica.
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="form-check form-switch">
                  <input v-model="form.is_active" class="form-check-input" type="checkbox" id="activeSwitch" />
                  <label class="form-check-label fw-semibold small" for="activeSwitch">
                    Activo
                  </label>
                </div>
              </div>
            </div>

            <!-- Preview del costo -->
            <div v-if="form.cost_type && form.value" class="alert alert-light border mt-2">
              <div class="small fw-semibold text-muted mb-1">Vista previa</div>
              <div v-if="form.context === 'DISCOUNT'" class="text-success">
                <i class="bi bi-tag-fill me-1"></i>
                Descuento de
                <strong>{{ form.cost_type === 'PERCENTAGE' ? form.value + '%' : '$' + Number(form.value).toFixed(2) }}</strong>
                sobre el precio base.
              </div>
              <div v-else class="text-dark">
                <i class="bi bi-plus-circle-fill text-primary me-1"></i>
                Cargo de
                <strong>{{ form.cost_type === 'PERCENTAGE' ? form.value + '%' : '$' + Number(form.value).toFixed(2) }}</strong>
                sobre el precio base.
              </div>
            </div>

            <!-- API Error -->
            <div v-if="apiError" class="alert alert-danger mt-3 small">{{ apiError }}</div>

          </form>
        </div>

        <div class="modal-footer border-top">
          <button type="button" class="btn btn-light" @click="$emit('close')">Cancelar</button>
          <button type="button" class="btn btn-primary px-4" :disabled="saving" @click="submit">
            <span v-if="saving" class="spinner-border spinner-border-sm me-2"></span>
            {{ isEdit ? 'Guardar Cambios' : 'Crear Costo' }}
          </button>
        </div>

      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import useApi from '@/composables/useApi';

const props = defineProps({
  cost: { type: Object, default: null },
});
const emit = defineEmits(['saved', 'close']);

const api     = useApi();
const saving  = ref(false);
const apiError = ref('');
const errors  = reactive({});

const isEdit = computed(() => !!props.cost);

const form = reactive({
  name:            '',
  description:     '',
  cost_type:       '',
  context:         '',
  value:           '',
  applies_globally: false,
  is_active:       true,
});

onMounted(() => {
  if (props.cost) {
    Object.assign(form, {
      name:            props.cost.name,
      description:     props.cost.description || '',
      cost_type:       props.cost.cost_type,
      context:         props.cost.context,
      value:           props.cost.value,
      applies_globally: props.cost.applies_globally,
      is_active:       props.cost.is_active,
    });
  }
});

function validate() {
  Object.keys(errors).forEach(k => delete errors[k]);
  let ok = true;
  if (!form.name.trim())  { errors.name = 'Requerido.'; ok = false; }
  if (!form.cost_type)    { errors.cost_type = 'Requerido.'; ok = false; }
  if (!form.context)      { errors.context = 'Requerido.'; ok = false; }
  if (form.value === '' || form.value === null) { errors.value = 'Requerido.'; ok = false; }
  if (form.cost_type === 'PERCENTAGE' && Number(form.value) > 100) {
    errors.value = 'El porcentaje no puede superar 100.'; ok = false;
  }
  return ok;
}

async function submit() {
  if (!validate()) return;
  saving.value  = true;
  apiError.value = '';
  const payload = {
    name:            form.name.trim(),
    description:     form.description.trim(),
    cost_type:       form.cost_type,
    context:         form.context,
    value:           form.value,
    applies_globally: form.applies_globally,
    is_active:       form.is_active,
  };
  try {
    if (isEdit.value) {
      await api.patch(`dashboard/additional-costs/${props.cost.uuid}/update/`, payload);
    } else {
      await api.post('dashboard/additional-costs/', payload);
    }
    emit('saved');
  } catch (e) {
    const data = e.response?.data;
    if (data && typeof data === 'object') {
      Object.entries(data).forEach(([k, v]) => { errors[k] = Array.isArray(v) ? v[0] : v; });
    } else {
      apiError.value = 'Error al guardar. Intente de nuevo.';
    }
  } finally {
    saving.value = false;
  }
}
</script>
