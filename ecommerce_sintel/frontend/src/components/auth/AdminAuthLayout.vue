<template>
  <div class="admin-auth-shell">
    <div class="admin-auth-card auth-enter">
      <div class="admin-auth-logo">
        <span class="admin-logo-box">S</span>
        <span class="admin-logo-text">Sintel <em>Admin</em></span>
      </div>
      <slot />
    </div>
  </div>
</template>

<script setup>
// Deliberadamente NO comparte nada con CustomerAuthLayout.vue (ni props ni CSS) --
// regla de separacion absoluta entre auth de cliente y de admin. Tema oscuro tomado
// del sidebar del panel (ai_skills/frontend/design_system/colors.md: #0a0a0a +
// gradiente #fff->#38bdf8), sin panel de marca/ventas (spec: acceso administrativo,
// no una pantalla comercial).
</script>

<style scoped>
.admin-auth-shell {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: #0a0a0a;
  background-image: radial-gradient(circle at 20% 20%, rgba(56, 189, 248, .08), transparent 45%);
  font-family: 'Inter', sans-serif;
}

.admin-auth-card {
  width: 100%;
  max-width: 400px;
  background: #16171a;
  border: 1px solid rgba(255, 255, 255, .08);
  border-radius: 1.25rem;
  box-shadow: 0 20px 60px rgba(0, 0, 0, .5);
  padding: 2.5rem;
}

.admin-auth-logo {
  display: flex;
  align-items: center;
  gap: .6rem;
  margin-bottom: 1.75rem;
  justify-content: center;
}
.admin-logo-box {
  width: 40px; height: 40px;
  border-radius: .85rem;
  display: flex; align-items: center; justify-content: center;
  font-weight: 800; font-size: 1.1rem;
  background: linear-gradient(135deg, #fff 0%, #38bdf8 100%);
  color: #0a0a0a;
}
.admin-logo-text { font-weight: 700; color: #fff; font-size: 1.05rem; }
.admin-logo-text em { color: #38bdf8; font-style: normal; }

/* Entrada sutil de la tarjeta -- fade + leve elevacion, sin rebote (spec:
   animaciones nunca exageradas). Respeta prefers-reduced-motion. */
.auth-enter { animation: admin-auth-fade-in .35s ease-out; }
@keyframes admin-auth-fade-in {
  from { opacity: 0; transform: translateY(8px); }
  to   { opacity: 1; transform: translateY(0); }
}
@media (prefers-reduced-motion: reduce) {
  .auth-enter { animation: none; }
}
</style>
