<template>
  <HomeRenderer
    :banners="banners"
    :modules="modules"
    :feature-banner-sections="featureBannerSections"
    :flash-offers="flashOffers"
    :featured-products="featuredProducts"
    :featured-equipment="featuredEquipment"
    :featured-services="featuredServices"
    :home-cards="homeCards"
    :card-group-titles="cardGroupTitles"
    :card-groups="cardGroups"
    :footer-cta="footerCta"
    :brand-slider="brandSlider"
    :loading="loading"
  />
</template>

<script setup>
import { ref, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import HomeRenderer from '@/renderers/HomeRenderer.vue';
import { useSeo } from '@/composables/useSeo';

// ── Estado ────────────────────────────────────────────────────────────────────
const api = useApi();
const { setSeo } = useSeo();
const loading = ref(true);

const footerCta         = ref({});
const banners           = ref([]);
const modules           = ref([]);
const featureBannerSections = ref([]);
const flashOffers       = ref([]);
const featuredProducts  = ref([]);
const featuredEquipment = ref([]);
const featuredServices  = ref([]);
const homeCards         = ref([]);
const cardGroupTitles   = ref({});
const cardGroups        = ref([]);
const brandSlider       = ref({ config: {}, items: [] });

// ── Fetch ─────────────────────────────────────────────────────────────────────
// HomeView solo obtiene los datos -- todo el render vive en HomeRenderer.vue,
// compartido con la Vista Previa del panel admin (/panel/home-config). Ver
// ai_skills/frontend/editor/home_render_audit_2026_07_11.md (Fase 3).
onMounted(async () => {
  try {
    const { data } = await api.get('core/home-feed/');
    banners.value           = data.banners            || [];
    modules.value           = data.modules            || [];
    featureBannerSections.value = data.feature_banner_sections || [];
    flashOffers.value       = data.flash_offers       || [];
    featuredProducts.value  = data.featured_products  || [];
    featuredEquipment.value = data.featured_equipment || [];
    featuredServices.value  = data.featured_services  || [];
    homeCards.value         = data.home_cards         || [];
    cardGroupTitles.value   = data.card_group_titles  || {};
    cardGroups.value        = data.card_groups        || [];
    if (data.footer_cta)    footerCta.value = data.footer_cta;
    if (data.brand_slider)  brandSlider.value = data.brand_slider;
  } catch (err) {
    console.error('[HomeView] Error cargando home-feed:', err);
  } finally {
    loading.value = false;
  }

  try {
    const { data: site } = await api.get('core/site-config/');
    const seo = site.seo || {};
    setSeo({
      title: seo.meta_title || site.brand?.site_name,
      description: seo.meta_description || site.brand?.tagline,
      ogImage: seo.og_image,
      jsonLd: {
        '@context': 'https://schema.org',
        '@type': 'Organization',
        name: site.brand?.site_name,
        logo: site.brand?.logo,
      },
    });
  } catch (err) {
    console.error('[HomeView] Error cargando site-config para SEO:', err);
  }
});
</script>
