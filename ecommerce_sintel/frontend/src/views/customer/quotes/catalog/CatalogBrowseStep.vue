<template>
  <div>
    <h1 class="step-title">Elige del catálogo</h1>
    <p class="step-subtitle">Selecciona productos, equipos en renta y/o servicios técnicos.</p>

    <div class="browse-layout">
      <div class="browse-main">
        <ul class="nav nav-pills gap-2 mb-3 browse-tabs">
          <li class="nav-item" v-for="t in tabs" :key="t.key">
            <button class="nav-link tab-pill" :class="{ active: activeTab === t.key }" @click="activeTab = t.key">
              <i :class="['bi', t.icon, 'me-1']"></i>{{ t.label }}
            </button>
          </li>
        </ul>

        <input v-model="search" type="text" class="form-control mb-3" placeholder="Buscar..." />

        <div v-if="loading" class="text-center py-5"><div class="spinner-border text-success"></div></div>
        <div v-else-if="!filteredItems.length" class="text-center py-5 text-muted">No hay resultados.</div>

        <div v-else class="item-grid">
          <div v-for="item in filteredItems" :key="item.uuid" class="item-card">
            <div class="item-img">
              <img v-if="wizard.primaryImage(item)" :src="wizard.primaryImage(item)" :alt="item.name" />
              <i v-else :class="['bi', tabIcon]"></i>
            </div>
            <div class="item-body">
              <p class="item-name">{{ item.name }}</p>
              <p class="item-price">
                ${{ fmt(displayPrice(item)) }}<span v-if="activeTab === 'rentals'" class="item-price-unit">/día</span>
              </p>

              <template v-if="activeTab === 'rentals'">
                <div class="row g-2 mb-2">
                  <div class="col-6">
                    <label class="form-label small mb-1">Desde</label>
                    <input type="date" class="form-control form-control-sm" v-model="dateState(item.uuid).start" :min="today" />
                  </div>
                  <div class="col-6">
                    <label class="form-label small mb-1">Hasta</label>
                    <input type="date" class="form-control form-control-sm" v-model="dateState(item.uuid).end" :min="dateState(item.uuid).start || today" />
                  </div>
                </div>
              </template>

              <template v-if="activeTab === 'products'">
                <div class="qty-controls mb-2">
                  <button class="qty-btn" @click="decQty(item.uuid)"><i class="bi bi-dash"></i></button>
                  <span class="qty-badge">{{ getQty(item.uuid) }}</span>
                  <button class="qty-btn" @click="incQty(item.uuid)"><i class="bi bi-plus"></i></button>
                </div>
              </template>

              <button class="btn-add" :disabled="!canAdd(item)" @click="handleAdd(item)">
                <i class="bi bi-plus-lg me-1"></i>Agregar
              </button>
              <p v-if="activeTab === 'products' && !hasStock(item)" class="text-danger small mt-1 mb-0">Sin stock</p>
            </div>
          </div>
        </div>
      </div>

      <aside class="browse-cart">
        <h3 class="cart-title"><i class="bi bi-cart3 me-2"></i>Tu selección ({{ wizard.cartCount.value }})</h3>
        <div v-if="!wizard.cart.length" class="cart-empty">
          <i class="bi bi-cart-x d-block mb-2"></i>
          <p class="mb-0 small">Aún no agregas nada.</p>
        </div>
        <div v-else class="cart-list">
          <div v-for="c in wizard.cart" :key="c.key" class="cart-line">
            <div class="cart-line-info">
              <p class="cart-line-name">{{ c.name }}</p>
              <p v-if="c.kind === 'rental'" class="cart-line-meta">{{ c.rentStartDate }} → {{ c.rentEndDate }} ({{ c.days }} día{{ c.days > 1 ? 's' : '' }})</p>
              <p class="cart-line-meta">${{ fmt(c.unitPrice) }} c/u</p>
            </div>
            <div class="cart-line-actions">
              <div class="qty-controls">
                <button class="qty-btn" @click="wizard.updateQuantity(c.key, c.quantity - 1)" :disabled="c.quantity <= 1"><i class="bi bi-dash"></i></button>
                <span class="qty-badge">{{ c.quantity }}</span>
                <button class="qty-btn" @click="wizard.updateQuantity(c.key, c.quantity + 1)"><i class="bi bi-plus"></i></button>
              </div>
              <span class="cart-line-subtotal">${{ fmt(c.unitPrice * c.quantity) }}</span>
              <button class="btn-remove" @click="wizard.removeFromCart(c.key)" title="Quitar"><i class="bi bi-trash3"></i></button>
            </div>
          </div>
        </div>
        <div v-if="wizard.cart.length" class="cart-total">
          <span>Total estimado</span>
          <span class="cart-total-amount">${{ fmt(wizard.cartTotal.value) }}</span>
        </div>
        <p v-if="wizard.cart.length" class="cart-hint">El precio final (con impuestos) se calcula al enviar la solicitud.</p>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue';

const props = defineProps({ wizard: { type: Object, required: true } });

const tabs = [
  { key: 'products', label: 'Productos', icon: 'bi-box-seam' },
  { key: 'rentals', label: 'Renta', icon: 'bi-tools' },
  { key: 'services', label: 'Servicios', icon: 'bi-wrench-adjustable' },
];

const activeTab = ref('products');
const search = ref('');

const today = new Date().toISOString().slice(0, 10);
const rentalDates = reactive({});
const productQty = reactive({});

function dateState(uuid) {
  if (!rentalDates[uuid]) {
    const end = new Date();
    end.setDate(end.getDate() + 1);
    rentalDates[uuid] = { start: today, end: end.toISOString().slice(0, 10) };
  }
  return rentalDates[uuid];
}

function getQty(uuid) {
  if (!(uuid in productQty)) productQty[uuid] = 1;
  return productQty[uuid];
}

function incQty(uuid) {
  productQty[uuid] = getQty(uuid) + 1;
}

function decQty(uuid) {
  productQty[uuid] = Math.max(1, getQty(uuid) - 1);
}

const catalogKey = computed(() => (activeTab.value === 'rentals' ? 'equipment' : activeTab.value));
const loading = computed(() => props.wizard.loadingCatalog[catalogKey.value]);
const tabIcon = computed(() => tabs.find((t) => t.key === activeTab.value)?.icon || 'bi-box-seam');

const rawList = computed(() => {
  if (activeTab.value === 'products') return props.wizard.products.value;
  if (activeTab.value === 'rentals') return props.wizard.equipment.value;
  return props.wizard.services.value;
});

const filteredItems = computed(() => {
  const q = search.value.trim().toLowerCase();
  if (!q) return rawList.value;
  return rawList.value.filter((i) => i.name.toLowerCase().includes(q));
});

function displayPrice(item) {
  const variant = props.wizard.defaultVariant(item);
  if (!variant) return 0;
  if (activeTab.value === 'products') return parseFloat(variant.discounted_price || variant.effective_price || variant.price || 0);
  if (activeTab.value === 'rentals') return parseFloat(variant.rental_price_per_day || 0);
  return parseFloat(variant.calculated_price ?? variant.fixed_price ?? 0);
}

function hasStock(item) {
  const variant = props.wizard.defaultVariant(item);
  return (variant?.stock ?? 0) > 0;
}

function canAdd(item) {
  const variant = props.wizard.defaultVariant(item);
  if (!variant) return false;
  if (activeTab.value === 'rentals') {
    const d = dateState(item.uuid);
    return !!(d.start && d.end && d.end > d.start);
  }
  if (activeTab.value === 'products') return hasStock(item);
  return true;
}

function handleAdd(item) {
  const variant = props.wizard.defaultVariant(item);
  if (!variant) return;
  if (activeTab.value === 'products') {
    props.wizard.addProduct(item, variant, getQty(item.uuid));
    productQty[item.uuid] = 1;
  } else if (activeTab.value === 'rentals') {
    const d = dateState(item.uuid);
    props.wizard.addEquipment(item, variant, d.start, d.end);
  } else {
    props.wizard.addService(item, variant);
  }
}

const fmt = (val) => new Intl.NumberFormat('es-CO').format(parseFloat(val) || 0);
</script>

<style scoped>
.step-title { font-size: clamp(1.8rem, 4vw, 2.6rem); font-weight: 850; letter-spacing: -0.03em; margin-bottom: 0.4rem; }
.step-subtitle { color: #64748b; margin-bottom: 1.6rem; }

.browse-layout { display: grid; grid-template-columns: 1fr 320px; gap: 1.6rem; align-items: start; }
@media (max-width: 860px) { .browse-layout { grid-template-columns: 1fr; } }

.tab-pill {
  border-radius: 999px !important; border: 1.5px solid #e2e8f0 !important;
  color: #475569 !important; font-size: 0.85rem;
}
.tab-pill.active { background: #16a34a !important; border-color: #16a34a !important; color: #fff !important; }

.item-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(210px, 1fr)); gap: 1rem; }
.item-card { border: 1px solid #eef2f7; border-radius: 16px; overflow: hidden; background: #fff; display: flex; flex-direction: column; }
.item-img { height: 120px; background: #f8fafc; display: flex; align-items: center; justify-content: center; }
.item-img img { width: 100%; height: 100%; object-fit: cover; }
.item-img i { font-size: 2rem; color: #cbd5e1; }
.item-body { padding: 0.9rem; display: flex; flex-direction: column; gap: 0.1rem; }
.item-name { font-weight: 700; font-size: 0.88rem; margin-bottom: 0.2rem; min-height: 2.4em; }
.item-price { color: #16a34a; font-weight: 800; font-size: 0.95rem; margin-bottom: 0.5rem; }
.item-price-unit { font-size: 0.7rem; color: #94a3b8; font-weight: 600; }

.btn-add {
  border: 0; border-radius: 10px; background: #16a34a; color: #fff; font-weight: 700;
  font-size: 0.82rem; padding: 0.5rem; cursor: pointer;
}
.btn-add:disabled { opacity: 0.4; cursor: not-allowed; }

.qty-controls { display: flex; align-items: center; gap: 6px; }
.qty-btn {
  width: 26px; height: 26px; border-radius: 6px; border: 1px solid #e2e8f0; background: #fff;
  display: flex; align-items: center; justify-content: center; font-size: 0.75rem; cursor: pointer;
}
.qty-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.qty-badge { min-width: 22px; text-align: center; font-weight: 700; font-size: 0.85rem; }

.browse-cart {
  background: #f8fafc; border-radius: 18px; padding: 1.2rem; position: sticky; top: 1rem;
  border: 1px solid #eef2f7; max-height: 80vh; overflow-y: auto;
}
.cart-title { font-size: 0.95rem; font-weight: 800; margin-bottom: 1rem; }
.cart-empty { text-align: center; color: #94a3b8; padding: 1.5rem 0; }
.cart-empty i { font-size: 1.8rem; }
.cart-line { border-bottom: 1px solid #e2e8f0; padding: 0.7rem 0; }
.cart-line:last-child { border-bottom: none; }
.cart-line-name { font-weight: 700; font-size: 0.82rem; margin-bottom: 0.15rem; }
.cart-line-meta { font-size: 0.72rem; color: #94a3b8; margin-bottom: 0.1rem; }
.cart-line-actions { display: flex; align-items: center; justify-content: space-between; margin-top: 0.4rem; gap: 0.5rem; }
.cart-line-subtotal { font-weight: 800; font-size: 0.82rem; color: #16a34a; }
.btn-remove { border: 0; background: none; color: #ef4444; cursor: pointer; padding: 0.2rem; }
.cart-total { display: flex; justify-content: space-between; align-items: center; margin-top: 1rem; padding-top: 0.8rem; border-top: 2px solid #e2e8f0; font-weight: 700; font-size: 0.85rem; }
.cart-total-amount { color: #16a34a; font-size: 1.05rem; }
.cart-hint { font-size: 0.68rem; color: #94a3b8; margin-top: 0.5rem; margin-bottom: 0; }
</style>
