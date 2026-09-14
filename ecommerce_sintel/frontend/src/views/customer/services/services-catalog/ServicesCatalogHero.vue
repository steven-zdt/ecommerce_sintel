<template>
  <section class="catalog-hero">
    <div class="ch-glow ch-glow-1"></div>
    <div class="ch-glow ch-glow-2"></div>
    <div class="container-xl">
      <div class="ch-inner">
        <!-- Left: breadcrumb + title -->
        <div class="ch-left">
          <nav class="ch-breadcrumb" aria-label="breadcrumb">
            <RouterLink to="/" class="ch-bc-link">Inicio</RouterLink>
            <span class="ch-bc-sep">/</span>
            <span class="ch-bc-current">Servicios</span>
          </nav>
          <div class="d-flex align-items-center gap-3 mt-1">
            <h1 class="ch-title">Servicios Tecnicos</h1>
            <span v-if="totalCount && !loading" class="ch-count-badge">
              {{ totalCount.toLocaleString('es-CO') }} servicios
            </span>
          </div>
          <p class="ch-sub">Compra soluciones profesionales con alcance, garantia y equipos certificados.</p>
          <div class="ch-actions">
            <a href="#services-marketplace" class="ch-cta-primary">
              <i class="bi bi-bag-check"></i>
              Comprar servicio
            </a>
            <RouterLink to="/registro-profesional" class="ch-cta-provider">
              <i class="bi bi-person-workspace"></i>
              Ofrecer servicios
            </RouterLink>
          </div>
          <div class="ch-trust-row">
            <span><i class="bi bi-shield-check"></i> Garantia incluida</span>
            <span><i class="bi bi-credit-card"></i> Pago seguro</span>
            <span><i class="bi bi-calendar-check"></i> Agenda flexible</span>
          </div>
        </div>

        <!-- Right: search desktop -->
        <div class="ch-search-wrap d-none d-lg-flex">
          <i class="bi bi-search ch-search-icon"></i>
          <input
            :value="search"
            type="text"
            class="ch-search-input"
            placeholder="Buscar servicio tecnico..."
            @input="$emit('update:search', $event.target.value)"
          >
          <button v-if="search" class="ch-search-clear" @click="$emit('clear-search')">
            <i class="bi bi-x"></i>
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  totalCount: { type: Number, default: 0 },
  loading: { type: Boolean, default: false },
  search: { type: String, default: '' },
});
defineEmits(['update:search', 'clear-search']);
</script>

<style scoped>
.catalog-hero {
  position: relative;
  background: linear-gradient(135deg, #1c0a00 0%, #78350f 55%, #d97706 100%);
  overflow: hidden;
  padding: 2.5rem 0 2rem;
}
.ch-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  pointer-events: none;
  opacity: 0.35;
}
.ch-glow-1 {
  width: 420px; height: 420px;
  background: #f59e0b;
  top: -120px; right: -80px;
}
.ch-glow-2 {
  width: 300px; height: 300px;
  background: #fbbf24;
  bottom: -100px; left: 5%;
}
.ch-inner {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 2rem;
  flex-wrap: wrap;
}
.ch-left { flex: 1; min-width: 0; }
.ch-breadcrumb {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.78rem;
  margin-bottom: 0.35rem;
}
.ch-bc-link {
  color: rgba(255,255,255,.65);
  text-decoration: none;
  transition: color 0.18s;
}
.ch-bc-link:hover { color: #fff; }
.ch-bc-sep { color: rgba(255,255,255,.3); font-size: 0.7rem; }
.ch-bc-current { color: rgba(255,255,255,.8); }

.ch-title {
  font-size: clamp(1.5rem, 3.5vw, 2.3rem);
  font-weight: 900;
  color: #fff;
  letter-spacing: -0.03em;
  margin: 0;
  line-height: 1;
}
.ch-count-badge {
  font-size: 0.72rem;
  font-weight: 700;
  background: rgba(255,255,255,.12);
  backdrop-filter: blur(8px);
  color: rgba(255,255,255,.9);
  border: 1px solid rgba(255,255,255,.2);
  border-radius: 9999px;
  padding: 0.25rem 0.75rem;
  white-space: nowrap;
}
.ch-sub {
  font-size: 0.85rem;
  color: rgba(255,255,255,.55);
  margin: 0.5rem 0 0;
}
.ch-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-top: 1rem;
}
.ch-cta-primary,
.ch-cta-provider {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.55rem 1.1rem;
  border-radius: 9999px;
  font-size: 0.82rem;
  font-weight: 700;
  text-decoration: none;
  transition: background .15s ease, transform .15s ease;
}
.ch-cta-primary {
  background: #fff;
  color: #0f172a;
  border: 1.5px solid rgba(255,255,255,.7);
  box-shadow: 0 14px 30px rgba(15,23,42,.18);
}
.ch-cta-provider {
  background: rgba(255,255,255,.12);
  backdrop-filter: blur(8px);
  border: 1.5px solid rgba(255,255,255,.25);
  color: #fff;
}
.ch-cta-primary:hover {
  background: #f8fafc;
  color: #0f172a;
  transform: translateY(-1px);
}
.ch-cta-provider:hover {
  background: rgba(255,255,255,.2);
  color: #fff;
  transform: translateY(-1px);
}
.ch-trust-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-top: 1rem;
  color: rgba(255,255,255,.78);
  font-size: 0.76rem;
}
.ch-trust-row span {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  background: rgba(15,23,42,.2);
  border: 1px solid rgba(255,255,255,.16);
  border-radius: 999px;
  padding: 0.28rem 0.65rem;
}

/* Search in hero */
.ch-search-wrap {
  align-items: center;
  background: rgba(255,255,255,.1);
  backdrop-filter: blur(12px);
  border: 1.5px solid rgba(255,255,255,.2);
  border-radius: 14px;
  padding: 0.55rem 1rem;
  gap: 0.6rem;
  min-width: 280px;
  flex-shrink: 0;
}
.ch-search-icon { color: rgba(255,255,255,.55); font-size: 0.9rem; flex-shrink: 0; }
.ch-search-input {
  background: none;
  border: none;
  outline: none;
  color: #fff;
  font-size: 0.88rem;
  flex: 1;
  min-width: 0;
}
.ch-search-input::placeholder { color: rgba(255,255,255,.4); }
.ch-search-clear {
  background: none;
  border: none;
  color: rgba(255,255,255,.6);
  cursor: pointer;
  padding: 0;
  font-size: 1rem;
  line-height: 1;
  flex-shrink: 0;
}
.ch-search-clear:hover { color: #fff; }

@media (max-width: 575px) {
  .catalog-hero { padding-bottom: 1.6rem; }
  .ch-actions { width: 100%; }
  .ch-cta-primary,
  .ch-cta-provider { justify-content: center; flex: 1 1 150px; }
}
</style>
