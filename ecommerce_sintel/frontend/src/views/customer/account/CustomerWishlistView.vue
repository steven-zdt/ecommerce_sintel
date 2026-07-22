<template>
  <CustomerAccountShell>
    <CustomerPageHeader title="Lista de deseos" subtitle="Productos que guardaste para despues." />

    <CustomerSkeleton v-if="loading" layout="grid" :count="4" height="240px" />
    <CustomerErrorState v-else-if="loadError" @retry="fetchWishlist" />

    <CustomerEmptyState
      v-else-if="items.length === 0"
      icon="bi-heart"
      title="Tu lista de deseos esta vacia"
      description="Agrega productos desde la tienda para guardarlos aqui."
    >
      <template #action>
        <RouterLink to="/tienda" class="btn btn-primary">Explorar tienda</RouterLink>
      </template>
    </CustomerEmptyState>

    <div v-else class="wishlist-grid">
      <CustomerCard v-for="item in items" :key="item.uuid" tag="div" class="wishlist-item">
        <div class="wishlist-image">
          <i class="bi bi-bag-heart"></i>
        </div>
        <div class="wishlist-body">
          <p class="item-name">{{ item.product_name }}</p>
          <p class="item-sku text-muted small">SKU: {{ item.sku }}</p>
          <p class="item-price">${{ fmt(item.price) }}</p>
        </div>

        <CustomerConfirmInline
          v-if="pendingRemove?.uuid === item.uuid"
          message="Eliminar este producto de tu lista de deseos?"
          :loading="removingId === item.uuid"
          @confirm="removeItem(item)"
          @cancel="pendingRemove = null"
        />
        <div v-else class="wishlist-actions">
          <RouterLink to="/tienda" class="btn btn-sm btn-outline-primary flex-grow-1">
            <i class="bi bi-bag me-1"></i>Ver producto
          </RouterLink>
          <CustomerButton variant="secondary" @click="addToCart(item)" :loading="addingId === item.uuid">
            <i class="bi bi-cart-plus"></i>
          </CustomerButton>
          <CustomerButton variant="icon" aria-label="Eliminar de la lista de deseos" @click="pendingRemove = item">
            <i class="bi bi-trash"></i>
          </CustomerButton>
        </div>
      </CustomerCard>
    </div>
  </CustomerAccountShell>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useCartStore } from '@/store/cart';
import CustomerAccountShell from '@/components/customer/account/CustomerAccountShell.vue';
import CustomerPageHeader from '@/components/customer/account/CustomerPageHeader.vue';
import CustomerCard from '@/components/customer/account/CustomerCard.vue';
import CustomerButton from '@/components/customer/account/CustomerButton.vue';
import CustomerConfirmInline from '@/components/customer/account/CustomerConfirmInline.vue';
import CustomerEmptyState from '@/components/customer/account/CustomerEmptyState.vue';
import CustomerErrorState from '@/components/customer/account/CustomerErrorState.vue';
import CustomerSkeleton from '@/components/customer/account/CustomerSkeleton.vue';

const api = useApi();
const toast = useToast();
const cartStore = useCartStore();

const loading = ref(true);
const loadError = ref(false);
const items = ref([]);
const removingId = ref(null);
const addingId = ref(null);
const pendingRemove = ref(null);

const fmt = (v) => new Intl.NumberFormat('es-CO').format(parseFloat(v) || 0);

async function fetchWishlist() {
  loading.value = true;
  loadError.value = false;
  try {
    const res = await api.get('cart/wishlist/');
    items.value = res.data.results ?? res.data ?? [];
  } catch {
    loadError.value = true;
    toast.error('Error al cargar la lista de deseos');
  } finally {
    loading.value = false;
  }
}

async function removeItem(item) {
  removingId.value = item.uuid;
  try {
    await api.delete(`cart/wishlist/${item.uuid}/`);
    items.value = items.value.filter(i => i.uuid !== item.uuid);
    toast.success('Eliminado de la lista de deseos');
  } catch {
    toast.error('Error al eliminar el producto');
  } finally {
    removingId.value = null;
    pendingRemove.value = null;
  }
}

async function addToCart(item) {
  addingId.value = item.uuid;
  try {
    await cartStore.addItem(item.variant_uuid, 1);
    toast.success('Agregado al carrito');
  } catch {
    toast.error('No se pudo agregar al carrito');
  } finally {
    addingId.value = null;
  }
}

onMounted(fetchWishlist);
</script>

<style scoped>
.wishlist-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;
}

.wishlist-item { padding: 0; overflow: hidden; }

.wishlist-image {
  height: 120px;
  background: var(--acc-accent-bg, #eff6ff);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 2.2rem;
  color: var(--acc-accent, #2563eb);
}

.wishlist-body { padding: 16px; flex: 1; }
.item-name { font-weight: 600; font-size: 0.9rem; color: var(--acc-text, #111827); margin-bottom: 4px; }
.item-sku { margin-bottom: 8px; }
.item-price { font-size: 1.1rem; font-weight: 700; color: var(--acc-accent, #2563eb); margin: 0; }

.wishlist-actions {
  padding: 12px 16px;
  border-top: 1px solid #f3f4f6;
  display: flex;
  gap: 8px;
}
</style>
