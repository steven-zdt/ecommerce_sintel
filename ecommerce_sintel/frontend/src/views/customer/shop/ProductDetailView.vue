<template>
  <div class="product-detail">
    <div class="container-xl py-3 py-lg-4">

      <!-- Breadcrumb -->
      <nav class="mb-3" aria-label="breadcrumb">
        <ol class="breadcrumb breadcrumb-sm mb-0">
          <li class="breadcrumb-item">
            <RouterLink to="/tienda" class="text-decoration-none text-muted">
              <i class="bi bi-house me-1"></i>Tienda
            </RouterLink>
          </li>
          <li v-if="product?.category_name" class="breadcrumb-item text-muted">
            {{ product.category_name }}
          </li>
          <li class="breadcrumb-item active text-truncate" style="max-width:220px">
            {{ product?.name }}
          </li>
        </ol>
      </nav>

      <!-- Skeleton -->
      <div v-if="loading" class="row g-4">
        <div class="col-lg-5">
          <div class="skeleton rounded-3" style="height:420px"></div>
          <div class="d-flex gap-2 mt-2">
            <div v-for="i in 4" :key="i" class="skeleton rounded-2 flex-shrink-0" style="width:72px;height:72px"></div>
          </div>
        </div>
        <div class="col-lg-7">
          <div class="skeleton rounded mb-3" style="height:32px;width:75%"></div>
          <div class="skeleton rounded mb-2" style="height:18px;width:35%"></div>
          <div class="skeleton rounded mb-4" style="height:60px"></div>
          <div class="skeleton rounded mb-3" style="height:52px;width:50%"></div>
          <div class="skeleton rounded" style="height:48px"></div>
        </div>
      </div>

      <!-- Producto -->
      <div v-else-if="product" class="row g-4 g-lg-5">

        <!-- ── COLUMNA IZQUIERDA: galería ── -->
        <div class="col-lg-5">
          <div class="gallery-sticky">

            <!-- Imagen principal -->
            <div class="main-image-wrap rounded-3 border bg-white position-relative">
              <img
                v-if="activeImage"
                :src="activeImage"
                :alt="product.name"
                class="main-image"
              >
              <div v-else class="main-image d-flex align-items-center justify-content-center bg-light">
                <i class="bi bi-box-seam text-muted" style="font-size:5rem;opacity:.25"></i>
              </div>

              <!-- Badge descuento sobre imagen -->
              <span
                v-if="discountPct > 0"
                class="badge bg-danger position-absolute top-0 start-0 m-2 px-2 py-1"
                style="font-size:.8rem"
              >
                -{{ discountPct }}%
              </span>

              <!-- Badge destacado -->
              <span
                v-if="product.is_featured"
                class="badge bg-warning text-dark position-absolute top-0 end-0 m-2"
                style="font-size:.75rem"
              >
                <i class="bi bi-star-fill me-1"></i>Destacado
              </span>
            </div>

            <!-- Miniaturas -->
            <div v-if="allImages.length > 1" class="d-flex gap-2 mt-2 flex-wrap">
              <button
                v-for="(img, i) in allImages"
                :key="i"
                class="thumb-btn border rounded-2 bg-white p-1"
                :class="{ 'thumb-active': activeImageIndex === i }"
                @click="activeImageIndex = i"
              >
                <img :src="img" :alt="`Vista ${i + 1}`" class="thumb-img">
              </button>
            </div>

            <!-- Trust badges -->
            <div class="trust-row mt-3 d-flex gap-2 flex-wrap">
              <div class="trust-item">
                <i class="bi bi-truck text-success"></i>
                <span>Envio disponible</span>
              </div>
              <div class="trust-item">
                <i class="bi bi-shield-check text-primary"></i>
                <span>Compra segura</span>
              </div>
              <div class="trust-item">
                <i class="bi bi-arrow-repeat text-warning"></i>
                <span>Garantia del producto</span>
              </div>
            </div>

            <!-- Metodos de pago -->
            <div class="mt-3 p-2 rounded-2 border text-center">
              <p class="small text-muted mb-1 fw-semibold">Medios de pago aceptados</p>
              <div class="d-flex justify-content-center align-items-center gap-2 flex-wrap">
                <span class="pay-chip"><i class="bi bi-credit-card-2-front me-1"></i>Tarjeta</span>
                <span class="pay-chip"><i class="bi bi-bank me-1"></i>PSE</span>
                <span class="pay-chip"><i class="bi bi-phone me-1"></i>Nequi</span>
                <span class="pay-chip"><i class="bi bi-cash-coin me-1"></i>Contra entrega</span>
              </div>
            </div>
          </div>
        </div>

        <!-- ── COLUMNA DERECHA: info + acciones ── -->
        <div class="col-lg-7">

          <!-- Marca + categoria + rating -->
          <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
            <span v-if="product.brand_name" class="badge bg-primary-subtle text-primary border border-primary-subtle">
              {{ product.brand_name }}
            </span>
            <span v-if="product.category_name" class="badge bg-light text-muted border">
              {{ product.category_name }}
            </span>
            <div v-if="product.review_count" class="d-flex align-items-center gap-1 ms-auto">
              <div class="d-flex text-warning" style="font-size:.85rem">
                <i v-for="n in 5" :key="n"
                   :class="['bi', n <= Math.round(product.avg_rating || 0) ? 'bi-star-fill' : 'bi-star']"></i>
              </div>
              <span class="text-muted small">({{ product.review_count }})</span>
            </div>
          </div>

          <!-- Nombre -->
          <h1 class="h3 fw-bold lh-sm mb-2">{{ product.name }}</h1>

          <!-- Descripcion corta -->
          <p v-if="product.short_description" class="text-secondary mb-3" style="font-size:.95rem">
            {{ product.short_description }}
          </p>

          <!-- SKU inline -->
          <p v-if="selectedVariant?.sku" class="text-muted small mb-3">
            <i class="bi bi-upc me-1"></i>SKU: <code>{{ selectedVariant.sku }}</code>
          </p>

          <hr class="my-3">

          <!-- BLOQUE PRECIO -->
          <div class="price-block mb-3">
            <div v-if="discountPct > 0" class="d-flex align-items-center gap-2 mb-1">
              <span class="text-muted text-decoration-line-through fs-5">
                {{ fmtCOP(originalPrice) }}
              </span>
              <span class="badge bg-danger px-2 py-1">-{{ discountPct }}%</span>
            </div>
            <div class="d-flex align-items-end gap-2">
              <span class="price-main">{{ fmtCOP(effectivePrice) }}</span>
              <span v-if="discountPct > 0" class="text-success fw-semibold small mb-1">
                Ahorras {{ fmtCOP(originalPrice - effectivePrice) }}
              </span>
            </div>
            <p class="text-muted small mt-1 mb-0">
              <i class="bi bi-info-circle me-1"></i>Precio incluye IVA
            </p>
          </div>

          <!-- Stock -->
          <div class="mb-3">
            <StockBadge v-if="selectedVariant" :stock="selectedVariant.stock ?? 0" />
          </div>

          <!-- Selector de variantes -->
          <div v-if="variants.length > 1" class="mb-4">
            <p class="small fw-bold text-dark mb-2">
              Variante <span class="text-danger">*</span>
            </p>
            <div class="d-flex flex-wrap gap-2">
              <button
                v-for="v in variants"
                :key="v.uuid"
                :class="['variant-btn', selectedVariant?.uuid === v.uuid ? 'variant-active' : '']"
                :disabled="!v.stock"
                @click="selectedVariant = v"
              >
                <span v-for="(val, key) in v.attributes" :key="key">{{ val }}</span>
                <span v-if="!v.stock" class="ms-1 text-danger small">(Agotado)</span>
              </button>
            </div>
          </div>

          <!-- Atributos de variante seleccionada -->
          <div v-if="variantAttributes.length > 0" class="attr-chips mb-3 d-flex flex-wrap gap-2">
            <span v-for="attr in variantAttributes" :key="attr.key" class="attr-chip">
              <span class="attr-key">{{ attr.key }}:</span> {{ attr.val }}
            </span>
          </div>

          <!-- Logistica -->
          <div v-if="hasLogistics" class="logistics-box mb-4 p-3 rounded-3 border small">
            <p class="fw-semibold mb-2 text-dark"><i class="bi bi-box me-1"></i>Dimensiones y peso</p>
            <div class="d-flex flex-wrap gap-3 text-muted">
              <span v-if="selectedVariant.weight">
                <strong>Peso:</strong> {{ selectedVariant.weight }} kg
              </span>
              <span v-if="selectedVariant.length">
                <strong>Largo:</strong> {{ selectedVariant.length }} cm
              </span>
              <span v-if="selectedVariant.width">
                <strong>Ancho:</strong> {{ selectedVariant.width }} cm
              </span>
              <span v-if="selectedVariant.height">
                <strong>Alto:</strong> {{ selectedVariant.height }} cm
              </span>
            </div>
          </div>

          <!-- Cantidad -->
          <div class="d-flex align-items-center gap-2 mb-3">
            <span class="small fw-bold text-dark">Cantidad:</span>
            <div class="input-group qty-group">
              <button class="btn btn-outline-secondary" @click="qty = Math.max(1, qty - 1)">
                <i class="bi bi-dash"></i>
              </button>
              <input
                v-model.number="qty"
                type="number" min="1"
                :max="selectedVariant?.stock || 1"
                class="form-control text-center qty-input"
              >
              <button class="btn btn-outline-secondary"
                      @click="qty = Math.min(selectedVariant?.stock || 1, qty + 1)">
                <i class="bi bi-plus"></i>
              </button>
            </div>
            <span v-if="selectedVariant?.stock" class="text-muted small">
              ({{ selectedVariant.stock }} disponibles)
            </span>
          </div>

          <!-- Botones de accion -->
          <div class="d-flex flex-column gap-2 mb-4">
            <button
              class="btn btn-primary btn-lg fw-bold"
              @click="addToCart"
              :disabled="addingToCart || !selectedVariant?.stock"
            >
              <span v-if="addingToCart" class="spinner-border spinner-border-sm me-2"></span>
              <i v-else class="bi bi-bag-plus me-2"></i>
              {{ !selectedVariant?.stock ? 'Agotado' : 'Agregar al carrito' }}
            </button>

            <button
              class="btn btn-success fw-bold"
              @click="buyNow"
              :disabled="cartStore.isEmpty"
            >
              <i class="bi bi-lightning-charge-fill me-2"></i>
              {{ cartStore.isEmpty ? 'Agrega al carrito primero' : 'Comprar ahora' }}
            </button>

            <RouterLink
              :to="`/cotizar?product=${product.uuid}`"
              class="btn btn-outline-secondary"
            >
              <i class="bi bi-file-earmark-text me-2"></i>Solicitar cotizacion
            </RouterLink>
          </div>

        </div>
      </div>

      <!-- ── TABS: Descripcion / Especificaciones ── -->
      <div v-if="product && !loading" class="mt-5">
        <ul class="nav nav-tabs detail-tabs mb-0">
          <li class="nav-item">
            <button
              class="nav-link"
              :class="{ active: activeTab === 'desc' }"
              @click="activeTab = 'desc'"
            >
              <i class="bi bi-card-text me-1"></i>Descripcion
            </button>
          </li>
          <li v-if="variantAttributes.length > 0 || product.condition" class="nav-item">
            <button
              class="nav-link"
              :class="{ active: activeTab === 'specs' }"
              @click="activeTab = 'specs'"
            >
              <i class="bi bi-list-columns me-1"></i>Especificaciones
            </button>
          </li>
          <li v-if="product.video_url" class="nav-item">
            <button
              class="nav-link"
              :class="{ active: activeTab === 'video' }"
              @click="activeTab = 'video'"
            >
              <i class="bi bi-play-circle me-1"></i>Video
            </button>
          </li>
        </ul>

        <div class="tab-content-box border border-top-0 rounded-bottom-3 p-4">

          <!-- Tab Descripcion -->
          <div v-show="activeTab === 'desc'">
            <div v-if="product.description" class="product-description" style="white-space:pre-wrap">
              {{ product.description }}
            </div>
            <p v-else class="text-muted fst-italic mb-0">Sin descripcion detallada.</p>
          </div>

          <!-- Tab Especificaciones -->
          <div v-show="activeTab === 'specs'">
            <table class="table table-sm table-bordered specs-table mb-0">
              <tbody>
                <tr v-if="product.condition">
                  <th class="specs-key">Condicion</th>
                  <td>{{ product.condition }}</td>
                </tr>
                <tr v-for="attr in variantAttributes" :key="attr.key">
                  <th class="specs-key">{{ attr.key }}</th>
                  <td>{{ attr.val }}</td>
                </tr>
                <tr v-if="selectedVariant?.sku">
                  <th class="specs-key">SKU</th>
                  <td><code>{{ selectedVariant.sku }}</code></td>
                </tr>
                <tr v-if="selectedVariant?.weight">
                  <th class="specs-key">Peso</th>
                  <td>{{ selectedVariant.weight }} kg</td>
                </tr>
              </tbody>
            </table>
          </div>

          <!-- Tab Video -->
          <div v-show="activeTab === 'video'">
            <div v-if="embedUrl" class="ratio ratio-16x9 rounded-3 overflow-hidden">
              <iframe
                :src="embedUrl"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowfullscreen
                title="Video del producto"
              ></iframe>
            </div>
            <a v-else :href="product.video_url" target="_blank" rel="noopener"
               class="btn btn-outline-primary btn-sm">
              <i class="bi bi-play-circle me-1"></i>Ver video externo
            </a>
          </div>

        </div>
      </div>

      <!-- ── RESENAS ── -->
      <div v-if="product && !loading" class="mt-5">
        <div class="d-flex align-items-center gap-3 mb-4">
          <h5 class="fw-bold mb-0"><i class="bi bi-chat-square-text me-2 text-primary"></i>Resenas</h5>
          <div v-if="product.review_count" class="d-flex align-items-center gap-1">
            <div class="d-flex text-warning">
              <i v-for="n in 5" :key="n"
                 :class="['bi', n <= Math.round(product.avg_rating || 0) ? 'bi-star-fill' : 'bi-star']"></i>
            </div>
            <span class="text-muted small ms-1">
              {{ (product.avg_rating || 0).toFixed(1) }} de 5 ({{ product.review_count }} resenas)
            </span>
          </div>
          <span v-else class="text-muted small">Sin resenas aun — se el primero</span>
        </div>

        <!-- Formulario nueva resena -->
        <div v-if="authStore.isAuthenticated && !myReview"
             class="card border-primary border-opacity-25 mb-4 p-4">
          <p class="fw-bold mb-3"><i class="bi bi-pencil me-1"></i>Escribe tu resena</p>
          <div class="mb-3 d-flex gap-1">
            <button
              v-for="n in 5"
              :key="n"
              type="button"
              :class="['btn btn-sm star-btn', reviewForm.rating >= n ? 'active' : '']"
              @click="reviewForm.rating = n"
            >
              <i class="bi bi-star-fill"></i>
            </button>
          </div>
          <textarea
            v-model="reviewForm.comment"
            class="form-control mb-3"
            rows="3"
            placeholder="Cuéntanos tu experiencia con este producto..."
          ></textarea>
          <button
            class="btn btn-primary btn-sm"
            :disabled="reviewLoading || !reviewForm.rating || !reviewForm.comment"
            @click="submitReview"
          >
            <span v-if="reviewLoading" class="spinner-border spinner-border-sm me-1"></span>
            <i v-else class="bi bi-send me-1"></i>
            Publicar resena
          </button>
        </div>

        <!-- Lista de resenas -->
        <div v-if="reviewsLoading" class="text-center py-4">
          <div class="spinner-border spinner-border-sm text-primary"></div>
        </div>
        <div v-else-if="reviews.length === 0" class="text-muted small text-center py-4">
          Aun no hay resenas para este producto.
        </div>
        <div v-else class="d-flex flex-column gap-3">
          <div v-for="r in reviews" :key="r.uuid" class="review-card border rounded-3 p-3">
            <div class="d-flex align-items-start gap-3">
              <div class="review-avatar text-white rounded-circle d-flex align-items-center justify-content-center fw-bold flex-shrink-0">
                {{ initials(r.user_email) }}
              </div>
              <div class="flex-grow-1">
                <div class="d-flex align-items-center gap-2 flex-wrap mb-1">
                  <span class="fw-semibold small">{{ maskEmail(r.user_email) }}</span>
                  <span v-if="r.is_verified_purchase"
                        class="badge bg-success-subtle text-success border border-success-subtle"
                        style="font-size:.68rem">
                    <i class="bi bi-patch-check-fill me-1"></i>Compra verificada
                  </span>
                  <div class="d-flex text-warning ms-auto" style="font-size:.82rem">
                    <i v-for="n in 5" :key="n"
                       :class="['bi', n <= r.rating ? 'bi-star-fill' : 'bi-star']"></i>
                  </div>
                </div>
                <div class="text-muted mb-2" style="font-size:.72rem">{{ fmtDate(r.created_at) }}</div>
                <p class="mb-0 small" style="white-space:pre-wrap">{{ r.comment }}</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Producto no encontrado -->
      <div v-if="!loading && !product" class="text-center py-5">
        <i class="bi bi-exclamation-circle display-4 text-muted d-block mb-3"></i>
        <p class="text-muted">Producto no encontrado.</p>
        <RouterLink to="/tienda" class="btn btn-primary btn-sm">
          <i class="bi bi-arrow-left me-1"></i>Volver a la tienda
        </RouterLink>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, RouterLink, useRouter } from 'vue-router';
import { shopService } from '@/services/shop/shopService';
import { useToast } from '@/composables/useToast';
import { useCartStore } from '@/store/cart';
import { useAuthStore } from '@/store/auth';
import StockBadge from '@/components/customer/ui/StockBadge.vue';

const toast     = useToast();
const cartStore = useCartStore();
const authStore = useAuthStore();
const route     = useRoute();
const router    = useRouter();

const loading         = ref(true);
const product         = ref(null);
const variants        = ref([]);
const selectedVariant = ref(null);
const qty             = ref(1);
const addingToCart    = ref(false);
const activeImageIndex = ref(0);
const activeTab       = ref('desc');

const reviews        = ref([]);
const reviewsLoading = ref(false);
const reviewLoading  = ref(false);
const reviewForm     = ref({ rating: 0, comment: '' });
const myReview       = ref(false);

// Galeria: soporta product.images[] o product.image string
const allImages = computed(() => {
  if (product.value?.images?.length) {
    return product.value.images
      .slice()
      .sort((a, b) => (b.is_primary ? 1 : 0) - (a.is_primary ? 1 : 0))
      .map(i => i.image || i.url || i);
  }
  return product.value?.image ? [product.value.image] : [];
});

const activeImage = computed(() => allImages.value[activeImageIndex.value] || null);

// Precio con descuento
const originalPrice = computed(() =>
  parseFloat(selectedVariant.value?.price || 0)
);
// El precio mostrado debe ser el que realmente se cobra en el carrito/checkout
// (PricingService.calculate_variant_price(..., include_active_taxes=True)) --
// antes se mostraba effective_price sin IVA junto a la leyenda "Precio incluye
// IVA", una discrepancia real entre lo que el cliente ve y lo que paga. `price_info.
// final_price_net` (ya calculado por el backend, mismo patron que Servicios
// Tecnicos) es el neto con impuestos; se conserva el fallback previo por si
// price_info no vino en la respuesta (endpoint viejo/cache).
const effectivePrice = computed(() => {
  const info = selectedVariant.value?.price_info;
  if (info?.final_price_net != null) return parseFloat(info.final_price_net);
  return parseFloat(
    selectedVariant.value?.discounted_price ||
    selectedVariant.value?.effective_price ||
    selectedVariant.value?.price || 0
  );
});
const discountPct = computed(() => {
  if (!selectedVariant.value?.discounted_price) return 0;
  if (originalPrice.value <= 0) return 0;
  return Math.round((1 - effectivePrice.value / originalPrice.value) * 100);
});

// Atributos de la variante como array [{key, val}]
const variantAttributes = computed(() => {
  const attrs = selectedVariant.value?.attributes;
  if (!attrs || typeof attrs !== 'object') return [];
  return Object.entries(attrs).map(([key, val]) => ({ key, val }));
});

const hasLogistics = computed(() =>
  selectedVariant.value &&
  (selectedVariant.value.weight || selectedVariant.value.length ||
   selectedVariant.value.width  || selectedVariant.value.height)
);

const embedUrl = computed(() => {
  const url = product.value?.video_url;
  if (!url) return null;
  const yt = url.match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})/);
  if (yt) return `https://www.youtube.com/embed/${yt[1]}`;
  const vi = url.match(/vimeo\.com\/(\d+)/);
  if (vi) return `https://player.vimeo.com/video/${vi[1]}`;
  return null;
});

const fmtCOP = (n) =>
  new Intl.NumberFormat('es-CO', {
    style: 'currency',
    currency: 'COP',
    maximumFractionDigits: 0,
  }).format(n);

const fmtDate = (d) => d
  ? new Date(d).toLocaleDateString('es-CO', { year: 'numeric', month: 'short', day: 'numeric' })
  : '';

const initials  = (email) => (email || '?').slice(0, 2).toUpperCase();
const maskEmail = (email) => {
  if (!email) return 'Anonimo';
  const [user, domain] = email.split('@');
  return `${user.slice(0, 2)}***@${domain}`;
};

async function fetchProduct() {
  loading.value = true;
  try {
    const uuid = route.params.uuid;
    product.value = await shopService.detail(uuid);
    variants.value = product.value.variants || [];
    selectedVariant.value = variants.value.find(v => v.is_default) || variants.value[0] || null;
    activeImageIndex.value = 0;
    await fetchReviews(uuid);
  } catch {
    toast.error('Error al cargar el producto');
  } finally {
    loading.value = false;
  }
}

async function fetchReviews(uuid) {
  reviewsLoading.value = true;
  try {
    const data = await shopService.reviews(uuid);
    reviews.value = data.results ?? data;
    if (authStore.isAuthenticated) {
      myReview.value = reviews.value.some(r => r.user_email === authStore.user?.email);
    }
  } catch {
    reviews.value = [];
  } finally {
    reviewsLoading.value = false;
  }
}

async function addToCart() {
  if (!authStore.isAuthenticated) {
    toast.info('Inicia sesion para agregar al carrito');
    router.push('/login');
    return;
  }
  if (!selectedVariant.value) return;
  addingToCart.value = true;
  try {
    await cartStore.addItem(selectedVariant.value.uuid, qty.value);
    toast.success(`"${product.value.name}" agregado al carrito`);
  } catch {
    toast.error('No se pudo agregar al carrito');
  } finally {
    addingToCart.value = false;
  }
}

function buyNow() {
  if (!authStore.isAuthenticated) {
    toast.info('Inicia sesion para continuar');
    router.push('/login');
    return;
  }
  if (cartStore.isEmpty) return;
  router.push('/checkout');
}

async function submitReview() {
  if (!reviewForm.value.rating || !reviewForm.value.comment.trim()) return;
  reviewLoading.value = true;
  try {
    await shopService.addReview(product.value.uuid, {
      rating:  reviewForm.value.rating,
      comment: reviewForm.value.comment.trim(),
    });
    toast.success('Resena publicada');
    reviewForm.value = { rating: 0, comment: '' };
    await fetchReviews(product.value.uuid);
    const data = await shopService.detail(product.value.uuid);
    product.value = { ...product.value, avg_rating: data.avg_rating, review_count: data.review_count };
  } catch (e) {
    const msg = e.response?.data?.non_field_errors?.[0]
      || e.response?.data?.detail
      || 'Error al publicar la resena';
    toast.error(msg);
  } finally {
    reviewLoading.value = false;
  }
}

onMounted(fetchProduct);
</script>

<style scoped>
/* ── Galeria ── */
.gallery-sticky {
  position: sticky;
  top: 80px;
}
.main-image-wrap {
  width: 100%;
  aspect-ratio: 1 / 1;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.main-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
  transition: transform .3s ease;
}
.main-image-wrap:hover .main-image { transform: scale(1.04); }

.thumb-btn {
  cursor: pointer;
  border-color: #e5e7eb !important;
  transition: border-color .15s;
}
.thumb-btn:hover { border-color: #93c5fd !important; }
.thumb-active { border-color: #2563eb !important; box-shadow: 0 0 0 2px rgba(37,99,235,.25); }
.thumb-img { width: 64px; height: 64px; object-fit: contain; display: block; }

/* ── Trust badges ── */
.trust-row { border-top: 1px solid #f3f4f6; padding-top: 12px; }
.trust-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: .78rem;
  color: #6b7280;
}
.trust-item i { font-size: 1rem; }

/* ── Metodos de pago ── */
.pay-chip {
  font-size: .72rem;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  padding: 3px 8px;
  color: #374151;
}

/* ── Precio ── */
.price-block { background: #fafafa; border-radius: 12px; padding: 16px; border: 1px solid #f0f0f0; }
.price-main { font-size: 2rem; font-weight: 800; color: #dc2626; line-height: 1; }

/* ── Variantes ── */
.variant-btn {
  border: 1.5px solid #e5e7eb;
  border-radius: 8px;
  padding: 6px 14px;
  background: #fff;
  color: #374151;
  font-size: .85rem;
  transition: all .15s;
  cursor: pointer;
}
.variant-btn:hover:not(:disabled) { border-color: #93c5fd; color: #2563eb; }
.variant-active { border-color: #2563eb !important; background: #eff6ff; color: #2563eb; font-weight: 600; }
.variant-btn:disabled { opacity: .5; cursor: not-allowed; }

/* ── Atributos chips ── */
.attr-chip {
  font-size: .78rem;
  background: #f3f4f6;
  border-radius: 6px;
  padding: 3px 10px;
  color: #374151;
}
.attr-key { font-weight: 600; color: #111827; }

/* ── Logistica box ── */
.logistics-box { background: #f9fafb; }

/* ── Cantidad ── */
.qty-group { width: 120px; }
.qty-input { max-width: 50px; }

/* ── Tabs ── */
.detail-tabs .nav-link {
  color: #6b7280;
  border-color: #dee2e6 #dee2e6 #fff;
  font-size: .9rem;
  padding: 10px 18px;
}
.detail-tabs .nav-link.active { color: #2563eb; font-weight: 600; border-bottom-color: #fff; }
.tab-content-box { background: #fff; min-height: 120px; }
.product-description { font-size: .92rem; line-height: 1.7; color: #374151; }

/* ── Specs table ── */
.specs-table { font-size: .88rem; }
.specs-key { width: 38%; background: #f9fafb; color: #374151; font-weight: 600; }

/* ── Botones accion ── */
.btn-primary { background: #2563eb; border-color: #2563eb; }
.btn-primary:hover { background: #1d4ed8; border-color: #1d4ed8; }
.btn-success { background: #16a34a; border-color: #16a34a; }
.btn-success:hover { background: #15803d; border-color: #15803d; }

/* ── Reviews ── */
.review-avatar {
  width: 36px; height: 36px; min-width: 36px;
  background: #2563eb;
  font-size: .75rem;
}
.review-card { background: #fff; transition: box-shadow .15s; }
.review-card:hover { box-shadow: 0 2px 8px rgba(0,0,0,.07); }
.star-btn { color: #d1d5db; background: none; border: none; font-size: 1.2rem; padding: 2px 4px; }
.star-btn.active { color: #f59e0b; }
.star-btn:hover { color: #f59e0b; }

/* ── Breadcrumb ── */
.breadcrumb-sm { font-size: .82rem; }

/* ── Skeleton ── */
.skeleton {
  background: linear-gradient(90deg, #f0f0f0 25%, #e8e8e8 37%, #f0f0f0 63%);
  background-size: 400% 100%;
  animation: shimmer 1.4s infinite;
}
@keyframes shimmer {
  0%   { background-position: 100% 50%; }
  100% { background-position: 0 50%; }
}
</style>
