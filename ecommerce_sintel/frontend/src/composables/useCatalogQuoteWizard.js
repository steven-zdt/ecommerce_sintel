import { ref, reactive, computed } from 'vue';
import useApi from '@/composables/useApi';
import { shopService } from '@/services/shop/shopService';
import { servicesService } from '@/services/technical_services/servicesService';
import { quotesService } from '@/services/quotes/quotesService';

const blankApplicant = () => ({
  client_name: '', client_email: '', notes: '',
  valid_until: (() => {
    const d = new Date();
    d.setDate(d.getDate() + 15);
    return d.toISOString().slice(0, 10);
  })(),
});

let cartKeySeq = 0;

function daysBetween(start, end) {
  if (!start || !end) return 1;
  const ms = new Date(end) - new Date(start);
  return Math.max(Math.round(ms / (1000 * 60 * 60 * 24)), 1);
}

/**
 * useCatalogQuoteWizard — Cotizacion de Catalogo: el cliente elige productos
 * (shop), equipos en renta (renting) y/o servicios tecnicos (technical_services)
 * ya publicados, ve un precio estimado al instante y envia la solicitud.
 * Publica/anonima. El backend recalcula todo con precios reales al crear
 * (QuotationBuilder.create_quotation) — el frontend nunca envia un total,
 * solo variant_id/quantity/fechas.
 */
export function useCatalogQuoteWizard() {
  const api = useApi();

  const step = ref(0);
  const steps = ['Catálogo', 'Solicitante', 'Resumen'];

  const products = ref([]);
  const equipment = ref([]);
  const services = ref([]);
  const loadingCatalog = reactive({ products: false, equipment: false, services: false });
  const catalogLoaded = reactive({ products: false, equipment: false, services: false });

  const cart = reactive([]);
  const applicant = reactive(blankApplicant());

  const submitting = ref(false);
  const error = ref('');
  const createdQuotation = ref(null);

  async function fetchProducts() {
    if (catalogLoaded.products) return;
    loadingCatalog.products = true;
    try {
      const data = await shopService.list();
      products.value = (data.results ?? data).filter((p) => p.is_active !== false);
      catalogLoaded.products = true;
    } catch {
      error.value = 'No pudimos cargar el catálogo de productos.';
    } finally {
      loadingCatalog.products = false;
    }
  }

  async function fetchEquipment() {
    if (catalogLoaded.equipment) return;
    loadingCatalog.equipment = true;
    try {
      const { data } = await api.get('renting/equipment/');
      equipment.value = (data.results ?? data).filter((e) => e.is_active !== false);
      catalogLoaded.equipment = true;
    } catch {
      error.value = 'No pudimos cargar el catálogo de equipos en renta.';
    } finally {
      loadingCatalog.equipment = false;
    }
  }

  async function fetchServices() {
    if (catalogLoaded.services) return;
    loadingCatalog.services = true;
    try {
      const data = await servicesService.list();
      services.value = (data.results ?? data).filter((s) => s.is_active !== false);
      catalogLoaded.services = true;
    } catch {
      error.value = 'No pudimos cargar el catálogo de servicios.';
    } finally {
      loadingCatalog.services = false;
    }
  }

  function primaryImage(item) {
    const img = item.images?.find((i) => i.is_primary) || item.images?.[0];
    return img?.image || null;
  }

  function defaultVariant(item) {
    return item.variants?.find((v) => v.is_default) || item.variants?.[0] || null;
  }

  function addProduct(product, variant, quantity = 1) {
    const existing = cart.find((c) => c.kind === 'product' && c.variantId === variant.id);
    if (existing) {
      existing.quantity += quantity;
      return;
    }
    const unitPrice = parseFloat(variant.discounted_price || variant.effective_price || variant.price || 0);
    cart.push({
      key: `product-${variant.id}-${cartKeySeq++}`,
      kind: 'product',
      variantId: variant.id,
      variantUuid: variant.uuid,
      name: `${product.name} (${variant.sku})`,
      sku: variant.sku,
      imageUrl: primaryImage(product),
      quantity,
      unitPrice,
    });
  }

  function addService(service, variant) {
    const existing = cart.find((c) => c.kind === 'service' && c.variantId === variant.id);
    if (existing) {
      existing.quantity += 1;
      return;
    }
    const unitPrice = parseFloat(variant.calculated_price ?? variant.fixed_price ?? 0);
    cart.push({
      key: `service-${variant.id}-${cartKeySeq++}`,
      kind: 'service',
      variantId: variant.id,
      variantUuid: variant.uuid,
      name: `${service.name} (${variant.sku})`,
      sku: variant.sku,
      imageUrl: primaryImage(service),
      quantity: 1,
      unitPrice,
    });
  }

  function addEquipment(item, variant, rentStartDate, rentEndDate) {
    const existing = cart.find((c) =>
      c.kind === 'rental' && c.variantId === variant.id &&
      c.rentStartDate === rentStartDate && c.rentEndDate === rentEndDate,
    );
    if (existing) {
      existing.quantity += 1;
      return;
    }
    const days = daysBetween(rentStartDate, rentEndDate);
    const pricePerDay = parseFloat(variant.rental_price_per_day || 0);
    cart.push({
      key: `rental-${variant.id}-${cartKeySeq++}`,
      kind: 'rental',
      variantId: variant.id,
      variantUuid: variant.uuid,
      name: `${item.name} (${variant.sku})`,
      sku: variant.sku,
      imageUrl: primaryImage(item),
      quantity: 1,
      unitPrice: pricePerDay * days,
      rentStartDate,
      rentEndDate,
      days,
    });
  }

  function removeFromCart(key) {
    const idx = cart.findIndex((c) => c.key === key);
    if (idx !== -1) cart.splice(idx, 1);
  }

  function updateQuantity(key, quantity) {
    const item = cart.find((c) => c.key === key);
    if (item && quantity >= 1) item.quantity = quantity;
  }

  const cartCount = computed(() => cart.reduce((sum, c) => sum + c.quantity, 0));
  const cartTotal = computed(() => cart.reduce((sum, c) => sum + c.unitPrice * c.quantity, 0));

  function findProductByUuid(uuid) {
    return products.value.find((p) => p.uuid === uuid) || null;
  }

  function findEquipmentByUuid(uuid) {
    return equipment.value.find((e) => e.uuid === uuid) || null;
  }

  function validateApplicant() {
    return !!(applicant.client_name && applicant.client_email && applicant.valid_until);
  }

  function buildPayload() {
    const product_items = [];
    const service_items = [];
    const rental_items = [];
    for (const item of cart) {
      if (item.kind === 'product') {
        product_items.push({ variant_id: item.variantId, quantity: item.quantity });
      } else if (item.kind === 'service') {
        for (let i = 0; i < item.quantity; i++) service_items.push(item.variantId);
      } else if (item.kind === 'rental') {
        for (let i = 0; i < item.quantity; i++) {
          rental_items.push({
            variant_id: item.variantId,
            rent_start_date: item.rentStartDate,
            rent_end_date: item.rentEndDate,
          });
        }
      }
    }
    return {
      client_name: applicant.client_name,
      client_email: applicant.client_email,
      valid_until: applicant.valid_until,
      notes: applicant.notes,
      product_items, service_items, rental_items,
    };
  }

  async function submitQuotation() {
    if (!cart.length) {
      error.value = 'Agrega al menos un producto, equipo o servicio.';
      return false;
    }
    submitting.value = true;
    error.value = '';
    try {
      const data = await quotesService.createFromCatalog(buildPayload());
      createdQuotation.value = data;
      cart.splice(0, cart.length);
      return true;
    } catch (e) {
      const fieldErrors = e.response?.data;
      const firstFieldError = fieldErrors && typeof fieldErrors === 'object'
        ? Object.values(fieldErrors).flat()[0]
        : null;
      error.value = fieldErrors?.detail || firstFieldError || 'No pudimos enviar tu solicitud. Intenta de nuevo.';
      return false;
    } finally {
      submitting.value = false;
    }
  }

  function clear() {
    step.value = 0;
    cart.splice(0, cart.length);
    Object.assign(applicant, blankApplicant());
    createdQuotation.value = null;
    error.value = '';
  }

  return {
    step, steps,
    products, equipment, services, loadingCatalog,
    cart, applicant,
    submitting, error, createdQuotation,
    fetchProducts, fetchEquipment, fetchServices,
    primaryImage, defaultVariant,
    addProduct, addService, addEquipment,
    removeFromCart, updateQuantity,
    cartCount, cartTotal,
    findProductByUuid, findEquipmentByUuid,
    validateApplicant, buildPayload, submitQuotation, clear,
  };
}
