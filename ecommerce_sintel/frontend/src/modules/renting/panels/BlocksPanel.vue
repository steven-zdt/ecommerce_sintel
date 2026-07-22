<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-3">
      <h6 class="fw-semibold mb-0">Bloqueos de Equipo</h6>
      <button class="btn btn-sm btn-primary" @click="showCreateForm = !showCreateForm">
        <i class="bi bi-plus-lg me-1"></i> Nuevo bloqueo
      </button>
    </div>

    <!-- Formulario inline de nuevo bloqueo -->
    <div v-if="showCreateForm" class="action-form card border-0 shadow-sm mb-3">
      <div class="card-body">
        <div class="row g-2">
          <div class="col-md-4">
            <label class="form-label small text-muted">Variante</label>
            <select v-model="form.equipment_variant" class="form-select form-select-sm">
              <option v-for="v in store.variants" :key="v.uuid" :value="v.uuid">{{ v.sku }}</option>
            </select>
          </div>
          <div class="col-md-4">
            <label class="form-label small text-muted">Motivo del bloqueo</label>
            <select v-model="form.block_type" class="form-select form-select-sm">
              <option value="MAINTENANCE">Mantenimiento</option>
              <option value="DAMAGE">Daño</option>
              <option value="INVENTORY">Conteo de inventario</option>
              <option value="OTHER">Otro</option>
            </select>
          </div>
          <div class="col-md-2">
            <label class="form-label small text-muted">Desde</label>
            <input v-model="form.start_date" type="date" class="form-control form-control-sm" />
          </div>
          <div class="col-md-2">
            <label class="form-label small text-muted">Hasta</label>
            <input v-model="form.end_date" type="date" class="form-control form-control-sm" />
          </div>
          <div class="col-12">
            <label class="form-label small text-muted">Motivo (detalle)</label>
            <textarea v-model="form.reason" class="form-control form-control-sm" rows="2" placeholder="Ej: compresor requiere mantenimiento preventivo..."></textarea>
          </div>
        </div>
        <div class="mt-3">
          <button class="btn btn-sm btn-primary" :disabled="store.actionLoading || !canSubmit" @click="createBlock">
            <span v-if="store.actionLoading" class="spinner-border spinner-border-sm me-1"></span>
            Confirmar bloqueo
          </button>
          <button class="btn btn-sm btn-light border ms-2" @click="showCreateForm = false">Cancelar</button>
        </div>
      </div>
    </div>

    <!-- Tabla de bloqueos -->
    <div class="card border-0 shadow-sm">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="bg-light text-muted small text-uppercase">
            <tr>
              <th class="px-3 py-3">SKU</th>
              <th class="py-3">Motivo</th>
              <th class="py-3">Rango</th>
              <th class="py-3 text-center">Estado</th>
              <th class="py-3 text-end px-3">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="store.loading">
              <td colspan="5" class="text-center py-4">
                <div class="spinner-border spinner-border-sm text-primary me-2"></div>
                <span class="text-muted">Cargando bloqueos...</span>
              </td>
            </tr>
            <tr v-else-if="!store.equipmentBlocks.length">
              <td colspan="5" class="text-center py-4 text-muted">
                <i class="bi bi-shield-lock fs-2 d-block mb-2"></i>
                Sin bloqueos registrados.
              </td>
            </tr>
            <template v-for="b in store.equipmentBlocks" :key="b.uuid">
              <tr>
                <td class="px-3 fw-semibold">{{ b.equipment_variant_sku }}</td>
                <td>{{ b.block_type_display }}<br /><small class="text-muted">{{ b.reason }}</small></td>
                <td>{{ b.start_date }} — {{ b.end_date }}</td>
                <td class="text-center">
                  <span
                    class="badge rounded-pill"
                    :class="b.status === 'active' ? 'bg-warning-subtle text-warning' : 'bg-secondary-subtle text-secondary'"
                  >{{ b.status_display }}</span>
                </td>
                <td class="text-end px-3">
                  <button
                    v-if="b.status === 'active'"
                    class="btn btn-sm btn-outline-warning"
                    @click="openRelease = openRelease === b.uuid ? null : b.uuid"
                  >
                    Liberar
                  </button>
                </td>
              </tr>
              <tr v-if="openRelease === b.uuid">
                <td colspan="5" class="bg-light">
                  <div class="action-form">
                    <textarea v-model="releaseReason" class="form-control form-control-sm mb-2" rows="2" placeholder="Motivo de la liberacion (opcional)..."></textarea>
                    <button class="btn btn-sm btn-warning" :disabled="store.actionLoading" @click="releaseBlock(b.uuid)">Confirmar liberacion</button>
                    <button class="btn btn-sm btn-light border ms-2" @click="openRelease = null">Cancelar</button>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRentingCatalogAdminStore } from '@/store/rentingAdmin/catalog';
import { useToast } from '@/composables/useToast';

const props = defineProps({
  equipmentUuid: { type: String, required: true },
});

const store = useRentingCatalogAdminStore();
const toast = useToast();

const showCreateForm = ref(false);
const openRelease = ref(null);
const releaseReason = ref('');

const form = ref({
  equipment_variant: '',
  block_type: 'MAINTENANCE',
  start_date: '',
  end_date: '',
  reason: '',
});

const canSubmit = computed(() =>
  form.value.equipment_variant && form.value.start_date && form.value.end_date && form.value.reason.trim()
);

async function createBlock() {
  const result = await store.createEquipmentBlock({ ...form.value });
  if (result.ok) {
    toast.success('Bloqueo registrado correctamente.');
    showCreateForm.value = false;
    form.value = {
      equipment_variant: store.variants[0]?.uuid || '',
      block_type: 'MAINTENANCE', start_date: '', end_date: '', reason: '',
    };
    await store.fetchEquipmentBlocks(props.equipmentUuid);
  } else {
    toast.error(result.error);
  }
}

async function releaseBlock(uuid) {
  const result = await store.releaseEquipmentBlock(uuid, releaseReason.value);
  if (result.ok) {
    toast.success('Bloqueo liberado.');
    openRelease.value = null;
    releaseReason.value = '';
    await store.fetchEquipmentBlocks(props.equipmentUuid);
  } else {
    toast.error(result.error);
  }
}

onMounted(async () => {
  if (store.variants.length === 0) {
    await store.fetchVariants(props.equipmentUuid);
  }
  form.value.equipment_variant = store.variants[0]?.uuid || '';
  await store.fetchEquipmentBlocks(props.equipmentUuid);
});
</script>

<style scoped>
.action-form { max-width: 640px; }
</style>
