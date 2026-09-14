<template>
  <BaseHorizontalCard
    :image="primaryImage"
    image-fit="contain"
    placeholder-icon="bi-box-seam"
    placeholder-bg="linear-gradient(135deg, #f8fafc, #f1f5f9)"
    placeholder-color="#cbd5e1"
    :title="product.name"
    :description="product.description || ''"
    accent-color="#2563eb"
    accent-shadow="rgba(37,99,235,.09)"
    accent-border="#bfdbfe"
    @view="$emit('view', product)"
  >
    <template #image-badge>
      <span v-if="hasDiscount" class="phc-discount-badge">-{{ discountPct }}%</span>
    </template>

    <template #tags>
      <p v-if="categoryName" class="phc-category">{{ categoryName }}</p>
    </template>

    <template #badges>
      <div class="phc-badges">
        <span v-if="stock > 5" class="phc-stock phc-stock-ok">
          <i class="bi bi-check-circle me-1"></i>En stock ({{ stock }})
        </span>
        <span v-else-if="stock > 0" class="phc-stock phc-stock-low">
          <i class="bi bi-exclamation-circle me-1"></i>Ultimas unidades ({{ stock }})
        </span>
        <span v-else class="phc-stock phc-stock-out">
          <i class="bi bi-x-circle me-1"></i>Agotado
        </span>
        <span v-if="product.is_featured" class="phc-stock phc-stock-feat">
          <i class="bi bi-star-fill me-1"></i>Destacado
        </span>
      </div>
    </template>

    <template #price>
      <span v-if="hasDiscount" class="phc-price-original">{{ fmtCOP(originalPrice) }}</span>
      <span class="phc-price-current">{{ fmtCOP(effectivePrice) }}</span>
      <span v-if="hasDiscount" class="phc-savings">
        Ahorra {{ fmtCOP(savingsAmount) }}
      </span>
    </template>

    <template #actions>
      <button class="phc-btn-cart" :disabled="stock === 0 || adding" @click="handleAddToCart">
        <span v-if="adding" class="spinner-border spinner-border-sm me-1" role="status"></span>
        <i v-else class="bi bi-cart-plus me-1"></i>
        {{ stock === 0 ? 'Agotado' : 'Agregar' }}
      </button>
      <button class="phc-btn-view" @click="$emit('view', product)">
        <i class="bi bi-eye me-1"></i>Detalle
      </button>
    </template>
  </BaseHorizontalCard>
</template>

<script setup>
import { ref, computed } from 'vue';
import BaseHorizontalCard from '@/components/base/BaseHorizontalCard.vue';
import { formatCOP } from '@/utils/money';
import { resolvePrimaryImage } from '@/utils/media';

const props = defineProps({
  product: { type: Object, required: true },
});

const emit = defineEmits(['add-to-cart', 'view']);
const adding = ref(false);

// Fix (Auditoria Enterprise de Imagenes, 2026-08-04): esta card leia `product.image`, campo
// que NUNCA existio en ProductSerializer (solo existe `product.images[]`) -- la vista de lista
// de /tienda mostraba el placeholder para TODOS los productos, tuvieran o no imagen real.
const primaryImage = computed(() => resolvePrimaryImage(props.product.images) || '');

const defaultVariant = computed(() =>
  props.product.variants?.find(v => v.is_default) || props.product.variants?.[0] || {}
);

const stock = computed(() =>
  props.product.stock ?? defaultVariant.value.stock ?? 0
);

const categoryName = computed(() =>
  props.product.category_name || props.product.category?.name || null
);

const originalPrice = computed(() =>
  parseFloat(defaultVariant.value.price || 0)
);

const effectivePrice = computed(() =>
  parseFloat(
    defaultVariant.value.discounted_price ||
    defaultVariant.value.effective_price ||
    defaultVariant.value.price || 0
  )
);

const hasDiscount = computed(() =>
  !!defaultVariant.value.discounted_price && effectivePrice.value < originalPrice.value
);

const discountPct = computed(() =>
  hasDiscount.value ? Math.round((1 - effectivePrice.value / originalPrice.value) * 100) : 0
);

const savingsAmount = computed(() =>
  hasDiscount.value ? originalPrice.value - effectivePrice.value : 0
);

const fmtCOP = (n) => formatCOP(n, { withSymbol: true });

async function handleAddToCart() {
  if (stock.value === 0 || adding.value) return;
  adding.value = true;
  try { emit('add-to-cart', props.product); }
  finally { adding.value = false; }
}
</script>

<style scoped>
.phc-discount-badge {
  position: absolute; top: 0.5rem; left: 0.5rem;
  background: linear-gradient(135deg, #ef4444, #dc2626); color: #fff;
  font-size: 0.65rem; font-weight: 800; border-radius: 9999px; padding: 0.18rem 0.48rem;
}
.phc-category {
  font-size: 0.65rem; font-weight: 700; text-transform: uppercase;
  letter-spacing: 1px; color: #64748b; margin: 0 0 0.3rem;
}
.phc-badges { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.phc-stock {
  font-size: 0.68rem; font-weight: 600; border-radius: 9999px;
  padding: 0.2rem 0.6rem; display: inline-flex; align-items: center;
}
.phc-stock-ok   { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; }
.phc-stock-low  { background: #fffbeb; color: #d97706; border: 1px solid #fde68a; }
.phc-stock-out  { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
.phc-stock-feat { background: #fefce8; color: #a16207; border: 1px solid #fef08a; }

.phc-price-original { font-size: 0.78rem; color: #94a3b8; text-decoration: line-through; }
.phc-price-current { font-size: 1.2rem; font-weight: 800; color: #1e40af; line-height: 1; }
.phc-savings { font-size: 0.72rem; color: #16a34a; font-weight: 600; }

.phc-btn-cart {
  font-size: 0.82rem; font-weight: 600; color: #fff;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  border: none; border-radius: 9999px; padding: 0.55rem 0.9rem; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: transform 0.22s ease, box-shadow 0.22s ease, opacity 0.18s;
  box-shadow: 0 2px 10px rgba(37,99,235,.3);
}
.phc-btn-cart:hover:not(:disabled) { transform: translateY(-1px); box-shadow: 0 5px 14px rgba(37,99,235,.4); }
.phc-btn-cart:disabled { background: #e2e8f0; color: #94a3b8; box-shadow: none; cursor: not-allowed; }
.phc-btn-view {
  font-size: 0.78rem; font-weight: 600; color: #2563eb;
  background: rgba(37,99,235,.07); border: 1px solid rgba(37,99,235,.18);
  border-radius: 9999px; padding: 0.45rem 0.9rem; cursor: pointer;
  display: flex; align-items: center; justify-content: center; transition: background 0.2s, color 0.2s;
}
.phc-btn-view:hover { background: rgba(37,99,235,.14); }

@media (max-width: 575px) {
  .phc-price-current { font-size: 1rem; }
}
</style>
