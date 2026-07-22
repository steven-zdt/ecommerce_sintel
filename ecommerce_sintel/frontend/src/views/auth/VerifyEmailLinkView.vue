<template>
  <div class="login-page">
    <div class="login-wrapper">
      <div class="logo-box">S</div>

      <template v-if="status === 'loading'">
        <h2 class="login-title">Verificando tu correo...</h2>
        <div class="spinner mx-auto mt-3"></div>
      </template>

      <template v-else-if="status === 'success'">
        <h2 class="login-title text-success">
          <i class="bi bi-check-circle-fill me-1"></i> Correo verificado
        </h2>
        <p class="login-subtitle">Tu correo fue verificado exitosamente. Ya puedes iniciar sesión.</p>
      </template>

      <template v-else>
        <h2 class="login-title text-danger">
          <i class="bi bi-x-circle-fill me-1"></i> No se pudo verificar
        </h2>
        <p class="login-subtitle">{{ errorMsg }}</p>
      </template>

      <div class="back-link">
        <RouterLink to="/login">
          <i class="bi bi-arrow-left me-1"></i> Ir a iniciar sesión
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import useApi from '@/composables/useApi';

const route = useRoute();
const api = useApi();

const status = ref('loading'); // 'loading' | 'success' | 'error'
const errorMsg = ref('');

onMounted(async () => {
  const token = route.query.token;
  if (!token) {
    status.value = 'error';
    errorMsg.value = 'Enlace inválido: falta el token de verificación.';
    return;
  }
  try {
    await api.post('auth/verify-email-confirm/', { token });
    status.value = 'success';
  } catch (err) {
    status.value = 'error';
    errorMsg.value = err.response?.data?.token?.[0] || err.response?.data?.detail || 'El enlace es inválido o expiró.';
  }
});
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f0f4ff 0%, #e8efff 100%);
  font-family: 'Inter', sans-serif;
}
.login-wrapper {
  width: 100%;
  max-width: 420px;
  background: rgba(255, 255, 255, 0.92);
  backdrop-filter: blur(10px);
  border-radius: 1.5rem;
  box-shadow: 0 20px 60px rgba(30, 58, 138, 0.12);
  padding: 2.5rem;
  text-align: center;
}
.logo-box {
  width: 64px; height: 64px;
  background: linear-gradient(135deg, #2563eb 0%, #1e3a8a 100%);
  color: white;
  border-radius: 1.25rem;
  display: flex; align-items: center; justify-content: center;
  margin: 0 auto 1.5rem;
  font-size: 1.75rem; font-weight: 800;
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.3);
}
.login-title { font-size: 1.5rem; font-weight: 700; margin-bottom: .25rem; }
.login-subtitle { color: #64748b; font-size: .875rem; margin-bottom: 1.5rem; }
.spinner {
  display: inline-block; width: 28px; height: 28px;
  border: 3px solid rgba(37,99,235,.2); border-top-color: #2563eb;
  border-radius: 50%; animation: spin .7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.back-link { margin-top: 1.25rem; }
.back-link a { color: #94a3b8; font-size: .875rem; text-decoration: none; }
.back-link a:hover { color: #1e3a8a; }
</style>
