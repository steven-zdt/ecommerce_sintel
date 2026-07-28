<template>
  <div v-if="loading" class="text-center py-5">
    <div class="spinner-border text-primary"></div>
  </div>

  <div v-else-if="detail">
    <!-- Identidad -->
    <div class="d-flex align-items-start justify-content-between mb-3">
      <div>
        <h5 class="fw-bold mb-1">{{ detail.full_name || detail.email }}</h5>
        <div class="text-muted small">{{ detail.email }}</div>
      </div>
      <div class="d-flex flex-column gap-1 align-items-end">
        <span :class="['badge rounded-pill', detail.is_active ? 'bg-success' : 'bg-secondary']">
          {{ detail.is_active ? 'Activo' : 'Inactivo' }}
        </span>
        <span :class="['badge rounded-pill', detail.is_verified ? 'bg-success-subtle text-success' : 'bg-warning-subtle text-warning']">
          <i :class="detail.is_verified ? 'bi bi-patch-check-fill' : 'bi bi-patch-exclamation'"></i>
          {{ detail.is_verified ? 'Verificado' : 'Sin verificar' }}
        </span>
        <span v-if="detail.kyc_status" class="badge rounded-pill" :class="enums.cssClass('kyc-verification-statuses', detail.kyc_status)">
          KYC: {{ enums.label('kyc-verification-statuses', detail.kyc_status, detail.kyc_status) }}
        </span>
      </div>
    </div>

    <div class="row g-2 mb-3 text-muted small">
      <div class="col-6"><i class="bi bi-calendar-event me-1"></i> Registro: {{ formatDate(detail.date_joined) }}</div>
      <div class="col-6"><i class="bi bi-clock-history me-1"></i> Último acceso: {{ detail.last_login ? formatDate(detail.last_login) : 'Nunca' }}</div>
    </div>

    <!-- Tipo de perfil -->
    <div class="mb-4">
      <span v-if="detail.is_staff" class="badge bg-primary-subtle text-primary border border-primary-subtle">Administrador</span>
      <span v-else class="badge" :class="enums.cssClass('user-types', detail.profile?.user_type)">
        {{ enums.label('user-types', detail.profile?.user_type, detail.profile?.user_type) }}
      </span>
    </div>

    <!-- Identidad / contacto -->
    <section class="mb-4">
      <h6 class="text-uppercase text-muted small fw-bold mb-2">Contacto</h6>
      <dl class="row small mb-0">
        <dt class="col-5 text-muted">Teléfono</dt><dd class="col-7">{{ detail.profile?.phone_number || '—' }}</dd>
        <dt class="col-5 text-muted">Documento</dt><dd class="col-7">{{ documentLabel }}</dd>
        <dt class="col-5 text-muted">Dirección</dt><dd class="col-7">{{ detail.profile?.address || '—' }}</dd>
        <dt class="col-5 text-muted">Ciudad / Estado</dt><dd class="col-7">{{ cityStateLabel }}</dd>
        <dt class="col-5 text-muted">País</dt><dd class="col-7">{{ detail.profile?.country || '—' }}</dd>
      </dl>
    </section>

    <!-- Perfil profesional (segun tipo) -->
    <section v-if="showProfessionalSection" class="mb-4">
      <h6 class="text-uppercase text-muted small fw-bold mb-2">Información profesional</h6>
      <dl class="row small mb-0">
        <dt class="col-5 text-muted">Empresa</dt><dd class="col-7">{{ detail.profile?.company || '—' }}</dd>
        <dt class="col-5 text-muted">Cargo</dt><dd class="col-7">{{ detail.profile?.position || '—' }}</dd>
        <dt class="col-5 text-muted">Tarifa/hora</dt><dd class="col-7">{{ formatRate(detail.profile?.hourly_rate) }}</dd>
        <dt class="col-5 text-muted">Tarifa/día</dt><dd class="col-7">{{ formatRate(detail.profile?.daily_rate) }}</dd>
        <dt class="col-5 text-muted">Tarifa/proyecto</dt><dd class="col-7">{{ formatRate(detail.profile?.project_rate) }}</dd>
      </dl>
    </section>

    <!-- Perfil de tecnico -->
    <section v-if="detail.technician_profile" class="mb-4">
      <h6 class="text-uppercase text-muted small fw-bold mb-2">Perfil de técnico</h6>
      <div class="d-flex align-items-center gap-2 mb-2">
        <span :class="['badge rounded-pill', detail.technician_profile.is_available ? 'bg-success-subtle text-success' : 'bg-secondary-subtle text-secondary']">
          {{ detail.technician_profile.is_available ? 'Disponible' : 'No disponible' }}
        </span>
      </div>
      <div class="d-flex flex-wrap gap-1">
        <span v-for="s in detail.technician_profile.specialties" :key="s" class="badge bg-info-subtle text-info border border-info-subtle">{{ s }}</span>
        <span v-if="!detail.technician_profile.specialties?.length" class="text-muted small">Sin especialidades registradas.</span>
      </div>
    </section>

    <!-- Perfil de despachador -->
    <section v-if="detail.dispatcher_profile" class="mb-4">
      <h6 class="text-uppercase text-muted small fw-bold mb-2">Perfil de despachador</h6>
      <dl class="row small mb-0">
        <dt class="col-5 text-muted">Tipo</dt><dd class="col-7">{{ detail.dispatcher_profile.dispatcher_type }}</dd>
        <dt class="col-5 text-muted">Vehículo</dt><dd class="col-7">{{ detail.dispatcher_profile.vehicle_type || '—' }} {{ detail.dispatcher_profile.vehicle_plate }}</dd>
        <dt class="col-5 text-muted">Cobertura</dt><dd class="col-7">{{ (detail.dispatcher_profile.coverage_cities || []).join(', ') || '—' }}</dd>
        <dt class="col-5 text-muted">Disponible</dt><dd class="col-7">{{ detail.dispatcher_profile.is_available ? 'Sí' : 'No' }}</dd>
      </dl>
    </section>

    <!-- Grupos -->
    <section class="mb-4">
      <div class="d-flex align-items-center justify-content-between mb-2">
        <h6 class="text-uppercase text-muted small fw-bold mb-0">Grupos</h6>
        <button class="btn btn-sm btn-link p-0" @click="toggleGroupsEditor">
          {{ editingGroups ? 'Cancelar' : 'Editar' }}
        </button>
      </div>

      <div v-if="!editingGroups" class="d-flex flex-wrap gap-1">
        <span v-for="g in detail.groups" :key="g.id" class="badge bg-secondary-subtle text-secondary border border-secondary-subtle">{{ g.name }}</span>
        <span v-if="!detail.groups?.length" class="text-muted small">Sin grupos asignados.</span>
      </div>
      <div v-else>
        <div v-for="g in groupsCatalog" :key="g.id" class="form-check">
          <input
            class="form-check-input"
            type="checkbox"
            :id="`group-${g.id}`"
            :value="g.id"
            v-model="selectedGroupIds"
          />
          <label class="form-check-label small" :for="`group-${g.id}`">{{ g.name }}</label>
        </div>
        <button class="btn btn-sm btn-primary mt-2" :disabled="actionLoading" @click="saveGroups">
          <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>
          Guardar grupos
        </button>
      </div>
      <p class="text-muted smaller fst-italic mb-0 mt-2">
        Esta asignación no otorga permisos en la aplicación. La autorización actual se basa en
        is_staff/is_superuser y el tipo de perfil.
      </p>
    </section>

    <!-- Verificacion KYC -->
    <section class="mb-4">
      <h6 class="text-uppercase text-muted small fw-bold mb-2">Verificación KYC</h6>
      <KycVerificationPanel
        v-if="detail.kyc_verification"
        :verification="detail.kyc_verification"
        :reviewable="false"
        @changed="() => loadDetail(props.item.uuid)"
      />
      <div v-else class="text-muted small">Sin verificación KYC.</div>
    </section>

    <!-- Auditoria -->
    <section class="mb-3">
      <h6 class="text-uppercase text-muted small fw-bold mb-2">Historial de actividad</h6>
      <div v-if="auditLog.length === 0" class="text-muted small">Sin eventos registrados.</div>
      <ul v-else class="list-unstyled small mb-0">
        <li v-for="entry in auditLog" :key="entry.uuid" class="border-bottom py-2">
          <div class="d-flex justify-content-between">
            <span class="fw-semibold">{{ entry.action_display }}</span>
            <span class="text-muted smaller">{{ formatDate(entry.created_at) }}</span>
          </div>
          <div class="text-muted smaller">Por: {{ entry.actor_email || 'Sistema' }}</div>
        </li>
      </ul>
      <button v-if="auditNext" class="btn btn-sm btn-light border mt-2" :disabled="auditLoading" @click="loadMoreAudit">
        <span v-if="auditLoading" class="spinner-border spinner-border-sm me-1"></span>
        Cargar más
      </button>
    </section>

    <!-- Acciones -->
    <div class="d-flex gap-2 justify-content-end border-top pt-3">
      <button
        class="btn btn-sm"
        :class="detail.is_active ? 'btn-outline-secondary' : 'btn-outline-success'"
        :disabled="actionLoading"
        @click="confirmToggleActive"
      >
        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>
        {{ detail.is_active ? 'Desactivar' : 'Activar' }}
      </button>
      <button class="btn btn-outline-danger btn-sm" :disabled="actionLoading" @click="confirmResetPassword">
        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>
        Restablecer contraseña
      </button>
      <button v-if="!detail.is_verified" class="btn btn-outline-secondary btn-sm" :disabled="actionLoading" @click="doResendVerification">
        <span v-if="actionLoading" class="spinner-border spinner-border-sm me-1"></span>
        Reenviar verificación
      </button>
      <button class="btn btn-primary btn-sm" @click="$emit('edit')">Editar</button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import { storeToRefs } from 'pinia';
import { formatCOP } from '@/utils/money';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useEnums } from '@/composables/useEnums';
import { useAuthStore } from '@/store/auth';
import { useUsersAdminStore } from '@/store/usersAdmin';
import KycVerificationPanel from '@/modules/kyc/KycVerificationPanel.vue';

const props = defineProps({
  item: { type: Object, default: null },
});
const emit = defineEmits(['edit', 'changed']);

const toast = useToast();
const { handleError } = useErrorHandler();
const enums = useEnums();
const authStore = useAuthStore();
const store = useUsersAdminStore();
const {
  currentDetail: detail, detailLoading: loading,
  auditLog, auditNext, auditLoading,
  groupsCatalog,
  actionLoading,
} = storeToRefs(store);

const editingGroups = ref(false);
const selectedGroupIds = ref([]);

const PROFESSIONAL_TYPES = new Set(['PROFESSIONAL', 'CONTRACTOR', 'SPECIALIST', 'ACCOUNTANT', 'TECHNICIAN']);
const showProfessionalSection = computed(() => PROFESSIONAL_TYPES.has(detail.value?.profile?.user_type));

const documentLabel = computed(() => {
  const p = detail.value?.profile;
  if (!p?.document) return '—';
  return `${p.document_type || ''} ${p.document}`.trim();
});
const cityStateLabel = computed(() => {
  const p = detail.value?.profile;
  return [p?.city, p?.state].filter(Boolean).join(', ') || '—';
});

function formatDate(d) {
  return d ? new Date(d).toLocaleString('es-CO', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—';
}
function formatRate(v) {
  if (!v) return '—';
  return formatCOP(v, { withSymbol: true });
}
function loadDetail(uuid) {
  return store.fetchDetail(uuid);
}

function loadAudit(uuid, url = null) {
  return store.fetchAudit(uuid, url);
}
function loadMoreAudit() {
  if (auditNext.value) loadAudit(props.item.uuid, auditNext.value);
}

async function confirmResetPassword() {
  if (!confirm(`¿Restablecer la contraseña de ${detail.value.email}? Se enviará una temporal por correo.`)) return;
  const res = await store.resetPassword(props.item.uuid);
  if (res.ok) {
    toast.success('Contraseña restablecida y enviada por correo.');
    emit('changed');
  } else {
    handleError(res.error, 'No se pudo restablecer la contraseña.');
  }
}

async function confirmToggleActive() {
  if (authStore.user?.uuid === detail.value.uuid) {
    toast.error('No puedes desactivarte a ti mismo.');
    return;
  }
  const next = !detail.value.is_active;
  if (!confirm(`¿${next ? 'Activar' : 'Desactivar'} el acceso de ${detail.value.email} a la plataforma?`)) return;
  const res = await store.patchUser(props.item.uuid, { is_active: next });
  if (res.ok) {
    detail.value = { ...detail.value, ...res.data };
    toast.success(`Usuario ${next ? 'activado' : 'desactivado'} correctamente.`);
    emit('changed');
  } else {
    handleError(res.error, 'No se pudo cambiar el estado.');
  }
}

async function doResendVerification() {
  const res = await store.resendVerification(props.item.uuid);
  if (res.ok) toast.success('Enlace de verificación reenviado.');
  else handleError(res.error, 'No se pudo reenviar la verificación.');
}

async function toggleGroupsEditor() {
  if (!editingGroups.value) {
    const res = await store.fetchGroupsCatalog();
    if (!res.ok) { toast.error('No se pudo cargar el catálogo de grupos.'); return; }
  }
  selectedGroupIds.value = (detail.value.groups || []).map((g) => g.id);
  editingGroups.value = !editingGroups.value;
}

async function saveGroups() {
  const res = await store.saveGroups(props.item.uuid, selectedGroupIds.value);
  if (res.ok) {
    detail.value = res.data;
    editingGroups.value = false;
    toast.success('Grupos actualizados.');
    emit('changed');
  } else {
    handleError(res.error, 'No se pudieron actualizar los grupos.');
  }
}

watch(
  () => props.item?.uuid,
  (uuid) => {
    if (!uuid) return;
    editingGroups.value = false;
    auditLog.value = [];
    auditNext.value = null;
    loadDetail(uuid);
    loadAudit(uuid);
    enums.ensure('user-types');
    enums.ensure('kyc-verification-statuses');
    enums.ensure('kyc-document-statuses');
  },
  { immediate: true },
);
</script>

<style scoped>
.smaller { font-size: 0.75rem; }
dt { font-weight: 500; }
</style>
