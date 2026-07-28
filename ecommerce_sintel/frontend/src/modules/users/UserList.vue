<template>
  <div class="users-module">

    <!-- Cabecera -->
    <div class="d-flex justify-content-between align-items-center mb-3">
      <div>
        <h4 class="fw-bold mb-0">Gestión de Usuarios</h4>
        <p class="text-muted small mb-0">{{ totalCount }} usuario{{ totalCount !== 1 ? 's' : '' }} en el sistema</p>
      </div>
      <button class="btn btn-primary" @click="openCreate">
        <i class="bi bi-person-plus me-1"></i> Nuevo Usuario
      </button>
    </div>

    <!-- Filtros -->
    <div class="row g-2 mb-2">
      <div class="col-md-4">
        <div class="input-group">
          <span class="input-group-text bg-white border-end-0">
            <i class="bi bi-search text-muted"></i>
          </span>
          <input
            v-model="search"
            class="form-control border-start-0 ps-0"
            placeholder="Buscar por nombre, email, documento, empresa..."
          />
        </div>
      </div>
      <div class="col-md-2">
        <select v-model="filters.user_type" class="form-select" @change="loadPage()">
          <option value="">Todos los tipos</option>
          <option v-for="(meta, code) in userTypes" :key="code" :value="code">{{ meta.label }}</option>
        </select>
      </div>
      <div class="col-md-2">
        <select v-model="filters.is_active" class="form-select" @change="loadPage()">
          <option value="">Activo/Inactivo</option>
          <option value="true">Activos</option>
          <option value="false">Inactivos</option>
        </select>
      </div>
      <div class="col-md-2">
        <select v-model="filters.is_verified" class="form-select" @change="loadPage()">
          <option value="">Verificado?</option>
          <option value="true">Verificados</option>
          <option value="false">No verificados</option>
        </select>
      </div>
      <div class="col-md-2">
        <button class="btn btn-light border w-100" @click="showAdvanced = !showAdvanced">
          <i class="bi bi-sliders me-1"></i> Más filtros
        </button>
      </div>
    </div>

    <div v-if="showAdvanced" class="row g-2 mb-3">
      <div class="col-md-4">
        <input v-model="filters.company" class="form-control" placeholder="Empresa" />
      </div>
      <div class="col-md-4">
        <input v-model="filters.city" class="form-control" placeholder="Ciudad" />
      </div>
      <div class="col-md-4">
        <input v-model="filters.country" class="form-control" placeholder="País" />
      </div>
    </div>
    <div v-else class="mb-3"></div>

    <!-- Tabla -->
    <div class="card shadow-sm border-0 overflow-hidden">
      <div class="table-responsive">
        <table class="table table-hover align-middle mb-0">
          <thead class="table-light">
            <tr>
              <th>Email</th>
              <th>Nombre Completo</th>
              <th>Tipo</th>
              <th>Upgrade solicitado</th>
              <th>Estado KYC</th>
              <th>Estado</th>
              <th>Verificado</th>
              <th>Registro</th>
              <th>Último acceso</th>
              <th class="text-end">Acciones</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="loading">
              <td colspan="10" class="text-center py-5">
                <div class="spinner-border text-primary" role="status"></div>
                <div class="mt-2 text-muted small">Cargando usuarios...</div>
              </td>
            </tr>
            <tr v-else-if="items.length === 0">
              <td colspan="10" class="text-center py-5 text-muted">
                <i class="bi bi-inbox fs-3 d-block mb-2"></i>
                No hay usuarios que coincidan con los filtros.
              </td>
            </tr>
            <template v-for="user in items" :key="user.uuid">

              <!-- Confirmacion inline: toggle -->
              <tr v-if="pendingToggle?.uuid === user.uuid" class="bg-warning-subtle">
                <td colspan="10" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-exclamation-triangle-fill text-warning"></i>
                    <span class="small">
                      ¿Deseas <strong>{{ user.is_active ? 'desactivar' : 'activar' }}</strong>
                      a <strong>{{ user.email }}</strong>?
                    </span>
                    <div class="ms-auto d-flex gap-2">
                      <button class="btn btn-sm btn-warning" @click="executeToggle(user)" :disabled="actionLoading">
                        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>
                        Confirmar
                      </button>
                      <button class="btn btn-sm btn-light border" @click="pendingToggle = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>

              <!-- Confirmacion inline: eliminar permanente -->
              <tr v-else-if="pendingDelete?.uuid === user.uuid" class="bg-danger-subtle">
                <td colspan="10" class="p-0">
                  <div class="d-flex align-items-center gap-3 px-3 py-2">
                    <i class="bi bi-trash-fill text-danger"></i>
                    <span class="small">
                      Acción <strong>irreversible</strong>. ¿Eliminar permanentemente a
                      <strong>{{ user.email }}</strong>?
                    </span>
                    <div class="ms-auto d-flex gap-2">
                      <button class="btn btn-sm btn-danger" @click="executeDelete(user)" :disabled="actionLoading">
                        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>
                        Eliminar
                      </button>
                      <button class="btn btn-sm btn-light border" @click="pendingDelete = null">Cancelar</button>
                    </div>
                  </div>
                </td>
              </tr>

              <!-- Fila normal -->
              <tr v-else :class="{ 'opacity-60': !user.is_active }" role="button" @click="openDetail(user)">
                <td>
                  <div class="fw-semibold d-flex align-items-center gap-1">
                    {{ user.email }}
                    <span v-if="isSelf(user)" class="badge bg-primary-subtle text-primary border border-primary-subtle smaller">Tu cuenta</span>
                  </div>
                </td>
                <td class="text-muted small">{{ user.full_name || '—' }}</td>
                <td>
                  <span v-if="user.is_staff" class="badge bg-primary-subtle text-primary border border-primary-subtle">Administrador</span>
                  <span v-else class="badge" :class="enums.cssClass('user-types', user.profile?.user_type)">
                    {{ enums.label('user-types', user.profile?.user_type, user.profile?.user_type) }}
                  </span>
                </td>
                <td>
                  <span v-if="user.kyc_verification?.requested_user_type" class="badge bg-primary-subtle text-primary border border-primary-subtle">
                    {{ enums.label('user-types', user.kyc_verification.requested_user_type, user.kyc_verification.requested_user_type) }}
                  </span>
                  <span v-else class="text-muted smaller">—</span>
                </td>
                <td>
                  <span v-if="user.kyc_status" class="badge" :class="enums.cssClass('kyc-verification-statuses', user.kyc_status)">
                    {{ enums.label('kyc-verification-statuses', user.kyc_status, user.kyc_status) }}
                  </span>
                  <span v-else class="text-muted smaller">—</span>
                </td>
                <td>
                  <span :class="['badge rounded-pill', user.is_active ? 'bg-success' : 'bg-secondary']">
                    {{ user.is_active ? 'Activo' : 'Inactivo' }}
                  </span>
                </td>
                <td>
                  <i :class="user.is_verified ? 'bi bi-patch-check-fill text-success' : 'bi bi-patch-exclamation text-muted'"></i>
                </td>
                <td class="smaller text-muted">{{ formatDate(user.date_joined) }}</td>
                <td class="smaller text-muted">{{ user.last_login ? formatDate(user.last_login) : 'Nunca' }}</td>
                <td class="text-end" @click.stop>
                  <div class="btn-group btn-group-sm shadow-sm bg-white rounded">
                    <RouterLink
                      v-if="user.kyc_verification?.requested_user_type"
                      :to="{ name: 'kyc-admin-detail', params: { uuid: user.kyc_verification.uuid } }"
                      class="btn btn-light border-end"
                      title="Ver Validación"
                    >
                      <i class="bi bi-patch-check text-primary"></i>
                    </RouterLink>
                    <button class="btn btn-light border-end" @click="openEdit(user)" title="Editar">
                      <i class="bi bi-pencil text-primary"></i>
                    </button>
                    <button
                      class="btn btn-light"
                      :class="{ 'border-end': !user.is_active && !isSelf(user) }"
                      @click="!isSelf(user) && (pendingToggle = user)"
                      :disabled="isSelf(user)"
                      :title="isSelf(user) ? 'No puedes desactivarte a ti mismo' : (user.is_active ? 'Desactivar' : 'Activar')"
                    >
                      <i :class="['bi', user.is_active ? 'bi-slash-circle text-danger' : 'bi-check-circle text-success', isSelf(user) ? 'opacity-25' : '']"></i>
                    </button>
                    <button
                      v-if="!user.is_active && !isSelf(user)"
                      class="btn btn-light"
                      @click="pendingDelete = user"
                      title="Eliminar permanentemente"
                    >
                      <i class="bi bi-trash text-danger"></i>
                    </button>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- Paginación -->
      <div class="card-footer bg-white border-0 d-flex justify-content-between align-items-center py-3 px-4">
        <div class="text-muted smaller">{{ totalCount }} registros encontrados</div>
        <div class="d-flex gap-2">
          <button class="btn btn-sm btn-light border" :disabled="!prevPage || loading" @click="loadPage(prevPage)">
            <i class="bi bi-chevron-left"></i>
          </button>
          <button class="btn btn-sm btn-light border" :disabled="!nextPage || loading" @click="loadPage(nextPage)">
            <i class="bi bi-chevron-right"></i>
          </button>
        </div>
      </div>
    </div>

    <!-- Offcanvas: crear/editar/detalle (una sola instancia, conmutada por mode) -->
    <SintelOffcanvas
      v-model="show"
      :title="offcanvasTitle"
      :subtitle="offcanvasSubtitle"
      :width="mode === 'detail' ? '720px' : '480px'"
    >
      <UserForm
        v-if="mode === 'create' || mode === 'edit'"
        :item="selected"
        :mode="mode"
        @success="onFormSuccess"
        @cancel="close"
      />
      <UserDetail
        v-else-if="mode === 'detail'"
        :item="selected"
        @edit="openEdit(selected)"
        @changed="loadPage()"
      />
    </SintelOffcanvas>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted } from 'vue';
import { useRoute, RouterLink } from 'vue-router';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useOffcanvas } from '@/composables/useOffcanvas';
import { useEnums } from '@/composables/useEnums';
import { useAuthStore } from '@/store/auth';
import { useUsersAdminStore } from '@/store/usersAdmin';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';
import UserForm from './UserForm.vue';
import UserDetail from './UserDetail.vue';

const toast = useToast();
const { handleError } = useErrorHandler();
const route = useRoute();
const authStore = useAuthStore();
const enums = useEnums();
const { show, mode, selected, openCreate, openEdit, openDetail, close } = useOffcanvas();
const store = useUsersAdminStore();
const {
  items, totalCount, nextPage, prevPage, listLoading: loading,
  actionLoading,
} = storeToRefs(store);

const pendingToggle = ref(null);
const pendingDelete = ref(null);
const showAdvanced = ref(false);

const search = ref('');
const userTypes = ref({});

const filters = reactive({
  user_type: '',
  is_active: '',
  is_verified: '',
  company: '',
  city: '',
  country: '',
});

async function loadPage(url = null) {
  await store.fetchList(url || buildEndpoint());
  if (store.error) toast.error(store.error);
}

function buildEndpoint() {
  const params = new URLSearchParams();
  if (search.value) params.append('search', search.value);
  if (filters.user_type) params.append('user_type', filters.user_type);
  if (filters.is_active) params.append('is_active', filters.is_active);
  if (filters.is_verified) params.append('is_verified', filters.is_verified);
  if (filters.company) params.append('company', filters.company);
  if (filters.city) params.append('city', filters.city);
  if (filters.country) params.append('country', filters.country);
  return `users/?${params.toString()}`;
}

let debounceTimer = null;
watch([search, () => filters.company, () => filters.city, () => filters.country], () => {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(() => loadPage(), 400);
});

const executeToggle = async (user) => {
  const res = await store.patchUser(user.uuid, { is_active: !user.is_active });
  if (res.ok) {
    toast.success(`Usuario ${!user.is_active ? 'activado' : 'desactivado'} correctamente`);
    await loadPage();
  } else {
    handleError(res.error, 'No se pudo cambiar el estado');
  }
  pendingToggle.value = null;
};

const executeDelete = async (user) => {
  const res = await store.deleteUser(user.uuid);
  if (res.ok) {
    toast.success(`Usuario ${user.email} eliminado permanentemente`);
    await loadPage();
  } else {
    handleError(res.error, 'No se pudo eliminar el usuario');
  }
  pendingDelete.value = null;
};

const onFormSuccess = () => { close(); loadPage(); };

const offcanvasTitle = computed(() => {
  if (mode.value === 'create') return 'Nuevo Usuario';
  if (mode.value === 'edit') return 'Editar Usuario';
  return 'Detalle de Usuario';
});
const offcanvasSubtitle = computed(() => {
  if (mode.value === 'edit' || mode.value === 'detail') return selected.value?.email || '';
  return 'Completa los datos del nuevo usuario';
});

const isSelf = (user) => authStore.user?.uuid === user.uuid;

const formatDate = (d) =>
  d ? new Date(d).toLocaleDateString('es-CO', { day: '2-digit', month: 'short', year: 'numeric' }) : '—';

onMounted(async () => {
  userTypes.value = await enums.ensure('user-types');
  enums.ensure('kyc-verification-statuses');
  if (route.query.search) search.value = String(route.query.search);
  loadPage();
});
</script>

<style scoped>
.smaller { font-size: 0.8rem; }
.opacity-60 { opacity: 0.6; }
.users-module :deep(.sintel-offcanvas) { z-index: 1045; }
</style>
