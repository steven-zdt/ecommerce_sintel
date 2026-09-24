<template>
  <!-- ══════════════════════════════════════════════════════════════════════
       SHOP — Presentation Layer (extraida de PublicDetailView.vue, item
       P2-2 de la auditoria). Igual que Services, el DTO unificado
       (ShopPublicDetailPresenter) es demasiado escueto -- el padre
       complementa con shopService.detail()/.reviews() (endpoints publicos
       ya existentes) y entrega el resultado ya resuelto via props, en la
       misma secuencia que antes de la descomposicion.

       Rediseno 3 columnas (2026-09-16, mision "Remodelar PDP" -- ver
       AUDITORIA/PRODUCT_DETAIL_PDP_BASELINE.md/PRODUCT_DETAIL_PDP_REDESIGN.md):
       galeria | informacion | compra, separados en 3 columnas reales de
       Bootstrap (antes: galeria + una sola columna que anidaba info+compra).
       Desktop (lg+, 992px): 4/5/3. Tablet (md, 768-991px): galeria+info a 2
       columnas, compra debajo a ancho completo (brief seccion 24: "purchase
       below"). Mobile (<768px): las 3 apiladas en su orden natural del DOM
       (galeria, info, compra) -- ver seccion "Gaps" del doc de rediseno para
       la decision consciente de NO reordenar precio antes de variantes en
       mobile via CSS order (hubiera exigido partir ProductPurchaseCard en
       2 componentes, mas invasivo de lo que justifica esta iteracion).
       Cero cambios de logica de negocio/API, solo presentacion + grid.
       ══════════════════════════════════════════════════════════════════════ -->
  <div class="product-detail-block">
    <div class="row g-4 g-lg-4">
      <!-- Columna 1: galeria -->
      <div class="col-12 col-md-6 col-lg-4">
        <div class="gallery-sticky">
          <BaseGallery
            :images="shopAllImages"
            :title="shopProduct.name"
            theme="shop"
            thumb-layout="vertical"
            zoom
            lightbox
            icon-class="bi-box-seam"
          >
            <template #badge>
              <span v-if="shopDiscountPct > 0" class="pd-gallery-badge pd-gallery-badge-discount">
                -{{ shopDiscountPct }}%
              </span>
              <span v-if="shopProduct.is_featured" class="pd-gallery-badge pd-gallery-badge-featured">
                <i class="bi bi-star-fill me-1"></i>Destacado
              </span>
            </template>
          </BaseGallery>

          <div class="trust-row mt-3 d-flex gap-2 flex-wrap">
            <div class="trust-item"><i class="bi bi-truck text-success"></i><span>Envio disponible</span></div>
            <div class="trust-item"><i class="bi bi-shield-check text-primary"></i><span>Compra segura</span></div>
            <div class="trust-item"><i class="bi bi-arrow-repeat text-warning"></i><span>Garantia del producto</span></div>
          </div>

          <div class="pay-methods mt-3">
            <p class="pay-methods-label">Medios de pago aceptados</p>
            <div class="d-flex justify-content-center align-items-center gap-2 flex-wrap">
              <span class="pay-chip"><i class="bi bi-credit-card-2-front me-1"></i>Tarjeta</span>
              <span class="pay-chip"><i class="bi bi-bank me-1"></i>PSE</span>
              <span class="pay-chip"><i class="bi bi-phone me-1"></i>Nequi</span>
              <span class="pay-chip"><i class="bi bi-cash-coin me-1"></i>Contra entrega</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Columna 2: informacion del producto -->
      <div class="col-12 col-md-6 col-lg-5">
        <div class="pd-badges-row">
          <TagBadge v-if="shopFeaturedTag" :tag="shopFeaturedTag" />
          <TagBadge v-if="shopConditionTag" :tag="shopConditionTag" />
          <span v-if="shopProduct.brand_name" class="pd-chip">{{ shopProduct.brand_name }}</span>
          <span v-if="shopProduct.category_name" class="pd-chip pd-chip-muted">{{ shopProduct.category_name }}</span>
        </div>

        <h1 class="pd-title">{{ shopProduct.name }}</h1>

        <RatingDisplay v-if="shopProduct.review_count" :rating="shopRatingObject" :show-breakdown="false" class="mb-2" />

        <p v-if="shopProduct.short_description" class="pd-short-desc">
          {{ shopProduct.short_description }}
        </p>
        <p v-if="shopSelectedVariant?.sku" class="pd-sku">
          <i class="bi bi-upc me-1"></i>SKU: <code>{{ shopSelectedVariant.sku }}</code>
        </p>

        <UrgencyBanner
          v-if="shopSelectedVariant"
          :status="shopStockStatus"
          :available-now="shopSelectedVariant.stock ?? 0"
          :total-stock="shopSelectedVariant.stock ?? 0"
        />

        <div v-if="shopVariants.length > 1" class="mt-4">
          <p class="pd-field-label">Variante <span class="text-danger">*</span></p>
          <div class="d-flex flex-wrap gap-2">
            <button
              v-for="v in shopVariants"
              :key="v.uuid"
              type="button"
              :class="['variant-btn', shopSelectedVariant?.uuid === v.uuid ? 'variant-active' : '']"
              :disabled="!v.stock"
              @click="shopSelectedVariant = v"
            >
              <span v-for="(val, key) in v.attributes" :key="key">{{ val }}</span>
              <span v-if="!v.stock" class="ms-1 text-danger small">(Agotado)</span>
            </button>
          </div>
        </div>

        <div v-if="shopVariantAttributes.length > 0" class="attr-chips mt-3 d-flex flex-wrap gap-2">
          <span v-for="attr in shopVariantAttributes" :key="attr.key" class="attr-chip">
            <span class="attr-key">{{ attr.key }}:</span> {{ attr.val }}
          </span>
        </div>

        <div v-if="shopHasLogistics" class="logistics-box mt-3">
          <p class="pd-field-label mb-2"><i class="bi bi-box me-1"></i>Dimensiones y peso</p>
          <div class="d-flex flex-wrap gap-3 text-muted small">
            <span v-if="shopSelectedVariant.weight"><strong>Peso:</strong> {{ shopSelectedVariant.weight }} kg</span>
            <span v-if="shopSelectedVariant.length"><strong>Largo:</strong> {{ shopSelectedVariant.length }} cm</span>
            <span v-if="shopSelectedVariant.width"><strong>Ancho:</strong> {{ shopSelectedVariant.width }} cm</span>
            <span v-if="shopSelectedVariant.height"><strong>Alto:</strong> {{ shopSelectedVariant.height }} cm</span>
          </div>
        </div>
      </div>

      <!-- Columna 3: panel de compra (ya existia completo, solo se reubica en
           su propia columna en vez de anidarlo al final de la columna de info) -->
      <div class="col-12 col-lg-3">
        <div class="purchase-sticky">
          <ProductPurchaseCard
            :price-label="fmtCOP(shopEffectivePrice)"
            :original-price-label="fmtCOP(shopOriginalPrice)"
            :discount-pct="shopDiscountPct"
            :savings-label="shopDiscountPct > 0 ? fmtCOP(shopOriginalPrice - shopEffectivePrice) : ''"
            :stock="shopSelectedVariant?.stock ?? 0"
            delivery-label="Envio a nivel nacional"
            :quantity="shopQty"
            :max-quantity="shopSelectedVariant?.stock || 1"
            :adding-to-cart="shopAddingToCart"
            :wishlist-loading="shopWishlistLoading"
            :is-wishlisted="shopIsWishlisted"
            :buy-now-label="shopBuyNowLabel"
            :buy-now-disabled="shopBuyNowDisabled"
            :product-uuid="shopProduct.uuid"
            @update:quantity="shopQty = $event"
            @add-to-cart="shopAddToCart"
            @buy-now="shopBuyNow"
            @toggle-wishlist="shopToggleWishlist"
          />
        </div>
      </div>
    </div>

    <!-- Secciones de contenido de la PDP (Fase 4, reingenieria PDP 2026-08-05) --
         orden y visibilidad vienen de shopProduct.content_blocks (ContentBlockConfig,
         ver DISENO_FASE2_SHOP_CONTENIDO_PDP_2026-08-05.md). Los componentes de
         @/components/renting/detail/ (2026-08-03) se reusan tal cual, sin fork --
         solo se agrega gating de visibilidad + `order` de CSS por bloque.
         ProductTabs.vue se retira: sus tabs "specs"/"video" duplicaban las
         secciones de Ficha tecnica/Videos de aqui abajo (hallazgo Fase 1). -->
    <div class="shop-detail-sections mt-5">
      <!-- Descripcion general -->
      <section v-if="blockVisible('description') && shopProduct.description" class="detail-section" :style="blockStyle('description')">
        <div class="section-head">
          <span class="section-kicker">Producto</span>
          <h2>Descripcion general</h2>
        </div>
        <DescriptionSection :text="shopProduct.description" />
      </section>

      <!-- Alcance -->
      <section v-if="blockVisible('scope') && shopProduct.scope" class="detail-section" :style="blockStyle('scope')">
        <div class="section-head">
          <span class="section-kicker">Producto</span>
          <h2>Alcance</h2>
        </div>
        <DescriptionSection :text="shopProduct.scope" />
      </section>

      <!-- Que incluye -->
      <section v-if="blockVisible('included') && shopProduct.included_items?.length" class="detail-section" :style="blockStyle('included')">
        <div class="section-head">
          <span class="section-kicker">Alcance</span>
          <h2>Que incluye</h2>
        </div>
        <EquipmentIncludedList :items="shopProduct.included_items" />
      </section>

      <!-- Que NO incluye -->
      <section v-if="blockVisible('excluded') && shopProduct.excluded_items?.length" class="detail-section" :style="blockStyle('excluded')">
        <div class="section-head">
          <span class="section-kicker">Alcance</span>
          <h2>Que NO incluye</h2>
        </div>
        <EquipmentExcludedList :items="shopProduct.excluded_items" />
      </section>

      <!-- Instalacion (Requirements) -->
      <section v-if="blockVisible('installation') && shopProduct.requirements?.length" class="detail-section" :style="blockStyle('installation')">
        <div class="section-head">
          <span class="section-kicker">Instalacion</span>
          <h2>Antes de comprar</h2>
        </div>
        <EquipmentRequirementList :items="shopProduct.requirements" />
      </section>

      <!-- Como funciona (ProductFunctioningStep, 2026-08-06) -->
      <section v-if="blockVisible('functioning') && shopProduct.functioning_steps?.length" class="detail-section" :style="blockStyle('functioning')">
        <div class="section-head">
          <span class="section-kicker">Funcionamiento</span>
          <h2>Como funciona</h2>
        </div>
        <div class="process-steps">
          <div v-for="step in shopProduct.functioning_steps" :key="step.uuid" class="process-step-card">
            <img v-if="step.image" :src="step.image" alt="" class="process-step-img">
            <span class="process-step-number">{{ step.step_number }}</span>
            <h4>{{ step.title }}</h4>
            <p v-if="step.description">{{ step.description }}</p>
            <span v-if="step.estimated_time" class="process-step-time"><i class="bi bi-clock me-1"></i>{{ step.estimated_time }}</span>
          </div>
        </div>
      </section>

      <!-- Soporte (servicios incluidos / opcionales) -->
      <section v-if="blockVisible('support') && (shopProduct.services_included?.length || shopProduct.optional_services?.length)" class="detail-section" :style="blockStyle('support')">
        <div class="section-head">
          <span class="section-kicker">Servicios</span>
          <h2>Instalacion y soporte</h2>
        </div>
        <EquipmentServiceList
          :included-services="shopProduct.services_included || []"
          :optional-services="shopProduct.optional_services || []"
        />
      </section>

      <!-- Beneficios (Features) -->
      <section v-if="blockVisible('benefits') && shopProduct.features?.length" class="detail-section" :style="blockStyle('benefits')">
        <div class="section-head">
          <span class="section-kicker">Caracteristicas</span>
          <h2>Beneficios</h2>
        </div>
        <EquipmentFeatureTable :features="shopProduct.features" />
      </section>

      <!-- Garantia -->
      <section v-if="blockVisible('warranty') && shopProduct.warranty" class="detail-section" :style="blockStyle('warranty')">
        <div class="section-head">
          <span class="section-kicker">Producto</span>
          <h2>Garantia</h2>
        </div>
        <DescriptionSection :text="shopProduct.warranty" />
      </section>

      <!-- Ficha tecnica -->
      <section v-if="blockVisible('specs') && shopProduct.specification_groups?.length" class="detail-section" :style="blockStyle('specs')">
        <div class="section-head">
          <span class="section-kicker">Ficha tecnica</span>
          <h2>Especificaciones tecnicas</h2>
        </div>
        <EquipmentSpecificationTable :groups="shopProduct.specification_groups" />
      </section>

      <!-- Documentacion -->
      <section v-if="blockVisible('documents') && shopProduct.documents?.length" class="detail-section" :style="blockStyle('documents')">
        <div class="section-head">
          <span class="section-kicker">Documentacion</span>
          <h2>Manuales y certificados</h2>
        </div>
        <div class="d-flex flex-column gap-3">
          <EquipmentManualList :documents="shopProduct.documents" :equipment-uuid="shopProduct.uuid" base-path="shop/products" />
          <EquipmentDocumentList :documents="shopProduct.documents" :equipment-uuid="shopProduct.uuid" base-path="shop/products" />
          <EquipmentDownloadSection :documents="shopProduct.documents" :equipment-uuid="shopProduct.uuid" base-path="shop/products" />
        </div>
      </section>

      <!-- Videos -->
      <section v-if="blockVisible('videos') && shopProduct.videos?.length" class="detail-section" :style="blockStyle('videos')">
        <div class="section-head">
          <span class="section-kicker">Video</span>
          <h2>Videos del producto</h2>
        </div>
        <EquipmentVideoGallery :videos="shopProduct.videos" />
      </section>

      <!-- FAQ -->
      <section v-if="blockVisible('faq') && shopProduct.faqs?.length" class="detail-section" :style="blockStyle('faq')">
        <div class="section-head">
          <span class="section-kicker">Preguntas frecuentes</span>
          <h2>Resolvemos tus dudas</h2>
        </div>
        <BaseAccordion :items="shopProduct.faqs" accent-color="#2563eb" />
      </section>

      <!-- Productos compatibles -->
      <section v-if="blockVisible('compatible') && shopProduct.compatible_products?.length" class="detail-section" :style="blockStyle('compatible')">
        <div class="section-head">
          <span class="section-kicker">Compatibilidad</span>
          <h2>Productos compatibles</h2>
        </div>
        <div class="row g-3">
          <div v-for="p in shopProduct.compatible_products" :key="p.uuid" class="col-6 col-md-3">
            <ItemCard :item="p" type="product" @view="shopGoToProduct(p)" @add-to-cart="shopQuickAddToCart(p)" />
          </div>
        </div>
      </section>

      <!-- Accesorios recomendados -->
      <section v-if="blockVisible('accessories') && shopProduct.accessories?.length" class="detail-section" :style="blockStyle('accessories')">
        <div class="section-head">
          <span class="section-kicker">Extras</span>
          <h2>Accesorios recomendados</h2>
        </div>
        <div class="row g-3">
          <div v-for="p in shopProduct.accessories" :key="p.uuid" class="col-6 col-md-3">
            <ItemCard :item="p" type="product" @view="shopGoToProduct(p)" @add-to-cart="shopQuickAddToCart(p)" />
          </div>
        </div>
      </section>

      <!-- Productos relacionados -->
      <section v-if="blockVisible('related') && shopProduct.related_products?.length" class="detail-section" :style="blockStyle('related')">
        <div class="section-head">
          <span class="section-kicker">Tambien te puede interesar</span>
          <h2>Productos relacionados</h2>
        </div>
        <div class="row g-3">
          <div v-for="p in shopProduct.related_products" :key="p.uuid" class="col-6 col-md-3">
            <ItemCard :item="p" type="product" @view="shopGoToProduct(p)" @add-to-cart="shopQuickAddToCart(p)" />
          </div>
        </div>
      </section>
    </div>

    <!-- Reseñas -->
    <div class="detail-section mt-4">
      <div class="d-flex align-items-center gap-3 mb-4 flex-wrap">
        <div class="section-head mb-0">
          <span class="section-kicker">Opiniones</span>
          <h2>Reseñas de clientes</h2>
        </div>
        <RatingDisplay v-if="shopProduct.review_count" :rating="shopRatingObject" :show-breakdown="false" class="ms-auto" />
        <span v-else class="text-muted small ms-auto">Sin resenas aun — se el primero</span>
      </div>

      <div v-if="authStore.isAuthenticated && !shopMyReview" class="review-form-card mb-4">
        <p class="fw-bold mb-3"><i class="bi bi-pencil me-1"></i>Escribe tu resena</p>
        <StarRating v-model:rating="shopReviewForm.rating" :size="22" class="mb-3" />
        <textarea
          v-model="shopReviewForm.comment"
          class="form-control mb-3"
          rows="3"
          placeholder="Cuéntanos tu experiencia con este producto..."
        ></textarea>
        <button
          type="button"
          class="btn-pill btn-pill-primary"
          :disabled="shopReviewLoading || !shopReviewForm.rating || !shopReviewForm.comment"
          @click="shopSubmitReview"
        >
          <span v-if="shopReviewLoading" class="spinner-border spinner-border-sm me-1"></span>
          <i v-else class="bi bi-send me-1"></i>
          Publicar resena
        </button>
        <p class="text-muted small mb-0 mt-2">
          Solo puedes resenar productos que ya hayas comprado y recibido.
        </p>
      </div>
      <!-- [AGREGADO 2026-08-06] Antes, un usuario no autenticado no veia ningun
           control ni mensaje en este bloque -- faltaba el link para iniciar
           sesion y poder resenar, mismo patron que ya tenia BaseReviews.vue
           (usado por Renting/Services) desde antes. -->
      <div v-else-if="!authStore.isAuthenticated" class="review-form-card mb-4">
        <RouterLink to="/login" class="fw-semibold">Inicia sesion</RouterLink>
        para calificar este producto.
      </div>

      <div v-if="shopReviewsLoading" class="text-center py-4">
        <div class="spinner-border spinner-border-sm text-primary"></div>
      </div>
      <div v-else-if="shopReviews.length === 0" class="text-muted small text-center py-4">
        Aun no hay resenas para este producto.
      </div>
      <div v-else class="d-flex flex-column gap-3">
        <div v-for="r in shopReviews" :key="r.uuid" class="review-card">
          <div class="d-flex align-items-start gap-3">
            <div class="review-avatar">{{ shopInitials(r.user_email) }}</div>
            <div class="flex-grow-1">
              <div class="d-flex align-items-center gap-2 flex-wrap mb-1">
                <span class="fw-semibold small">{{ shopMaskEmail(r.user_email) }}</span>
                <span v-if="r.is_verified_purchase" class="pd-chip pd-chip-success">
                  <i class="bi bi-patch-check-fill me-1"></i>Compra verificada
                </span>
                <StarRating :rating="r.rating" :size="14" read-only class="ms-auto" />
              </div>
              <div class="text-muted mb-2" style="font-size:.72rem">{{ shopFmtDate(r.created_at) }}</div>
              <p class="mb-0 small" style="white-space:pre-wrap">{{ r.comment }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, defineAsyncComponent } from 'vue';
import { useRouter } from 'vue-router';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { shopService } from '@/services/shop/shopService';
import { formatCOP } from '@/utils/money';
import { useCartStore } from '@/store/cart';
import { useWishlistStore } from '@/store/wishlist';
import { useAuthStore } from '@/store/auth';
import BaseGallery from '@/components/base/BaseGallery.vue';
import TagBadge from '@/components/marketplace/TagBadge.vue';
import UrgencyBanner from '@/components/marketplace/UrgencyBanner.vue';
import RatingDisplay from '@/components/marketplace/RatingDisplay.vue';
import StarRating from '@/components/ui/StarRating.vue';
import ProductPurchaseCard from '@/components/shop/detail/ProductPurchaseCard.vue';

// Catalogo enriquecido (2026-08-03) + bloques Fase 4 (2026-08-05): componentes
// below-fold de .shop-detail-sections, todos lazy via defineAsyncComponent --
// mismo patron que RentingDetailContent.vue, ahora tambien aplicado a
// DescriptionSection/ItemCard (antes estaticos, code-splitting real).
const EquipmentFeatureTable = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentFeatureTable.vue')
);
const DescriptionSection = defineAsyncComponent(() =>
  import('@/components/shop/detail/DescriptionSection.vue')
);
const ItemCard = defineAsyncComponent(() =>
  import('@/components/customer/ui/ItemCard.vue')
);
const EquipmentIncludedList = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentIncludedList.vue')
);
const EquipmentExcludedList = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentExcludedList.vue')
);
const EquipmentSpecificationTable = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentSpecificationTable.vue')
);
const EquipmentRequirementList = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentRequirementList.vue')
);
const EquipmentServiceList = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentServiceList.vue')
);
const EquipmentVideoGallery = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentVideoGallery.vue')
);
const EquipmentManualList = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentManualList.vue')
);
const EquipmentDocumentList = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentDocumentList.vue')
);
const EquipmentDownloadSection = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentDownloadSection.vue')
);
const BaseAccordion = defineAsyncComponent(() =>
  import('@/components/base/BaseAccordion.vue')
);

const props = defineProps({
  // Producto rico ya resuelto por el padre (shopService.detail()).
  product: { type: Object, required: true },
  // Resenas ya resueltas por el padre (shopService.reviews()) en el mismo
  // ciclo de carga -- el hijo se queda con una copia local porque publicar
  // una resena la refresca sin volver a pasar por el padre.
  initialReviews: { type: Array, default: () => [] },
});

const router = useRouter();
const { success, error: showError, info } = useToast();
const { handleError } = useErrorHandler();
const cartStore = useCartStore();
const wishlistStore = useWishlistStore();
const authStore = useAuthStore();

const shopProduct = ref(null);
const shopVariants = ref([]);
const shopSelectedVariant = ref(null);
const shopQty = ref(1);
const shopAddingToCart = ref(false);
const shopWishlistLoading = ref(false);
const shopReviews = ref([]);
const shopReviewsLoading = ref(false);
const shopReviewLoading = ref(false);
const shopReviewForm = ref({ rating: 0, comment: '' });

// Deriva el estado local del producto entregado por el padre. Es la misma
// secuencia que hacia fetchShopRichDetail() antes de la descomposicion
// (variante por defecto -> primera variante -> null).
watch(
  () => props.product,
  (value) => {
    shopProduct.value = value;
    shopVariants.value = value?.variants || [];
    shopSelectedVariant.value = shopVariants.value.find((v) => v.is_default) || shopVariants.value[0] || null;
    shopQty.value = 1;
  },
  { immediate: true }
);

watch(
  () => props.initialReviews,
  (value) => { shopReviews.value = value || []; },
  { immediate: true }
);

const shopMyReview = computed(() =>
  authStore.isAuthenticated && shopReviews.value.some((r) => r.user_email === authStore.user?.email)
);

// images como array de objetos {image,is_primary,alt_text} -- BaseGallery ya sabe leer
// esa forma directamente (patron Renting), no hace falta remapear a string[].
const shopAllImages = computed(() => {
  if (!shopProduct.value?.images?.length) return [];
  return shopProduct.value.images.slice().sort((a, b) => (b.is_primary ? 1 : 0) - (a.is_primary ? 1 : 0));
});

const shopOriginalPrice = computed(() => parseFloat(shopSelectedVariant.value?.price || 0));

// El precio mostrado es el neto con impuestos (price_info.final_price_net,
// ya calculado por el backend) -- evita la discrepancia entre lo que el
// cliente ve y lo que paga en checkout. Se conserva el fallback anterior
// por si price_info no viene en la respuesta.
const shopEffectivePrice = computed(() => {
  const info = shopSelectedVariant.value?.price_info;
  if (info?.final_price_net != null) return parseFloat(info.final_price_net);
  return parseFloat(
    shopSelectedVariant.value?.discounted_price ||
    shopSelectedVariant.value?.effective_price ||
    shopSelectedVariant.value?.price || 0
  );
});

const shopDiscountPct = computed(() => {
  if (!shopSelectedVariant.value?.discounted_price) return 0;
  if (shopOriginalPrice.value <= 0) return 0;
  return Math.round((1 - shopEffectivePrice.value / shopOriginalPrice.value) * 100);
});

const shopVariantAttributes = computed(() => {
  const attrs = shopSelectedVariant.value?.attributes;
  if (!attrs || typeof attrs !== 'object') return [];
  return Object.entries(attrs).map(([key, val]) => ({ key, val }));
});

const shopHasLogistics = computed(() =>
  shopSelectedVariant.value &&
  (shopSelectedVariant.value.weight || shopSelectedVariant.value.length ||
   shopSelectedVariant.value.width || shopSelectedVariant.value.height)
);

const shopIsWishlisted = computed(() =>
  !!shopSelectedVariant.value && wishlistStore.isInWishlist(shopSelectedVariant.value.uuid)
);

// Orquestacion de bloques de contenido (Fase 4, 2026-08-05) -- content_blocks ya
// viene resuelto (order + visibilidad, con defaults) desde ProductDetailSerializer.
const shopBlockMeta = computed(() => {
  const map = {};
  for (const block of shopProduct.value?.content_blocks || []) {
    map[block.block_type] = block;
  }
  return map;
});
function blockVisible(type) {
  return shopBlockMeta.value[type]?.is_visible !== false;
}
function blockStyle(type) {
  const order = shopBlockMeta.value[type]?.display_order;
  return order != null ? { order } : {};
}

// Adaptadores para los componentes marketplace/* (no usados hasta ahora por Shop) --
// se derivan de campos que YA vienen en el payload, sin nuevas consultas.
const shopRatingObject = computed(() => ({
  average_rating: shopProduct.value?.avg_rating || 0,
  total_count: shopProduct.value?.review_count || 0,
  rating_breakdown: {},
}));

const shopStockStatus = computed(() => (shopSelectedVariant.value?.stock ? 'available' : 'unavailable'));

const CONDITION_TAGS = {
  new: { code: 'NUEVO', label: 'Nuevo', color: 'success' },
  used: { code: 'USADO', label: 'Usado', color: 'secondary' },
  refurbished: { code: 'REACONDICIONADO', label: 'Reacondicionado', color: 'info' },
};
const shopConditionTag = computed(() => CONDITION_TAGS[shopProduct.value?.condition] || null);
const shopFeaturedTag = computed(() =>
  shopProduct.value?.is_featured ? { code: 'PREMIUM', label: 'Destacado', color: 'warning' } : null
);

const shopBuyNowLabel = computed(() => (cartStore.isEmpty ? 'Agrega al carrito primero' : 'Comprar ahora'));
const shopBuyNowDisabled = computed(() => cartStore.isEmpty);

function fmtCOP(value) {
  const number = parseFloat(value);
  if (!Number.isFinite(number) || number <= 0) return 'A cotizar';
  return formatCOP(number, { withSymbol: true });
}

function shopInitials(email) {
  return (email || '?').slice(0, 2).toUpperCase();
}

function shopMaskEmail(email) {
  if (!email) return 'Anonimo';
  const [user, domain] = email.split('@');
  return `${user.slice(0, 2)}***@${domain}`;
}

function shopFmtDate(d) {
  return d ? new Date(d).toLocaleDateString('es-CO', { year: 'numeric', month: 'short', day: 'numeric' }) : '';
}

async function fetchShopReviews(uuid) {
  shopReviewsLoading.value = true;
  try {
    const data = await shopService.reviews(uuid);
    shopReviews.value = data.results ?? data;
  } catch {
    shopReviews.value = [];
  } finally {
    shopReviewsLoading.value = false;
  }
}

async function shopAddToCart() {
  if (!authStore.isAuthenticated) {
    info('Inicia sesion para agregar al carrito');
    router.push('/login');
    return;
  }
  if (!shopSelectedVariant.value) return;
  shopAddingToCart.value = true;
  try {
    await cartStore.addItem(shopSelectedVariant.value.uuid, shopQty.value);
    success(`"${shopProduct.value.name}" agregado al carrito`);
  } catch {
    showError('No se pudo agregar al carrito');
  } finally {
    shopAddingToCart.value = false;
  }
}

async function shopToggleWishlist() {
  if (!authStore.isAuthenticated) {
    info('Inicia sesion para guardar en tu lista de deseos');
    router.push('/login');
    return;
  }
  if (!shopSelectedVariant.value) return;
  shopWishlistLoading.value = true;
  try {
    const added = await wishlistStore.toggle(shopSelectedVariant.value.uuid);
    success(added ? 'Agregado a tu lista de deseos' : 'Eliminado de tu lista de deseos');
  } catch {
    showError('No se pudo actualizar la lista de deseos');
  } finally {
    shopWishlistLoading.value = false;
  }
}

// Compatibles/accesorios/relacionados (Fase 4) -- ItemCard ya resuelve imagen/precio/
// stock correctamente para la forma real de ProductSerializer, se reusa tal cual.
function shopGoToProduct(item) {
  router.push({ name: 'product-detail', params: { uuid: item.uuid } });
}

async function shopQuickAddToCart(item) {
  const variant = item.variants?.find((v) => v.is_default) || item.variants?.[0];
  if (!variant) return;
  if (!authStore.isAuthenticated) {
    info('Inicia sesion para agregar al carrito');
    router.push('/login');
    return;
  }
  try {
    await cartStore.addItem(variant.uuid, 1);
    success(`"${item.name}" agregado al carrito`);
  } catch {
    showError('No se pudo agregar al carrito');
  }
}

function shopBuyNow() {
  if (!authStore.isAuthenticated) {
    info('Inicia sesion para continuar');
    router.push('/login');
    return;
  }
  if (cartStore.isEmpty) return;
  router.push('/checkout');
}

async function shopSubmitReview() {
  if (!shopReviewForm.value.rating || !shopReviewForm.value.comment.trim()) return;
  shopReviewLoading.value = true;
  try {
    await shopService.addReview(shopProduct.value.uuid, {
      rating: shopReviewForm.value.rating,
      comment: shopReviewForm.value.comment.trim(),
    });
    success('Resena publicada');
    shopReviewForm.value = { rating: 0, comment: '' };
    await fetchShopReviews(shopProduct.value.uuid);
    const data = await shopService.detail(shopProduct.value.uuid);
    shopProduct.value = { ...shopProduct.value, avg_rating: data.avg_rating, review_count: data.review_count };
  } catch (e) {
    handleError(e, 'Error al publicar la resena');
  } finally {
    shopReviewLoading.value = false;
  }
}
</script>

<style scoped>
/* ════════════════════════════════════════════════════════════════════════
   SHOP PDP — Rediseno Enterprise (2026-08-04). Mismo lenguaje visual que
   .rental-detail (RentingDetailContent.vue): #0f172a/#64748b/#e2e8f0/#2563eb,
   radios 12/14/16/999px, headings peso 850, sombra ambiental
   0 14px 30px rgba(15,23,42,.06). Namespaced bajo .product-detail-block.
   ════════════════════════════════════════════════════════════════════════ */
.product-detail-block .gallery-sticky { position: sticky; top: 88px; }

.product-detail-block .pd-gallery-badge {
  display: inline-block;
  border-radius: 999px;
  padding: .3rem .7rem;
  font-size: .75rem;
  font-weight: 800;
  margin-right: .4rem;
}
.product-detail-block .pd-gallery-badge-discount { background: #dc2626; color: #fff; }
.product-detail-block .pd-gallery-badge-featured { background: #fef3c7; color: #92400e; }

.product-detail-block .trust-row { border-top: 1px solid #e2e8f0; padding-top: 12px; }
.product-detail-block .trust-item {
  display: flex; align-items: center; gap: 5px;
  font-size: .78rem; color: #64748b;
}
.product-detail-block .trust-item i { font-size: 1rem; }

.product-detail-block .pay-methods { padding: .75rem; border: 1px solid #e2e8f0; border-radius: 14px; text-align: center; }
.product-detail-block .pay-methods-label { color: #64748b; font-size: .78rem; font-weight: 700; margin-bottom: .5rem; }
.product-detail-block .pay-chip {
  font-size: .72rem; background: #f8fafc; border: 1px solid #e2e8f0;
  border-radius: 999px; padding: .3rem .65rem; color: #374151;
}

.product-detail-block .pd-badges-row { display: flex; flex-wrap: wrap; gap: .5rem; margin-bottom: .75rem; }
.product-detail-block .pd-chip {
  display: inline-flex; align-items: center;
  background: #eff6ff; color: #2563eb; border: 1px solid #bfdbfe;
  border-radius: 999px; padding: .3rem .7rem; font-size: .78rem; font-weight: 700;
}
.product-detail-block .pd-chip-muted { background: #f8fafc; color: #64748b; border-color: #e2e8f0; }
.product-detail-block .pd-chip-success { background: #f0fdf4; color: #16a34a; border: 1px solid #bbf7d0; font-size: .68rem; }

.product-detail-block .pd-title {
  color: #0f172a; font-size: 2rem; font-weight: 900; line-height: 1.15; margin: 0 0 .6rem;
}
.product-detail-block .pd-short-desc { color: #64748b; font-size: .95rem; line-height: 1.6; margin-bottom: .6rem; }
.product-detail-block .pd-sku { color: #94a3b8; font-size: .8rem; margin-bottom: 1rem; }
.product-detail-block .pd-field-label { font-size: .84rem; font-weight: 800; color: #0f172a; margin-bottom: 0; }

.product-detail-block .variant-btn {
  border: 1.5px solid #e2e8f0; border-radius: 999px; padding: .5rem 1rem;
  background: #fff; color: #374151; font-size: .85rem; font-weight: 600;
  transition: all .15s ease; cursor: pointer;
}
.product-detail-block .variant-btn:hover:not(:disabled) { border-color: #93c5fd; color: #2563eb; }
.product-detail-block .variant-active { border-color: #2563eb; background: #eff6ff; color: #2563eb; }
.product-detail-block .variant-btn:disabled { opacity: .5; cursor: not-allowed; }
.product-detail-block .variant-btn:focus-visible { outline: 2px solid #2563eb; outline-offset: 2px; }

.product-detail-block .attr-chip {
  font-size: .78rem; background: #f8fafc; border: 1px solid #e2e8f0;
  border-radius: 999px; padding: .3rem .75rem; color: #374151;
}
.product-detail-block .attr-key { font-weight: 700; color: #0f172a; }

.product-detail-block .logistics-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px; padding: .85rem; }

.product-detail-block .purchase-sticky { position: static; }
@media (min-width: 992px) {
  .product-detail-block .purchase-sticky { position: sticky; top: 88px; }
}

.product-detail-block .btn-pill {
  display: inline-flex; align-items: center; justify-content: center;
  border-radius: 999px; padding: .65rem 1.3rem; font-weight: 800; font-size: .86rem;
  border: 1px solid transparent; cursor: pointer; transition: all .15s ease;
}
.product-detail-block .btn-pill:disabled { opacity: .55; cursor: not-allowed; }
.product-detail-block .btn-pill-primary { background: #2563eb; color: #fff; }
.product-detail-block .btn-pill-primary:hover:not(:disabled) { background: #1d4ed8; }

/* Secciones del catalogo enriquecido -- mismas reglas que .rental-detail
   .detail-sections/.detail-section/.section-head/.section-kicker en
   RentingDetailContent.vue (mismo acento azul #2563eb, ya el propio de
   shop), solo namespaced bajo .product-detail-block. */
.product-detail-block .shop-detail-sections {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1.25rem;
}

.product-detail-block .detail-section {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1.1rem;
}

.product-detail-block .section-head { margin-bottom: .9rem; }

.product-detail-block .section-kicker {
  display: block;
  color: #0369a1;
  font-size: .72rem;
  font-weight: 850;
  letter-spacing: .06em;
  text-transform: uppercase;
  margin-bottom: .25rem;
}

.product-detail-block .section-head h2 { color: #0f172a; font-size: 1.25rem; font-weight: 850; margin: 0; }

.product-detail-block .process-steps {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: .75rem;
}

.product-detail-block .process-step-card {
  position: relative;
  background: #eff6ff;
  border: 1px solid #dbeafe;
  border-radius: 14px;
  padding: 1rem .9rem .8rem;
}

.product-detail-block .process-step-img {
  width: 100%;
  height: 90px;
  object-fit: cover;
  border-radius: 10px;
  margin-bottom: .5rem;
}

.product-detail-block .process-step-number {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: #1e40af;
  color: #fff;
  font-weight: 800;
  font-size: .78rem;
  margin-bottom: .4rem;
}

.product-detail-block .process-step-card h4 {
  color: #0f172a;
  font-size: .88rem;
  font-weight: 800;
  margin: 0 0 .25rem;
}

.product-detail-block .process-step-card p {
  color: #475569;
  font-size: .8rem;
  line-height: 1.5;
  margin: 0 0 .4rem;
}

.product-detail-block .process-step-time {
  display: inline-flex;
  align-items: center;
  color: #1e40af;
  font-size: .72rem;
  font-weight: 700;
}

.product-detail-block .review-form-card {
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 16px; padding: 1.25rem;
}

.product-detail-block .review-avatar {
  width: 36px; height: 36px; min-width: 36px;
  background: #2563eb; color: #fff; border-radius: 999px;
  display: flex; align-items: center; justify-content: center;
  font-size: .75rem; font-weight: 800;
}

.product-detail-block .review-card {
  background: #fff; border: 1px solid #e2e8f0; border-radius: 14px; padding: 1rem;
  transition: box-shadow .15s ease;
}
.product-detail-block .review-card:hover { box-shadow: 0 4px 12px rgba(15, 23, 42, .08); }

@media (max-width: 991px) {
  .product-detail-block .gallery-sticky { position: static; }
}

@media (prefers-reduced-motion: reduce) {
  .product-detail-block .variant-btn,
  .product-detail-block .review-card,
  .product-detail-block .btn-pill {
    transition: none;
  }
}
</style>
