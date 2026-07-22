<template>
  <CustomerAuthLayout variant="split">
    <h1 class="h4 fw-bold mb-1">Bienvenido de nuevo</h1>
    <p class="text-muted small mb-4">Ingresa tus credenciales para acceder a tu cuenta</p>

    <div v-if="errorMsg" class="error-alert" role="alert" aria-live="polite">
      <i class="bi bi-exclamation-triangle-fill me-2"></i>{{ errorMsg }}
    </div>

    <form @submit.prevent="handleLogin" novalidate>
      <div class="form-floating mb-3">
        <input
          id="login-email"
          v-model="form.email"
          type="email"
          class="form-control"
          placeholder="tu@email.com"
          autocomplete="email"
          required
        >
        <label for="login-email">Correo electrónico</label>
      </div>

      <div class="form-floating mb-1 position-relative">
        <input
          id="login-password"
          v-model="form.password"
          :type="showPassword ? 'text' : 'password'"
          class="form-control pe-5"
          placeholder="Contraseña"
          autocomplete="current-password"
          required
          @keyup="onPasswordKeyup"
        >
        <label for="login-password">Contraseña</label>
        <button
          type="button" class="eye-btn" tabindex="-1"
          :aria-label="showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'"
          @click="showPassword = !showPassword"
        >
          <i :class="showPassword ? 'bi bi-eye-slash' : 'bi bi-eye'" aria-hidden="true"></i>
        </button>
      </div>
      <p v-if="capsLockOn" class="caps-lock-hint" role="status">
        <i class="bi bi-info-circle me-1" aria-hidden="true"></i>Bloq Mayús está activado
      </p>

      <div class="d-flex justify-content-between align-items-center my-3">
        <div class="form-check">
          <input id="remember-me" v-model="remember" class="form-check-input" type="checkbox">
          <label for="remember-me" class="form-check-label small">Recordarme</label>
        </div>
        <RouterLink :to="{ name: 'forgot-password' }" class="small forgot-link">¿Olvidaste tu contraseña?</RouterLink>
      </div>

      <button type="submit" class="btn-login" :disabled="loading">
        <span v-if="!loading">Iniciar sesión</span>
        <span v-else><span class="spinner"></span> Autenticando...</span>
      </button>
    </form>

    <p class="text-center text-muted small mt-4 mb-0">
      ¿No tienes cuenta?
      <RouterLink :to="{ name: 'register' }" class="fw-semibold text-decoration-none">Crear cuenta</RouterLink>
    </p>
  </CustomerAuthLayout>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useAuth } from '@/composables/useAuth';
import { useAuthStore } from '@/store/auth';
import CustomerAuthLayout from '@/components/auth/CustomerAuthLayout.vue';

const router = useRouter();
const authStore = useAuthStore();
const { login } = useAuth();

const form = reactive({ email: '', password: '' });
const loading = ref(false);
const errorMsg = ref('');
const showPassword = ref(false);
const remember = ref(true);
const capsLockOn = ref(false);

onMounted(() => document.getElementById('login-email')?.focus());

function onPasswordKeyup(event) {
  capsLockOn.value = event.getModifierState && event.getModifierState('CapsLock');
}

async function handleLogin() {
  errorMsg.value = '';
  loading.value = true;
  try {
    const user = await login(form.email, form.password, remember.value);
    // El backend ya rechaza is_staff/is_superuser en este endpoint -- esto es
    // defensa en profundidad, nunca deberia ejecutarse. Las cuentas de
    // administracion inician sesion SOLO desde panel.sintel.net.co; jamas se
    // debe reflejar (ni siquiera brevemente) una sesion de admin en el sitio
    // publico de clientes.
    if (user.is_staff === true || user.is_superuser === true) {
      authStore.logout();
      errorMsg.value = 'Esta cuenta debe iniciar sesion desde el panel de administracion.';
      return;
    }
    router.push({ name: 'shop-catalog' });
  } catch (err) {
    const detail = err.response?.data?.detail || err.response?.data?.non_field_errors?.[0];
    errorMsg.value = detail || 'Credenciales invalidas. Intentalo de nuevo.';
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.error-alert {
  background: #fef2f2; color: #dc2626; border: 1px solid #fecaca;
  border-radius: .75rem; padding: .75rem 1rem;
  font-size: .875rem; margin-bottom: 1.25rem;
}

.eye-btn {
  position: absolute; right: .9rem; top: 50%; transform: translateY(-50%);
  background: none; border: none; color: #94a3b8; cursor: pointer; padding: 0; z-index: 5;
}

.caps-lock-hint {
  font-size: .8rem; color: #b45309; margin: .35rem 0 0;
}

.forgot-link { color: #2563eb; text-decoration: none; }
.forgot-link:hover { text-decoration: underline; }

.btn-login {
  width: 100%; padding: .8rem;
  background: linear-gradient(135deg, #2563eb 0%, #1e3a8a 100%);
  color: #fff; border: none; border-radius: .75rem;
  font-size: 1rem; font-weight: 600; cursor: pointer;
  transition: all .3s; margin-top: .25rem;
}
.btn-login:hover:not(:disabled) {
  opacity: .9; transform: scale(1.01);
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.3);
}
.btn-login:disabled { opacity: .65; cursor: not-allowed; }

.spinner {
  display: inline-block; width: 14px; height: 14px;
  border: 2px solid rgba(255,255,255,.4); border-top-color: #fff;
  border-radius: 50%; animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
</style>
