<template>
  <div class="ppc-card">
    <!-- Precio -->
    <div class="ppc-price-row">
      <span v-if="discountPct > 0" class="ppc-original">{{ originalPriceLabel }}</span>
      <span class="ppc-price">{{ priceLabel }}</span>
      <span v-if="discountPct > 0" class="ppc-discount-pill">-{{ discountPct }}%</span>
    </div>
    <p v-if="discountPct > 0 && savingsLabel" class="ppc-savings">
      <i class="bi bi-tag-fill me-1"></i>Ahorras {{ savingsLabel }}
    </p>
    <p class="ppc-vat-note"><i class="bi bi-info-circle me-1"></i>Precio incluye IVA</p>

    <div class="ppc-sep"></div>

    <!-- Disponibilidad / entrega / garantia -->
    <div class="ppc-info-rows">
      <div class="ppc-info-row">
        <span class="ppc-info-label"><i class="bi bi-box-seam"></i>Disponibilidad</span>
        <span class="ppc-info-value" :class="stockClass">{{ stockLabel }}</span>
      </div>
      <div v-if="deliveryLabel" class="ppc-info-row">
        <span class="ppc-info-label"><i class="bi bi-truck"></i>Entrega</span>
        <span class="ppc-info-value">{{ deliveryLabel }}</span>
      </div>
      <div class="ppc-info-row">
        <span class="ppc-info-label"><i class="bi bi-shield-check"></i>Garantia</span>
        <span class="ppc-info-value">Garantia del fabricante</span>
      </div>
    </div>

    <div class="ppc-sep"></div>

    <!-- Cantidad -->
    <div class="ppc-qty-row">
      <span class="ppc-info-label">Cantidad</span>
      <div class="ppc-qty-stepper">
        <button
          type="button"
          class="ppc-qty-btn"
          :disabled="quantity <= 1"
          aria-label="Disminuir cantidad"
          @click="$emit('update:quantity', Math.max(1, quantity - 1))"
        >
          <i class="bi bi-dash"></i>
        </button>
        <input
          class="ppc-qty-input"
          type="number"
          min="1"
          :max="maxQuantity || 1"
          :value="quantity"
          aria-label="Cantidad"
          @input="$emit('update:quantity', Math.min(maxQuantity || 1, Math.max(1, Number($event.target.value) || 1)))"
        >
        <button
          type="button"
          class="ppc-qty-btn"
          :disabled="quantity >= (maxQuantity || 1)"
          aria-label="Aumentar cantidad"
          @click="$emit('update:quantity', Math.min(maxQuantity || 1, quantity + 1))"
        >
          <i class="bi bi-plus"></i>
        </button>
      </div>
    </div>

    <!-- Acciones -- "Comprar ahora" domina (solido, ancho completo, arriba); "Agregar al
         carrito" se ve secundario (outline) junto al icon-button de wishlist. -->
    <div class="ppc-actions">
      <button
        type="button"
        class="ppc-btn ppc-btn-primary"
        :disabled="buyNowDisabled"
        @click="$emit('buy-now')"
      >
        <i class="bi bi-lightning-charge-fill me-2"></i>{{ buyNowLabel }}
      </button>

      <div class="ppc-actions-row">
        <button
          type="button"
          class="ppc-btn ppc-btn-secondary"
          :disabled="addingToCart || !hasStock"
          @click="$emit('add-to-cart')"
        >
          <span v-if="addingToCart" class="spinner-border spinner-border-sm me-2"></span>
          <i v-else class="bi bi-bag-check-fill me-2"></i>
          {{ hasStock ? 'Agregar al carrito' : 'Agotado' }}
        </button>
        <button
          type="button"
          class="ppc-icon-btn"
          :class="{ 'is-active': isWishlisted }"
          :disabled="wishlistLoading"
          :aria-label="isWishlisted ? 'Quitar de lista de deseos' : 'Agregar a lista de deseos'"
          :title="isWishlisted ? 'Quitar de lista de deseos' : 'Agregar a lista de deseos'"
          @click="$emit('toggle-wishlist')"
        >
          <span v-if="wishlistLoading" class="spinner-border spinner-border-sm"></span>
          <i v-else :class="['bi', isWishlisted ? 'bi-heart-fill' : 'bi-heart']"></i>
        </button>
      </div>

      <RouterLink v-if="productUuid" :to="`/cotizar?product=${productUuid}`" class="ppc-quote-link">
        <i class="bi bi-file-earmark-text me-2"></i>Solicitar cotizacion
      </RouterLink>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  priceLabel: { type: String, required: true },
  originalPriceLabel: { type: String, default: '' },
  discountPct: { type: Number, default: 0 },
  savingsLabel: { type: String, default: '' },
  stock: { type: Number, default: 0 },
  deliveryLabel: { type: String, default: '' },
  quantity: { type: Number, default: 1 },
  maxQuantity: { type: Number, default: 1 },
  addingToCart: { type: Boolean, default: false },
  wishlistLoading: { type: Boolean, default: false },
  isWishlisted: { type: Boolean, default: false },
  buyNowLabel: { type: String, default: 'Comprar ahora' },
  buyNowDisabled: { type: Boolean, default: false },
  productUuid: { type: String, default: '' },
});

defineEmits(['add-to-cart', 'buy-now', 'toggle-wishlist', 'update:quantity']);

const hasStock = computed(() => props.stock > 0);

const stockLabel = computed(() => {
  if (props.stock <= 0) return 'Agotado';
  if (props.stock <= 5) return `Ultimas unidades (${props.stock})`;
  return `En stock (${props.stock})`;
});

const stockClass = computed(() => {
  if (props.stock <= 0) return 'ppc-text-danger';
  if (props.stock <= 5) return 'ppc-text-warning';
  return 'ppc-text-success';
});
</script>

<style scoped>
.ppc-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1.15rem;
  box-shadow: 0 14px 30px rgba(15, 23, 42, .06);
}

.ppc-price-row { display: flex; align-items: baseline; flex-wrap: wrap; gap: .55rem; }
.ppc-original { color: #94a3b8; text-decoration: line-through; font-size: 1rem; }
.ppc-price { color: #0f172a; font-size: 2rem; font-weight: 900; line-height: 1; }
.ppc-discount-pill {
  display: inline-flex; align-items: center;
  background: #fef2f2; color: #dc2626; border: 1px solid #fecaca;
  border-radius: 999px; padding: .2rem .6rem; font-size: .78rem; font-weight: 800;
}
.ppc-savings { color: #16a34a; font-weight: 700; font-size: .82rem; margin: .4rem 0 0; }
.ppc-vat-note { color: #94a3b8; font-size: .76rem; margin: .35rem 0 0; }

.ppc-sep { height: 1px; background: #e2e8f0; margin: 1rem 0; }

.ppc-info-rows { display: flex; flex-direction: column; gap: .6rem; }
.ppc-info-row { display: flex; align-items: center; justify-content: space-between; gap: .75rem; }
.ppc-info-label {
  display: inline-flex; align-items: center; gap: .45rem;
  color: #64748b; font-size: .84rem; font-weight: 600;
}
.ppc-info-label i { color: #94a3b8; }
.ppc-info-value { color: #0f172a; font-size: .84rem; font-weight: 700; text-align: right; }
.ppc-text-success { color: #16a34a; }
.ppc-text-warning { color: #d97706; }
.ppc-text-danger { color: #dc2626; }

.ppc-qty-row { display: flex; align-items: center; justify-content: space-between; gap: .75rem; margin-bottom: 1rem; }
.ppc-qty-stepper {
  display: inline-flex; align-items: center;
  border: 1px solid #e2e8f0; border-radius: 999px; overflow: hidden;
}
.ppc-qty-btn {
  width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center;
  border: 0; background: #f8fafc; color: #0f172a; cursor: pointer;
  transition: background-color .15s ease;
}
.ppc-qty-btn:hover:not(:disabled) { background: #eff6ff; }
.ppc-qty-btn:disabled { color: #cbd5e1; cursor: not-allowed; }
.ppc-qty-input {
  width: 44px; text-align: center; border: 0; border-left: 1px solid #e2e8f0; border-right: 1px solid #e2e8f0;
  height: 32px; font-weight: 700; color: #0f172a; -moz-appearance: textfield;
}
.ppc-qty-input::-webkit-outer-spin-button, .ppc-qty-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }

.ppc-actions { display: flex; flex-direction: column; gap: .6rem; }
.ppc-actions-row { display: flex; gap: .6rem; }

.ppc-btn {
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 999px; padding: .8rem 1.4rem; font-weight: 800; font-size: .92rem;
  border: 1px solid transparent; cursor: pointer;
  transition: transform .15s ease, box-shadow .15s ease, background-color .15s ease, opacity .15s ease;
}
.ppc-btn:disabled { opacity: .55; cursor: not-allowed; }

/* CTA dominante: "Comprar ahora" -- solido, ancho completo, arriba de todo. */
.ppc-btn-primary {
  width: 100%; background: #2563eb; color: #fff; box-shadow: 0 8px 18px rgba(37, 99, 235, .25);
}
.ppc-btn-primary:hover:not(:disabled) { background: #1d4ed8; transform: translateY(-1px); box-shadow: 0 10px 22px rgba(37, 99, 235, .3); }
.ppc-btn-primary:active:not(:disabled) { transform: translateY(0); }

/* Secundario: "Agregar al carrito" -- outline, se ve secundario frente al boton solido de arriba. */
.ppc-btn-secondary {
  flex: 1; background: #fff; color: #2563eb; border-color: #bfdbfe;
}
.ppc-btn-secondary:hover:not(:disabled) { background: #eff6ff; border-color: #93c5fd; }

.ppc-icon-btn {
  width: 52px; flex-shrink: 0; display: inline-flex; align-items: center; justify-content: center;
  border-radius: 999px; border: 1px solid #e2e8f0; background: #fff; color: #64748b;
  cursor: pointer; font-size: 1.05rem; transition: all .15s ease;
}
.ppc-icon-btn:hover:not(:disabled) { border-color: #fca5a5; color: #dc2626; }
.ppc-icon-btn.is-active { background: #fef2f2; border-color: #fca5a5; color: #dc2626; }
.ppc-icon-btn:disabled { opacity: .6; cursor: not-allowed; }

.ppc-quote-link {
  display: inline-flex; align-items: center; justify-content: center;
  color: #64748b; font-size: .84rem; font-weight: 700; text-decoration: none;
  padding: .5rem; border-radius: 999px; transition: color .15s ease, background-color .15s ease;
}
.ppc-quote-link:hover { color: #2563eb; background: #f8fafc; }

.ppc-btn:focus-visible, .ppc-icon-btn:focus-visible, .ppc-qty-btn:focus-visible, .ppc-quote-link:focus-visible {
  outline: 2px solid #2563eb; outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
  .ppc-btn, .ppc-icon-btn, .ppc-qty-btn { transition: none; }
}
</style>
