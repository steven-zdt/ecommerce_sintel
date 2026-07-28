<template>
  <div>
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h4 class="fw-bold m-0">Marcas de Renta</h4>
      <button class="btn btn-primary" @click="openCreate">
        <i class="bi bi-plus-lg me-1"></i> Nueva Marca
      </button>
    </div>

    <div class="card shadow-sm border-0 overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>Nombre</th>
              <th>Slug</th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="3" class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
              </td>
            </tr>
            <tr v-else-if="brands.length === 0">
              <td colspan="3" class="text-center py-5 text-muted">Sin marcas registradas.</td>
            </tr>
            <template v-for="brd in brands" :key="brd.uuid">
              <tr v-if="pendingDelete?.uuid === brd.uuid" class="bg-danger-subtle">
                <td colspan="3" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-danger"></i>
                    <span class="small">¿Eliminar marca <strong>{{ brd.name }}</strong>?</span>
                    <div class="ms-auto d-flex gap-2">
                      <button class="btn btn-sm btn-danger" @click="executeDelete(brd)" :disabled="actionLoading">
                        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>Confirmar
                      </button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>
              <tr v-else>
                <td class="fw-bold">{{ brd.name }}</td>
                <td><code class="small text-muted">{{ brd.slug }}</code></td>
                <td class="text-end">
                  <div class="btn-group btn-group-sm shadow-sm bg-white rounded">
                    <button class="btn btn-light border-end" @click="openEdit(brd)" title="Editar">
                      <i class="bi bi-pencil text-primary"></i>
                    </button>
                    <button class="btn btn-light" @click="pendingDelete = brd" title="Eliminar">
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
      :title="mode === 'create' ? 'Nueva Marca' : 'Editar Marca'"
      :subtitle="mode === 'create' ? 'Marca para equipos de renta' : `Modificando: ${selected?.name}`"
      width="380px"
    >
      <RentingBrandForm :item="selected" :mode="mode" @success="onFormSuccess" @cancel="close" />
    </SintelOffcanvas>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useOffcanvas } from '@/composables/useOffcanvas';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';
import RentingBrandForm from './RentingBrandForm.vue';

const api = useApi();
const toast = useToast();
const { show, mode, selected, openCreate, openEdit, close } = useOffcanvas();

const loading = ref(true);
const actionLoading = ref(false);
const brands = ref([]);
const pendingDelete = ref(null);

const fetchBrands = async () => {
  loading.value = true;
  try {
    const res = await api.get('dashboard/renting-brands/');
    brands.value = res.data.results || res.data;
  } catch {
    toast.error('Error al cargar marcas');
  } finally {
    loading.value = false;
  }
};

const executeDelete = async (brd) => {
  actionLoading.value = true;
  try {
    await api.delete(`dashboard/renting-brands/${brd.uuid}/`);
    toast.success(`Marca "${brd.name}" eliminada`);
    await fetchBrands();
  } catch {
    toast.error('No se pudo eliminar la marca');
  } finally {
    actionLoading.value = false;
    pendingDelete.value = null;
  }
};

const onFormSuccess = () => { close(); fetchBrands(); };
onMounted(fetchBrands);
</script>
