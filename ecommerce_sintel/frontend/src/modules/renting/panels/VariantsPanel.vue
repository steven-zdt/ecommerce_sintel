<template>
  <div>
    <div class="d-flex align-items-center justify-content-between mb-3">
      <h6 class="fw-semibold mb-0">Variantes de Equipo</h6>
      <button class="btn btn-sm btn-primary" @click="openCreate">
        <i class="bi bi-plus-lg me-1"></i> Nueva Variante
      </button>
    </div>

    <!-- Tabla de variantes -->
    <div class="card border-0 shadow-sm">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="bg-light text-muted small text-uppercase">
            <tr>
              <th class="px-3 py-3">SKU</th>
              <th class="py-3">Precio / Día</th>
              <th class="py-3">Precio / Hora</th>
              <th class="py-3 text-center">Stock</th>
              <th class="py-3 text-center">Activa</th>
              <th class="py-3 text-end px-3">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="store.loading">
              <td colspan="6" class="text-center py-4">
                <div class="spinner-border spinner-border-sm text-primary me-2"></div>
                <span class="text-muted">Cargando variantes...</span>
              </td>
            </tr>
            <tr v-else-if="!store.variants.length">
              <td colspan="6" class="text-center py-4 text-muted">
                <i class="bi bi-layers fs-2 d-block mb-2"></i>
                Sin variantes registradas.
              </td>
            </tr>
            <tr v-for="v in store.variants" :key="v.uuid">
              <td class="px-3 fw-semibold">{{ v.sku }}</td>
              <td>{{ formatCOP(v.rental_price_per_day) }}</td>
              <td>{{ formatCOP(v.rental_price_per_hour) || '—' }}</td>
              <td class="text-center">
                <span
                  class="badge rounded-pill"
                  :class="v.stock > 0 ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'"
                >{{ v.stock }}</span>
              </td>
              <td class="text-center">
                <i :class="v.is_active ? 'bi bi-check-circle-fill text-success' : 'bi bi-x-circle text-muted'"></i>
              </td>
              <td class="text-end px-3">
                <div class="btn-group btn-group-sm">
                  <button class="btn btn-light border-end" @click="openEdit(v)" title="Editar">
                    <i class="bi bi-pencil text-primary"></i>
                  </button>
                  <button
                    class="btn btn-light"
                    @click="confirmDelete(v)"
                    :disabled="store.actionLoading"
                    title="Eliminar"
                  >
                    <i class="bi bi-trash text-danger"></i>
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal Crear/Editar -->
    <VariantFormModal
      v-if="showModal"
      :equipment-uuid="equipmentUuid"
      :variant="selectedVariant"
      :mode="formMode"
      @success="onSuccess"
      @close="showModal = false"
    />

    <!-- Confirmación de delete inline -->
    <div v-if="pendingDelete" class="alert alert-danger mt-3 d-flex align-items-center gap-3">
      <i class="bi bi-exclamation-triangle-fill"></i>
      <span>¿Eliminar variante <strong>{{ pendingDelete.sku }}</strong>?</span>
      <div class="ms-auto d-flex gap-2">
        <button class="btn btn-sm btn-danger" @click="executeDelete" :disabled="store.actionLoading">
          <span v-if="store.actionLoading" class="spinner-border spinner-border-sm me-1"></span>
          Confirmar
        </button>
        <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import { useRentingCatalogAdminStore } from '@/store/rentingAdmin/catalog';
import { useToast } from '@/composables/useToast';
import VariantFormModal from '../VariantFormModal.vue';

const props = defineProps({
  equipmentUuid: { type: String, required: true },
});

const store = useRentingCatalogAdminStore();
const toast = useToast();

const showModal = ref(false);
const formMode = ref('create');
const selectedVariant = ref(null);
const pendingDelete = ref(null);

function formatCOP(value) {
  if (!value) return null;
  return new Intl.NumberFormat('es-CO', {
    style: 'currency', currency: 'COP', minimumFractionDigits: 0,
  }).format(value);
}

function openCreate() {
  selectedVariant.value = null;
  formMode.value = 'create';
  showModal.value = true;
}

function openEdit(variant) {
  selectedVariant.value = variant;
  formMode.value = 'edit';
  showModal.value = true;
}

function confirmDelete(variant) {
  pendingDelete.value = variant;
}

async function executeDelete() {
  const result = await store.deleteVariant(props.equipmentUuid, pendingDelete.value.uuid);
  if (result.ok) {
    toast.success('Variante eliminada correctamente.');
    pendingDelete.value = null;
  } else {
    toast.error(result.error);
  }
}

async function onSuccess() {
  showModal.value = false;
  toast.success('Variante guardada correctamente.');
  await store.fetchVariants(props.equipmentUuid);
}
</script>
