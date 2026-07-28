<template>
  <div class="category-list-module">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h4 class="fw-bold m-0">Gestión de Categorías</h4>
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
              <th>Descripción</th>
              <th>Estado</th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="4" class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
                <div class="mt-2 text-muted small">Cargando categorías...</div>
              </td>
            </tr>
            <tr v-else-if="categories.length === 0">
              <td colspan="4" class="text-center py-5 text-muted">
                No se encontraron categorías.
              </td>
            </tr>
            <template v-for="category in categories" :key="category.uuid">
              <!-- Confirmación Inline -->
              <tr v-if="pendingDelete?.uuid === category.uuid" class="bg-danger-subtle">
                <td colspan="4" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                    <span class="small">
                      ¿Seguro que deseas eliminar la categoría <strong>{{ category.name }}</strong>?
                    </span>
                    <div class="ms-auto d-flex gap-2">
                      <button 
                        class="btn btn-sm btn-danger" 
                        @click="executeDelete(category)"
                        :disabled="actionLoading"
                      >
                        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>
                        Confirmar
                      </button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>
              <!-- Fila Normal -->
              <tr v-else>
                <td class="fw-bold">{{ category.name }}</td>
                <td class="text-truncate" style="max-width: 250px;">{{ category.description || 'Sin descripción' }}</td>
                <td>
                  <span :class="['badge rounded-pill', category.is_active ? 'bg-success' : 'bg-secondary']">
                    {{ category.is_active ? 'Activa' : 'Inactiva' }}
                  </span>
                </td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm shadow-sm bg-white rounded">
                    <button class="btn btn-light border-end" @click="openEdit(category)" title="Editar">
                      <i class="bi bi-pencil text-primary"></i>
                    </button>
                    <button class="btn btn-light" @click="pendingDelete = category" title="Eliminar">
                      <i class="bi bi-trash text-danger"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- Paginación Simple -->
      <div class="card-footer bg-white d-flex justify-content-between align-items-center py-3" v-if="totalCount > 0">
        <span class="text-muted smaller">
          Mostrando {{ categories.length }} de {{ totalCount }} registros
        </span>
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

    <!-- Offcanvas para Crear/Editar -->
    <SintelOffcanvas
      v-model="show"
      :title="mode === 'create' ? 'Nueva Categoría' : 'Editar Categoría'"
      :subtitle="mode === 'create' ? 'Organiza tus productos y servicios' : `Modificando: ${selected?.name}`"
    >
      <CategoryForm 
        :item="selected" 
        :mode="mode" 
        @success="onFormSuccess" 
        @cancel="close"
      />
    </SintelOffcanvas>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useOffcanvas } from '@/composables/useOffcanvas';
import { useShopAdminStore } from '@/store/shopAdmin';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';
import CategoryForm from './CategoryForm.vue';

const toast = useToast();
const { show, mode, selected, openCreate, openEdit, close } = useOffcanvas();
const store = useShopAdminStore();
const {
  categories, categoriesTotalCount: totalCount, categoriesTotalPages: totalPages,
  categoriesPagination: pagination, categoriesLoading: loading,
  actionLoading,
} = storeToRefs(store);

const currentPage = ref(1);
const pendingDelete = ref(null);

const fetchCategories = () => store.fetchCategories(currentPage.value);

const executeDelete = async (category) => {
  const res = await store.deleteCategory(category.uuid);
  if (res.ok) {
    toast.success(`Categoría "${category.name}" eliminada`);
    await fetchCategories();
  } else {
    toast.error('No se pudo eliminar la categoría');
  }
  pendingDelete.value = null;
};

const onFormSuccess = () => {
  close();
  fetchCategories();
};

const changePage = (page) => {
  if (page >= 1 && page <= totalPages.value) {
    currentPage.value = page;
    fetchCategories();
  }
};

onMounted(fetchCategories);
</script>

<style scoped>
.smaller { font-size: 0.85rem; }
</style>
