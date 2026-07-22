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
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
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
</script>

<style scoped>
.profile-avatar {
  width: 80px; height: 80px; background: linear-gradient(135deg, #2563eb, #1e3a8a);
  color: #fff; border-radius: 1.25rem; display: flex; align-items: center; justify-content: center;
  font-size: 2rem; font-weight: 700; box-shadow: 0 8px 20px rgba(37, 99, 235, .3);
}
</style>
