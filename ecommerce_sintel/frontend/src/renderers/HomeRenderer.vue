<template>
  <div class="home-root">

    <!-- ── HERO ──────────────────────────────────────────────────────────────── -->
    <template v-if="showSection('hero')">
      <HeroSection :banners="banners" :loading="loading" />
      <DividerWave from="#080d1a" fill="#ffffff" />
    </template>

    <!-- ── MARKETPLACE SHOWCASE + STATS ──────────────────────────────────────── -->
    <!-- Reemplaza al antiguo ModuleGrid.vue (grid fijo) -- MarketplaceShowcase.vue
         es un carrusel horizontal premium (ver frontend/.AGENT/doc, seccion
         "Marketplace Showcase 2.0"). ModuleGrid.vue/ModuleCard.vue quedan en
         disco sin importar (mismo trato que HeroCarousel.vue/ModuleCardsGrid.vue). -->
    <template v-if="showSection('modules')">
      <MarketplaceShowcase :modules="modules" :loading="loading" />

      <div v-if="!loading && stats.length" class="home-stats-belt">
        <div class="container-xl">
          <div class="home-stats-row">
            <AnimatedCounter
              v-for="s in stats"
              :key="s.label"
              :value="s.value"
              :label="s.label"
              :suffix="s.suffix"
            />
          </div>
        </div>
      </div>
    </template>

    <!-- ── FEATURE BANNER (secciones promocionales genericas) ─────────────────── -->
    <template v-if="showSection('feature_banner')">
      <FeatureBannerRenderer :sections="featureBannerSections" :loading="loading" />
    </template>

    <!-- ── FLASH OFFERS ─────────────────────────────────────────────────────── -->
    <template v-if="showSection('flash') && (loading || flashOffers.length)">
      <DividerWave from="#ffffff" fill="#080d1a" />
      <FlashOffers :offers="flashOffers" :loading="loading" />
      <DividerWave from="#080d1a" fill="#f8fafc" />
    </template>

    <!-- ── FEATURED SECTIONS ─────────────────────────────────────────────────── -->
    <div v-if="showSection('featured')" class="home-featured-belt">
      <div class="container-xl home-featured-inner">
        <FeaturedSection
          v-for="section in featuredSections"
          :key="section.type"
          v-show="loading || section.items.length"
          v-bind="section"
          :loading="loading"
        />

        <div v-if="!loading && isEmpty" class="home-empty">
          <i class="bi bi-grid-3x3-gap home-empty-icon"></i>
          <h6 class="home-empty-title">Explora nuestro catalogo</h6>
          <p class="home-empty-sub">Encuentra productos, equipos y servicios tecnologicos.</p>
          <div class="d-flex gap-3 justify-content-center flex-wrap mt-3">
            <RouterLink to="/tienda" class="btn btn-primary btn-sm px-4">Ir a la tienda</RouterLink>
            <RouterLink to="/servicios" class="btn btn-outline-primary btn-sm px-4">Ver servicios</RouterLink>
          </div>
        </div>
      </div>
    </div>

    <!-- ── SECCIONES DINÁMICAS (HomeCardGroups + HomeCards) ──────────────────── -->
    <template v-if="showSection('cards')">
      <template v-if="loading">
        <div class="home-section-skeleton">
          <div class="container-xl">
            <LoadingSkeleton width="220px" height="32px" radius="6px" class="sk-header" />
            <div class="sk-grid">
              <LoadingSkeleton v-for="n in 3" :key="n" height="160px" radius="16px" />
            </div>
          </div>
        </div>
      </template>

      <template v-else>
        <!-- Grupos configurados con layout visual -->
        <template v-if="cardGroups.length">
          <SectionRenderer
            v-for="group in visibleGroups"
            :key="group.uuid || group.name"
            :group="group"
            :cards="homeCards"
          />
        </template>

        <!-- Fallback: grupos sin configuración explícita (solo group_name en cards) -->
        <template v-else-if="homeCards.length">
          <SectionRenderer
            v-for="(groupCards, groupName) in ungroupedCards"
            :key="groupName"
            :group="{ name: groupName, title: cardGroupTitles[groupName] || groupName, layout_type: 'grid', columns: 3, padding: 'normal' }"
            :cards="homeCards"
          />
        </template>

        <div v-else class="home-empty py-4">
          <p class="home-empty-sub mb-0">Sin tarjetas configuradas para este grupo.</p>
        </div>
      </template>
    </template>

    <!-- ── FOOTER CTA ────────────────────────────────────────────────────────── -->
    <FooterCTA v-if="showSection('cta')" :config="footerCta" />

    <!-- ── SLIDER DE MARCAS / CLIENTES ──────────────────────────────────────── -->
    <BrandSlider
      v-if="showSection('brand_slider') && brandSlider.config?.is_visible !== false"
      :config="brandSlider.config || {}"
      :items="brandSlider.items || []"
    />

  </div>
</template>

<script setup>
import { computed } from 'vue';
import { RouterLink } from 'vue-router';

import HeroSection     from '@/components/ui/landing/HeroSection.vue';
import DividerWave     from '@/components/ui/landing/DividerWave.vue';
import MarketplaceShowcase from '@/components/ui/showcase/MarketplaceShowcase.vue';
import FeatureBannerRenderer from '@/components/ui/showcase/FeatureBannerRenderer.vue';
import AnimatedCounter from '@/components/ui/landing/AnimatedCounter.vue';
import FlashOffers     from '@/components/ui/landing/FlashOffers.vue';
import FeaturedSection from '@/components/ui/landing/FeaturedSection.vue';
import FooterCTA       from '@/components/ui/landing/FooterCTA.vue';
import BrandSlider     from '@/components/ui/landing/BrandSlider.vue';
import LoadingSkeleton from '@/components/ui/landing/LoadingSkeleton.vue';
import SectionRenderer from './SectionRenderer.vue';

/**
 * HomeRenderer — motor de render UNICO del cuerpo de la pagina de inicio.
 *
 * Usado por:
 *  - views/customer/HomeView.vue (Landing publica, /) con datos de core/home-feed/
 *  - modules/core/HomeConfigView.vue (Vista Previa del panel admin) con el estado
 *    EN MEMORIA de los formularios de edicion (sin guardar aun)
 *
 * Ambos consumidores pasan el MISMO shape de props (igual a la respuesta de
 * core/home-feed/) -- no hay markup ni CSS exclusivo de ninguno de los dos.
 * Ver ai_skills/frontend/editor/home_render_audit_2026_07_11.md (Fase 3).
 */
const props = defineProps({
  banners:           { type: Array,   default: () => [] },
  modules:           { type: Array,   default: () => [] },
  featureBannerSections: { type: Array, default: () => [] },
  flashOffers:       { type: Array,   default: () => [] },
  featuredProducts:  { type: Array,   default: () => [] },
  featuredEquipment: { type: Array,   default: () => [] },
  featuredServices:  { type: Array,   default: () => [] },
  homeCards:         { type: Array,   default: () => [] },
  cardGroupTitles:   { type: Object,  default: () => ({}) },
  cardGroups:        { type: Array,   default: () => [] },
  footerCta:         { type: Object,  default: () => ({}) },
  brandSlider:       { type: Object,  default: () => ({ config: {}, items: [] }) },
  loading:           { type: Boolean, default: false },
  // Filtro opcional de secciones a renderizar -- null/undefined = todas.
  // Usado por la Vista Previa del panel admin para mostrar solo la seccion
  // que se esta editando en ese momento, dentro del frame angosto del sidebar.
  sections: { type: Array, default: null },
});

function showSection(key) {
  return !props.sections || props.sections.includes(key);
}

const isEmpty = computed(() =>
  !props.featuredProducts.length &&
  !props.featuredEquipment.length &&
  !props.featuredServices.length
);

const visibleGroups = computed(() =>
  props.cardGroups.filter(g => g.is_visible !== false)
    .sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
);

const ungroupedCards = computed(() => {
  const groups = {};
  for (const c of props.homeCards) {
    if (!c.is_active) continue;
    if (!groups[c.group_name]) groups[c.group_name] = [];
    groups[c.group_name].push(c);
  }
  return groups;
});

// Una sola definicion de la familia de secciones destacadas. El contenido de
// sus items sigue viniendo integramente de Core; esta configuracion solo
// expresa la navegacion propia de cada catalogo publico y evita tres bloques
// de markup identico.
const featuredSections = computed(() => [
  {
    eyebrow: 'Tienda', title: '*Productos* destacados', link: '/tienda',
    linkLabel: 'Ver tienda completa', items: props.featuredProducts, type: 'product',
  },
  {
    eyebrow: 'Alquiler', title: 'Equipos *disponibles*', link: '/alquiler',
    linkLabel: 'Ver catalogo de equipos', items: props.featuredEquipment, type: 'rental',
  },
  {
    eyebrow: 'Servicios', title: 'Servicios *tecnicos*', link: '/servicios',
    linkLabel: 'Ver todos los servicios', items: props.featuredServices, type: 'service',
  },
]);

const stats = computed(() => {
  const total = props.featuredProducts.length + props.featuredEquipment.length + props.featuredServices.length;
  if (!total) return [];
  return [
    { value: total,                                                          label: 'Items disponibles', suffix: '+' },
    { value: props.modules.length,                                          label: 'Modulos activos',   suffix: ''  },
    { value: props.flashOffers.length,                                     label: 'Ofertas activas',   suffix: ''  },
    { value: props.homeCards.filter(c => c.is_active).length,               label: 'Servicios',         suffix: ''  },
  ].filter(s => s.value > 0);
});
</script>

<style scoped>
.home-root {
  background: var(--landing-surface);
  min-height: 100vh;
}
.home-stats-belt { background: var(--landing-surface); padding-bottom: clamp(1.5rem, 3vw, 2.5rem); }
.home-stats-row {
  display: flex; justify-content: center; flex-wrap: wrap; gap: 0;
  border: 1px solid var(--landing-border); border-radius: var(--landing-radius-lg);
  background: var(--landing-surface-subtle); overflow: hidden;
}
.home-stats-row > * { flex: 1 1 160px; border-right: 1px solid var(--landing-border); }
.home-stats-row > *:last-child { border-right: none; }
.home-featured-belt { background: var(--landing-surface-subtle); padding: clamp(3rem, 6vw, 5rem) 0; }
.home-featured-inner { display: flex; flex-direction: column; gap: 3rem; }
.home-empty { text-align: center; padding: 4rem 1rem; color: #64748b; }
.home-empty-icon { font-size: 3.5rem; display: block; margin-bottom: 1rem; opacity: .45; }
.home-empty-title { font-weight: 700; color: #334155; margin-bottom: .4rem; }
.home-empty-sub { font-size: .9rem; color: #94a3b8; margin: 0; }

/* Skeletons */
.home-section-skeleton { padding: 3rem 0; }
.sk-header { margin: 0 auto 1.5rem; }
.sk-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
@media(max-width:576px) { .sk-grid { grid-template-columns: repeat(2,1fr); } }
</style>
