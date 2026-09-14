<template>
  <section class="catalog-hero">
    <div class="ch-glow ch-glow-1"></div>
    <div class="ch-glow ch-glow-2"></div>
    <div class="container-xl">
      <div class="ch-inner">
        <div class="ch-left">
          <nav class="ch-breadcrumb" aria-label="breadcrumb">
            <RouterLink to="/" class="ch-bc-link">Inicio</RouterLink>
            <span class="ch-bc-sep">/</span>
            <span class="ch-bc-current">Alquiler</span>
          </nav>
          <div class="d-flex align-items-center gap-3 mt-1">
            <h1 class="ch-title">Alquiler de Equipos</h1>
            <span v-if="totalCount && !loading" class="ch-count-badge">
              {{ totalCount.toLocaleString('es-CO') }} equipos
            </span>
          </div>
          <p class="ch-sub">Soluciones temporales completas: equipo, logistica, instalacion, soporte y disponibilidad inteligente.</p>
          <div class="ch-actions">
            <a href="#renting-marketplace" class="ch-cta-primary"><i class="bi bi-calendar-check"></i>Reservar solucion</a>
            <RouterLink to="/cotizar" class="ch-cta-secondary"><i class="bi bi-file-earmark-text"></i>Cotizar proyecto</RouterLink>
          </div>
          <div class="ch-trust-row">
            <span><i class="bi bi-box-seam"></i> Equipos certificados</span>
            <span><i class="bi bi-truck"></i> Transporte opcional</span>
            <span><i class="bi bi-shield-check"></i> Soporte postventa</span>
          </div>
        </div>

        <div class="ch-right d-none d-lg-flex">
          <label class="ch-featured-toggle">
            <input :checked="featured" type="checkbox" @change="$emit('update:featured', $event.target.checked)">
            <span class="ch-toggle-track"></span>
            <span class="ch-toggle-label">Solo destacados</span>
          </label>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  totalCount: { type: Number, default: 0 },
  loading: { type: Boolean, default: false },
  featured: { type: Boolean, default: false },
});
defineEmits(['update:featured']);
</script>

<style scoped>
.catalog-hero { position: relative; background: linear-gradient(135deg, #1a0533 0%, #4c1d95 55%, #7c3aed 100%); overflow: hidden; padding: 2.5rem 0 2rem; }
.ch-glow { position: absolute; border-radius: 50%; filter: blur(80px); pointer-events: none; opacity: 0.35; }
.ch-glow-1 { width: 420px; height: 420px; background: #a78bfa; top: -120px; right: -80px; }
.ch-glow-2 { width: 300px; height: 300px; background: #c4b5fd; bottom: -100px; left: 5%; }
.ch-inner { position: relative; display: flex; align-items: center; justify-content: space-between; gap: 2rem; flex-wrap: wrap; }
.ch-left { flex: 1; min-width: 0; }
.ch-breadcrumb { display: flex; align-items: center; gap: 0.4rem; font-size: 0.78rem; margin-bottom: 0.35rem; }
.ch-bc-link { color: rgba(255,255,255,.65); text-decoration: none; transition: color 0.18s; }
.ch-bc-link:hover { color: #fff; }
.ch-bc-sep { color: rgba(255,255,255,.3); font-size: 0.7rem; }
.ch-bc-current { color: rgba(255,255,255,.8); }
.ch-title { font-size: clamp(1.5rem, 3.5vw, 2.3rem); font-weight: 900; color: #fff; letter-spacing: -0.03em; margin: 0; line-height: 1; }
.ch-count-badge { font-size: 0.72rem; font-weight: 700; background: rgba(255,255,255,.12); backdrop-filter: blur(8px); color: rgba(255,255,255,.9); border: 1px solid rgba(255,255,255,.2); border-radius: 9999px; padding: 0.25rem 0.75rem; white-space: nowrap; }
.ch-sub { font-size: 0.85rem; color: rgba(255,255,255,.55); margin: 0.5rem 0 0; }
.ch-actions { display: flex; flex-wrap: wrap; gap: .75rem; margin-top: 1rem; }
.ch-cta-primary, .ch-cta-secondary { display: inline-flex; align-items: center; gap: .5rem; border-radius: 999px; padding: .58rem 1.1rem; font-size: .82rem; font-weight: 760; text-decoration: none; transition: transform .16s ease, background .16s ease; }
.ch-cta-primary { background: #fff; color: #111827; box-shadow: 0 14px 30px rgba(15,23,42,.2); }
.ch-cta-secondary { background: rgba(255,255,255,.12); color: #fff; border: 1px solid rgba(255,255,255,.24); }
.ch-cta-primary:hover, .ch-cta-secondary:hover { transform: translateY(-1px); }
.ch-cta-primary:hover { color: #111827; background: #f8fafc; }
.ch-cta-secondary:hover { color: #fff; background: rgba(255,255,255,.18); }
.ch-trust-row { display: flex; flex-wrap: wrap; gap: .55rem; margin-top: 1rem; }
.ch-trust-row span { display: inline-flex; align-items: center; gap: .35rem; color: rgba(255,255,255,.8); background: rgba(15,23,42,.18); border: 1px solid rgba(255,255,255,.15); border-radius: 999px; padding: .28rem .65rem; font-size: .76rem; font-weight: 650; }
.ch-right { align-items: center; }
.ch-featured-toggle { display: flex; align-items: center; gap: 0.65rem; cursor: pointer; background: rgba(255,255,255,.1); backdrop-filter: blur(12px); border: 1.5px solid rgba(255,255,255,.2); border-radius: 12px; padding: 0.65rem 1rem; }
.ch-featured-toggle input { position: absolute; opacity: 0; width: 0; height: 0; }
.ch-toggle-track { display: block; width: 38px; height: 22px; border-radius: 999px; background: rgba(255,255,255,.2); position: relative; flex-shrink: 0; transition: background 0.22s; }
.ch-toggle-track::after { content: ''; position: absolute; top: 3px; left: 3px; width: 16px; height: 16px; border-radius: 50%; background: #fff; box-shadow: 0 1px 4px rgba(0,0,0,.2); transition: transform 0.22s cubic-bezier(0.34,1.56,0.64,1); }
.ch-featured-toggle input:checked + .ch-toggle-track { background: #a78bfa; }
.ch-featured-toggle input:checked + .ch-toggle-track::after { transform: translateX(16px); }
.ch-toggle-label { font-size: 0.82rem; font-weight: 600; color: rgba(255,255,255,.9); }
@media (max-width: 575px) { .ch-actions { width: 100%; } .ch-cta-primary, .ch-cta-secondary { justify-content: center; flex: 1 1 150px; } }
</style>
