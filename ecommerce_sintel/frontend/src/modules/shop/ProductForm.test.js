import { beforeEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';
import { ref } from 'vue';
import ProductForm from './ProductForm.vue';

const createProduct = vi.fn();
const store = {
  _refs: {
    productCategories: ref([]), productBrands: ref([]), variants: ref([]),
    productImages: ref([]), costRules: ref([]), actionLoading: ref(false),
  },
  createProduct,
  updateProduct: vi.fn(),
  fetchProductCategories: vi.fn(),
  fetchProductBrands: vi.fn(),
  fetchActiveTaxes: vi.fn(),
};

vi.mock('pinia', () => ({ storeToRefs: (target) => target._refs }));
vi.mock('@/store/shopAdmin', () => ({ useShopAdminStore: () => store }));
vi.mock('@/composables/useToast', () => ({ useToast: () => ({ success: vi.fn(), error: vi.fn() }) }));
vi.mock('@/composables/useErrorHandler', () => ({ useErrorHandler: () => ({ handleError: vi.fn() }) }));

const stubs = {
  GeneralTab: { template: '<button data-test="submit-product" @click="$emit(\'submit\')">crear</button>' },
  SeoTab: { template: '<div />' },
  VariantsTab: { props: ['productUuid'], template: '<div data-test="variants">{{ productUuid }}</div>' },
  CostosTab: { template: '<div />' },
  ImagenesTab: { template: '<div />' },
};

describe('ProductForm create → edit', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    store._refs.variants.value = [];
    store._refs.productImages.value = [];
    store._refs.costRules.value = [];
  });

  it('crea el producto y abre Variantes sin cerrar el formulario', async () => {
    createProduct.mockResolvedValue({
      ok: true,
      data: { uuid: 'producto-creado-uuid', name: 'Producto P2-2' },
    });
    const wrapper = mount(ProductForm, {
      props: { mode: 'create' },
      global: { stubs },
    });

    await wrapper.get('[data-test="submit-product"]').trigger('click');
    await flushPromises();

    expect(createProduct).toHaveBeenCalledOnce();
    expect(wrapper.text()).toContain('Producto creado.');
    expect(wrapper.get('[data-test="variants"]').text()).toBe('producto-creado-uuid');
    expect(wrapper.findAll('.nav-link').some((tab) => tab.text().includes('Variantes'))).toBe(true);
  });
});
