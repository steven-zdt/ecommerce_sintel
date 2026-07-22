<template>
  <CustomerAccountShell>
    <CustomerPageHeader title="Mi perfil" subtitle="Tu informacion personal, de contacto y seguridad, en un solo lugar." />

    <CustomerSkeleton v-if="loading" :count="3" height="140px" />
    <CustomerErrorState v-else-if="loadError" @retry="fetchProfile" />

    <template v-else>
      <!-- Informacion Personal -->
      <CustomerSection title="Informacion Personal" icon="bi-person-badge">
        <template #actions>
          <CustomerButton variant="secondary" @click="scrollToSecurity">
            <i class="bi bi-gear me-1"></i>Gestionar cuenta
          </CustomerButton>
          <CustomerButton variant="secondary" @click="showAvatarPanel = true">
            <i class="bi bi-camera me-1"></i>Cambiar foto
          </CustomerButton>
          <CustomerButton variant="primary" @click="openEdit">
            <i class="bi bi-pencil me-1"></i>Editar perfil
          </CustomerButton>
        </template>

        <div class="profile-identity">
          <CustomerAvatar :src="currentAvatar" :initials="initials" :size="88" @click="showAvatarPanel = true" />
          <div class="profile-identity-text">
            <p class="profile-name">{{ fullName }}</p>
            <span class="badge bg-primary-subtle text-primary border border-primary-subtle small">
              {{ userTypeLabel }}
            </span>
          </div>
        </div>

        <CustomerDetailRow label="Nombre completo" :value="fullName" icon="bi-person" />
        <CustomerDetailRow label="Tipo de usuario" :value="userTypeLabel" icon="bi-tag" />
        <CustomerDetailRow label="Fecha de registro" :value="formattedJoinDate" icon="bi-calendar3" />
        <CustomerDetailRow label="Estado de la cuenta" icon="bi-shield-check">
          <span class="badge" :class="user?.is_active ? 'bg-success-subtle text-success' : 'bg-secondary-subtle text-secondary'">
            {{ user?.is_active ? 'Activa' : 'Inactiva' }}
          </span>
        </CustomerDetailRow>
      </CustomerSection>

      <!-- Informacion de Contacto -->
      <CustomerSection title="Informacion de Contacto" icon="bi-person-lines-fill">
        <CustomerDetailRow label="Correo" :value="user?.email" icon="bi-envelope" />
        <CustomerDetailRow label="Celular" :value="profile?.phone_number || 'No registrado'" icon="bi-telephone" />
        <CustomerDetailRow label="Tipo de documento" :value="profile?.document_type || 'No registrado'" icon="bi-card-text" />
        <CustomerDetailRow label="Numero de documento" :value="profile?.document || 'No registrado'" icon="bi-hash" />
      </CustomerSection>

      <!-- Ubicacion -->
      <CustomerSection title="Ubicacion" icon="bi-geo-alt">
        <CustomerDetailRow label="Direccion" :value="profile?.address || 'No registrada'" icon="bi-signpost-2" />
        <CustomerDetailRow label="Ciudad" :value="profile?.city || 'No registrada'" icon="bi-building" />
        <CustomerDetailRow label="Departamento" :value="profile?.state || 'No registrado'" icon="bi-map" />
        <CustomerDetailRow label="Pais" :value="profile?.country || 'No registrado'" icon="bi-flag" />
      </CustomerSection>

      <!-- Seguridad -->
      <CustomerSection ref="securitySection" title="Seguridad" icon="bi-shield-lock">
        <CustomerDetailRow label="Verificacion de correo" icon="bi-envelope-check">
          <span class="badge" :class="user?.is_verified ? 'bg-success-subtle text-success' : 'bg-warning-subtle text-warning'">
            {{ user?.is_verified ? 'Verificado' : 'Pendiente' }}
          </span>
        </CustomerDetailRow>
        <CustomerDetailRow label="Estado del telefono" icon="bi-telephone-plus">
          <span class="badge" :class="profile?.phone_number ? 'bg-success-subtle text-success' : 'bg-secondary-subtle text-secondary'">
            {{ profile?.phone_number ? 'Registrado' : 'Sin registrar' }}
          </span>
        </CustomerDetailRow>

        <form class="mt-4 pt-3 border-top" @submit.prevent="changePassword">
          <p class="fw-semibold small mb-3">Cambiar contrasena</p>
          <div class="row g-3">
            <div class="col-sm-4">
              <label class="form-label small fw-semibold">Contrasena actual</label>
              <input v-model="pwForm.old_password" type="password" class="form-control" required />
            </div>
            <div class="col-sm-4">
              <label class="form-label small fw-semibold">Nueva contrasena</label>
              <input v-model="pwForm.new_password" type="password" class="form-control" required />
            </div>
            <div class="col-sm-4">
              <label class="form-label small fw-semibold">Confirmar nueva</label>
              <input v-model="pwForm.confirm" type="password" class="form-control" required />
            </div>
          </div>
          <div class="d-flex justify-content-end mt-3">
            <CustomerButton variant="danger" size="md" :loading="savingPw">
              Cambiar contrasena
            </CustomerButton>
          </div>
        </form>
      </CustomerSection>
    </template>

    <!-- Editar perfil -->
    <CustomerOverlayPanel v-model="showEdit" title="Editar perfil" subtitle="Actualiza tu informacion personal, de contacto y ubicacion.">
      <form @submit.prevent="saveProfile">
        <div class="row g-3">
          <div class="col-sm-6">
            <label class="form-label small fw-semibold">Nombre</label>
            <input v-model="form.first_name" type="text" class="form-control" />
          </div>
          <div class="col-sm-6">
            <label class="form-label small fw-semibold">Apellido</label>
            <input v-model="form.last_name" type="text" class="form-control" />
          </div>
          <div class="col-sm-6">
            <label class="form-label small fw-semibold">Celular</label>
            <input v-model="form.phone_number" type="tel" class="form-control" placeholder="3001234567" />
          </div>
          <div class="col-sm-6">
            <label class="form-label small fw-semibold">Empresa</label>
            <input v-model="form.company" type="text" class="form-control" />
          </div>
          <div class="col-12">
            <label class="form-label small fw-semibold">Direccion</label>
            <input v-model="form.address" type="text" class="form-control" />
          </div>
          <div class="col-sm-4">
            <label class="form-label small fw-semibold">Ciudad</label>
            <input v-model="form.city" type="text" class="form-control" />
          </div>
          <div class="col-sm-4">
            <label class="form-label small fw-semibold">Departamento</label>
            <input v-model="form.state" type="text" class="form-control" />
          </div>
          <div class="col-sm-4">
            <label class="form-label small fw-semibold">Pais</label>
            <input v-model="form.country" type="text" class="form-control" />
          </div>
        </div>
        <div class="d-flex justify-content-end mt-4">
          <CustomerButton variant="primary" size="md" :loading="saving">
            <i class="bi bi-floppy me-2"></i>Guardar cambios
          </CustomerButton>
        </div>
      </form>
    </CustomerOverlayPanel>

    <!-- Cambiar foto -->
    <CustomerOverlayPanel v-model="showAvatarPanel" title="Cambiar foto de perfil" width="420px">
      <div class="avatar-upload-area">
        <CustomerAvatar :src="avatarPreview || currentAvatar" :initials="initials" :size="96" />
        <div class="avatar-actions">
          <label class="btn btn-outline-primary btn-sm" for="avatar-input">
            <i class="bi bi-upload me-1"></i>Subir foto
          </label>
          <input id="avatar-input" type="file" accept="image/jpeg,image/png,image/webp" class="d-none" @change="onAvatarChange" />
          <CustomerButton v-if="avatarFile" variant="primary" :loading="savingAvatar" @click="saveAvatar">
            Guardar foto
          </CustomerButton>
          <p class="text-muted small mb-0">JPG, PNG o WEBP. Max 5MB.</p>
        </div>
      </div>
    </CustomerOverlayPanel>
  </CustomerAccountShell>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useEnums } from '@/composables/useEnums';
import { useToast } from '@/composables/useToast';
import { useAuthStore } from '@/store/auth';
import CustomerAccountShell from '@/components/customer/account/CustomerAccountShell.vue';
import CustomerPageHeader from '@/components/customer/account/CustomerPageHeader.vue';
import CustomerSection from '@/components/customer/account/CustomerSection.vue';
import CustomerDetailRow from '@/components/customer/account/CustomerDetailRow.vue';
import CustomerAvatar from '@/components/customer/account/CustomerAvatar.vue';
import CustomerButton from '@/components/customer/account/CustomerButton.vue';
import CustomerOverlayPanel from '@/components/customer/account/CustomerOverlayPanel.vue';
import CustomerSkeleton from '@/components/customer/account/CustomerSkeleton.vue';
import CustomerErrorState from '@/components/customer/account/CustomerErrorState.vue';

const api = useApi();
const toast = useToast();
const authStore = useAuthStore();
const enums = useEnums();

const loading = ref(true);
const loadError = ref(false);
const saving = ref(false);
const savingAvatar = ref(false);
const savingPw = ref(false);
const showEdit = ref(false);
const showAvatarPanel = ref(false);
const securitySection = ref(null);

function scrollToSecurity() {
  securitySection.value?.$el?.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

const avatarFile = ref(null);
const avatarPreview = ref(null);

const user = ref(null);
const profile = computed(() => user.value?.profile || null);

const form = ref({ first_name: '', last_name: '', phone_number: '', company: '', address: '', city: '', state: '', country: '' });
const pwForm = ref({ old_password: '', new_password: '', confirm: '' });

const fullName = computed(() => user.value?.full_name || [profile.value?.first_name, profile.value?.last_name].filter(Boolean).join(' ') || user.value?.email || 'Mi cuenta');

const initials = computed(() => {
  const parts = fullName.value.split(' ').filter(Boolean);
  return parts.slice(0, 2).map(p => p[0]?.toUpperCase()).join('');
});

const formattedJoinDate = computed(() => {
  if (!user.value?.date_joined) return 'No disponible';
  try {
    return new Date(user.value.date_joined).toLocaleDateString('es-CO', { day: '2-digit', month: 'long', year: 'numeric' });
  } catch {
    return user.value.date_joined;
  }
});

const userTypeLabel = computed(() => enums.label('user-types', profile.value?.user_type, profile.value?.user_type || 'Cliente'));

const currentAvatar = computed(() => {
  const pic = profile.value?.profile_picture;
  if (!pic) return null;
  return pic.startsWith('http') ? pic : `/media/${pic}`;
});

async function fetchProfile() {
  loading.value = true;
  loadError.value = false;
  try {
    await enums.ensure('user-types');
    const res = await api.get('auth/profile/');
    user.value = res.data;
  } catch {
    loadError.value = true;
    toast.error('Error al cargar el perfil');
  } finally {
    loading.value = false;
  }
}

function openEdit() {
  form.value = {
    first_name: profile.value?.first_name || '',
    last_name: profile.value?.last_name || '',
    phone_number: profile.value?.phone_number || '',
    company: profile.value?.company || '',
    address: profile.value?.address || '',
    city: profile.value?.city || '',
    state: profile.value?.state || '',
    country: profile.value?.country || '',
  };
  showEdit.value = true;
}

function onAvatarChange(e) {
  const file = e.target.files?.[0];
  if (!file) return;
  if (file.size > 5 * 1024 * 1024) {
    toast.error('La imagen no puede superar 5MB');
    return;
  }
  avatarFile.value = file;
  avatarPreview.value = URL.createObjectURL(file);
}

async function saveAvatar() {
  if (!avatarFile.value) return;
  savingAvatar.value = true;
  try {
    const fd = new FormData();
    fd.append('profile_picture', avatarFile.value);
    const res = await api.patch('auth/profile/', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    user.value = { ...user.value, profile: { ...user.value.profile, ...res.data } };
    authStore.user = { ...authStore.user, ...res.data };
    avatarFile.value = null;
    showAvatarPanel.value = false;
    toast.success('Foto actualizada');
  } catch {
    toast.error('Error al actualizar la foto');
  } finally {
    savingAvatar.value = false;
  }
}

async function saveProfile() {
  saving.value = true;
  try {
    const res = await api.patch('auth/profile/', { ...form.value });
    user.value = { ...user.value, profile: { ...user.value.profile, ...res.data } };
    authStore.user = { ...authStore.user, ...res.data };
    showEdit.value = false;
    toast.success('Perfil actualizado');
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Error al guardar');
  } finally {
    saving.value = false;
  }
}

async function changePassword() {
  if (pwForm.value.new_password !== pwForm.value.confirm) {
    toast.error('Las contrasenas no coinciden');
    return;
  }
  savingPw.value = true;
  try {
    await api.post('auth/change-password/', {
      old_password: pwForm.value.old_password,
      new_password: pwForm.value.new_password,
    });
    pwForm.value = { old_password: '', new_password: '', confirm: '' };
    toast.success('Contrasena cambiada correctamente');
  } catch (e) {
    toast.error(e.response?.data?.old_password?.[0] || e.response?.data?.detail || 'Error al cambiar contrasena');
  } finally {
    savingPw.value = false;
  }
}

onMounted(fetchProfile);
</script>

<style scoped>
.profile-identity {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid #f3f4f6;
}

.profile-name {
  font-weight: 700;
  font-size: 1.05rem;
  color: var(--acc-text, #111827);
  margin: 0 0 4px;
}

.avatar-upload-area {
  display: flex;
  align-items: center;
  gap: 20px;
}

.avatar-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
