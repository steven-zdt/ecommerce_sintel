<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h4 class="fw-bold m-0">Categorías de Renta</h4>
      <button class="btn btn-primary" @click="openCreate">
        <i class="bi bi-plus-lg me-1"></i> Nueva Categoría
      </button>
    </div>

    <div class="card shadow-sm border-0 overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>Nombre</th>
              <th>Slug</th>
              <th>Estado</th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="4" class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
              </td>
            </tr>
            <tr v-else-if="categories.length === 0">
              <td colspan="4" class="text-center py-5 text-muted">Sin categorías registradas.</td>
            </tr>
            <template v-for="cat in categories" :key="cat.uuid">
              <tr v-if="pendingDelete?.uuid === cat.uuid" class="bg-danger-subtle">
                <td colspan="4" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                    <span class="small">¿Eliminar categoría <strong>{{ cat.name }}</strong>?</span>
                    <div class="ms-auto d-flex gap-2">
                      <button class="btn btn-sm btn-danger" @click="executeDelete(cat)" :disabled="actionLoading">
                        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>Confirmar
                      </button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>
              <tr v-else>
                <td class="fw-bold">{{ cat.name }}</td>
                <td><code class="small text-muted">{{ cat.slug }}</code></td>
                <td>
                  <span :class="cat.is_active ? 'badge bg-success-subtle text-success' : 'badge bg-secondary-subtle text-secondary'">
                    {{ cat.is_active ? 'Activa' : 'Inactiva' }}
                  </span>
                </td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm shadow-sm bg-white rounded">
                    <button class="btn btn-light border-end" @click="openEdit(cat)" title="Editar">
                      <i class="bi bi-pencil text-primary"></i>
                    </button>
                    <button class="btn btn-light" @click="pendingDelete = cat" title="Eliminar">
                      <i class="bi bi-trash text-danger"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <SintelOffcanvas
      v-model="show"
      :title="mode === 'create' ? 'Nueva Categoría' : 'Editar Categoría'"
      :subtitle="mode === 'create' ? 'Categoría para equipos de renta' : `Modificando: ${selected?.name}`"
      width="400px"
    >
      <RentingCategoryForm :item="selected" :mode="mode" @success="onFormSuccess" @cancel="close" />
    </SintelOffcanvas>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useOffcanvas } from '@/composables/useOffcanvas';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';
import RentingCategoryForm from './RentingCategoryForm.vue';

const api = useApi();
const toast = useToast();
const { show, mode, selected, openCreate, openEdit, close } = useOffcanvas();

const loading = ref(true);
const actionLoading = ref(false);
const categories = ref([]);
const pendingDelete = ref(null);

const fetchCategories = async () => {
  loading.value = true;
  try {
    const res = await api.get('dashboard/renting-categories/');
    categories.value = res.data.results || res.data;
  } catch {
    toast.error('Error al cargar categorías');
  } finally {
    loading.value = false;
  }
};

const executeDelete = async (cat) => {
  actionLoading.value = true;
  try {
    await api.delete(`dashboard/renting-categories/${cat.id}/`);
    toast.success(`Categoría "${cat.name}" eliminada`);
    await fetchCategories();
  } catch {
    toast.error('No se pudo eliminar la categoría');
  } finally {
    actionLoading.value = false;
    pendingDelete.value = null;
  }
};

const onFormSuccess = () => { close(); fetchCategories(); };
onMounted(fetchCategories);
</script>
