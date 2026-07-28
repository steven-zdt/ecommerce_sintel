<template>
  <div class="dispatcher-list p-4">
    <div class="list-header">
      <h2>Despachadores</h2>
      <button class="btn btn-primary btn-sm" @click="openCreate">
        <i class="bi bi-plus-lg me-1"></i> Nuevo
      </button>
    </div>

    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
    </div>

    <table v-else class="table table-hover align-middle">
      <thead class="table-light">
        <tr>
          <th>Email</th>
          <th>Tipo</th>
          <th>Vehiculo</th>
          <th>Ciudades</th>
          <th>Disponible</th>
          <th>Activo</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="dp in dispatchers" :key="dp.uuid" :class="{ 'bg-danger-subtle': confirmingUuid === dp.uuid }">
          <template v-if="confirmingUuid === dp.uuid">
            <td colspan="6" class="text-danger small">¿Eliminar a "{{ dp.email }}" como despachador?</td>
            <td class="text-end">
              <button class="btn btn-sm btn-danger me-1" :disabled="removing" @click="remove(dp.uuid)">Confirmar</button>
              <button class="btn btn-sm btn-outline-secondary" @click="confirmingUuid = null">Cancelar</button>
            </td>
          </template>
          <template v-else>
            <td>{{ dp.email }}</td>
            <td>{{ dp.dispatcher_type }}</td>
            <td>{{ dp.vehicle_plate || '—' }} {{ dp.vehicle_type }}</td>
            <td class="small">{{ (dp.coverage_cities || []).join(', ') || '—' }}</td>
            <td>
              <span :class="dp.is_available ? 'text-success' : 'text-muted'">
                {{ dp.is_available ? 'Si' : 'No' }}
              </span>
            </td>
            <td>
              <span :class="dp.is_active ? 'text-success' : 'text-muted'">
                {{ dp.is_active ? 'Si' : 'No' }}
              </span>
            </td>
            <td>
              <button class="btn btn-sm btn-outline-danger" @click="confirmingUuid = dp.uuid">Eliminar</button>
            </td>
          </template>
        </tr>
        <tr v-if="!dispatchers.length">
          <td colspan="7" class="text-center text-muted py-4">Sin despachadores registrados.</td>
        </tr>
      </tbody>
    </table>

    <!-- Formulario crear despachador -->
    <BaseModal v-model="showForm" title="Nuevo despachador">
      <div class="mb-2">
        <label class="form-label">Usuario *</label>
        <div v-if="selectedUser" class="dl-selected-user">
          <i class="bi bi-person-check-fill text-success me-2"></i>
          <span class="flex-grow-1">{{ selectedUser.email }}</span>
          <button type="button" class="btn btn-sm btn-outline-secondary" @click="clearSelectedUser">Cambiar</button>
        </div>
        <div v-else class="dl-user-search">
          <input
            v-model="userQuery"
            type="text"
            class="form-control form-control-sm"
            placeholder="Buscar por email..."
            @input="onUserQueryInput"
          />
          <ul v-if="userResults.length" class="dl-user-results">
            <li v-for="u in userResults" :key="u.id" @click="selectUser(u)">
              {{ u.email }}
            </li>
          </ul>
          <div v-else-if="searchingUsers" class="dl-user-hint">Buscando...</div>
          <div v-else-if="userQuery.length >= 2" class="dl-user-hint">Sin resultados.</div>
        </div>
      </div>
      <div class="mb-2">
        <label class="form-label">Tipo</label>
        <select v-model="form.dispatcher_type" class="form-select form-select-sm">
          <option value="DRIVER">Conductor</option>
          <option value="LOGISTICS">Logistica</option>
          <option value="FIELD_OPS">Operario de campo</option>
        </select>
      </div>
      <div class="mb-2">
        <label class="form-label">Placa</label>
        <input v-model="form.vehicle_plate" class="form-control form-control-sm" />
      </div>
      <div class="mb-2">
        <label class="form-label">Tipo de vehiculo</label>
        <input v-model="form.vehicle_type" class="form-control form-control-sm" />
      </div>
      <div class="mb-3">
        <label class="form-label">Ciudades (separadas por coma)</label>
        <input v-model="citiesInput" class="form-control form-control-sm" placeholder="Bogotá, Medellín" />
      </div>
      <p v-if="formError" class="text-danger small mt-2">{{ formError }}</p>
      <template #footer>
        <button class="btn btn-outline-secondary btn-sm" @click="closeForm">Cancelar</button>
        <button class="btn btn-primary btn-sm" :disabled="saving || !selectedUser" @click="save">
          <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
          Guardar
        </button>
      </template>
    </BaseModal>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useOperationsAdminStore } from '@/store/operationsAdmin';
import BaseModal from '@/components/base/BaseModal.vue';

const api     = useApi();
const toast   = useToast();
const store   = useOperationsAdminStore();
const { dispatchers, dispatchersLoading: loading } = storeToRefs(store);

const showForm    = ref(false);
const saving      = ref(false);
const removing    = ref(false);
const formError   = ref('');
const citiesInput = ref('');
const confirmingUuid = ref(null);

const selectedUser   = ref(null);
const userQuery      = ref('');
const userResults    = ref([]);
const searchingUsers = ref(false);
let userSearchTimeout = null;

const form = reactive({
  user_id:         '',
  dispatcher_type: 'DRIVER',
  vehicle_plate:   '',
  vehicle_type:    '',
});

function fetchAll() {
  return store.fetchDispatchers();
}

onMounted(fetchAll);

function onUserQueryInput() {
  clearTimeout(userSearchTimeout);
  if (userQuery.value.trim().length < 2) {
    userResults.value = [];
    return;
  }
  userSearchTimeout = setTimeout(searchUsers, 400);
}

async function searchUsers() {
  searchingUsers.value = true;
  try {
    const { data } = await api.get('users/', { params: { search: userQuery.value.trim(), is_active: 'true' } });
    userResults.value = (data.results ?? data).slice(0, 8);
  } finally {
    searchingUsers.value = false;
  }
}

function selectUser(u) {
  selectedUser.value = u;
  form.user_id = u.id;
  userQuery.value = '';
  userResults.value = [];
}

function clearSelectedUser() {
  selectedUser.value = null;
  form.user_id = '';
}

function resetForm() {
  formError.value = '';
  citiesInput.value = '';
  userQuery.value = '';
  userResults.value = [];
  clearSelectedUser();
  Object.assign(form, { user_id: '', dispatcher_type: 'DRIVER', vehicle_plate: '', vehicle_type: '' });
}

function openCreate() {
  resetForm();
  showForm.value = true;
}

function closeForm() {
  showForm.value = false;
  resetForm();
}

async function save() {
  formError.value = '';
  saving.value    = true;
  const cities = citiesInput.value
    ? citiesInput.value.split(',').map(c => c.trim()).filter(Boolean)
    : [];
  const res = await store.createDispatcher({ ...form, coverage_cities: cities });
  if (res.ok) {
    toast.success('Despachador creado.');
    showForm.value = false;
    resetForm();
  } else {
    formError.value = res.error?.response?.data?.user_id || res.error?.response?.data?.detail || 'Error.';
  }
  saving.value = false;
}

async function remove(uuid) {
  removing.value = true;
  const res = await store.deleteDispatcher(uuid);
  if (res.ok) toast.success('Despachador eliminado.'); else toast.error('Error al eliminar.');
  removing.value = false;
  confirmingUuid.value = null;
}
</script>

<style scoped>
.dispatcher-list { background: #fff; min-height: 80vh; }
.list-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
.list-header h2 { font-size: 1.3rem; font-weight: 700; margin: 0; }

.dl-selected-user {
  display: flex; align-items: center; gap: .5rem;
  border: 1px solid #e5e7eb; border-radius: 8px; padding: .4rem .6rem; font-size: .875rem;
}
.dl-user-search { position: relative; }
.dl-user-results {
  position: absolute; z-index: 10; top: 100%; left: 0; right: 0;
  background: #fff; border: 1px solid #e5e7eb; border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0,0,0,.1); margin-top: 4px; padding: 4px 0;
  max-height: 220px; overflow-y: auto; list-style: none;
}
.dl-user-results li { padding: .4rem .75rem; font-size: .875rem; cursor: pointer; }
.dl-user-results li:hover { background: #f3f4f6; }
.dl-user-hint { font-size: .8rem; color: #9ca3af; margin-top: 4px; }
</style>
