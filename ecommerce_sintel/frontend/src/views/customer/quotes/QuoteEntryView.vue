<template>
  <div class="qw-root">
    <div class="qw-bg-glow qw-glow-1"></div>
    <div class="qw-bg-glow qw-glow-2"></div>

    <div class="container py-5" style="max-width:920px; position:relative">
      <div class="qw-header">
        <div class="qw-header-icon">
          <i class="bi bi-file-earmark-text"></i>
        </div>
        <nav class="qw-breadcrumb">
          <RouterLink to="/" class="qw-bc-link">Inicio</RouterLink>
          <span class="qw-bc-sep">/</span>
          <span class="qw-bc-current">Cotizar</span>
        </nav>
        <h1 class="qw-title">¿Qué quieres cotizar?</h1>
        <p class="qw-sub">Elige el tipo de cotización que necesitas.</p>
      </div>

      <div class="entry-grid">
        <RouterLink to="/cotizar/catalogo" class="entry-card">
          <div class="entry-icon entry-icon-catalog"><i class="bi bi-bag-check"></i></div>
          <h2 class="entry-title">Cotización de Catálogo</h2>
          <p class="entry-desc">
            Elige productos, equipos en renta y/o servicios técnicos ya publicados.
            Ves el precio al instante y descargas el PDF de una vez.
          </p>
          <span class="entry-cta">Cotizar del catálogo <i class="bi bi-arrow-right ms-1"></i></span>
          <span class="entry-badge">Sin registro</span>
        </RouterLink>

        <RouterLink to="/cotizar/personalizada" class="entry-card">
          <div class="entry-icon entry-icon-custom"><i class="bi bi-clipboard-check"></i></div>
          <h2 class="entry-title">Cotización Personalizada</h2>
          <p class="entry-desc">
            Responde un cuestionario técnico sobre tu proyecto (equipos, materiales,
            mano de obra). Un asesor revisa tu solicitud y te envía la cotización con precios.
          </p>
          <span class="entry-cta">Solicitar cotización <i class="bi bi-arrow-right ms-1"></i></span>
          <span class="entry-badge">Requiere iniciar sesión</span>
        </RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const route = useRoute();
const router = useRouter();

onMounted(() => {
  // Deep-links desde ProductDetailView.vue (?product=uuid) y RentalDetailView.vue
  // (?equipment=uuid) ya apuntaban aqui — la intencion ya es clara, saltamos
  // directo a Cotizacion de Catalogo con ese item preseleccionado.
  if (route.query.product || route.query.equipment) {
    router.replace({ path: '/cotizar/catalogo', query: route.query });
  }
});
</script>

<style scoped>
.qw-root { position: relative; min-height: 100vh; overflow: hidden; background: #fafafa; }
.qw-bg-glow { position: absolute; border-radius: 50%; filter: blur(80px); opacity: 0.25; pointer-events: none; }
.qw-glow-1 { width: 420px; height: 420px; background: #a78bfa; top: -120px; right: -100px; }
.qw-glow-2 { width: 380px; height: 380px; background: #7c3aed; bottom: -140px; left: -100px; }

.qw-header { text-align: center; margin-bottom: 2.5rem; }
.qw-header-icon {
  width: 56px; height: 56px; border-radius: 16px; background: #6d28d9; color: #fff;
  display: flex; align-items: center; justify-content: center; margin: 0 auto 1rem; font-size: 1.5rem;
}
.qw-breadcrumb { font-size: 0.82rem; color: #94a3b8; margin-bottom: 0.6rem; }
.qw-bc-link { color: #94a3b8; text-decoration: none; }
.qw-bc-sep { margin: 0 0.4rem; }
.qw-bc-current { color: #6d28d9; font-weight: 600; }
.qw-title { font-size: clamp(2rem, 5vw, 2.8rem); font-weight: 850; letter-spacing: -0.03em; margin-bottom: 0.4rem; }
.qw-sub { color: #64748b; }

.entry-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 1.5rem; }
.entry-card {
  position: relative; display: block; background: #fff; border-radius: 24px; padding: 2rem;
  box-shadow: 0 10px 40px rgba(15, 23, 42, 0.06); text-decoration: none; color: inherit;
  transition: transform 0.15s ease, box-shadow 0.15s ease; border: 1px solid #f1f5f9;
}
.entry-card:hover { transform: translateY(-4px); box-shadow: 0 16px 50px rgba(15, 23, 42, 0.1); color: inherit; }
.entry-icon {
  width: 54px; height: 54px; border-radius: 16px; display: flex; align-items: center;
  justify-content: center; font-size: 1.5rem; margin-bottom: 1.2rem; color: #fff;
}
.entry-icon-catalog { background: linear-gradient(135deg, #16a34a, #22c55e); }
.entry-icon-custom { background: linear-gradient(135deg, #6d28d9, #a78bfa); }
.entry-title { font-size: 1.3rem; font-weight: 800; margin-bottom: 0.6rem; }
.entry-desc { color: #64748b; font-size: 0.9rem; line-height: 1.5; margin-bottom: 1.4rem; min-height: 4.5em; }
.entry-cta { font-weight: 700; color: #6d28d9; font-size: 0.9rem; }
.entry-badge {
  position: absolute; top: 1.4rem; right: 1.4rem; font-size: 0.68rem; font-weight: 700;
  text-transform: uppercase; background: #f3e8ff; color: #6b21a8; border-radius: 999px; padding: 0.25rem 0.6rem;
}
</style>
