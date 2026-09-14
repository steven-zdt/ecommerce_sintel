/**
 * coreAdmin.js — Pinia store para el modulo Core admin.
 *
 * Undecimo incremento de la migracion a stores Pinia de modulos admin
 * (auditoria 2026-07-23, doc 13 P1-4). Originalmente solo cubria
 * `AboutUsAdminView.vue` (301 LOC, configuracion de /nosotros + valores
 * institucionales) -- `HomeConfigView.vue` (2.629 LOC) y
 * `ModuleBuilderModal.vue` (1.588 LOC) NO se migraron en ese momento.
 *
 * Decimotercer incremento (2026-07-27): se agregan aqui TODAS las acciones de
 * `HomeConfigView.vue` (12 sub-dominios: modulos, banners, tarjetas, grupos de
 * tarjetas, footer, enlaces de footer, columnas de footer, marca, navbar, CTA
 * final, items del slider de marcas, config del slider de marcas) y las 2
 * acciones de `ModuleBuilderModal.vue` (crear/actualizar modulo). Esto cierra
 * P1-4 (migracion a stores Pinia) al 100% -- ya no queda ningun modulo admin
 * de los 11 dominios originales llamando a useApi() directo.
 *
 * P1-3 (descomponer HomeConfigView.vue en subcomponentes por seccion) se deja
 * DELIBERADAMENTE fuera de este incremento -- es un refactor distinto y mucho
 * mas riesgoso (un editor CMS en vivo con preview compartido entre las 8
 * secciones), decidido con el usuario que amerita su propia sesion dedicada
 * (ver AUDITORIA/01_AUDITORIA_GENERAL.md §7.6/§7.20). Aqui SOLO se mueve la
 * capa de datos (donde viven las llamadas a la API) al store -- la estructura
 * del componente (single-file, 8 secciones con v-if, modales via Teleport,
 * drag-and-drop, preview en vivo) no se toca.
 *
 * Todas las acciones de creacion/actualizacion que aceptan `payload` detectan
 * `payload instanceof FormData` para decidir el Content-Type -- el componente
 * sigue decidiendo el mismo que antes (FormData solo cuando hay un archivo
 * adjunto/eliminado) y el store simplemente lo respeta, sin necesitar un
 * parametro extra de headers en cada call site.
 *
 * El draft de cada formulario (banner/tarjeta/grupo/enlace/columna/marca/
 * navbar/CTA/item de marca, mas el formulario de ModuleBuilderModal) sigue
 * local al componente -- mismo criterio que los 12 incrementos anteriores.
 */
import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

export const useCoreAdminStore = defineStore('coreAdmin', {
  state: () => ({
    // ── Nosotros (AboutUsAdminView.vue) ───────────────────────────────────
    config: null,
    values: [],
    valuesLoading: false,

    // ── Home Builder (HomeConfigView.vue) ─────────────────────────────────
    modules: [],
    modulesLoading: false,

    banners: [],
    bannersLoading: false,

    cards: [],
    cardsLoading: false,
    cardGroups: [],
    cardGroupsLoading: false,

    featureBannerSections: [],
    featureBannerSectionsLoading: false,

    footerLinks: [],
    footerContact: null,
    footerLoading: false,

    footerGroups: [],
    footerGroupsLoading: false,

    brand: null,
    brandLoading: false,

    navbarLinks: [],
    navbarLoading: false,

    footerCta: null,
    ctaLoading: false,

    brandItems: [],
    brandItemsLoading: false,
    brandSliderConfig: null,
    brandConfigLoading: false,

    actionLoading: false,
    error: null,
  }),

  actions: {
    _api() {
      return useApi();
    },

    async _mutate(action) {
      this.actionLoading = true;
      try {
        await action();
        return { ok: true };
      } catch (err) {
        return { ok: false, error: err };
      } finally {
        this.actionLoading = false;
      }
    },

    async _mutateData(action) {
      this.actionLoading = true;
      try {
        const { data } = await action();
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err };
      } finally {
        this.actionLoading = false;
      }
    },

    _headersFor(payload) {
      return payload instanceof FormData ? { headers: { 'Content-Type': 'multipart/form-data' } } : {};
    },

    // ── Nosotros ───────────────────────────────────────────────────────────
    async fetchConfig() {
      try {
        const { data } = await this._api().get('dashboard/about-us/config/');
        this.config = data;
      } catch {
        this.error = 'Error cargando la configuracion de Nosotros.';
      }
    },

    async fetchValues() {
      this.valuesLoading = true;
      try {
        const { data } = await this._api().get('dashboard/about-us/');
        this.values = data;
      } catch {
        this.error = 'Error cargando los valores institucionales.';
      } finally {
        this.valuesLoading = false;
      }
    },

    saveConfig(formData) {
      return this._mutate(() => this._api().patch('dashboard/about-us/config/update/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }));
    },

    createValue(payload) {
      return this._mutate(() => this._api().post('dashboard/about-us/create/', payload));
    },

    updateValue(uuid, payload) {
      return this._mutate(() => this._api().patch(`dashboard/about-us/${uuid}/`, payload));
    },

    deleteValue(uuid) {
      return this._mutate(() => this._api().delete(`dashboard/about-us/${uuid}/delete/`));
    },

    // ── Modulos (Home Builder) ───────────────────────────────────────────────
    async fetchModules() {
      this.modulesLoading = true;
      try {
        const { data } = await this._api().get('dashboard/home-config/modules/');
        this.modules = data;
      } catch {
        this.error = 'Error al cargar los modulos.';
      } finally {
        this.modulesLoading = false;
      }
    },

    createModule(payload) {
      return this._mutateData(() => this._api().post('dashboard/home-config/modules/create/', payload, this._headersFor(payload)));
    },

    updateModule(uuid, payload) {
      return this._mutateData(() => this._api().patch(`dashboard/home-config/modules/${uuid}/`, payload, this._headersFor(payload)));
    },

    deleteModule(uuid) {
      return this._mutate(() => this._api().delete(`dashboard/home-config/modules/${uuid}/delete/`));
    },

    // ── Banners ──────────────────────────────────────────────────────────────
    async fetchBanners() {
      this.bannersLoading = true;
      try {
        const { data } = await this._api().get('dashboard/home-config/banners/');
        this.banners = data;
      } catch {
        this.error = 'Error al cargar los banners.';
      } finally {
        this.bannersLoading = false;
      }
    },

    createBanner(payload) {
      return this._mutateData(() => this._api().post('dashboard/home-config/banners/create/', payload, this._headersFor(payload)));
    },

    updateBanner(uuid, payload) {
      return this._mutateData(() => this._api().patch(`dashboard/home-config/banners/${uuid}/`, payload, this._headersFor(payload)));
    },

    deleteBanner(uuid) {
      return this._mutate(() => this._api().delete(`dashboard/home-config/banners/${uuid}/delete/`));
    },

    // ── Tarjetas ─────────────────────────────────────────────────────────────
    async fetchCards() {
      this.cardsLoading = true;
      try {
        const { data } = await this._api().get('dashboard/home-cards/');
        this.cards = data;
      } catch {
        this.error = 'Error al cargar las tarjetas.';
      } finally {
        this.cardsLoading = false;
      }
    },

    createCard(payload) {
      return this._mutateData(() => this._api().post('dashboard/home-cards/create/', payload, this._headersFor(payload)));
    },

    updateCard(uuid, payload) {
      return this._mutateData(() => this._api().patch(`dashboard/home-cards/${uuid}/`, payload, this._headersFor(payload)));
    },

    deleteCard(uuid) {
      return this._mutate(() => this._api().delete(`dashboard/home-cards/${uuid}/delete/`));
    },

    // ── Grupos de tarjetas ───────────────────────────────────────────────────
    async fetchCardGroups() {
      this.cardGroupsLoading = true;
      try {
        const { data } = await this._api().get('dashboard/home-card-groups/');
        this.cardGroups = data;
      } catch {
        this.error = 'Error al cargar los grupos de tarjetas.';
      } finally {
        this.cardGroupsLoading = false;
      }
    },

    upsertCardGroup(payload) {
      return this._mutateData(() => this._api().post('dashboard/home-card-groups/upsert/', payload, this._headersFor(payload)));
    },

    deleteCardGroup(uuid) {
      return this._mutate(() => this._api().delete(`dashboard/home-card-groups/${uuid}/delete/`));
    },

    // ── Feature Banner (secciones + bloques) ─────────────────────────────────
    async fetchFeatureBannerSections() {
      this.featureBannerSectionsLoading = true;
      try {
        const { data } = await this._api().get('dashboard/feature-banner-sections/');
        this.featureBannerSections = data;
      } catch {
        this.error = 'Error al cargar las secciones de Feature Banner.';
      } finally {
        this.featureBannerSectionsLoading = false;
      }
    },

    createFeatureBannerSection(payload) {
      return this._mutateData(() => this._api().post('dashboard/feature-banner-sections/create/', payload, this._headersFor(payload)));
    },

    updateFeatureBannerSection(uuid, payload) {
      return this._mutateData(() => this._api().patch(`dashboard/feature-banner-sections/${uuid}/`, payload, this._headersFor(payload)));
    },

    deleteFeatureBannerSection(uuid) {
      return this._mutate(() => this._api().delete(`dashboard/feature-banner-sections/${uuid}/delete/`));
    },

    createFeatureBannerBlock(payload) {
      return this._mutateData(() => this._api().post('dashboard/feature-banner-blocks/create/', payload, this._headersFor(payload)));
    },

    updateFeatureBannerBlock(uuid, payload) {
      return this._mutateData(() => this._api().patch(`dashboard/feature-banner-blocks/${uuid}/`, payload, this._headersFor(payload)));
    },

    deleteFeatureBannerBlock(uuid) {
      return this._mutate(() => this._api().delete(`dashboard/feature-banner-blocks/${uuid}/delete/`));
    },

    reorderFeatureBannerBlocks(sectionUuid, orderedUuids) {
      return this._mutate(() => this._api().post('dashboard/feature-banner-blocks/reorder/', { section: sectionUuid, ordered_uuids: orderedUuids }));
    },

    // ── Footer (contacto + enlaces) ──────────────────────────────────────────
    async fetchFooter() {
      this.footerLoading = true;
      try {
        const { data } = await this._api().get('dashboard/footer/');
        this.footerLinks = data.links || [];
        this.footerContact = data.contact || null;
      } catch {
        this.error = 'Error al cargar el footer.';
      } finally {
        this.footerLoading = false;
      }
    },

    saveFooterContact(payload) {
      return this._mutate(() => this._api().post('dashboard/footer/contact/', payload));
    },

    createFooterLink(payload) {
      return this._mutateData(() => this._api().post('dashboard/footer/links/create/', payload));
    },

    updateFooterLink(uuid, payload) {
      return this._mutateData(() => this._api().patch(`dashboard/footer/links/${uuid}/`, payload));
    },

    deleteFooterLink(uuid) {
      return this._mutate(() => this._api().delete(`dashboard/footer/links/${uuid}/delete/`));
    },

    reorderFooterLinks(uuids) {
      return this._mutate(() => this._api().post('dashboard/footer/links/reorder/', { items: uuids }));
    },

    // ── Columnas de footer ───────────────────────────────────────────────────
    async fetchFooterGroups() {
      this.footerGroupsLoading = true;
      try {
        const { data } = await this._api().get('dashboard/footer-groups/');
        this.footerGroups = data;
      } catch {
        this.error = 'Error al cargar las columnas del footer.';
      } finally {
        this.footerGroupsLoading = false;
      }
    },

    createFooterGroup(payload) {
      return this._mutateData(() => this._api().post('dashboard/footer-groups/create/', payload));
    },

    updateFooterGroup(uuid, payload) {
      return this._mutateData(() => this._api().patch(`dashboard/footer-groups/${uuid}/`, payload));
    },

    deleteFooterGroup(uuid) {
      return this._mutate(() => this._api().delete(`dashboard/footer-groups/${uuid}/delete/`));
    },

    reorderFooterGroups(uuids) {
      return this._mutate(() => this._api().post('dashboard/footer-groups/reorder/', { items: uuids }));
    },

    // ── Marca ────────────────────────────────────────────────────────────────
    async fetchSiteBrand() {
      this.brandLoading = true;
      try {
        const { data } = await this._api().get('dashboard/site-brand/');
        this.brand = data;
      } catch {
        this.error = 'Error al cargar la marca.';
      } finally {
        this.brandLoading = false;
      }
    },

    updateSiteBrand(payload) {
      return this._mutateData(() => this._api().patch('dashboard/site-brand/update/', payload, this._headersFor(payload)));
    },

    // ── Navbar ───────────────────────────────────────────────────────────────
    async fetchNavbarLinks() {
      this.navbarLoading = true;
      try {
        const { data } = await this._api().get('dashboard/navbar/');
        this.navbarLinks = data;
      } catch {
        this.error = 'Error al cargar el navbar.';
      } finally {
        this.navbarLoading = false;
      }
    },

    createNavLink(payload) {
      return this._mutateData(() => this._api().post('dashboard/navbar/create/', payload));
    },

    updateNavLink(uuid, payload) {
      return this._mutateData(() => this._api().patch(`dashboard/navbar/${uuid}/`, payload));
    },

    deleteNavLink(uuid) {
      return this._mutate(() => this._api().delete(`dashboard/navbar/${uuid}/delete/`));
    },

    // ── CTA final ────────────────────────────────────────────────────────────
    async fetchFooterCta() {
      this.ctaLoading = true;
      try {
        const { data } = await this._api().get('dashboard/footer-cta/');
        this.footerCta = data;
      } catch {
        this.error = 'Error al cargar el CTA final.';
      } finally {
        this.ctaLoading = false;
      }
    },

    updateFooterCta(payload) {
      return this._mutate(() => this._api().patch('dashboard/footer-cta/update/', payload));
    },

    // ── Slider de marcas — items ─────────────────────────────────────────────
    async fetchBrandItems() {
      this.brandItemsLoading = true;
      try {
        const { data } = await this._api().get('dashboard/brand-slider/');
        this.brandItems = data;
      } catch {
        this.error = 'Error al cargar el slider de marcas.';
      } finally {
        this.brandItemsLoading = false;
      }
    },

    createBrandItem(payload) {
      return this._mutateData(() => this._api().post('dashboard/brand-slider/create/', payload, this._headersFor(payload)));
    },

    updateBrandItem(uuid, payload) {
      return this._mutateData(() => this._api().patch(`dashboard/brand-slider/${uuid}/`, payload, this._headersFor(payload)));
    },

    deleteBrandItem(uuid) {
      return this._mutate(() => this._api().delete(`dashboard/brand-slider/${uuid}/delete/`));
    },

    reorderBrandItems(uuids) {
      return this._mutate(() => this._api().post('dashboard/brand-slider/reorder/', { items: uuids }));
    },

    // ── Slider de marcas — configuracion ─────────────────────────────────────
    async fetchBrandSliderConfig() {
      this.brandConfigLoading = true;
      try {
        const { data } = await this._api().get('dashboard/brand-slider/config/');
        this.brandSliderConfig = data;
      } catch {
        this.error = 'Error al cargar la configuracion del slider.';
      } finally {
        this.brandConfigLoading = false;
      }
    },

    updateBrandSliderConfig(payload) {
      return this._mutate(() => this._api().patch('dashboard/brand-slider/config/update/', payload));
    },
  },
});
