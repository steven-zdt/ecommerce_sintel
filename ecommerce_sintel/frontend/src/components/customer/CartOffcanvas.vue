<template>
  <SintelOffcanvas
    :modelValue="modelValue"
    title="Mi carrito"
    :subtitle="cartStore.isEmpty ? 'Tu carrito esta vacio' : `${cartStore.itemCount} producto(s)`"
    width="440px"
    @update:modelValue="$emit('update:modelValue', $event)"
  >
    <!-- Cargando -->
    <div v-if="cartStore.loading" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
    </div>

    <!-- Sin auth -->
    <div v-else-if="!authStore.isAuthenticated" class="text-center py-5">
      <i class="bi bi-bag display-4 text-muted"></i>
      <p class="mt-3 text-muted">Inicia sesion para ver tu carrito</p>
      <RouterLink to="/login" class="btn btn-primary mt-2" @click="$emit('update:modelValue', false)">
        Iniciar sesion
      </RouterLink>
    </div>

    <!-- Carrito vacio -->
    <div v-else-if="cartStore.isEmpty" class="text-center py-5">
      <i class="bi bi-bag display-4 text-muted"></i>
      <p class="mt-3 text-muted small">Aun no tienes productos en tu carrito</p>
      <RouterLink to="/tienda" class="btn btn-primary btn-sm mt-2" @click="$emit('update:modelValue', false)">
        <i class="bi bi-shop me-1"></i>Ir a la tienda
      </RouterLink>
    </div>

    <!-- Lista de items -->
    <div v-else>
      <div
        v-for="item in cartStore.items"
        :key="item.uuid"
        class="cart-item d-flex gap-3 align-items-start mb-3 p-3 rounded-3 border"
      >
        <!-- Icono segun tipo -->
        <div class="cart-item-img bg-light rounded-2 d-flex align-items-center justify-content-center flex-shrink-0">
          <i :class="['bi', item.item_type === 'service' ? 'bi-tools' : 'bi-box-seam', 'text-muted']"></i>
        </div>

        <!-- Info -->
        <div class="flex-grow-1 min-width-0">
          <p class="fw-bold small mb-0 text-truncate">{{ item.product_name || 'Producto' }}</p>
          <p class="text-muted mb-1" style="font-size:.75rem">{{ item.variant_sku }}</p>

          <!-- Precio unitario con IVA -->
          <p class="text-muted mb-2" style="font-size:.75rem">
            ${{ fmt(item.unit_price_with_tax) }} c/u · IVA incluido
          </p>

          <!-- Controles de cantidad + subtotal -->
          <div class="d-flex align-items-center justify-content-between">
            <!-- +/- -->
            <div class="qty-controls d-flex align-items-center gap-1">
              <button
                class="btn btn-outline-secondary btn-sm qty-btn"
                @click="changeQty(item, item.quantity - 1)"
                :disabled="updating === item.uuid || item.quantity <= 1"
              >
                <i class="bi bi-dash"></i>
              </button>
              <span class="qty-badge">{{ item.quantity }}</span>
              <button
                class="btn btn-outline-secondary btn-sm qty-btn"
                @click="changeQty(item, item.quantity + 1)"
                :disabled="updating === item.uuid"
              >
                <span v-if="updating === item.uuid" class="spinner-border spinner-border-sm" style="width:.7rem;height:.7rem"></span>
                <i v-else class="bi bi-plus"></i>
              </button>
            </div>

            <!-- Final price + eliminar -->
            <div class="d-flex align-items-center gap-2">
              <span class="small fw-bold text-primary">${{ fmt(item.final_price) }}</span>
              <button
                class="btn btn-link btn-sm p-0 text-danger"
                @click="removeItem(item.uuid)"
                :disabled="removing === item.uuid"
                title="Eliminar"
              >
                <span v-if="removing === item.uuid" class="spinner-border spinner-border-sm"></span>
                <i v-else class="bi bi-trash3"></i>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Footer con total -->
    <template #footer>
      <div v-if="authStore.isAuthenticated && !cartStore.isEmpty" class="w-100">
        <div class="d-flex justify-content-between mb-1">
          <span class="small text-muted">Total (IVA incluido)</span>
          <span class="fw-bold text-primary fs-6">${{ fmt(cartStore.total) }}</span>
        </div>
        <p class="text-muted mb-3" style="font-size:.72rem">Los impuestos se muestran en el resumen de pago</p>
        <div class="d-flex gap-2">
          <RouterLink
            to="/checkout"
            class="btn btn-primary flex-grow-1"
            @click="$emit('update:modelValue', false)"
          >
            <i class="bi bi-credit-card me-1"></i>Finalizar compra
          </RouterLink>
          <button
            class="btn btn-light border"
            @click="handleClearCart"
            :disabled="clearing"
            title="Vaciar carrito"
          >
            <span v-if="clearing" class="spinner-border spinner-border-sm"></span>
            <i v-else class="bi bi-trash"></i>
          </button>
        </div>
      </div>
    </template>
  </SintelOffcanvas>
</template>

<script setup>
import { ref } from 'vue';
import { useAuthStore } from '@/store/auth';
import { useCartStore } from '@/store/cart';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import SintelOffcanvas from '@/components/ui/SintelOffcanvas.vue';
import { formatCOP } from '@/utils/money';

const props = defineProps({
  modelValue: { type: Boolean, required: true },
});
defineEmits(['update:modelValue']);

const authStore = useAuthStore();
const cartStore = useCartStore();
const toast = useToast();
const { handleError } = useErrorHandler();
const removing = ref(null);
const updating = ref(null);
const clearing = ref(false);

async function removeItem(uuid) {
  removing.value = uuid;
  try {
    await cartStore.removeItem(uuid);
    toast.success('Producto eliminado del carrito');
  } catch {
    toast.error('No se pudo eliminar el producto');
  } finally {
    removing.value = null;
  }
}

async function changeQty(item, newQty) {
  if (newQty < 1) return;
  updating.value = item.uuid;
  try {
    const variantUuid = item.item_type === 'product' ? item.variant_uuid : null;
    const serviceUuid = item.item_type === 'service' ? item.variant_uuid : null;
    await cartStore.updateQuantity(variantUuid, serviceUuid, newQty);
  } catch (e) {
    handleError(e, 'No se pudo actualizar la cantidad');
  } finally {
    updating.value = null;
  }
}

async function handleClearCart() {
  clearing.value = true;
  try {
    await cartStore.clearCart();
    toast.info('Carrito vaciado');
  } catch {
    toast.error('Error al vaciar el carrito');
  } finally {
    clearing.value = false;
  }
}

const fmt = (val) => formatCOP(val);
</script>

<style scoped>
.cart-item-img {
  width: 50px;
  height: 50px;
  font-size: 1.1rem;
  flex-shrink: 0;
}
.min-width-0 { min-width: 0; }

.qty-controls { gap: 4px; }
.qty-btn {
  width: 26px;
  height: 26px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  font-size: .75rem;
}
.qty-badge {
  min-width: 28px;
  text-align: center;
  font-size: .82rem;
  font-weight: 600;
}
</style>
