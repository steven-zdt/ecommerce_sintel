<template>
  <section ref="el" class="fcta-root" :class="{ 'fcta-visible': visible }">
    <!-- Orbs decorativos -->
    <div class="fcta-orb fcta-orb-1"></div>
    <div class="fcta-orb fcta-orb-2"></div>

    <div class="container-xl fcta-inner">
      <div class="fcta-content">
        <span class="fcta-eyebrow">{{ cfg.eyebrow }}</span>
        <h2 class="fcta-title">
          {{ cfg.title_prefix }}<br>
          <em>{{ cfg.title_highlighted }}</em>
        </h2>
        <p class="fcta-sub">{{ cfg.subtitle }}</p>

        <div class="fcta-btns">
          <component
            :is="primaryIsExternal ? 'a' : RouterLink"
            :to="primaryIsExternal ? undefined : cfg.btn_primary_url"
            :href="primaryIsExternal ? cfg.btn_primary_url : undefined"
            :target="primaryIsExternal ? '_blank' : undefined"
            :rel="primaryIsExternal ? 'noopener noreferrer' : undefined"
            class="fcta-btn-primary"
          >
            {{ cfg.btn_primary_label }}
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <path d="M3 8h10M9 4l4 4-4 4" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
          </component>
          <component
            :is="ghostIsExternal ? 'a' : RouterLink"
            :to="ghostIsExternal ? undefined : cfg.btn_ghost_url"
            :href="ghostIsExternal ? cfg.btn_ghost_url : undefined"
            :target="ghostIsExternal ? '_blank' : undefined"
            :rel="ghostIsExternal ? 'noopener noreferrer' : undefined"
            class="fcta-btn-ghost"
          >
            {{ cfg.btn_ghost_label }}
          </component>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup>
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import { useScrollReveal } from '@/composables/useScrollReveal';

const props = defineProps({
  config: { type: Object, default: () => ({}) },
});

const DEFAULTS = {
  eyebrow:           'Empieza hoy',
  title_prefix:      'Impulsa tu empresa con',
  title_highlighted: 'Sintel Technology',
  subtitle:          'Soluciones tecnologicas, equipos y servicios profesionales en un solo lugar.',
  btn_primary_label: 'Solicitar cotizacion',
  btn_primary_url:   '/cotizar',
  btn_ghost_label:   'Explorar catalogo',
  btn_ghost_url:     '/tienda',
};

const cfg = computed(() => ({ ...DEFAULTS, ...props.config }));

const primaryIsExternal = computed(() => /^https?:\/\//.test(cfg.value.btn_primary_url));
const ghostIsExternal   = computed(() => /^https?:\/\//.test(cfg.value.btn_ghost_url));

const { el, visible } = useScrollReveal({ threshold: 0.15 });
</script>

<style scoped>
.fcta-root {
  position: relative;
  background: linear-gradient(135deg, var(--landing-ink-950) 0%, #1e3a8a 50%, var(--landing-primary-strong) 100%);
  padding: var(--landing-space-8) 0;
  overflow: hidden;
}

/* ── Orbs decorativos ───────────────────────────────────────────────────────── */
.fcta-orb {
  position: absolute;
  border-radius: 50%;
  pointer-events: none;
  filter: blur(80px);
}
.fcta-orb-1 {
  width: 500px;
  height: 500px;
  background: radial-gradient(circle, rgba(6,182,212,.3), transparent 70%);
  top: -200px;
  right: -100px;
}
.fcta-orb-2 {
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(124,58,237,.25), transparent 70%);
  bottom: -150px;
  left: 5%;
}

/* ── Content ────────────────────────────────────────────────────────────────── */
.fcta-inner { position: relative; z-index: 2; }
.fcta-content {
  max-width: 680px;
  margin: 0 auto;
  text-align: center;
  opacity: 0;
  transform: translateY(28px);
  transition:
    opacity 0.7s cubic-bezier(0.16,1,0.3,1),
    transform 0.7s cubic-bezier(0.16,1,0.3,1);
}
.fcta-visible .fcta-content {
  opacity: 1;
  transform: translateY(0);
}

.fcta-eyebrow {
  display: inline-block;
  font-size: 0.68rem;
  font-weight: 700;
  letter-spacing: 2px;
  text-transform: uppercase;
  color: rgba(255,255,255,.7);
  background: rgba(255,255,255,.1);
  border: 1px solid rgba(255,255,255,.2);
  border-radius: 9999px;
  padding: 0.25rem 0.85rem;
  margin-bottom: 1.25rem;
}

.fcta-title {
  font-size: clamp(2rem, 4.5vw, 3.5rem);
  font-weight: 800;
  line-height: 1.1;
  color: #fff;
  margin: 0 0 1.25rem;
  text-shadow: 0 2px 12px rgba(0,0,0,.3);
}
.fcta-title em {
  font-style: normal;
  background: linear-gradient(135deg, #60a5fa, #a78bfa);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.fcta-sub {
  font-size: 1rem;
  color: rgba(255,255,255,.68);
  line-height: 1.65;
  margin: 0 0 2.25rem;
}

.fcta-btns {
  display: flex;
  gap: 0.85rem;
  justify-content: center;
  flex-wrap: wrap;
}

.fcta-btn-primary,
.fcta-btn-ghost {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.95rem;
  font-weight: 600;
  border-radius: var(--landing-radius-pill);
  padding: 0.78rem 1.85rem;
  text-decoration: none;
  transition: transform 0.28s var(--landing-ease),
              box-shadow 0.28s ease;
  cursor: pointer;
}
.fcta-btn-primary {
  background: #fff;
  color: #1d4ed8;
  box-shadow: 0 4px 16px rgba(255,255,255,.2);
}
.fcta-btn-primary:hover {
  color: #1e40af;
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 10px 28px rgba(255,255,255,.28);
}
.fcta-btn-ghost {
  background: rgba(255,255,255,.1);
  border: 1px solid rgba(255,255,255,.25);
  color: rgba(255,255,255,.9);
  backdrop-filter: blur(8px);
}
.fcta-btn-ghost:hover {
  background: rgba(255,255,255,.2);
  color: #fff;
  transform: translateY(-2px);
}
</style>
