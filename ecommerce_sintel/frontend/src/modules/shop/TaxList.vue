<template>
  <div class="tax-list-module">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h4 class="fw-bold m-0">Impuestos</h4>
      <button class="btn btn-primary" @click="openCreate">
        <i class="bi bi-plus-lg me-1"></i> Nuevo Impuesto
      </button>
    </div>

    <div class="card shadow-sm border-0 overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>Nombre</th>
              <th>Tipo</th>
              <th>Valor</th>
              <th>Estado</th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="5" class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
                <div class="mt-2 text-muted small">Cargando impuestos...</div>
              </td>
            </tr>
            <tr v-else-if="taxes.length === 0">
              <td colspan="5" class="text-center py-5 text-muted">No hay impuestos configurados.</td>
            </tr>
            <template v-for="tax in taxes" :key="tax.uuid">
              <tr v-if="pendingDelete?.uuid === tax.uuid" class="bg-danger-subtle">
                <td colspan="5" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                    <span class="small">¿Desactivar el impuesto <strong>{{ tax.name }}</strong>?</span>
                    <div class="ms-auto d-flex gap-2">
                      <button class="btn btn-sm btn-danger" @click="executeDelete(tax)" :disabled="actionLoading">
                        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>
                        Confirmar
                      </button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>
              <tr v-else>
                <td class="fw-bold">{{ tax.name }}</td>
                <td>
                  <span :class="['badge', tax.tax_type === 'percentage' ? 'bg-info-subtle text-info border border-info-subtle' : 'bg-warning-subtle text-warning border border-warning-subtle']">
                    {{ tax.tax_type === 'percentage' ? 'Porcentaje' : 'Fijo' }}
                  </span>
                </td>
                <td class="fw-bold">
                  {{ tax.tax_type === 'percentage' ? tax.value + '%' : '$' + formatNum(tax.value) }}
                </td>
                <td>
                  <span :class="['badge rounded-pill', tax.is_active ? 'bg-success' : 'bg-secondary']">
                    {{ tax.is_active ? 'Activo' : 'Inactivo' }}
                  </span>
                </td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm shadow-sm bg-white rounded">
                    <button class="btn btn-light border-end" @click="openEdit(tax)" title="Editar">
                      <i class="bi bi-pencil text-primary"></i>
                    </button>
                    <button class="btn btn-light" @click="pendingDelete = tax" title="Desactivar">
                      <i class="bi bi-trash text-danger"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <div class="card-footer bg-white d-flex justify-content-between align-items-center py-3" v-if="totalCount > 0">
        <span class="text-muted small">{{ taxes.length }} de {{ totalCount }} impuestos</span>
        <nav v-if="totalPages > 1">
          <ul class="pagination pagination-sm m-0">
            <li class="page-item" :class="{ disabled: !pagination.previous }">
              <button class="page-link" @click="changePage(currentPage - 1)">Ant.</button>
            </li>
            <li class="page-item" :class="{ disabled: !pagination.next }">
              <button class="page-link" @click="changePage(currentPage + 1)">Sig.</button>
            </li>
          </ul>
        </nav>
      </div>
    </div>

    <SintelOffcanvas
      v-model="show"
      :title="mode === 'create' ? 'Nuevo Impuesto' : 'Editar Impuesto'"
      :subtitle="mode === 'create' ? 'Define nombre, tipo y valor' : `Modificando: ${selected?.name}`"
      width="420px"
    >
      <TaxForm :item="selected" :mode="mode" @success="onFormSuccess" @cancel="close" />
    </SintelOffcanvas>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { formatCOP } from '@/utils/money';
import { useOffcanvas } from '@/composables/useOffcanvas';
import { useShopAdminStore } from '@/store/shopAdmin';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';
import TaxForm from './TaxForm.vue';

const toast = useToast();
const { show, mode, selected, openCreate, openEdit, close } = useOffcanvas();
const store = useShopAdminStore();
const {
  taxes, taxesTotalCount: totalCount, taxesTotalPages: totalPages,
  taxesPagination: pagination, taxesLoading: loading,
  actionLoading,
} = storeToRefs(store);

const currentPage = ref(1);
const pendingDelete = ref(null);

const fetchTaxes = () => store.fetchTaxes(currentPage.value);

const executeDelete = async (tax) => {
  const res = await store.deleteTax(tax.uuid);
  if (res.ok) {
    toast.success(`Impuesto "${tax.name}" eliminado`);
    await fetchTaxes();
  } else {
    toast.error('No se pudo desactivar el impuesto');
  }
  pendingDelete.value = null;
};

const onFormSuccess = () => { close(); fetchTaxes(); };

const changePage = (page) => {
  if (page >= 1 && page <= totalPages.value) { currentPage.value = page; fetchTaxes(); }
};

const formatNum = (val) => formatCOP(val);

onMounted(fetchTaxes);
</script>
