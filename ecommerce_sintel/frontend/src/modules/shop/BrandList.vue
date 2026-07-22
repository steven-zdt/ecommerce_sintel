<template>
  <div class="brand-list-module">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h4 class="fw-bold m-0">Marcas</h4>
      <div class="d-flex gap-2">
        <button class="btn btn-light border" @click="exportCSV" :disabled="brands.length === 0">
          <i class="bi bi-download me-1"></i>
          {{ selectedIds.size > 0 ? `Exportar seleccionadas (${selectedIds.size})` : 'Exportar CSV' }}
        </button>
        <button class="btn btn-primary" @click="openCreate">
          <i class="bi bi-plus-lg me-1"></i> Nueva Marca
        </button>
      </div>
    </div>

    <!-- Barra de acciones masivas — solo visible con seleccion activa -->
    <div v-if="selectedIds.size > 0" class="alert alert-primary d-flex align-items-center justify-content-between py-2 px-3 mb-3">
      <span class="small fw-bold">{{ selectedIds.size }} marca(s) seleccionada(s)</span>
      <div class="d-flex gap-2">
        <button class="btn btn-sm btn-danger" @click="pendingBulkDelete = true" :disabled="bulkLoading">
          <i class="bi bi-trash me-1"></i>Eliminar seleccionadas
        </button>
        <button class="btn btn-sm btn-light border" @click="selectedIds.clear()">Cancelar seleccion</button>
      </div>
    </div>

    <!-- Confirmacion de borrado masivo -->
    <div v-if="pendingBulkDelete" class="alert alert-danger d-flex align-items-center gap-3 py-2 px-3 mb-3">
      <i class="bi bi-exclamation-triangle-fill"></i>
      <span class="small">¿Eliminar {{ selectedIds.size }} marca(s)? Esta accion es permanente.</span>
      <div class="ms-auto d-flex gap-2">
        <button class="btn btn-sm btn-danger" @click="executeBulkDelete" :disabled="bulkLoading">
          <span v-if="bulkLoading" class="spinner-border spinner-border-sm me-1"></span>
          Confirmar
        </button>
        <button class="btn btn-sm btn-light border" @click="pendingBulkDelete = false">Cancelar</button>
      </div>
    </div>

    <div class="card shadow-sm border-0 overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th style="width:36px">
                <input
                  type="checkbox"
                  class="form-check-input"
                  :checked="allVisibleSelected"
                  @change="toggleSelectAll"
                  title="Seleccionar todas las visibles"
                >
              </th>
              <th>Nombre</th>
              <th>Slug</th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="4" class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
                <div class="mt-2 text-muted small">Cargando marcas...</div>
              </td>
            </tr>
            <tr v-else-if="brands.length === 0">
              <td colspan="4" class="text-center py-5 text-muted">No hay marcas registradas.</td>
            </tr>
            <template v-for="brand in brands" :key="brand.uuid">
              <tr v-if="pendingDelete?.uuid === brand.uuid" class="bg-danger-subtle">
                <td colspan="4" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                    <span class="small">¿Eliminar la marca <strong>{{ brand.name }}</strong>? Esta acción es permanente.</span>
                    <div class="ms-auto d-flex gap-2">
                      <button class="btn btn-sm btn-danger" @click="executeDelete(brand)" :disabled="actionLoading">
                        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>
                        Confirmar
                      </button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>
              <tr v-else>
                <td>
                  <input
                    type="checkbox"
                    class="form-check-input"
                    :checked="selectedIds.has(brand.uuid)"
                    @change="toggleSelect(brand.uuid)"
                  >
                </td>
                <td class="fw-bold">{{ brand.name }}</td>
                <td><code class="small text-muted">{{ brand.slug }}</code></td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm shadow-sm bg-white rounded">
                    <button class="btn btn-light border-end" @click="openEdit(brand)" title="Editar">
                      <i class="bi bi-pencil text-primary"></i>
                    </button>
                    <button class="btn btn-light" @click="pendingDelete = brand" title="Eliminar">
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
        <span class="text-muted small">{{ brands.length }} de {{ totalCount }} marcas</span>
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
      :title="mode === 'create' ? 'Nueva Marca' : 'Editar Marca'"
      :subtitle="mode === 'create' ? 'Agrega una marca al catálogo' : `Modificando: ${selected?.name}`"
      width="400px"
    >
      <BrandForm :item="selected" :mode="mode" @success="onFormSuccess" @cancel="close" />
    </SintelOffcanvas>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, reactive } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useOffcanvas } from '@/composables/useOffcanvas';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';
import BrandForm from './BrandForm.vue';

const api = useApi();
const toast = useToast();
const { show, mode, selected, openCreate, openEdit, close } = useOffcanvas();

const loading = ref(true);
const actionLoading = ref(false);
const brands = ref([]);
const totalCount = ref(0);
const totalPages = ref(0);
const currentPage = ref(1);
const pendingDelete = ref(null);
const pagination = reactive({ next: null, previous: null });

// --- Seleccion + acciones masivas + exportacion ---------------------------
const selectedIds = ref(new Set());
const pendingBulkDelete = ref(false);
const bulkLoading = ref(false);

const allVisibleSelected = computed(() =>
  brands.value.length > 0 && brands.value.every((b) => selectedIds.value.has(b.uuid))
);

function toggleSelect(uuid) {
  if (selectedIds.value.has(uuid)) selectedIds.value.delete(uuid);
  else selectedIds.value.add(uuid);
  // Set no es reactivo por mutacion directa en Vue 3 — reasignar para disparar el trigger.
  selectedIds.value = new Set(selectedIds.value);
}

function toggleSelectAll() {
  selectedIds.value = allVisibleSelected.value
    ? new Set()
    : new Set(brands.value.map((b) => b.uuid));
}

const fetchBrands = async () => {
  loading.value = true;
  try {
    const res = await api.get('shop/brands/', { params: { page: currentPage.value } });
    brands.value = res.data.results || res.data;
    totalCount.value = res.data.count || brands.value.length;
    totalPages.value = Math.ceil(totalCount.value / 25);
    pagination.next = res.data.next;
    pagination.previous = res.data.previous;
  } catch (err) {
    toast.error('Error al cargar marcas');
  } finally {
    loading.value = false;
  }
};

const executeDelete = async (brand) => {
  actionLoading.value = true;
  try {
    await api.delete(`dashboard/brands/${brand.id}/`);
    toast.success(`Marca "${brand.name}" eliminada`);
    await fetchBrands();
  } catch (err) {
    toast.error('No se pudo eliminar la marca');
  } finally {
    actionLoading.value = false;
    pendingDelete.value = null;
  }
};

async function executeBulkDelete() {
  bulkLoading.value = true;
  const ids = brands.value.filter((b) => selectedIds.value.has(b.uuid)).map((b) => b.id);
  try {
    // Reusa el endpoint de borrado individual existente — no requiere un
    // endpoint de bulk-delete nuevo en el backend.
    const results = await Promise.allSettled(ids.map((id) => api.delete(`dashboard/brands/${id}/`)));
    const failed = results.filter((r) => r.status === 'rejected').length;
    if (failed > 0) {
      toast.error(`${failed} de ${ids.length} no se pudieron eliminar`);
    } else {
      toast.success(`${ids.length} marca(s) eliminada(s)`);
    }
    selectedIds.value = new Set();
    await fetchBrands();
  } finally {
    bulkLoading.value = false;
    pendingBulkDelete.value = false;
  }
}

function exportCSV() {
  const rows = selectedIds.value.size > 0
    ? brands.value.filter((b) => selectedIds.value.has(b.uuid))
    : brands.value;
  if (rows.length === 0) return;

  const header = ['Nombre', 'Slug', 'Activo'];
  const lines = rows.map((b) => [b.name, b.slug, b.is_active ? 'Si' : 'No']
    .map((v) => `"${String(v ?? '').replace(/"/g, '""')}"`).join(','));
  const csv = [header.join(','), ...lines].join('\n');

  const blob = new Blob([`﻿${csv}`], { type: 'text/csv;charset=utf-8;' }); // BOM para Excel/es-CO
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = `marcas_${new Date().toISOString().slice(0, 10)}.csv`;
  link.click();
  URL.revokeObjectURL(url);
}

const onFormSuccess = () => { close(); fetchBrands(); };

const changePage = (page) => {
  if (page >= 1 && page <= totalPages.value) { currentPage.value = page; fetchBrands(); }
};

onMounted(fetchBrands);
</script>
