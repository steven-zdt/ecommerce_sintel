<template>
  <div class="hcb-shell">

    <!-- ══ SIDEBAR ══════════════════════════════════════════════════════════ -->
    <aside class="hcb-sidebar">
      <div class="hcb-logo">
        <i class="bi bi-layout-wtf"></i>
        <span>Home Builder</span>
      </div>

      <nav class="hcb-nav">
        <button
          v-for="s in sections"
          :key="s.id"
          :class="['hcb-nav-btn', currentSection === s.id ? 'hcb-nav-btn--active' : '']"
          @click="currentSection = s.id"
        >
          <i :class="['bi', s.icon]"></i>
          <span>{{ s.label }}</span>
          <span v-if="s.count" class="hcb-badge">{{ s.count }}</span>
        </button>
      </nav>

      <div class="hcb-sidebar-footer">
        <a href="/" target="_blank" class="hcb-preview-btn">
          <i class="bi bi-eye"></i> Ver sitio
        </a>
      </div>
    </aside>

    <!-- ══ EDITOR ════════════════════════════════════════════════════════════ -->
    <main class="hcb-editor" :key="currentSection">

      <!-- ── MÓDULOS ─────────────────────────────────────────────────────── -->
      <ModulesSection v-if="currentSection === 'modules'" />

      <!-- ── BANNERS ─────────────────────────────────────────────────────── -->
      <BannersSection v-if="currentSection === 'banners'" />

      <!-- ── TARJETAS ────────────────────────────────────────────────────── -->
      <CardsSection v-if="currentSection === 'cards'" />

      <!-- ── FEATURE BANNER ──────────────────────────────────────────────── -->
      <FeatureBannerSection v-if="currentSection === 'feature_banner'" />

      <!-- ── FOOTER ──────────────────────────────────────────────────────── -->
      <FooterSection v-if="currentSection === 'footer'" v-model:contact-form="contactForm" />

      <!-- ── MARCA ───────────────────────────────────────────────────────── -->
      <BrandSection
        v-if="currentSection === 'brand'"
        v-model:brand-form="brandForm"
        v-model:brand-preview-logo="brandPreviewLogo"
      />

      <!-- ── NAVBAR ──────────────────────────────────────────────────────── -->
      <NavbarSection v-if="currentSection === 'navbar'" :site-name="brandForm.site_name" />

      <!-- ── CTA FINAL ───────────────────────────────────────────────────── -->
      <CtaSection v-if="currentSection === 'cta'" v-model:cta-form="ctaForm" />

      <!-- ── SLIDER DE MARCAS ────────────────────────────────────────────── -->
      <BrandSliderSection v-if="currentSection === 'brand_slider'" v-model:brand-config-form="brandConfigForm" />

    </main>

    <!-- ══ PREVIEW ═══════════════════════════════════════════════════════════ -->
    <aside class="hcb-preview-panel">
      <div class="hcb-preview-header">
        <span class="hcb-preview-label">Vista previa</span>
        <div class="hcb-preview-viewport-btns">
          <button :class="['hcb-vp-btn', previewDevice === 'desktop' ? 'active' : '']" @click="previewDevice = 'desktop'" title="Desktop">
            <i class="bi bi-display"></i>
          </button>
          <button :class="['hcb-vp-btn', previewDevice === 'tablet' ? 'active' : '']" @click="previewDevice = 'tablet'" title="Tablet">
            <i class="bi bi-tablet"></i>
          </button>
          <button :class="['hcb-vp-btn', previewDevice === 'mobile' ? 'active' : '']" @click="previewDevice = 'mobile'" title="Mobile">
            <i class="bi bi-phone"></i>
          </button>
        </div>
      </div>

      <div class="hcb-preview-frame-wrap">
        <div :class="['hcb-preview-frame', `hcb-preview-frame--${previewDevice}`, 'hcb-preview-frame--real']">

          <!-- Vista previa REAL: mismo <HomeRenderer/> que la Landing publica,
               alimentado con el estado EN MEMORIA del formulario (sin guardar).
               Ver ai_skills/frontend/editor/home_render_audit_2026_07_11.md (Fase 3). -->
          <HomeRenderer
            v-if="sectionRendererKey"
            :sections="[sectionRendererKey]"
            :banners="banners"
            :modules="modulesOrdered"
            :home-cards="cards"
            :card-groups="previewCardGroups"
            :card-group-titles="groupTitlesMap"
            :feature-banner-sections="featureBannerSections"
            :footer-cta="ctaForm"
            :brand-slider="{ config: brandConfigForm, items: brandItems }"
            :loading="false"
          />

          <CustomerNavbar
            v-else-if="currentSection === 'brand' || currentSection === 'navbar'"
            standalone
            :brand-override="previewBrand"
            :nav-links-override="navbarLinks"
          />

          <CustomerFooter
            v-else-if="currentSection === 'footer'"
            :contact-override="contactForm"
            :nav-groups-override="previewNavGroups"
            :social-links-override="previewSocialLinks"
          />

        </div>
      </div>
    </aside>

  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useCoreAdminStore } from '@/store/coreAdmin';
import ModulesSection from './home-builder/ModulesSection.vue';
import BannersSection from './home-builder/BannersSection.vue';
import NavbarSection from './home-builder/NavbarSection.vue';
import CardsSection from './home-builder/CardsSection.vue';
import FeatureBannerSection from './home-builder/FeatureBannerSection.vue';
import FooterSection from './home-builder/FooterSection.vue';
import BrandSection from './home-builder/BrandSection.vue';
import CtaSection from './home-builder/CtaSection.vue';
import BrandSliderSection from './home-builder/BrandSliderSection.vue';
import HomeRenderer from '@/renderers/HomeRenderer.vue';
import CustomerNavbar from '@/components/customer/CustomerNavbar.vue';
import CustomerFooter from '@/components/customer/CustomerFooter.vue';
import { buildGroupMaps } from './home-builder/cardGroupsUtil.js';

const toast = useToast();
const store = useCoreAdminStore();
const {
  modules,
  banners,
  cards,
  cardGroups,
  featureBannerSections,
  footerLinks, footerContact,
  footerGroups,
  brand,
  navbarLinks,
  footerCta,
  brandItems,
  brandSliderConfig,
} = storeToRefs(store);

// ── Navegacion lateral ────────────────────────────────────────────────────────
const currentSection = ref('modules');

const sections = computed(() => [
  { id: 'modules', label: 'Modulos',  icon: 'bi-grid',          count: modules.value.length || null },
  { id: 'banners', label: 'Banners',  icon: 'bi-images',         count: banners.value.length || null },
  { id: 'cards',   label: 'Tarjetas', icon: 'bi-grid-1x2',       count: cards.value.length || null },
  { id: 'feature_banner', label: 'Feature Banner', icon: 'bi-window-stack', count: featureBannerSections.value.length || null },
  { id: 'footer',  label: 'Footer',   icon: 'bi-layout-text-window', count: footerGroups.value.length || null },
  { id: 'brand',   label: 'Marca',    icon: 'bi-building',       count: null },
  { id: 'navbar',  label: 'Navbar',   icon: 'bi-list',           count: navbarLinks.value.length || null },
  { id: 'cta',     label: 'CTA Final', icon: 'bi-megaphone',     count: null },
  { id: 'brand_slider', label: 'Slider de Marcas', icon: 'bi-collection', count: brandItems.value.length || null },
]);

// ── Preview device ─────────────────────────────────────────────────────────────
const previewDevice = ref('desktop');

// ── Vista previa REAL (Fase 3, 2026-07-11) ──────────────────────────────────────
// Mapea la seccion activa del builder a la seccion equivalente de HomeRenderer.
// 'footer'/'brand'/'navbar' no son parte del cuerpo de Home (viven en
// CustomerLayout) y se resuelven aparte, mas abajo en el template, con los
// componentes reales CustomerNavbar/CustomerFooter.
const SECTION_TO_RENDERER = { banners: 'hero', modules: 'modules', cards: 'cards', feature_banner: 'feature_banner', cta: 'cta', brand_slider: 'brand_slider' };
const sectionRendererKey = computed(() => SECTION_TO_RENDERER[currentSection.value] || null);

// groupTitlesMap/groupConfigMap propios del padre (copia independiente de los
// que maneja CardsSection.vue, ambos derivados de la MISMA store.cardGroups --
// ver home-builder/cardGroupsUtil.js). Solo para alimentar el preview
// compartido; el padre no los muta, CardsSection.vue es quien los edita.
const groupMaps = computed(() => buildGroupMaps(cardGroups.value));
const groupTitlesMap = computed(() => groupMaps.value.titleMap);
const groupConfigMap = computed(() => groupMaps.value.configMap);

// Transforma groupTitlesMap/groupConfigMap al shape de "card_groups" que
// espera SectionRenderer/useLayoutEngine (igual al que entrega
// core/home-feed/ en produccion). Los nombres de grupo salen de la union de
// grupos ya configurados (cardGroups) y grupos que solo existen porque una
// tarjeta los referencia (cards.group_name) sin config propia todavia.
const previewGroupNames = computed(() => {
  const names = new Set(Object.keys(groupTitlesMap.value));
  for (const c of cards.value) names.add(c.group_name);
  return [...names];
});
const previewCardGroups = computed(() =>
  previewGroupNames.value.map((gName) => ({
    uuid: gName,
    name: gName,
    title: groupTitlesMap.value[gName] || gName,
    layout_type: groupConfigMap.value[gName]?.layout_type || 'grid',
    columns: groupConfigMap.value[gName]?.columns || 3,
    is_visible: true,
    display_order: groupConfigMap.value[gName]?.display_order || 0,
  }))
);

const previewBrand = computed(() => ({
  site_name: brandForm.value.site_name,
  tagline:   brandForm.value.tagline,
  logo:      brandPreviewLogo.value,
}));

// footerGroups (FooterGroup reales) + footerLinks (flat, category='nav'|'social')
// -> shape que espera CustomerFooter (igual al de core/footer/: groups[].links[]).
const previewNavGroups = computed(() =>
  [...footerGroups.value]
    .filter((g) => g.is_active !== false)
    .sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
    .map((g) => ({
      ...g,
      links: footerLinks.value
        .filter((l) => l.category === 'nav' && l.group === g.uuid)
        .sort((a, b) => (a.display_order || 0) - (b.display_order || 0)),
    }))
);
const previewSocialLinks = computed(() => footerLinks.value.filter((l) => l.category === 'social'));

// ══ MÓDULOS ═══════════════════════════════════════════════════════════════════
// CRUD delegado a ModulesSection.vue (P1-3, 2026-07-27) -- `modulesOrdered` se
// mantiene aqui porque el panel de preview compartido (mas abajo) lo necesita
// sin importar que pestaña este activa.
const modulesOrdered = computed(() =>
  [...modules.value].sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
);

// ══ TARJETAS ═══════════════════════════════════════════════════════════════════
// CRUD delegado a CardsSection.vue -- `groupTitlesMap`/`groupConfigMap`/
// `previewCardGroups` quedan arriba porque el preview compartido los necesita.

// ══ FOOTER ═════════════════════════════════════════════════════════════════════
// CRUD delegado a FooterSection.vue. `contactForm` es v-model compartido con
// ese componente (el preview de CustomerFooter lo necesita en el padre) --
// ver FooterSection.vue. Se inicializa reactivamente desde footerContact (watch
// immediate) en vez de una copia puntual en onMounted, para que funcione sin
// importar si FooterSection ya esta montado cuando el fetch resuelve.
const contactForm = ref({ phone: '', email: '', address: '', working_hours: '' });
watch(footerContact, (c) => {
  if (c) contactForm.value = { phone: c.phone || '', email: c.email || '', address: c.address || '', working_hours: c.working_hours || '' };
}, { immediate: true });

// ══ MARCA ══════════════════════════════════════════════════════════════════════
// CRUD delegado a BrandSection.vue. brandForm/brandPreviewLogo son v-model
// compartido (usados tambien por NavbarSection.vue y por el preview
// compartido en las pestañas 'brand' y 'navbar') -- ver BrandSection.vue.
const brandForm = ref({ site_name: 'Sintel', tagline: '' });
const brandPreviewLogo = ref('');
watch(brand, (data) => {
  if (data) {
    brandForm.value = { site_name: data.site_name || '', tagline: data.tagline || '' };
    brandPreviewLogo.value = data.logo || '';
  }
}, { immediate: true });

// ══ CTA FINAL ══════════════════════════════════════════════════════════════════
// CRUD delegado a CtaSection.vue. ctaForm es v-model compartido (el preview
// compartido en la pestaña 'cta' lo necesita) -- ver CtaSection.vue.
const defaultCtaForm = () => ({
  eyebrow: '', title_prefix: '', title_highlighted: '', subtitle: '',
  btn_primary_label: '', btn_primary_url: '', btn_ghost_label: '', btn_ghost_url: '',
});
const ctaForm = ref(defaultCtaForm());
watch(footerCta, (data) => {
  if (data?.uuid) {
    ctaForm.value = {
      eyebrow:           data.eyebrow           || '',
      title_prefix:      data.title_prefix      || '',
      title_highlighted: data.title_highlighted || '',
      subtitle:          data.subtitle          || '',
      btn_primary_label: data.btn_primary_label || '',
      btn_primary_url:   data.btn_primary_url   || '',
      btn_ghost_label:   data.btn_ghost_label   || '',
      btn_ghost_url:     data.btn_ghost_url     || '',
    };
  }
}, { immediate: true });

// ══ SLIDER DE MARCAS ══════════════════════════════════════════════════════════
// CRUD delegado a BrandSliderSection.vue. brandConfigForm es v-model
// compartido (el preview compartido en la pestaña 'brand_slider' lo necesita)
// -- ver BrandSliderSection.vue. `brandItems` (store) no necesita v-model,
// el padre lo lee directo de storeToRefs para el preview.
const brandConfigForm = ref({
  title: 'Marcas y clientes', subtitle: '',
  autoplay: true, speed: 3500, direction: 'left', loop: true, pause_on_hover: true,
  items_desktop: 6, items_tablet: 4, items_mobile: 2,
  background_color: '', padding_top: 'normal', padding_bottom: 'normal',
  is_visible: true,
});
watch(brandSliderConfig, (data) => {
  if (data) {
    brandConfigForm.value = {
      title: data.title || '', subtitle: data.subtitle || '',
      autoplay: data.autoplay, speed: data.speed, direction: data.direction,
      loop: data.loop, pause_on_hover: data.pause_on_hover,
      items_desktop: data.items_desktop, items_tablet: data.items_tablet, items_mobile: data.items_mobile,
      background_color: data.background_color || '',
      padding_top: data.padding_top, padding_bottom: data.padding_bottom,
      is_visible: data.is_visible,
    };
  }
}, { immediate: true });

// ══ INIT ═══════════════════════════════════════════════════════════════════════
// Fetch inicial de TODAS las secciones aqui (no en cada subcomponente) para que
// los contadores del sidebar y el preview compartido tengan datos desde el
// primer render, sin importar cual pestaña este activa -- mismo comportamiento
// que antes de P1-3. Cada subcomponente re-fetchea su propia seccion despues de
// sus propias mutaciones.
onMounted(() => {
  store.fetchModules();
  store.fetchBanners();
  store.fetchCards();
  store.fetchCardGroups();
  store.fetchFeatureBannerSections();
  store.fetchFooter();
  store.fetchFooterGroups();
  store.fetchSiteBrand();
  store.fetchNavbarLinks();
  store.fetchFooterCta();
  store.fetchBrandItems();
  store.fetchBrandSliderConfig();
});
</script>

<style>
/* Home Builder: hoja de estilos GLOBAL (no scoped) a proposito -- P1-3 (2026-07-27)
   descompuso este editor en subcomponentes por seccion (ver ./home-builder/), y las
   clases .hcb-* (design system compartido del builder: botones, inputs, chips, grids,
   modales) se usan identicas en todos ellos. CSS `scoped` de Vue no cruza limites de
   componente -- si esta hoja siguiera scoped aqui, ningun estilo se aplicaria dentro
   de los componentes hijos. El prefijo hcb- (Home Config Builder) ya evita colisiones
   con el resto de la app; no duplicar estas reglas en cada subcomponente. */

/* ══ SHELL ══════════════════════════════════════════════════════════════════ */
.hcb-shell {
  display: grid;
  grid-template-columns: 220px 1fr 320px;
  height: calc(100vh - 70px);
  overflow: hidden;
  background: #f1f5f9;
  font-size: .875rem;
  margin: -1.5rem;
}

/* ══ SIDEBAR ════════════════════════════════════════════════════════════════ */
.hcb-sidebar {
  background: #0f172a;
  color: #94a3b8;
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  flex-shrink: 0;
}
.hcb-logo {
  display: flex; align-items: center; gap: .6rem;
  padding: 1.25rem 1.25rem 1rem;
  color: #fff; font-weight: 800; font-size: .95rem;
  border-bottom: 1px solid rgba(255,255,255,.07);
}
.hcb-logo .bi { font-size: 1.2rem; color: #2563eb; }
.hcb-nav { padding: .75rem .625rem; flex: 1; display: flex; flex-direction: column; gap: .25rem; }
.hcb-nav-btn {
  display: flex; align-items: center; gap: .6rem;
  padding: .625rem .875rem; border-radius: 10px;
  border: none; background: none; color: #94a3b8;
  cursor: pointer; text-align: left; width: 100%;
  font-size: .825rem; font-weight: 500;
  transition: background 180ms, color 180ms;
}
.hcb-nav-btn:hover { background: rgba(255,255,255,.06); color: #e2e8f0; }
.hcb-nav-btn--active { background: #2563eb !important; color: #fff !important; }
.hcb-nav-btn .bi { font-size: 1rem; flex-shrink: 0; }
.hcb-badge {
  margin-left: auto;
  background: rgba(255,255,255,.15); color: #fff;
  font-size: .65rem; font-weight: 700;
  padding: .15rem .45rem; border-radius: 99px;
}
.hcb-badge--gray { background: #e2e8f0; color: #64748b; }
.hcb-sidebar-footer { padding: 1rem 1.25rem; border-top: 1px solid rgba(255,255,255,.07); }
.hcb-preview-btn {
  display: flex; align-items: center; gap: .5rem;
  color: #94a3b8; text-decoration: none; font-size: .8rem;
  transition: color 200ms;
}
.hcb-preview-btn:hover { color: #fff; }

/* ══ EDITOR ═════════════════════════════════════════════════════════════════ */
.hcb-editor {
  overflow-y: auto;
  padding: 1.75rem 2rem;
}
.hcb-section-header {
  display: flex; align-items: flex-start; justify-content: space-between;
  margin-bottom: 1.5rem; gap: 1rem;
}
.hcb-section-title { font-size: 1.25rem; font-weight: 800; color: #0f172a; margin-bottom: .25rem; }
.hcb-section-sub   { color: #64748b; margin: 0; font-size: .825rem; }
.hcb-loading { display: flex; justify-content: center; padding: 3rem; }
.hcb-empty { text-align: center; color: #94a3b8; padding: 2rem; background: #fff; border-radius: 12px; }
.hcb-empty--sm { display: flex; align-items: center; justify-content: center; gap: .75rem; padding: 1.25rem; font-size: .85rem; }
.hcb-hint { font-size: .72rem; color: #94a3b8; }
.hcb-subheading {
  font-size: .78rem; font-weight: 700; text-transform: uppercase; letter-spacing: .04em;
  color: #94a3b8; margin: .5rem 0 -.25rem; padding-top: .5rem; border-top: 1px solid #e2e8f0;
}

/* Buttons */
.hcb-btn {
  display: inline-flex; align-items: center; gap: .4rem;
  padding: .5rem 1rem; border-radius: 8px;
  border: 1px solid #e2e8f0; background: #fff; cursor: pointer;
  font-size: .825rem; font-weight: 600; color: #374151;
  transition: all 180ms;
}
.hcb-btn:hover { background: #f8fafc; }
.hcb-btn--primary { background: #2563eb; border-color: #2563eb; color: #fff; }
.hcb-btn--primary:hover { background: #1d4ed8; border-color: #1d4ed8; }
.hcb-icon-btn {
  width: 30px; height: 30px; border-radius: 8px;
  border: 1px solid #e2e8f0; background: #fff;
  display: grid; place-items: center; cursor: pointer; font-size: .8rem;
  transition: all 180ms;
}
.hcb-icon-btn:hover { background: #f1f5f9; }
.hcb-icon-btn--danger:hover { background: #fef2f2; border-color: #ef4444; color: #ef4444; }
.hcb-icon-btn--success:hover { background: #f0fdf4; border-color: #22c55e; color: #22c55e; }
.hcb-icon-btn--sm { width: 26px; height: 26px; font-size: .75rem; }
.hcb-icon-btn--xs { width: 24px; height: 24px; font-size: .7rem; }
.hcb-btn-link { background: none; border: none; cursor: pointer; font-size: .8rem; padding: 0; }

/* Chips */
.hcb-chip {
  display: inline-flex; align-items: center;
  padding: .2rem .55rem; border-radius: 6px;
  background: #f1f5f9; color: #475569;
  font-size: .7rem; font-weight: 600;
}
.hcb-chip--green { background: #dcfce7; color: #16a34a; }
.hcb-chip--gray  { background: #f1f5f9; color: #94a3b8; }
.hcb-chip--xs    { font-size: .65rem; padding: .15rem .45rem; }

/* Modules grid */
.hcb-modules-grid { display: flex; flex-direction: column; gap: .75rem; }
.hcb-module-card {
  display: flex; align-items: center; gap: 1rem;
  background: #fff; border-radius: 12px; padding: 1rem 1.25rem;
  border: 1px solid #e2e8f0; transition: box-shadow 180ms;
}
.hcb-module-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,.06); }
.hcb-module-card--hidden { opacity: .55; }
.hcb-module-card__color {
  width: 44px; height: 44px; border-radius: 12px;
  display: grid; place-items: center; flex-shrink: 0;
  color: #fff; font-size: 1.1rem;
}
.hcb-module-card__body { flex: 1; min-width: 0; }
.hcb-module-card__label { font-weight: 700; color: #0f172a; margin-bottom: .35rem; }
.hcb-module-card__meta { display: flex; gap: .4rem; flex-wrap: wrap; }
.hcb-module-card__actions { display: flex; gap: .4rem; }

/* Banners list */
.hcb-banners-list { display: flex; flex-direction: column; gap: .625rem; }
.hcb-banner-row {
  display: flex; align-items: center; gap: 1rem;
  background: #fff; border-radius: 12px; padding: .875rem 1rem;
  border: 1px solid #e2e8f0;
}
.hcb-banner-row--inactive { opacity: .6; }
.hcb-drag-handle { cursor: grab; color: #94a3b8; flex-shrink: 0; }
.hcb-drag-handle:active { cursor: grabbing; }

/* Footer groups grid */
.hcb-fg-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: .75rem; }
.hcb-fg-card {
  display: flex; align-items: center; gap: .75rem;
  background: #fff; border-radius: 12px; padding: .875rem 1rem;
  border: 1px solid #e2e8f0; cursor: pointer; transition: border-color .15s ease;
}
.hcb-fg-card:hover { border-color: #93c5fd; }
.hcb-fg-card--selected { border-color: #2563eb; box-shadow: 0 0 0 1px #2563eb; }
.hcb-fg-card--inactive { opacity: .6; }
.hcb-fg-card__icon {
  width: 40px; height: 40px; border-radius: 8px; flex-shrink: 0;
  background: #eff6ff; color: #2563eb; display: grid; place-items: center; font-size: 1.1rem;
}
.hcb-fg-card__body { flex: 1; min-width: 0; }
.hcb-fg-card__title { font-weight: 600; color: #0f172a; }
.hcb-fg-card__meta { font-size: .75rem; color: #94a3b8; }
.hcb-banner-thumb {
  width: 80px; height: 52px; border-radius: 8px;
  overflow: hidden; flex-shrink: 0; background: #f1f5f9;
  display: grid; place-items: center;
}
.hcb-banner-thumb img { width: 100%; height: 100%; object-fit: cover; }
.hcb-banner-video-icon, .hcb-banner-placeholder { color: #94a3b8; font-size: 1.4rem; }
.hcb-banner-info { flex: 1; min-width: 0; }
.hcb-banner-title { font-weight: 600; color: #0f172a; margin-bottom: .3rem; }
.hcb-banner-meta  { display: flex; gap: .35rem; flex-wrap: wrap; }
.hcb-banner-actions { display: flex; gap: .4rem; }

/* Groups */
.hcb-groups-list { display: flex; flex-direction: column; gap: 1.5rem; }
.hcb-group-block { background: #fff; border-radius: 14px; border: 1px solid #e2e8f0; overflow: hidden; }
.hcb-group-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: .875rem 1.25rem; border-bottom: 1px solid #f1f5f9;
  background: #fafbfc; gap: .75rem;
}
.hcb-group-header__left  { display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; }
.hcb-group-header__right { display: flex; align-items: center; gap: .5rem; }
.hcb-group-name { font-weight: 700; color: #0f172a; }
.hcb-inline-input {
  border: 1px solid #2563eb; border-radius: 6px; padding: .3rem .6rem;
  font-size: .825rem; outline: none; min-width: 160px;
}

/* Cards grid */
.hcb-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: .75rem;
  padding: 1rem;
}
.hcb-card-thumb {
  border: 1px solid #e2e8f0; border-radius: 10px; padding: .75rem;
  display: flex; align-items: flex-start; gap: .6rem;
  background: #fff; transition: box-shadow 180ms;
}
.hcb-card-thumb:hover { box-shadow: 0 2px 10px rgba(0,0,0,.07); }
.hcb-card-thumb__icon {
  width: 34px; height: 34px; border-radius: 8px;
  display: grid; place-items: center; flex-shrink: 0; font-size: .9rem;
}
.hcb-card-thumb__body { flex: 1; min-width: 0; }
.hcb-card-thumb__title { font-weight: 600; font-size: .8rem; color: #0f172a; margin-bottom: .3rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hcb-card-thumb__meta  { display: flex; gap: .3rem; flex-wrap: wrap; }
.hcb-card-thumb__actions { display: flex; flex-direction: column; gap: .3rem; }

/* Card section */
.hcb-card-section { background: #fff; border-radius: 14px; border: 1px solid #e2e8f0; padding: 1.5rem; }
.hcb-subsection-title { font-weight: 700; color: #0f172a; margin-bottom: 1rem; font-size: .9rem; }

/* Links list */
.hcb-links-list { display: flex; flex-direction: column; gap: .5rem; }
.hcb-link-row {
  display: flex; align-items: center; gap: .75rem;
  padding: .625rem .875rem; background: #f8fafc;
  border-radius: 8px; border: 1px solid #e2e8f0;
}
.hcb-link-icon { color: #64748b; font-size: 1rem; flex-shrink: 0; }
.hcb-link-info { flex: 1; display: flex; align-items: center; gap: .4rem; flex-wrap: wrap; }
.hcb-link-title { font-weight: 600; color: #0f172a; }

/* Brand preview */
.hcb-brand-preview {
  display: flex; align-items: center; gap: 1rem;
  background: #f8fafc; border-radius: 12px; padding: 1.5rem;
  border: 1px solid #e2e8f0;
}
.hcb-brand-preview__logo {
  width: 64px; height: 64px; border-radius: 12px;
  overflow: hidden; flex-shrink: 0; background: #e2e8f0;
  display: grid; place-items: center;
}
.hcb-brand-preview__img { width: 100%; height: 100%; object-fit: contain; }
.hcb-brand-preview__placeholder { color: #94a3b8; font-size: 1.75rem; }
.hcb-brand-preview__name { font-weight: 800; font-size: 1.1rem; color: #0f172a; }
.hcb-brand-preview__tagline { color: #64748b; font-size: .85rem; }

/* Forms */
.hcb-form-grid { display: grid; grid-template-columns: 1fr 1fr; gap: .875rem; }
.hcb-field { display: flex; flex-direction: column; gap: .35rem; }
.hcb-field--full { grid-column: 1 / -1; }
.hcb-label { font-size: .75rem; font-weight: 600; color: #374151; }
.hcb-input {
  border: 1px solid #e2e8f0; border-radius: 8px; padding: .5rem .75rem;
  font-size: .875rem; color: #0f172a; background: #fff;
  outline: none; transition: border-color 180ms;
  width: 100%;
}
.hcb-input:focus { border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,.12); }
.hcb-select { border: 1px solid #e2e8f0; border-radius: 8px; padding: .5rem .75rem; font-size: .875rem; color: #0f172a; background: #fff; outline: none; width: 100%; }
.hcb-select:focus { border-color: #2563eb; }
.hcb-select-sm { border: 1px solid #e2e8f0; border-radius: 6px; padding: .3rem .5rem; font-size: .75rem; color: #374151; background: #fff; cursor: pointer; }
.hcb-color-input { width: 38px; height: 38px; border-radius: 8px; border: 1px solid #e2e8f0; padding: 2px; cursor: pointer; }
.hcb-upload-area {
  border: 2px dashed #e2e8f0; border-radius: 10px;
  padding: 1.5rem; text-align: center; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; gap: .5rem;
  color: #94a3b8; font-size: .825rem; transition: border-color 200ms, background 200ms;
}
.hcb-upload-area:hover, .hcb-upload-area--dragging {
  border-color: #2563eb; background: rgba(37,99,235,.04);
}
.hcb-upload-area .bi { font-size: 1.5rem; color: #cbd5e1; }
.hcb-upload-hint { font-size: .7rem; color: #cbd5e1; }

/* Media actual con opcion eliminar */
.hcb-media-current {
  border: 1px solid #e2e8f0; border-radius: 10px; overflow: hidden;
  background: #f8fafc;
}
.hcb-media-current__img {
  width: 100%; max-height: 160px; object-fit: cover; display: block;
}
.hcb-media-current__actions {
  display: flex; gap: .5rem; padding: .625rem;
  border-top: 1px solid #f1f5f9;
}
.hcb-btn--danger-sm {
  display: inline-flex; align-items: center; gap: .3rem;
  padding: .3rem .7rem; border-radius: 7px; font-size: .75rem; font-weight: 600;
  border: 1px solid #fca5a5; background: #fef2f2; color: #dc2626; cursor: pointer;
  transition: all 180ms;
}
.hcb-btn--danger-sm:hover { background: #fee2e2; border-color: #ef4444; }
.hcb-btn--sm {
  display: inline-flex; align-items: center; gap: .3rem;
  padding: .3rem .7rem; border-radius: 7px; font-size: .75rem; font-weight: 600;
  border: 1px solid #e2e8f0; background: #fff; color: #374151; cursor: pointer;
  transition: all 180ms;
}
.hcb-btn--sm:hover { background: #f8fafc; }

/* ══ PREVIEW ════════════════════════════════════════════════════════════════ */
.hcb-preview-panel {
  background: #fff; border-left: 1px solid #e2e8f0;
  display: flex; flex-direction: column; overflow: hidden;
}
.hcb-preview-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: .875rem 1rem; border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
}
.hcb-preview-label { font-weight: 700; font-size: .8rem; color: #374151; }
.hcb-preview-viewport-btns { display: flex; gap: .3rem; }
.hcb-vp-btn {
  width: 28px; height: 28px; border-radius: 6px;
  border: 1px solid #e2e8f0; background: #fff;
  display: grid; place-items: center; cursor: pointer; font-size: .75rem;
  transition: all 180ms;
}
.hcb-vp-btn.active, .hcb-vp-btn:hover { background: #2563eb; border-color: #2563eb; color: #fff; }
.hcb-preview-frame-wrap { flex: 1; overflow-y: auto; padding: 1rem; background: #f8fafc; }
.hcb-preview-frame { background: #fff; border-radius: 12px; overflow: hidden; border: 1px solid #e2e8f0; min-height: 200px; padding: 1rem; }
.hcb-preview-frame--tablet { max-width: 768px; margin: 0 auto; }
.hcb-preview-frame--mobile { max-width: 375px; margin: 0 auto; }

/* Preview: el contenido real ahora lo pintan HomeRenderer/CustomerNavbar/
   CustomerFooter (componentes reales, no markup propio) -- solo queda el
   contenedor del frame. El wrapper con position:relative crea un containing
   block para los descendientes position:fixed de CustomerNavbar (standalone
   usa position:relative de todos modos, pero se deja por robustez). */
.hcb-preview-frame--real { position: relative; padding: 0; }

/* ══ MODALES ════════════════════════════════════════════════════════════════ */
/* El chrome del modal (backdrop/header/footer) ahora vive en
   components/base/BaseModal.vue -- aqui solo quedan las clases de contenido
   especifico de cada formulario (hcb-form-grid, hcb-field, hcb-input, etc.) */

/* Banner live preview */
.hcb-banner-live-preview {
  position: relative; border-radius: 12px; overflow: hidden;
  background: #f1f5f9; min-height: 120px;
}
.hcb-blp-img { width: 100%; height: 160px; object-fit: cover; display: block; }
.hcb-blp-placeholder {
  height: 120px; display: flex; flex-direction: column;
  align-items: center; justify-content: center; gap: .5rem;
  color: #94a3b8; font-size: .85rem;
}
.hcb-blp-placeholder .bi { font-size: 2rem; }
.hcb-blp-overlay {
  position: absolute; bottom: 0; left: 0; right: 0;
  background: linear-gradient(to top, rgba(0,0,0,.65), transparent);
  padding: .875rem 1rem;
}
.hcb-blp-title    { color: #fff; font-weight: 800; font-size: .9rem; }
.hcb-blp-subtitle { color: rgba(255,255,255,.8); font-size: .8rem; margin-top: .2rem; }
.hcb-blp-eyebrow {
  color: rgba(255,255,255,.78); font-size: .65rem; font-weight: 700; letter-spacing: 1.5px;
  text-transform: uppercase; margin-bottom: .3rem;
}
.hcb-blp-cta {
  margin-top: .5rem; background: #2563eb; color: #fff; border: none;
  border-radius: 6px; padding: .3rem .75rem; font-size: .75rem; font-weight: 600; cursor: pointer;
}
.hcb-blp-cta--ghost {
  background: transparent; border: 1px solid rgba(255,255,255,.55); color: rgba(255,255,255,.9);
}

/* Module live preview */
.hcb-module-live-preview {
  display: flex; align-items: center; gap: 1rem;
  border-radius: 12px; padding: 1rem 1.25rem;
}
.hcb-mlp-icon {
  width: 48px; height: 48px; border-radius: 14px;
  display: grid; place-items: center; color: #fff; font-size: 1.25rem; flex-shrink: 0;
}

/* Card form two-col */
.hcb-card-form-col  { overflow-y: auto; }
.hcb-card-preview-col { display: flex; flex-direction: column; }
.hcb-card-live-preview { flex: 1; padding: .5rem; }
</style>
