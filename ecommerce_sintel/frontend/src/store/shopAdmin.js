/**
 * shopAdmin.js — Pinia store para el modulo Shop admin
 * (BrandList.vue, CategoryList.vue, TaxList.vue + TaxForm.vue, ProductList.vue,
 * ProductForm.vue).
 *
 * Decimo incremento (auditoria 2026-07-23, doc 13 P1-4): BrandList/CategoryList/
 * TaxList+TaxForm/ProductList. Sin capa de servicio previa -- llama a useApi()
 * directo, mismo criterio que operationsAdmin/usersAdmin.
 *
 * Duodecimo incremento (2026-07-27): se agrega `ProductForm.vue` (1.324 LOC --
 * variantes, imagenes, reglas de costo, multiples tabs, cada uno con su propio
 * CRUD), la pieza mas grande diferida deliberadamente del incremento anterior.
 * El draft de creacion/edicion (form general/SEO, newVariant, editingVariant,
 * costForm) sigue local al componente -- mismo criterio que el resto de la
 * migracion. `variants`/`costRules`/`productImages` SI viven en el store
 * porque son datos del servidor listados y mutados desde el mismo componente
 * (mismo patron que `values` en coreAdmin.js).
 *
 * `BrandForm.vue`/`CategoryForm.vue` tampoco se tocaron: son wrappers finos
 * sobre `BaseBrandForm.vue`/`BaseCategoryForm.vue`, componentes genericos
 * compartidos con `renting` (RentingBrandForm.vue/RentingCategoryForm.vue) --
 * atarlos a un store especifico de `shop` rompería su reusabilidad.
 *
 * `fetchCategories` (shop/categories/, paginado, para CategoryList.vue) y
 * `fetchProductCategories` (dashboard/categories/, sin paginar, para el
 * dropdown de categoria de ProductList.vue Y de ProductForm.vue -- mismo
 * endpoint exacto que ProductForm.vue llamaba por su cuenta, consolidado aqui)
 * son endpoints distintos a proposito -- el componente original ya los
 * distinguia asi. `fetchProductBrands` (dashboard/brands/, sin paginar) y
 * `fetchActiveTaxes` (dashboard/taxes/, filtrado is_active) son analogos,
 * nuevos para ProductForm.vue -- distintos de `fetchBrands`/`fetchTaxes`
 * (shop/brands/ y shop/taxes/, paginados, para BrandList/TaxList).
 */
import { defineStore } from 'pinia';
import useApi from '@/composables/useApi';

export const useShopAdminStore = defineStore('shopAdmin', {
  state: () => ({
    brands: [],
    brandsTotalCount: 0,
    brandsPagination: { next: null, previous: null },
    brandsLoading: false,

    categories: [],
    categoriesTotalCount: 0,
    categoriesPagination: { next: null, previous: null },
    categoriesLoading: false,
    productCategories: [],

    taxes: [],
    taxesTotalCount: 0,
    taxesPagination: { next: null, previous: null },
    taxesLoading: false,

    products: [],
    productsTotalCount: 0,
    productsPagination: { next: null, previous: null },
    productsLoading: false,

    productBrands: [],
    activeTaxes: [],

    variants: [],
    variantsLoading: false,

    costRules: [],

    productImages: [],
    imagesLoading: false,

    actionLoading: false,
    error: null,
  }),

  getters: {
    brandsTotalPages: (state) => Math.ceil(state.brandsTotalCount / 25),
    categoriesTotalPages: (state) => Math.ceil(state.categoriesTotalCount / 10),
    taxesTotalPages: (state) => Math.ceil(state.taxesTotalCount / 25),
    productsTotalPages: (state) => Math.ceil(state.productsTotalCount / 25),
  },

  actions: {
    _api() {
      return useApi();
    },

    // ── Marcas ────────────────────────────────────────────────────────────
    async fetchBrands(page = 1) {
      this.brandsLoading = true;
      try {
        const res = await this._api().get('shop/brands/', { params: { page } });
        this.brands = res.data.results ?? res.data;
        this.brandsTotalCount = res.data.count ?? this.brands.length;
        this.brandsPagination = { next: res.data.next, previous: res.data.previous };
      } catch {
        this.error = 'Error al cargar marcas';
      } finally {
        this.brandsLoading = false;
      }
    },

    deleteBrand(id) {
      return this._mutate(() => this._api().delete(`dashboard/brands/${id}/`));
    },

    async bulkDeleteBrands(ids) {
      this.actionLoading = true;
      try {
        const results = await Promise.allSettled(ids.map((id) => this._api().delete(`dashboard/brands/${id}/`)));
        const failed = results.filter((r) => r.status === 'rejected').length;
        return { ok: true, failed, total: ids.length };
      } finally {
        this.actionLoading = false;
      }
    },

    // ── Categorias ────────────────────────────────────────────────────────
    async fetchCategories(page = 1) {
      this.categoriesLoading = true;
      try {
        const res = await this._api().get('shop/categories/', { params: { page } });
        this.categories = res.data.results ?? res.data;
        this.categoriesTotalCount = res.data.count ?? this.categories.length;
        this.categoriesPagination = { next: res.data.next, previous: res.data.previous };
      } catch {
        this.error = 'Error al cargar el listado de categorías';
      } finally {
        this.categoriesLoading = false;
      }
    },

    async fetchProductCategories() {
      try {
        const res = await this._api().get('dashboard/categories/');
        this.productCategories = res.data.results ?? res.data;
      } catch {
        this.error = 'Error al cargar categorías';
      }
    },

    deleteCategory(id) {
      return this._mutate(() => this._api().delete(`dashboard/categories/${id}/`));
    },

    // ── Impuestos ─────────────────────────────────────────────────────────
    async fetchTaxes(page = 1) {
      this.taxesLoading = true;
      try {
        const res = await this._api().get('shop/taxes/', { params: { page } });
        this.taxes = res.data.results ?? res.data;
        this.taxesTotalCount = res.data.count ?? this.taxes.length;
        this.taxesPagination = { next: res.data.next, previous: res.data.previous };
      } catch {
        this.error = 'Error al cargar impuestos';
      } finally {
        this.taxesLoading = false;
      }
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

    createTax(payload) {
      return this._mutate(() => this._api().post('dashboard/taxes/', payload));
    },

    updateTax(id, payload) {
      return this._mutate(() => this._api().patch(`dashboard/taxes/${id}/`, payload));
    },

    deleteTax(id) {
      return this._mutate(() => this._api().delete(`dashboard/taxes/${id}/`));
    },

    // ── Productos ─────────────────────────────────────────────────────────
    async fetchProducts(params = {}) {
      this.productsLoading = true;
      try {
        const res = await this._api().get('dashboard/products/', { params });
        this.products = res.data.results ?? res.data;
        this.productsTotalCount = res.data.count ?? this.products.length;
        this.productsPagination = { next: res.data.next, previous: res.data.previous };
      } catch {
        this.error = 'Error al cargar el catálogo de productos';
      } finally {
        this.productsLoading = false;
      }
    },

    async patchProductInline(uuid, payload) {
      try {
        const { data } = await this._api().patch(`dashboard/products/${uuid}/`, payload);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err };
      }
    },

    deleteProduct(uuid) {
      return this._mutate(() => this._api().delete(`dashboard/products/${uuid}/`));
    },

    async createProduct(payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().post('dashboard/products/', payload);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err };
      } finally {
        this.actionLoading = false;
      }
    },

    async updateProduct(uuid, payload) {
      this.actionLoading = true;
      try {
        const { data } = await this._api().patch(`dashboard/products/${uuid}/`, payload);
        return { ok: true, data };
      } catch (err) {
        return { ok: false, error: err };
      } finally {
        this.actionLoading = false;
      }
    },

    async fetchProductBrands() {
      try {
        const res = await this._api().get('dashboard/brands/');
        this.productBrands = res.data.results ?? res.data;
      } catch {
        this.error = 'Error al cargar marcas';
      }
    },

    async fetchActiveTaxes() {
      try {
        const res = await this._api().get('dashboard/taxes/');
        this.activeTaxes = (res.data.results ?? res.data).filter((t) => t.is_active);
      } catch {
        this.error = 'Error al cargar impuestos';
      }
    },

    // ── Variantes de producto ─────────────────────────────────────────────
    async fetchVariants(productUuid) {
      this.variantsLoading = true;
      try {
        const res = await this._api().get(`dashboard/products/${productUuid}/variants/`);
        this.variants = res.data.results ?? res.data;
      } catch {
        this.error = 'Error al cargar variantes';
      } finally {
        this.variantsLoading = false;
      }
    },

    createVariant(productUuid, payload) {
      return this._mutate(() => this._api().post(`dashboard/products/${productUuid}/variants/create/`, payload));
    },

    updateVariant(productUuid, variantUuid, payload) {
      return this._mutate(() => this._api().patch(`dashboard/products/${productUuid}/variants/${variantUuid}/`, payload));
    },

    deleteVariant(productUuid, variantUuid) {
      return this._mutate(() => this._api().delete(`dashboard/products/${productUuid}/variants/${variantUuid}/delete/`));
    },

    // ── Reglas de costo ────────────────────────────────────────────────────
    async fetchCostRules() {
      try {
        const res = await this._api().get('dashboard/shop-cost-rules/');
        this.costRules = res.data.results ?? res.data;
      } catch {
        this.error = 'Error al cargar reglas de costo';
      }
    },

    createCostRule(payload) {
      return this._mutate(() => this._api().post('dashboard/shop-cost-rules/', payload));
    },

    toggleCostRule(rule) {
      return this._mutate(() => (
        rule.is_active
          ? this._api().post(`dashboard/shop-cost-rules/${rule.uuid}/deactivate/`)
          : this._api().patch(`dashboard/shop-cost-rules/${rule.uuid}/update/`, { is_active: true })
      ));
    },

    assignCostRule(ruleUuid, variantUuid) {
      return this._mutate(() => this._api().post(`dashboard/shop-cost-rules/${ruleUuid}/assign/`, { variant_uuid: variantUuid }));
    },

    // ── Imagenes de producto ───────────────────────────────────────────────
    async fetchProductImages(productUuid) {
      this.imagesLoading = true;
      try {
        const res = await this._api().get(`dashboard/products/${productUuid}/`);
        this.productImages = res.data.images || [];
      } catch {
        this.error = 'Error al cargar imagenes';
      } finally {
        this.imagesLoading = false;
      }
    },

    uploadProductImage(productUuid, formData) {
      return this._mutate(() => this._api().post(`dashboard/products/${productUuid}/add_image/`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      }));
    },

    deleteProductImage(productUuid, imgUuid) {
      return this._mutate(() => this._api().delete(`dashboard/products/${productUuid}/delete_image/${imgUuid}/`));
    },

    setPrimaryImage(productUuid, imgUuid) {
      return this._mutate(() => this._api().post(`dashboard/products/${productUuid}/set_primary/${imgUuid}/`));
    },
  },
});
