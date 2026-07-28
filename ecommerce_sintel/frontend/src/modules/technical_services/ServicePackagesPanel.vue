<template>
  <div class="p-1">
    <div class="d-flex align-items-center justify-content-between mb-3">
      <p class="text-muted small mb-0">
        Configura los paquetes que el cliente puede elegir al solicitar este servicio. Un servicio sin paquetes se sigue contratando igual (compatibilidad garantizada).
      </p>
      <button class="btn btn-primary btn-sm" @click="beginCreate" :disabled="isCreating">
        <i class="bi bi-plus-lg me-1"></i> Nuevo paquete
      </button>
    </div>

    <!-- Formulario nuevo paquete -->
    <div v-if="isCreating" class="card border-0 bg-light p-3 mb-3 rounded-3">
      <h6 class="fw-semibold small mb-3">Nuevo paquete</h6>
      <PackageFormFields v-model="newPackage" />
      <div class="d-flex justify-content-end gap-2 pt-2 border-top mt-2">
        <button class="btn btn-sm btn-light border" @click="cancelCreate">Cancelar</button>
        <button class="btn btn-sm btn-success" @click="handleCreate" :disabled="store.actionLoading">
          <span v-if="store.actionLoading" class="spinner-border spinner-border-sm me-1"></span>
          Guardar
        </button>
      </div>
    </div>

    <div v-if="store.loading && !store.packages.length" class="text-center py-4">
      <div class="spinner-border spinner-border-sm text-primary"></div>
    </div>
    <div v-else-if="!store.packages.length && !isCreating" class="text-center py-4 text-muted">
      <i class="bi bi-box-seam fs-3 d-block mb-2 opacity-50"></i>
      <p class="small mb-0">Sin paquetes configurados. El servicio se contrata directamente por variante.</p>
    </div>

    <div v-else class="d-flex flex-column gap-2">
      <div v-for="pkg in store.packages" :key="pkg.uuid" class="border rounded-3 overflow-hidden">

        <!-- Modo edicion -->
        <div v-if="editingPkg?.uuid === pkg.uuid" class="bg-light p-3">
          <h6 class="fw-semibold small mb-3">Editando: {{ pkg.name }}</h6>
          <PackageFormFields v-model="editingPkg" />
          <div class="d-flex justify-content-end gap-2 pt-2 border-top mt-2">
            <button class="btn btn-sm btn-light border" @click="editingPkg = null">Cancelar</button>
            <button class="btn btn-sm btn-warning text-dark fw-medium" @click="saveEdit" :disabled="store.actionLoading">
              <span v-if="store.actionLoading" class="spinner-border spinner-border-sm me-1"></span>
              Guardar
            </button>
          </div>
        </div>

        <!-- Fila borrado -->
        <div v-else-if="pendingDelete?.uuid === pkg.uuid" class="bg-danger-subtle p-3 d-flex align-items-center gap-3">
          <i class="bi bi-exclamation-triangle-fill text-danger"></i>
          <span class="small">¿Eliminar el paquete <strong>{{ pkg.name }}</strong>? Los pedidos existentes conservan su snapshot.</span>
          <div class="ms-auto d-flex gap-2">
            <button class="btn btn-sm btn-danger" @click="handleDelete(pkg)" :disabled="store.actionLoading">Confirmar</button>
            <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
          </div>
        </div>

        <!-- Modo vista -->
        <div v-else class="p-3">
          <div class="d-flex align-items-start justify-content-between gap-2">
            <div class="flex-grow-1">
              <div class="d-flex align-items-center gap-2 flex-wrap">
                <span class="fw-bold text-dark">{{ pkg.name }}</span>
                <span v-if="pkg.is_default" class="badge bg-primary-subtle text-primary border border-primary-subtle smaller">Por defecto</span>
                <span v-if="pkg.is_featured" class="badge bg-warning-subtle text-warning border border-warning-subtle smaller">Destacado</span>
                <span class="badge rounded-pill smaller" :class="pkg.is_active ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'">
                  <i :class="pkg.is_active ? 'bi bi-check-circle me-1' : 'bi bi-x-circle me-1'"></i>
                  {{ pkg.is_active ? 'Activo' : 'Inactivo' }}
                </span>
              </div>
              <p v-if="pkg.description" class="text-muted small mt-1 mb-1">{{ pkg.description }}</p>
              <div class="d-flex align-items-center gap-3 mt-1 small text-muted">
                <span class="fw-bold text-dark">${{ formatNum(pkg.base_price) }} COP</span>
                <span v-if="pkg.estimated_duration"><i class="bi bi-clock me-1"></i>{{ pkg.estimated_duration }} h</span>
                <span><i class="bi bi-list-check me-1"></i>{{ pkg.included_items?.length || 0 }} incluidos</span>
                <span><i class="bi bi-tags me-1"></i>{{ pkg.additional_costs?.length || 0 }} costos adicionales</span>
              </div>
            </div>
            <div class="btn-group btn-group-sm flex-shrink-0">
              <button class="btn btn-light border-end" @click="toggleExpand(pkg)" :title="expandedUuid === pkg.uuid ? 'Ocultar detalle' : 'Gestionar incluidos y costos'">
                <i class="bi" :class="expandedUuid === pkg.uuid ? 'bi-chevron-up' : 'bi-chevron-down'" style="font-size:.75rem"></i>
              </button>
              <button class="btn btn-light border-end" @click="startEdit(pkg)" title="Editar">
                <i class="bi bi-pencil text-primary" style="font-size:.75rem"></i>
              </button>
              <button class="btn btn-light border-end" @click="handleToggleActive(pkg)" :disabled="store.actionLoading" title="Activar/Desactivar">
                <i class="bi bi-power" :class="pkg.is_active ? 'text-danger' : 'text-success'" style="font-size:.75rem"></i>
              </button>
              <button class="btn btn-light border-end" @click="handleDuplicate(pkg)" :disabled="store.actionLoading" title="Duplicar">
                <i class="bi bi-copy text-info" style="font-size:.75rem"></i>
              </button>
              <button class="btn btn-light" @click="pendingDelete = pkg" title="Eliminar">
                <i class="bi bi-trash text-danger" style="font-size:.75rem"></i>
              </button>
            </div>
          </div>
        </div>

        <!-- Detalle expandido: incluidos + costos adicionales -->
        <div v-if="expandedUuid === pkg.uuid" class="border-top bg-light-subtle p-3">
          <PackageChildManager
            :package-uuid="pkg.uuid"
            resource="included-items"
            title="Items incluidos"
            icon="bi-list-check"
            :items="store.packageIncludedItems"
            :loading="store.loading"
            :empty-fields="emptyIncludedItem"
            :fetch="store.fetchPackageIncludedItems"
            :create="store.createPackageIncludedItem"
            :update="store.updatePackageIncludedItem"
            :remove="store.deletePackageIncludedItem"
          >
            <template #fields="{ model }">
              <div class="row g-2">
                <div class="col-12">
                  <input v-model="model.title" type="text" class="form-control form-control-sm" placeholder="Titulo (ej: 8 camaras)">
                </div>
                <div class="col-8">
                  <input v-model="model.description" type="text" class="form-control form-control-sm" placeholder="Descripcion (opcional)">
                </div>
                <div class="col-4">
                  <input v-model="model.icon" type="text" class="form-control form-control-sm" placeholder="bi-camera-video">
                </div>
              </div>
            </template>
            <template #display="{ item }">
              <i v-if="item.icon" :class="['bi', item.icon]" class="me-1 text-primary"></i>
              <span class="fw-semibold small">{{ item.title }}</span>
              <span v-if="item.description" class="text-muted small ms-1">- {{ item.description }}</span>
            </template>
          </PackageChildManager>

          <hr class="my-3">

          <PackageChildManager
            :package-uuid="pkg.uuid"
            resource="additional-costs"
            title="Costos adicionales"
            icon="bi-tags"
            :items="store.packageAdditionalCosts"
            :loading="store.loading"
            :empty-fields="emptyAdditionalCost"
            :fetch="store.fetchPackageAdditionalCosts"
            :create="store.createPackageAdditionalCost"
            :update="store.updatePackageAdditionalCost"
            :remove="store.deletePackageAdditionalCost"
          >
            <template #fields="{ model }">
              <div class="row g-2">
                <div class="col-6">
                  <input v-model="model.name" type="text" class="form-control form-control-sm" placeholder="Nombre (ej: Trabajo en altura)">
                </div>
                <div class="col-6">
                  <select v-model="model.cost_type" class="form-select form-select-sm">
                    <option v-for="opt in COST_TYPE_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                  </select>
                </div>
                <div class="col-4">
                  <input v-model.number="model.price" type="number" step="100" min="0" class="form-control form-control-sm" placeholder="Precio">
                </div>
                <div class="col-4">
                  <select v-model="model.unit" class="form-select form-select-sm">
                    <option v-for="opt in UNIT_OPTIONS" :key="opt.value" :value="opt.value">{{ opt.label }}</option>
                  </select>
                </div>
                <div class="col-4 d-flex align-items-center gap-2">
                  <div class="form-check form-check-inline mb-0">
                    <input v-model="model.is_required" class="form-check-input" type="checkbox" :id="'req-'+pkg.uuid">
                    <label class="form-check-label smaller" :for="'req-'+pkg.uuid">Obligatorio</label>
                  </div>
                </div>
                <div class="col-12">
                  <div class="form-check form-check-inline mb-0">
                    <input v-model="model.is_default" class="form-check-input" type="checkbox" :id="'def-'+pkg.uuid">
                    <label class="form-check-label smaller" :for="'def-'+pkg.uuid">Preseleccionado por defecto</label>
                  </div>
                </div>
              </div>
            </template>
            <template #display="{ item }">
              <span class="fw-semibold small">{{ item.name }}</span>
              <span class="badge bg-light text-secondary border smaller ms-1">{{ item.cost_type_display }}</span>
              <span class="text-muted small ms-1">${{ formatNum(item.price) }} ({{ item.unit_display }})</span>
              <span v-if="item.is_required" class="badge bg-danger-subtle text-danger smaller ms-1">Obligatorio</span>
              <span v-if="item.is_default" class="badge bg-info-subtle text-info smaller ms-1">Default</span>
            </template>
          </PackageChildManager>
        </div>
      </div>
    </div>

    <div class="d-flex justify-content-end mt-4 pt-2 border-top">
      <button type="button" class="btn btn-light border" @click="$emit('close')">Cerrar</button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import { useTechnicalServicePackagesStore } from '@/store/technicalServicesAdmin/packages';
import { useToast } from '@/composables/useToast';
import { formatCOP } from '@/utils/money';
import PackageFormFields from './PackageFormFields.vue';
import PackageChildManager from './PackageChildManager.vue';

const props = defineProps({
  service: { type: Object, required: true },
});
defineEmits(['close']);

const store = useTechnicalServicePackagesStore();
const toast = useToast();

const isCreating = ref(false);
const newPackage = ref({});
const editingPkg = ref(null);
const pendingDelete = ref(null);
const expandedUuid = ref(null);

const COST_TYPE_OPTIONS = [
  { value: 'HERRAMIENTA', label: 'Herramienta' },
  { value: 'ESCALERA', label: 'Escalera' },
  { value: 'ACCESORIO', label: 'Accesorio' },
  { value: 'CONSUMIBLE', label: 'Consumible' },
  { value: 'OPERARIO', label: 'Operario' },
  { value: 'SUPERVISOR', label: 'Supervisor' },
  { value: 'TRABAJO_ALTURA', label: 'Trabajo en altura' },
  { value: 'HORARIO_NOCTURNO', label: 'Horario nocturno' },
  { value: 'URGENCIA', label: 'Urgencia' },
  { value: 'OTRO', label: 'Otro' },
];
const UNIT_OPTIONS = [
  { value: 'FIJO', label: 'Fijo' },
  { value: 'HORA', label: 'Por hora' },
  { value: 'DIA', label: 'Por dia' },
  { value: 'UNIDAD', label: 'Por unidad' },
  { value: 'PERSONA', label: 'Por persona' },
];

const emptyIncludedItem = () => ({ title: '', description: '', icon: '', is_active: true });
const emptyAdditionalCost = () => ({
  name: '', description: '', cost_type: 'OTRO', price: 0, unit: 'FIJO',
  is_required: false, is_default: false, is_active: true,
});

const emptyPackage = () => ({
  name: '', description: '', package_type: '', icon: '',
  is_default: false, is_featured: false, is_active: true,
  estimated_duration: null, base_price: 0, notes: '',
});

const load = () => {
  if (props.service?.uuid) store.fetchPackages(props.service.uuid);
};
watch(() => props.service?.uuid, load, { immediate: true });

function beginCreate() {
  newPackage.value = emptyPackage();
  isCreating.value = true;
}
function cancelCreate() {
  isCreating.value = false;
}

async function handleCreate() {
  if (!newPackage.value.name?.trim()) return toast.error('El nombre es requerido.');
  const { ok, error } = await store.createPackage(props.service.uuid, newPackage.value);
  if (ok) {
    toast.success('Paquete creado.');
    cancelCreate();
  } else {
    toast.error(error || 'Error al crear el paquete.');
  }
}

function startEdit(pkg) {
  editingPkg.value = { ...pkg };
}

async function saveEdit() {
  const { ok, error } = await store.updatePackage(editingPkg.value.uuid, props.service.uuid, editingPkg.value);
  if (ok) {
    toast.success('Paquete actualizado.');
    editingPkg.value = null;
  } else {
    toast.error(error || 'Error al actualizar el paquete.');
  }
}

async function handleDelete(pkg) {
  const { ok, error } = await store.deletePackage(pkg.uuid, props.service.uuid);
  if (ok) {
    toast.success('Paquete eliminado.');
    pendingDelete.value = null;
  } else {
    toast.error(error || 'Error al eliminar el paquete.');
  }
}

async function handleToggleActive(pkg) {
  const { ok, error } = await store.togglePackage(pkg.uuid, props.service.uuid);
  if (ok) toast.success(pkg.is_active ? 'Paquete desactivado.' : 'Paquete activado.');
  else toast.error(error || 'Error al cambiar el estado.');
}

async function handleDuplicate(pkg) {
  const { ok, error } = await store.duplicatePackage(pkg.uuid, props.service.uuid);
  if (ok) toast.success('Paquete duplicado.');
  else toast.error(error || 'Error al duplicar el paquete.');
}

function toggleExpand(pkg) {
  if (expandedUuid.value === pkg.uuid) {
    expandedUuid.value = null;
    return;
  }
  expandedUuid.value = pkg.uuid;
  store.fetchPackageIncludedItems(pkg.uuid);
  store.fetchPackageAdditionalCosts(pkg.uuid);
}

const formatNum = (val) => {
  if (val == null || val === '') return '0';
  return formatCOP(val);
};
</script>

<style scoped>
.smaller { font-size: 0.7rem; }
</style>
