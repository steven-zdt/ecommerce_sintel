<template>
  <div>
    <h4 class="fw-bold mb-4">Mi Perfil</h4>
    <div class="row g-4">
      <!-- Avatar + info -->
      <div class="col-lg-4">
        <div class="card shadow-sm border-0 rounded-4 p-4 text-center">
          <div class="profile-avatar mx-auto mb-3">{{ initials }}</div>
          <h5 class="fw-bold mb-1">{{ profile.first_name }} {{ profile.last_name }}</h5>
          <p class="text-muted small mb-2">{{ profile.email }}</p>
          <span class="badge" :class="roleClass">{{ roleLabel }}</span>
        </div>
      </div>

      <!-- Datos editables -->
      <div class="col-lg-8">
        <div class="card shadow-sm border-0 rounded-4 p-4">
          <h6 class="fw-bold mb-3">Información Personal</h6>
          <form @submit.prevent="saveProfile">
            <div class="row g-3">
              <div class="col-sm-6">
                <label class="form-label">Nombre</label>
                <input v-model="profile.first_name" class="form-control" type="text" />
              </div>
              <div class="col-sm-6">
                <label class="form-label">Apellido</label>
                <input v-model="profile.last_name" class="form-control" type="text" />
              </div>
              <div class="col-12">
                <label class="form-label">Correo electrónico</label>
                <input :value="profile.email" class="form-control" type="email" disabled />
              </div>
              <div class="col-sm-6">
                <label class="form-label">Teléfono</label>
                <input v-model="profile.phone_number" class="form-control" type="tel" />
              </div>
            </div>
            <div class="d-flex gap-2 mt-4">
              <button type="submit" class="btn btn-primary" :disabled="saving">
                {{ saving ? 'Guardando...' : 'Guardar Cambios' }}
              </button>
            </div>
            <div v-if="successMsg" class="alert alert-success mt-3 py-2 small">{{ successMsg }}</div>
            <div v-if="errorMsg" class="alert alert-danger mt-3 py-2 small">{{ errorMsg }}</div>
          </form>
        </div>
      </div>

      <!-- Seguridad de la cuenta -->
      <div class="col-12">
        <div class="card shadow-sm border-0 rounded-4 p-4">
          <div class="d-flex flex-column flex-md-row justify-content-between align-items-md-center gap-3 mb-4">
            <div>
              <h6 class="fw-bold mb-1">Seguridad de la cuenta</h6>
              <p class="text-muted small mb-0">Actualiza tu contraseña o usa un código enviado a {{ profile.email }} si no recuerdas la actual.</p>
            </div>
            <RouterLink :to="{ name: 'admin-forgot-password' }" class="btn btn-outline-primary">
              <i class="bi bi-envelope-check me-1"></i>Restablecer con código
            </RouterLink>
          </div>

          <form @submit.prevent="changePassword">
            <div class="row g-3">
              <div class="col-md-4">
                <label for="admin-current-password" class="form-label">Contraseña actual</label>
                <input id="admin-current-password" v-model="passwordForm.old_password" class="form-control" type="password" autocomplete="current-password" required>
              </div>
              <div class="col-md-4">
                <label for="admin-new-password" class="form-label">Nueva contraseña</label>
                <input id="admin-new-password" v-model="passwordForm.new_password" class="form-control" type="password" autocomplete="new-password" required>
              </div>
              <div class="col-md-4">
                <label for="admin-confirm-password" class="form-label">Confirmar nueva contraseña</label>
                <input id="admin-confirm-password" v-model="passwordForm.confirm_password" class="form-control" type="password" autocomplete="new-password" required>
              </div>
            </div>
            <div class="d-flex flex-wrap align-items-center gap-3 mt-4">
              <button type="submit" class="btn btn-danger" :disabled="changingPassword">
                <span v-if="changingPassword" class="spinner-border spinner-border-sm me-2"></span>
                {{ changingPassword ? 'Actualizando...' : 'Cambiar contraseña' }}
              </button>
              <span v-if="passwordSuccessMsg" class="text-success small" role="status">{{ passwordSuccessMsg }}</span>
              <span v-if="passwordErrorMsg" class="text-danger small" role="alert">{{ passwordErrorMsg }}</span>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import useApi from '@/composables/useApi';
import { useAuthStore } from '@/store/auth';

const api = useApi();
const authStore = useAuthStore();

const profile = ref({ first_name: '', last_name: '', email: '', phone_number: '', is_staff: false });
// Ultimo estado confirmado por el servidor -- el header (linea 9) lee directo de
// `profile`, que tambien es el v-model de los inputs, asi que sin esto un guardado
// fallido dejaba el nombre "optimista" recien tipeado visible hasta recargar la
// pagina (hallazgo bajo, auditoria QA 2026-07-19).
const savedProfile = ref({ first_name: '', last_name: '', phone_number: '' });
const saving = ref(false);
const successMsg = ref('');
const errorMsg = ref('');
const passwordForm = ref({ old_password: '', new_password: '', confirm_password: '' });
const changingPassword = ref(false);
const passwordSuccessMsg = ref('');
const passwordErrorMsg = ref('');

const initials = computed(() => authStore.initials);
const roleLabel = computed(() => profile.value.is_staff ? 'Administrador' : 'Usuario');
const roleClass = computed(() => profile.value.is_staff ? 'bg-primary' : 'bg-secondary');

onMounted(async () => {
  try {
    const { data } = await api.get('auth/profile/');
    profile.value = { ...profile.value, ...data };
    savedProfile.value = { first_name: data.first_name, last_name: data.last_name, phone_number: data.phone_number };
    authStore.setUser(data);
  } catch (e) { console.error(e); }
});

async function saveProfile() {
  saving.value = true; successMsg.value = ''; errorMsg.value = '';
  try {
    const { data } = await api.patch('auth/profile/', {
      first_name: profile.value.first_name,
      last_name: profile.value.last_name,
      phone_number: profile.value.phone_number,
    });
    authStore.setUser(data);
    savedProfile.value = { first_name: data.first_name, last_name: data.last_name, phone_number: data.phone_number };
    successMsg.value = 'Perfil actualizado correctamente.';
  } catch (e) {
    profile.value.first_name = savedProfile.value.first_name;
    profile.value.last_name = savedProfile.value.last_name;
    profile.value.phone_number = savedProfile.value.phone_number;
    errorMsg.value = 'Error al guardar los cambios.';
  } finally {
    saving.value = false;
  }
}

async function changePassword() {
  passwordSuccessMsg.value = '';
  passwordErrorMsg.value = '';
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    passwordErrorMsg.value = 'Las contraseñas nuevas no coinciden.';
    return;
  }

  changingPassword.value = true;
  try {
    await api.post('auth/change-password/', {
      old_password: passwordForm.value.old_password,
      new_password: passwordForm.value.new_password,
    });
    passwordForm.value = { old_password: '', new_password: '', confirm_password: '' };
    passwordSuccessMsg.value = 'Contraseña actualizada correctamente.';
  } catch (error) {
    passwordErrorMsg.value = error.response?.data?.old_password?.[0]
      || error.response?.data?.new_password?.[0]
      || error.response?.data?.detail
      || 'No fue posible actualizar la contraseña.';
  } finally {
    changingPassword.value = false;
  }
}
</script>

<style scoped>
.profile-avatar {
  width: 80px; height: 80px; background: linear-gradient(135deg, #2563eb, #1e3a8a);
  color: #fff; border-radius: 1.25rem; display: flex; align-items: center; justify-content: center;
  font-size: 2rem; font-weight: 700; box-shadow: 0 8px 20px rgba(37, 99, 235, .3);
}
</style>
