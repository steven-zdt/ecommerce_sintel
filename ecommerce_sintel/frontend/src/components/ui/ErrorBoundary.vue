<template>
  <div v-if="error" class="error-boundary d-flex flex-column align-items-center justify-content-center text-center p-5">
    <i class="bi bi-exclamation-octagon text-danger" style="font-size: 2.5rem;"></i>
    <h5 class="fw-bold mt-3 mb-1">Algo salio mal</h5>
    <p class="text-muted small mb-3" style="max-width: 420px;">
      Ocurrio un error inesperado al mostrar esta pantalla. Puedes intentar de nuevo o volver al inicio.
    </p>
    <div class="d-flex gap-2">
      <button class="btn btn-primary btn-sm" @click="retry">
        <i class="bi bi-arrow-clockwise me-1"></i>Reintentar
      </button>
      <button class="btn btn-light border btn-sm" @click="goHome">Ir al inicio</button>
    </div>
  </div>
  <slot v-else></slot>
</template>

<script setup>
import { ref, onErrorCaptured } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();
const error = ref(null);

onErrorCaptured((err) => {
  error.value = err;
  // eslint-disable-next-line no-console
  console.error('[ErrorBoundary]', err);
  return false; // detiene la propagacion — evita que el error rompa toda la SPA
});

function retry() {
  error.value = null;
}

function goHome() {
  error.value = null;
  router.push({ path: '/' });
}
</script>

<style scoped>
.error-boundary { min-height: 40vh; }
</style>
