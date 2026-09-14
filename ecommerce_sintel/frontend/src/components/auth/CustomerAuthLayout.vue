<template>
  <div class="auth-shell" :class="`auth-shell--${variant}`">
    <div class="auth-main">
      <RouterLink to="/" class="auth-logo">
        <span class="auth-logo-box">{{ brandInitial }}</span>
        <span class="auth-logo-text">{{ brandName }}</span>
      </RouterLink>

      <div class="auth-content auth-enter" :class="{ 'auth-content--wide': variant === 'wide' }">
        <slot />
      </div>
    </div>

    <aside v-if="variant === 'split'" class="auth-brand-panel">
      <div class="auth-brand-inner">
        <h2 class="auth-brand-title">Todo lo que necesitas, en un solo lugar</h2>
        <p class="auth-brand-subtitle">
          Compra equipos, alquila herramientas y contrata servicios técnicos con la misma cuenta.
        </p>
        <ul class="auth-brand-list">
          <li><i class="bi bi-shop"></i> Tienda con despacho a todo el país</li>
          <li><i class="bi bi-box-seam"></i> Alquiler de equipos por días o meses</li>
          <li><i class="bi bi-tools"></i> Servicios técnicos con profesionales verificados</li>
        </ul>
      </div>
    </aside>

    <ToastManager />
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import ToastManager from '@/components/layout/ToastManager.vue';
import { useAppConfigStore } from '@/store/appConfig';

// White-label F7 (2026-08-14): antes "Sintel" hardcodeado -- ver
// AUDITORIA/WHITE_LABEL/WHITE_LABEL_FRONTEND_AUDIT.md. fetchConfig() propio
// porque esta pantalla NO pasa por CustomerLayout.vue (el que normalmente
// dispara el fetch inicial) -- login/register usan su propio layout.
const appConfigStore = useAppConfigStore();
const brandName = computed(() => appConfigStore.brand.site_name || 'Tu tienda');
const brandInitial = computed(() => (brandName.value || '?').charAt(0).toUpperCase());
onMounted(() => appConfigStore.fetchConfig());

defineProps({
  variant: {
    type: String,
    default: 'split',
    validator: (v) => ['split', 'wide'].includes(v),
  },
});
</script>

<style scoped>
.auth-shell {
  min-height: 100vh;
  display: flex;
  font-family: 'Inter', sans-serif;
  background: linear-gradient(160deg, #eff6ff 0%, #f8faff 60%, #f0fdf4 100%);
}

.auth-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 2.5rem 1.5rem;
  min-width: 0;
}

.auth-logo {
  display: flex;
  align-items: center;
  gap: .6rem;
  text-decoration: none;
  margin-bottom: 2rem;
  align-self: flex-start;
}
.auth-logo-box {
  width: 40px; height: 40px;
  background: linear-gradient(135deg, #2563eb 0%, #1e3a8a 100%);
  color: #fff;
  border-radius: .85rem;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 1.1rem;
  box-shadow: 0 6px 16px rgba(37, 99, 235, 0.28);
}
.auth-logo-text { font-weight: 700; color: #1e293b; font-size: 1.05rem; }

.auth-content {
  width: 100%;
  max-width: 420px;
  margin: auto 0;
}
.auth-content--wide {
  max-width: 1100px;
}

/* Entrada sutil de la tarjeta -- fade + leve elevacion, sin rebote (spec:
   animaciones nunca exageradas). Respeta prefers-reduced-motion. */
.auth-enter { animation: auth-fade-in .35s ease-out; }
@keyframes auth-fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
@media (prefers-reduced-motion: reduce) {
  .auth-enter { animation: none; }
}

.auth-brand-panel {
  flex: 0 0 38%;
  max-width: 560px;
  background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 100%);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 3rem;
}
.auth-brand-inner { max-width: 380px; }
.auth-brand-title { font-size: 1.75rem; font-weight: 800; margin-bottom: 1rem; line-height: 1.25; }
.auth-brand-subtitle { color: rgba(255,255,255,.85); margin-bottom: 2rem; }
.auth-brand-list { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 1rem; }
.auth-brand-list li { display: flex; align-items: center; gap: .75rem; font-weight: 500; }
.auth-brand-list i { font-size: 1.25rem; color: #93c5fd; }

@media (max-width: 991.98px) {
  .auth-brand-panel { display: none; }
}
</style>
