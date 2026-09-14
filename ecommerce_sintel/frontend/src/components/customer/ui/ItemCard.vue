<template>
  <div class="ic-root" @click="$emit('view', item)">

    <!-- ── Imagen ──────────────────────────────────────────────────────────── -->
    <div class="ic-img-wrap">
      <MediaImage
        :images="item.images"
        :alt="item.name"
        :placeholder-icon="placeholderIcon"
        placeholder-bg="linear-gradient(135deg, #f8fafc, #f1f5f9)"
        placeholder-color="#cbd5e1"
        image-fit="cover"
        class="ic-media"
      />

      <!-- Badges top-left -->
      <div class="ic-badges-tl">
        <span v-if="item.is_featured" class="ic-badge ic-badge-star">
          <i class="bi bi-star-fill"></i> Destacado
        </span>
        <span v-if="type === 'rental'" class="ic-badge ic-badge-rental">Alquiler</span>
        <span v-if="type === 'service'" class="ic-badge ic-badge-service">Servicio</span>
      </div>

      <!-- Discount badge top-right -->
      <div v-if="discountPercent" class="ic-badge-discount">
        -{{ discountPercent }}%
      </div>

      <!-- Hover overlay: acciones rápidas -->
      <div class="ic-overlay">
        <button class="ic-overlay-btn ic-overlay-view" @click.stop="$emit('view', item)">
          <i class="bi bi-eye me-1"></i>Ver detalle
        </button>
        <button
          v-if="type === 'product' && hasStock"
          class="ic-overlay-btn ic-overlay-cart"
          @click.stop="$emit('add-to-cart', item)"
        >
          <i class="bi bi-cart-plus"></i>
        </button>
      </div>
    </div>

    <!-- ── Cuerpo ───────────────────────────────────────────────────────────── -->
    <div class="ic-body">
      <span v-if="categoryName" class="ic-category">{{ categoryName }}</span>
      <p class="ic-name">{{ item.name }}</p>

      <div class="ic-price-wrap">
        <PriceDisplay
          v-if="type === 'product'"
          :price="defaultVariantPrice"
          :discountedPrice="defaultVariantDiscountedPrice"
          :discountStart="defaultVariant?.discount_start_date"
          :discountEnd="defaultVariant?.discount_end_date"
          mode="final"
          size="md"
        />
        <PriceDisplay
          v-else-if="type === 'rental'"
          :price="item.variants?.[0]?.rental_price_per_day"
          mode="per-day"
          size="md"
        />
        <PriceDisplay v-else-if="type === 'service'" :price="null" :cotizar="true" size="md" />
      </div>

      <div class="ic-stock-wrap">
        <StockBadge v-if="type === 'product'" :stock="item.stock ?? 0" />
        <StockBadge v-else-if="type === 'rental'" :available="item.is_active" />
      </div>
    </div>

    <!-- ── Footer de acciones ──────────────────────────────────────────────── -->
    <div class="ic-footer" @click.stop>
      <button class="ic-btn-primary" @click="$emit('view', item)">
        <span v-if="type === 'service'">
          <i class="bi bi-file-earmark-text me-1"></i>Cotizar
        </span>
        <span v-else>
          <i class="bi bi-eye me-1"></i>Ver detalle
        </span>
      </button>

      <button
        v-if="type === 'product'"
        class="ic-btn-cart"
        :disabled="!hasStock"
        @click="$emit('add-to-cart', item)"
        :title="hasStock ? 'Agregar al carrito' : 'Sin stock'"
      >
        <i class="bi bi-cart-plus"></i>
      </button>

      <button
        v-if="type === 'product' && defaultVariant"
        class="ic-btn-wishlist"
        :class="{ 'ic-btn-wishlist-active': isWishlisted }"
        :disabled="wishlistLoading"
        @click="toggleWishlist"
        :title="isWishlisted ? 'Quitar de lista de deseos' : 'Agregar a lista de deseos'"
        :aria-label="isWishlisted ? 'Quitar de lista de deseos' : 'Agregar a lista de deseos'"
      >
        <span v-if="wishlistLoading" class="spinner-border spinner-border-sm"></span>
        <i v-else :class="['bi', isWishlisted ? 'bi-heart-fill' : 'bi-heart']"></i>
      </button>
    </div>

  </div>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/store/auth';
import { useWishlistStore } from '@/store/wishlist';
import { useToast } from '@/composables/useToast';
import PriceDisplay from './PriceDisplay.vue';
import StockBadge from './StockBadge.vue';
import MediaImage from '@/components/ui/MediaImage.vue';

const props = defineProps({
  item: { type: Object, required: true },
  type: { type: String, default: 'product' },
});

defineEmits(['click', 'view', 'quote', 'add-to-cart']);

const router = useRouter();
const authStore = useAuthStore();
const wishlistStore = useWishlistStore();
const toast = useToast();

const wishlistLoading = ref(false);

const placeholderIcon = computed(() => ({
  rental: 'bi-truck',
  service: 'bi-tools',
}[props.type] ?? 'bi-box-seam'));

const categoryName = computed(() =>
  props.item.category_name || props.item.category?.name || props.item.service_category_name || null
);

const defaultVariant = computed(() =>
  props.item.variants?.find(v => v.is_default) || props.item.variants?.[0] || null
);

const defaultVariantPrice = computed(() =>
  defaultVariant.value?.effective_price || defaultVariant.value?.price || null
);

const defaultVariantDiscountedPrice = computed(() =>
  defaultVariant.value?.discounted_price || null
);

const hasStock = computed(() => (props.item.stock ?? defaultVariant.value?.stock ?? 0) > 0);

const isWishlisted = computed(() =>
  !!defaultVariant.value && wishlistStore.isInWishlist(defaultVariant.value.uuid)
);

async function toggleWishlist() {
  if (!authStore.isAuthenticated) {
    toast.info('Inicia sesion para guardar en tu lista de deseos');
    router.push('/login');
    return;
  }
  if (!defaultVariant.value) return;
  wishlistLoading.value = true;
  try {
    const added = await wishlistStore.toggle(defaultVariant.value.uuid);
    toast.success(added ? 'Agregado a tu lista de deseos' : 'Eliminado de tu lista de deseos');
  } catch {
    toast.error('No se pudo actualizar la lista de deseos');
  } finally {
    wishlistLoading.value = false;
  }
}

const discountPercent = computed(() => {
  const v = defaultVariant.value;
  if (!v?.discounted_price || !v?.price) return 0;
  const orig = parseFloat(v.price);
  const disc = parseFloat(v.discounted_price);
  if (!orig || disc >= orig) return 0;
  return Math.round((1 - disc / orig) * 100);
});
</script>

<style scoped>
/* ── Root ───────────────────────────────────────────────────────────────────── */
.ic-root {
  background: #fff;
  border: 1px solid rgba(0,0,0,.07);
  border-radius: 18px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  cursor: pointer;
  transition:
    transform 0.35s cubic-bezier(0.16,1,0.3,1),
    box-shadow 0.35s ease,
    border-color 0.22s ease;
  box-shadow: 0 2px 8px rgba(0,0,0,.05);
  height: 100%;
}
.ic-root:hover {
  transform: translateY(-6px);
  box-shadow: 0 16px 40px rgba(0,0,0,.1), 0 4px 12px rgba(0,0,0,.05);
  border-color: #bfdbfe;
}

/* ── Imagen ─────────────────────────────────────────────────────────────────── */
.ic-img-wrap {
  position: relative;
  width: 100%;
  padding-top: 72%;
  overflow: hidden;
  background: #f8fafc;
  flex-shrink: 0;
}
.ic-media { position: absolute; inset: 0; }
.ic-media :deep(.mi-img) { transition: transform 0.5s ease; }
.ic-root:hover .ic-media :deep(.mi-img) { transform: scale(1.06); }
.ic-media :deep(.mi-placeholder) { font-size: 2.5rem; }

/* ── Badges ─────────────────────────────────────────────────────────────────── */
.ic-badges-tl {
  position: absolute;
  top: 0.55rem;
  left: 0.55rem;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}
.ic-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.2rem;
  font-size: 0.6rem;
  font-weight: 700;
  border-radius: 9999px;
  padding: 0.2rem 0.55rem;
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}
.ic-badge-star    { background: rgba(245,158,11,.9); color: #78350f; }
.ic-badge-rental  { background: rgba(139,92,246,.88); color: #fff; }
.ic-badge-service { background: rgba(16,185,129,.88); color: #fff; }

.ic-badge-discount {
  position: absolute;
  top: 0.55rem;
  right: 0.55rem;
  background: linear-gradient(135deg, #ef4444, #dc2626);
  color: #fff;
  font-size: 0.65rem;
  font-weight: 800;
  border-radius: 9999px;
  padding: 0.2rem 0.55rem;
  box-shadow: 0 2px 6px rgba(220,38,38,.3);
}

/* ── Hover overlay ──────────────────────────────────────────────────────────── */
.ic-overlay {
  position: absolute;
  inset: 0;
  background: rgba(10,15,30,.45);
  backdrop-filter: blur(2px);
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.6rem;
  opacity: 0;
  transition: opacity 0.25s ease;
}
.ic-root:hover .ic-overlay { opacity: 1; }

.ic-overlay-btn {
  display: inline-flex;
  align-items: center;
  font-size: 0.8rem;
  font-weight: 600;
  border: none;
  border-radius: 9999px;
  padding: 0.5rem 1rem;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.ic-overlay-btn:hover { transform: scale(1.04); }

.ic-overlay-view {
  background: #fff;
  color: #1e40af;
  box-shadow: 0 2px 10px rgba(0,0,0,.2);
}
.ic-overlay-cart {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: #fff;
  box-shadow: 0 2px 10px rgba(37,99,235,.35);
  padding: 0.5rem 0.7rem;
  font-size: 1rem;
}

/* ── Body ───────────────────────────────────────────────────────────────────── */
.ic-body {
  padding: 0.9rem 1rem 0.6rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  flex: 1;
}
.ic-category {
  font-size: 0.65rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  color: #64748b;
}
.ic-name {
  font-size: 0.9rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
.ic-price-wrap {
  margin-top: auto;
  padding-top: 0.5rem;
}
.ic-stock-wrap { margin-top: 0.35rem; }

/* ── Footer de acciones ─────────────────────────────────────────────────────── */
.ic-footer {
  padding: 0.65rem 0.9rem;
  border-top: 1px solid rgba(0,0,0,.06);
  display: flex;
  gap: 0.5rem;
}
.ic-btn-primary {
  flex: 1;
  font-size: 0.8rem;
  font-weight: 600;
  color: #2563eb;
  background: rgba(37,99,235,.07);
  border: 1px solid rgba(37,99,235,.18);
  border-radius: 9999px;
  padding: 0.45rem 0.75rem;
  cursor: pointer;
  transition: background 0.2s, color 0.2s;
  white-space: nowrap;
}
.ic-btn-primary:hover {
  background: #2563eb;
  color: #fff;
  border-color: #2563eb;
}
.ic-btn-cart {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: #fff;
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 8px rgba(37,99,235,.3);
  transition: transform 0.22s ease, box-shadow 0.22s ease;
}
.ic-btn-cart:hover { transform: scale(1.1); box-shadow: 0 4px 12px rgba(37,99,235,.4); }
.ic-btn-cart:disabled {
  background: #e2e8f0;
  color: #94a3b8;
  box-shadow: none;
  cursor: not-allowed;
  transform: none;
}

.ic-btn-wishlist {
  flex-shrink: 0;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: #fff;
  color: #64748b;
  border: 1px solid rgba(0,0,0,.1);
  cursor: pointer;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.22s ease, box-shadow 0.22s ease, color 0.18s, border-color 0.18s;
}
.ic-btn-wishlist:hover { transform: scale(1.1); border-color: #fca5a5; color: #dc2626; }
.ic-btn-wishlist-active { color: #dc2626; border-color: #fca5a5; background: #fef2f2; }
.ic-btn-wishlist:disabled { cursor: not-allowed; transform: none; }
</style>
