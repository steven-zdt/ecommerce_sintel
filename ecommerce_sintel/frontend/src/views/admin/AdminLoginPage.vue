<template>
  <AdminAuthLayout>
    <h1 class="h5 fw-bold text-center text-white mb-1">Panel Administrativo</h1>
    <p class="text-center small mb-4 admin-subtitle">Acceso exclusivo para administradores del sistema</p>

    <div v-if="errorMsg" class="error-alert" role="alert" aria-live="polite">
      <i class="bi bi-exclamation-triangle-fill me-2"></i>{{ errorMsg }}
    </div>

    <form @submit.prevent="handleLogin" novalidate>
      <div class="form-floating mb-3">
        <input
          id="admin-login-email"
          v-model="form.email"
          type="email"
          class="form-control"
          placeholder="admin@sintel.com"
          autocomplete="email"
          required
        >
        <label for="admin-login-email">Correo electrónico</label>
      </div>

      <div class="form-floating mb-1 position-relative">
        <input
          id="admin-login-password"
          v-model="form.password"
          :type="showPassword ? 'text' : 'password'"
          class="form-control pe-5"
          placeholder="Contraseña"
          autocomplete="current-password"
          required
        >
        <label for="admin-login-password">Contraseña</label>
        <button
          type="button" class="eye-btn" tabindex="-1"
          :aria-label="showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'"
          @click="showPassword = !showPassword"
        >
          <i :class="showPassword ? 'bi bi-eye-slash' : 'bi bi-eye'" aria-hidden="true"></i>
        </button>
      </div>

      <div class="text-end my-3">
        <RouterLink :to="{ name: 'admin-forgot-password' }" class="small forgot-link">¿Olvidaste tu contraseña?</RouterLink>
      </div>

      <button type="submit" class="btn-login" :disabled="loading">
        <span v-if="!loading">Ingresar al Panel</span>
        <span v-else><span class="spinner"></span> Autenticando...</span>
      </button>
    </form>

    <div class="text-center mt-4">
      <RouterLink to="/tienda" class="back-link">
        <i class="bi bi-arrow-left me-1"></i> Volver a la tienda
      </RouterLink>
    </div>
  </AdminAuthLayout>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/store/auth';
import axios from 'axios';
import AdminAuthLayout from '@/components/auth/AdminAuthLayout.vue';

/*
 * ENDPOINT AISLADO — usa api/v1/admin-auth/login/ exclusivamente.
 * NO cambiar a auth/login/ ni a useAuth().login().
 * Ver: users/api/admin_auth.py en el backend.
 */
const adminAuthClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1/',
});

const router    = useRouter();
const authStore = useAuthStore();

const form         = reactive({ email: '', password: '' });
const loading      = ref(false);
const errorMsg     = ref('');
const showPassword = ref(false);

onMounted(() => document.getElementById('admin-login-email')?.focus());

async function handleLogin() {
  errorMsg.value = '';
  loading.value  = true;
  try {
    const { data } = await adminAuthClient.post('admin-auth/login/', {
      email:    form.email.trim().toLowerCase(),
      password: form.password,
    });
    authStore.setTokens({ access: data.tokens.access, refresh: data.tokens.refresh });
    authStore.setUser(data.user);
    router.push('/panel/dashboard');
  } catch (err) {
    const detail = err.response?.data?.detail || err.response?.data?.non_field_errors?.[0];
    errorMsg.value = detail || 'Credenciales invalidas. Intentalo de nuevo.';
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.admin-subtitle { color: rgba(255, 255, 255, .55); }

.error-alert {
  background: rgba(220, 38, 38, .12); color: #f87171; border: 1px solid rgba(220, 38, 38, .35);
  border-radius: .75rem; padding: .75rem 1rem;
  font-size: .875rem; margin-bottom: 1.25rem;
}

/* Inputs oscuros -- Bootstrap .form-floating asume fondo claro por defecto */
:deep(.form-control) {
  background: #0f1012;
  border: 1px solid rgba(255, 255, 255, .12);
  color: #fff;
}
:deep(.form-control:focus) {
  background: #0f1012;
  border-color: #38bdf8;
  box-shadow: 0 0 0 4px rgba(56, 189, 248, .15);
  color: #fff;
}
:deep(.form-floating > label) { color: rgba(255, 255, 255, .5); }
:deep(.form-control:-webkit-autofill) {
  -webkit-text-fill-color: #fff;
  -webkit-box-shadow: 0 0 0 1000px #0f1012 inset;
}

.eye-btn {
  position: absolute; right: .9rem; top: 50%; transform: translateY(-50%);
  background: none; border: none; color: rgba(255, 255, 255, .45); cursor: pointer; padding: 0; z-index: 5;
}

.forgot-link { color: #38bdf8; text-decoration: none; }
.forgot-link:hover { text-decoration: underline; }

.btn-login {
  width: 100%; padding: .8rem;
  background: linear-gradient(135deg, #38bdf8 0%, #0284c7 100%);
  color: #0a0a0a; border: none; border-radius: .75rem;
  font-size: 1rem; font-weight: 700; cursor: pointer;
  transition: all .3s;
}
.btn-login:hover:not(:disabled) {
  opacity: .9; transform: scale(1.01);
  box-shadow: 0 8px 20px rgba(56, 189, 248, .25);
}
.btn-login:disabled { opacity: .55; cursor: not-allowed; }

.spinner {
  display: inline-block; width: 14px; height: 14px;
  border: 2px solid rgba(10,10,10,.3); border-top-color: #0a0a0a;
  border-radius: 50%; animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.back-link { color: rgba(255, 255, 255, .45); font-size: .875rem; text-decoration: none; }
.back-link:hover { color: #38bdf8; }
</style>
