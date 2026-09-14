<template>
  <!-- ══════════════════════════════════════════════════════════════════════
       RENTING — Presentation Layer (extraida de PublicDetailView.vue,
       item P2-2 de la auditoria). Reutiliza los componentes reales que
       produccion ya usa (BaseGallery, TagBadge, UrgencyBanner,
       DiscountBadge, BaseAccordion, BaseReviews, Equipment*List) en vez de
       markup ad-hoc. Todo el bloque vive bajo `.rental-detail` para que su
       CSS (calcado de RentalDetailView.vue) no choque con las clases de la
       rama Shop/Servicios.

       El fetch NO vive aqui: el padre (PublicDetailView.vue) resuelve el
       DTO unificado y lo entrega ya resuelto via la prop `detail`, igual
       que antes de la descomposicion (cero cambio de secuencia de carga).
       ══════════════════════════════════════════════════════════════════════ -->
  <div class="rental-detail">
    <div class="row g-4 g-lg-5">
      <!-- Left Column: Gallery & Availability -->
      <div class="col-lg-5">
        <div class="gallery-sticky">
          <BaseGallery
            :images="detail.gallery?.all_images || []"
            :title="detail.hero?.name"
            icon-class="bi-hdd-rack"
            theme="renting"
          >
            <template #badge="{ activeImage }">
              <span v-if="activeImage" class="eq-gallery-type-badge">
                {{ activeImage.image_type || 'Galería' }}
              </span>
            </template>
          </BaseGallery>

          <!-- Trust Grid -->
          <div class="trust-grid">
            <div>
              <i class="bi bi-shield-check text-success"></i>
              <span>Equipo certificado</span>
            </div>
            <div>
              <i class="bi bi-credit-card text-primary"></i>
              <span>Pago seguro</span>
            </div>
            <div>
              <i class="bi bi-truck text-info"></i>
              <span>Logística opcional</span>
            </div>
            <div>
              <i class="bi bi-headset text-warning"></i>
              <span>Soporte postventa</span>
            </div>
          </div>

          <!-- Availability Card -->
          <div class="availability-card">
            <span class="section-kicker">Disponibilidad</span>
            <h2>{{ detail.availability?.status_label }}</h2>
            <p>{{ detail.availability?.status_detail }}</p>
            <RouterLink
              v-if="detail.hero?.cta_enabled"
              :to="{ name: 'rental-request', params: { uuid: detail.uuid } }"
              class="availability-link"
            >
              Consultar fechas exactas <i class="bi bi-arrow-right"></i>
            </RouterLink>
          </div>
        </div>
      </div>

      <!-- Right Column: Details & Info -->
      <div class="col-lg-7">
        <!-- Badges & Actions -->
        <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
          <TagBadge v-for="tag in detail.marketing?.tags" :key="tag.code" :tag="tag" />

          <span v-if="detail.hero?.brand_name" class="badge bg-primary-subtle text-primary border border-primary-subtle">
            {{ detail.hero.brand_name }}
          </span>
          <span v-if="detail.hero?.category_name" class="badge bg-light text-muted border">
            {{ detail.hero.category_name }}
          </span>
          <span :class="getAvailBadge()">{{ detail.availability?.status_label }}</span>

          <div v-if="detail.reviews?.average_rating" class="rating-badge-inline">
            <i class="bi bi-star-fill text-warning"></i>
            <span class="rating-value">{{ detail.reviews.average_rating.toFixed(1) }}</span>
            <span class="rating-count">({{ detail.reviews.total_count }})</span>
          </div>

          <div class="ms-lg-auto d-flex gap-2">
            <button type="button" class="icon-action-btn" title="Compartir" @click="shareItem">
              <i class="bi bi-share"></i>
            </button>
            <button
              type="button"
              class="icon-action-btn"
              :class="{ active: isFavorite }"
              :title="isFavorite ? 'Quitar de favoritos' : 'Agregar a favoritos'"
              @click="toggleFavorite"
            >
              <i :class="['bi', isFavorite ? 'bi-heart-fill' : 'bi-heart']"></i>
            </button>
          </div>
        </div>

        <!-- Title & Description -->
        <h1 class="equipment-title">{{ detail.hero?.name }}</h1>
        <p v-if="detail.hero?.description" class="value-prop">{{ detail.hero.description }}</p>

        <!-- Marketing Messages -->
        <div v-if="detail.marketing?.featured_benefit || detail.marketing?.trust_message" class="d-flex flex-wrap gap-2 mb-3">
          <span v-if="detail.marketing?.featured_benefit" class="badge bg-primary-subtle text-primary border border-primary-subtle">
            <i class="bi bi-lightning-charge-fill me-1"></i>{{ detail.marketing.featured_benefit }}
          </span>
          <span v-if="detail.marketing?.trust_message" class="badge bg-success-subtle text-success border border-success-subtle">
            <i class="bi bi-check-circle-fill me-1"></i>{{ detail.marketing.trust_message }}
          </span>
        </div>

        <!-- Urgency Banner -->
        <UrgencyBanner
          :status="detail.availability?.status"
          :available-now="detail.availability?.available_now || 0"
          :total-stock="detail.availability?.total_stock || 0"
          :urgency-message="detail.marketing?.urgency_message"
        />

        <!-- Discount Badge -->
        <DiscountBadge
          v-if="detail.pricing?.has_promotion"
          :discount="detail.pricing?.discount_percentage"
          :amount="detail.pricing?.formatted_discount_amount"
        />

        <!-- Quick Benefits -->
        <div v-if="detail.marketing?.quick_benefits?.length" class="quick-benefits mb-4">
          <span class="section-kicker">Beneficios destacados</span>
          <div class="benefits-grid">
            <div v-for="benefit in detail.marketing.quick_benefits" :key="benefit.label" class="benefit-item">
              <i :class="['bi', benefit.icon || 'bi-check-circle-fill']" class="benefit-icon"></i>
              <span>{{ benefit.label }}</span>
            </div>
          </div>
        </div>

        <!-- Quick Specs: Marca / Categoria / Variantes / Stock total (orden y campos verificados contra produccion) -->
        <div class="quick-specs">
          <div>
            <span>Marca</span>
            <strong>{{ detail.hero?.brand_name || 'N/A' }}</strong>
          </div>
          <div>
            <span>Categoria</span>
            <strong>{{ detail.hero?.category_name || 'N/A' }}</strong>
          </div>
          <div>
            <span>Variantes</span>
            <strong>{{ rentingVariantsCount }}</strong>
          </div>
          <div>
            <span>Stock total</span>
            <strong>{{ detail.availability?.available_now || 0 }} unidad(es)</strong>
          </div>
        </div>

        <!-- Configuracion / Package Panel (estructura y valores calcados de produccion en vivo) -->
        <div class="package-panel">
          <div class="panel-head">
            <div>
              <span class="section-kicker">Configuracion</span>
              <h2>Valor del alquiler</h2>
            </div>
            <span class="from-price">Desde {{ detail.pricing?.formatted_price_per_day }} / dia</span>
          </div>
          <div class="selected-package">
            <div>
              <h3>{{ rentingPackageLabel }}</h3>
              <p>{{ detail.pricing?.formatted_price_per_day }} / dia</p>
            </div>
            <RouterLink
              v-if="detail.hero?.cta_enabled"
              :to="{ name: 'rental-request', params: { uuid: detail.uuid } }"
              class="reserve-btn"
            >
              <i class="bi bi-calendar-check me-2"></i>{{ detail.hero?.cta_label || 'Reservar ahora' }}
            </RouterLink>
            <p v-else-if="detail.hero?.cta_disabled_reason" class="text-danger small mb-0">
              {{ detail.hero.cta_disabled_reason }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Secciones inferiores: tarjetas individuales dentro de .detail-sections
         (estructura y espaciado calcados de produccion en vivo). -->
    <div class="detail-sections">
      <!-- Features -->
      <section v-if="detail?.technical?.features?.length" class="detail-section">
        <div class="section-head">
          <span class="section-kicker">Caracteristicas</span>
          <h2>Caracteristicas destacadas</h2>
        </div>
        <div class="row g-3">
          <div v-for="feature in detail.technical.features" :key="feature.title" class="col-md-6 col-lg-4">
            <div class="feature-card">
              <span v-if="feature.icon" :class="['feature-icon', `bi ${feature.icon}`]"></span>
              <h5>{{ feature.title }}</h5>
              <p>{{ feature.value }}</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Included vs Excluded -->
      <section v-if="detail?.included_items?.length || detail?.excluded_items?.length" class="detail-section">
        <div class="section-head">
          <span class="section-kicker">Alcance</span>
          <h2>Que incluye y que no</h2>
        </div>
        <div class="row g-3">
          <div v-if="detail?.included_items?.length" class="col-lg-6">
            <EquipmentIncludedList :items="detail.included_items" />
          </div>
          <div v-if="detail?.excluded_items?.length" class="col-lg-6">
            <EquipmentExcludedList :items="detail.excluded_items" />
          </div>
        </div>
      </section>

      <!-- Specifications by Group -->
      <section v-if="detail?.technical?.specification_groups?.length" class="detail-section">
        <div class="section-head">
          <span class="section-kicker">Ficha tecnica</span>
          <h2>Especificaciones tecnicas</h2>
        </div>
        <div class="row g-3">
          <div v-for="group in detail.technical.specification_groups" :key="group.name" class="col-lg-6">
            <div class="spec-group-card">
              <h5>{{ group.name }}</h5>
              <div class="specs-table">
                <div v-for="spec in group.specs" :key="spec.name" class="spec-row">
                  <span class="spec-name">{{ spec.name }}</span>
                  <span class="spec-val">{{ spec.value }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- Requirements -->
      <section v-if="detail?.technical?.requirements?.length" class="detail-section">
        <div class="section-head">
          <span class="section-kicker">Requisitos</span>
          <h2>Requisitos de alquiler</h2>
        </div>
        <EquipmentRequirementList :items="detail.technical.requirements" />
      </section>

      <!-- Videos -->
      <section v-if="detail?.videos?.length" class="detail-section">
        <div class="section-head">
          <span class="section-kicker">Video</span>
          <h2>Videos</h2>
        </div>
        <EquipmentVideoGallery :videos="detail.videos" />
      </section>

      <!-- Documents -->
      <section v-if="detail?.documents?.length" class="detail-section">
        <div class="section-head">
          <span class="section-kicker">Documentacion</span>
          <h2>Manuales y certificados</h2>
        </div>
        <EquipmentDocumentList :documents="detail.documents" :equipment-uuid="detail.uuid" />
      </section>

      <!-- FAQs -->
      <section v-if="detail?.faq?.length" class="detail-section">
        <div class="section-head">
          <span class="section-kicker">Preguntas frecuentes</span>
          <h2>Resolvemos tus dudas</h2>
        </div>
        <BaseAccordion :items="detail.faq" accent-color="#2563eb" />
      </section>

      <!-- Reviews (kicker + titulo verificados 1:1 contra produccion) -->
      <section class="detail-section">
        <div class="section-head">
          <span class="section-kicker">Opiniones</span>
          <h2>Reseñas de clientes</h2>
        </div>
        <BaseReviews
          base-path="renting/equipment"
          :entity-uuid="detail.uuid"
          accent-color="#2563eb"
          item-label="este equipo"
        />
      </section>

      <!-- Related Equipment -->
      <section v-if="detail?.related_items?.length" class="detail-section">
        <div class="section-head">
          <span class="section-kicker">Relacionados</span>
          <h2>Equipos relacionados</h2>
        </div>
        <div class="row g-3">
          <div v-for="item in detail.related_items" :key="item.uuid" class="col-md-6 col-lg-4">
            <RouterLink :to="{ name: 'rental-detail', params: { uuid: item.uuid } }" class="related-card text-decoration-none">
              <MediaImage
                :src="item.image_url"
                :alt="item.name"
                placeholder-icon="bi-hdd-rack"
                placeholder-bg="linear-gradient(135deg, #eff6ff, #dbeafe)"
                placeholder-color="#2563eb"
                class="related-media"
              />
              <h6>{{ item.name }}</h6>
              <span class="price">{{ item.price_from }}</span>
            </RouterLink>
          </div>
        </div>
      </section>

      <!-- Integraciones (hardcoded, verificado 1:1 contra produccion -- siempre visible en Renting) -->
      <section class="detail-section related-section">
        <div class="section-head">
          <span class="section-kicker">Integraciones</span>
          <h2>Completa la solucion</h2>
        </div>
        <div class="related-grid">
          <RouterLink to="/tienda" class="related-card">
            <i class="bi bi-box-seam"></i>
            <span>Shop</span>
            <strong>Accesorios, consumibles y repuestos compatibles</strong>
          </RouterLink>
          <RouterLink to="/servicios" class="related-card">
            <i class="bi bi-tools"></i>
            <span>Technical Services</span>
            <strong>Instalacion, configuracion, monitoreo y soporte</strong>
          </RouterLink>
          <RouterLink to="/cotizar" class="related-card">
            <i class="bi bi-file-earmark-text"></i>
            <span>Proyecto</span>
            <strong>Solucion temporal con alcance y SLA personalizado</strong>
          </RouterLink>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, defineAsyncComponent } from 'vue';
import { useToast } from '@/composables/useToast';

// Above-fold: carga eager. Below-fold: lazy via defineAsyncComponent, igual
// que hacia RentalDetailView.vue (el componente que se restauro).
import BaseGallery from '@/components/base/BaseGallery.vue';
import MediaImage from '@/components/ui/MediaImage.vue';
import DiscountBadge from '@/components/marketplace/DiscountBadge.vue';
import UrgencyBanner from '@/components/marketplace/UrgencyBanner.vue';
import TagBadge from '@/components/marketplace/TagBadge.vue';

const EquipmentIncludedList = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentIncludedList.vue')
);
const EquipmentExcludedList = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentExcludedList.vue')
);
const EquipmentRequirementList = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentRequirementList.vue')
);
const EquipmentDocumentList = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentDocumentList.vue')
);
const EquipmentVideoGallery = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentVideoGallery.vue')
);
const BaseAccordion = defineAsyncComponent(() =>
  import('@/components/base/BaseAccordion.vue')
);
const BaseReviews = defineAsyncComponent(() =>
  import('@/components/base/BaseReviews.vue')
);

const props = defineProps({
  // DTO unificado ya resuelto por el padre (unified/detail/?module=renting).
  detail: { type: Object, required: true },
});

const { success } = useToast();

const isFavorite = ref(false);
const FAVORITES_KEY = 'sintel_favorites';

// "Variantes" y el nombre del paquete seleccionado no tienen un campo
// dedicado en el DTO unificado -- se derivan de pricing.components (mismo
// criterio ya verificado contra produccion en vivo para este bloque).
const rentingVariantsCount = computed(() => props.detail?.pricing?.components?.length || 1);

const rentingPackageLabel = computed(() =>
  props.detail?.pricing?.components?.[0]?.name || props.detail?.hero?.category_name || 'Estandar'
);

function getAvailBadge() {
  const status = props.detail?.availability?.status;
  const base = 'badge border';
  return {
    available: `${base} bg-success-subtle text-success`,
    limited: `${base} bg-warning-subtle text-warning`,
    unavailable: `${base} bg-danger-subtle text-danger`,
  }[status] || base;
}

function loadFavorites() {
  try {
    return JSON.parse(localStorage.getItem(FAVORITES_KEY) || '[]');
  } catch {
    return [];
  }
}

function toggleFavorite() {
  const favorites = loadFavorites();
  const uuid = props.detail?.uuid;
  const index = favorites.indexOf(uuid);
  if (index >= 0) {
    favorites.splice(index, 1);
    isFavorite.value = false;
  } else {
    favorites.push(uuid);
    isFavorite.value = true;
  }
  localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
}

async function shareItem() {
  const shareData = {
    title: props.detail?.hero?.name,
    // Antes: `Mira este ${getModuleLabel().toLowerCase()}` -- en esta rama
    // moduleType siempre es 'renting', asi que el literal es identico.
    text: `Mira este equipo: ${props.detail?.hero?.name}`,
    url: window.location.href,
  };
  try {
    if (navigator.share) {
      await navigator.share(shareData);
    } else {
      await navigator.clipboard.writeText(window.location.href);
      success('Enlace copiado al portapapeles');
    }
  } catch {
    // Usuario canceló
  }
}

watch(
  () => props.detail?.uuid,
  (uuid) => { isFavorite.value = uuid ? loadFavorites().includes(uuid) : false; },
  { immediate: true }
);
</script>

<style scoped>
/* ════════════════════════════════════════════════════════════════════════
   RENTING — CSS re-verificado 1:1 contra sintel.net.co/alquiler/equipo/...
   en vivo (computed styles extraidos via JS, no adivinados). El intento
   anterior se baso en RentalDetailView.vue (git history) que resulto estar
   desactualizado respecto a lo que produccion sirve hoy -- produccion usa
   un sistema de tarjetas blancas con borde #e2e8f0 y acento azul #2563eb
   (radios 14-16px, boton pildora), no el estilo de gradiente/var(--bs-*)
   del archivo recuperado. Mismo patron ya usado en .service-detail-block,
   solo con acento azul en vez de teal.
   ════════════════════════════════════════════════════════════════════════ */
.rental-detail { background: #fff; }

.rental-detail .gallery-sticky { position: sticky; top: 88px; }

.rental-detail .eq-gallery-type-badge {
  display: inline-block;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 0.25rem;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
}

.rental-detail .section-kicker {
  display: block;
  color: #0369a1;
  font-size: .72rem;
  font-weight: 850;
  letter-spacing: .06em;
  text-transform: uppercase;
  margin-bottom: .25rem;
}

.rental-detail .trust-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: .6rem;
  margin-top: .9rem;
}

.rental-detail .trust-grid > div {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: .65rem;
  display: flex;
  flex-direction: row;
  align-items: center;
  text-align: left;
  gap: .5rem;
  font-size: .8rem;
  color: #333;
}

.rental-detail .trust-grid i { font-size: 1.1rem; flex-shrink: 0; }

.rental-detail .availability-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1rem;
  margin-top: .9rem;
}

.rental-detail .availability-card h2 {
  font-size: 1.1rem;
  font-weight: 850;
  color: #0f172a;
  margin: 0 0 .25rem;
}

.rental-detail .availability-card p {
  font-size: .85rem;
  color: #64748b;
  margin-bottom: .75rem;
}

.rental-detail .availability-link {
  display: inline-flex;
  align-items: center;
  gap: .4rem;
  color: #2563eb;
  text-decoration: none;
  font-weight: 750;
  font-size: .8rem;
  transition: all 0.2s ease;
}

.rental-detail .availability-link:hover { text-decoration: underline; }

.rental-detail .icon-action-btn {
  width: 38px;
  height: 38px;
  padding: 0;
  border: 1px solid #e2e8f0;
  background: #fff;
  border-radius: 999px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #64748b;
  transition: all 0.2s ease;
}

.rental-detail .icon-action-btn:hover { border-color: #adb5bd; }

.rental-detail .icon-action-btn.active { color: #dc3545; border-color: #dc3545; }

.rental-detail .equipment-title {
  font-size: 2.4rem;
  font-weight: 900;
  color: #0f172a;
  line-height: 1.15;
  margin: .5rem 0 .75rem;
}

.rental-detail .value-prop {
  font-size: 1rem;
  color: #64748b;
  line-height: 1.65;
  margin-bottom: 1rem;
}

.rental-detail .rating-badge-inline {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  font-size: 0.85rem;
}

.rental-detail .rating-badge-inline .rating-value { font-weight: 700; color: #0f172a; }

.rental-detail .rating-badge-inline .rating-count { color: #64748b; }

.rental-detail .quick-benefits { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px; padding: 1rem; }

.rental-detail .benefits-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: .75rem;
  margin-top: .75rem;
}

.rental-detail .benefit-item { display: flex; align-items: center; gap: 0.5rem; font-size: 0.85rem; color: #333; }

.rental-detail .benefit-icon { color: #16a34a; font-size: 1.15rem; }

/* Quick Specs: Marca / Categoria / Variantes / Stock total */
.rental-detail .quick-specs {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: .65rem;
  margin-bottom: 1rem;
}

.rental-detail .quick-specs > div {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: .75rem;
}

.rental-detail .quick-specs span {
  display: block;
  color: #64748b;
  font-size: .72rem;
  font-weight: 700;
}

.rental-detail .quick-specs strong {
  display: block;
  color: #0f172a;
  font-size: .86rem;
  margin-top: .18rem;
}

/* Configuracion / Package Panel */
.rental-detail .package-panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1rem;
  box-shadow: 0 14px 30px rgba(15, 23, 42, .06);
}

.rental-detail .panel-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: .9rem;
}

.rental-detail .panel-head h2 {
  color: #0f172a;
  font-size: 1.25rem;
  font-weight: 850;
  margin: 0;
}

.rental-detail .from-price { color: #2563eb; font-weight: 850; white-space: nowrap; }

.rental-detail .selected-package {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  border-top: 1px solid #e2e8f0;
  margin-top: .9rem;
  padding-top: .9rem;
}

.rental-detail .selected-package h3 { color: #0f172a; font-size: 1rem; font-weight: 850; margin: 0 0 .2rem; }

.rental-detail .selected-package p { color: #64748b; font-size: .86rem; margin: 0; }

.rental-detail .reserve-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #2563eb;
  color: #fff;
  text-decoration: none;
  border-radius: 999px;
  padding: .75rem 1.15rem;
  font-weight: 850;
  white-space: nowrap;
  border: none;
}

.rental-detail .reserve-btn:hover { background: #1d4ed8; color: #fff; }

/* Secciones inferiores: tarjetas dentro de .detail-sections */
.rental-detail .detail-sections {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1.25rem;
}

.rental-detail .detail-section {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1.1rem;
}

.rental-detail .section-head { margin-bottom: .9rem; }

.rental-detail .section-head h2 { color: #0f172a; font-size: 1.25rem; font-weight: 850; margin: 0; }

.rental-detail .feature-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 1rem;
  text-align: center;
  transition: all 0.2s ease;
}

.rental-detail .feature-card:hover { box-shadow: 0 4px 12px rgba(15, 23, 42, .08); transform: translateY(-2px); }

.rental-detail .feature-icon { font-size: 1.75rem; color: #2563eb; display: block; margin-bottom: .6rem; }

.rental-detail .feature-card h5 { font-size: .92rem; font-weight: 700; color: #0f172a; margin-bottom: .35rem; }

.rental-detail .feature-card p { font-size: .82rem; color: #64748b; margin: 0; }

.rental-detail .spec-group-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px; padding: 1rem; }

.rental-detail .spec-group-card h5 { font-weight: 700; color: #0f172a; margin-bottom: .75rem; font-size: .92rem; }

.rental-detail .specs-table { display: flex; flex-direction: column; gap: 0.4rem; }

.rental-detail .spec-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.4rem 0;
  border-bottom: 1px solid #e2e8f0;
  font-size: .82rem;
}

.rental-detail .spec-row:last-child { border-bottom: none; }

.rental-detail .spec-name { color: #64748b; font-weight: 500; }

.rental-detail .spec-val { font-weight: 600; color: #0f172a; }

.rental-detail .related-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: .75rem; }

.rental-detail .related-card {
  display: block;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: .9rem;
  transition: all 0.2s ease;
  overflow: hidden;
  color: inherit;
}

.rental-detail .related-card:hover { box-shadow: 0 4px 12px rgba(15, 23, 42, .08); transform: translateY(-2px); }

.rental-detail .related-card i { font-size: 1.35rem; color: #2563eb; display: block; margin-bottom: .5rem; }

.rental-detail .related-card span { display: block; font-size: .72rem; font-weight: 700; color: #64748b; margin-bottom: .25rem; }

.rental-detail .related-media {
  width: 100%;
  height: 180px;
  border-radius: 10px;
  margin-bottom: 0.6rem;
  overflow: hidden;
  display: block;
}
.rental-detail .related-media :deep(.mi-img) { border-radius: 10px; }

.rental-detail .related-card h6 {
  font-weight: 700;
  margin-bottom: 0.3rem;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rental-detail .related-card strong { display: block; font-weight: 700; color: #0f172a; font-size: .86rem; }

.rental-detail .price { display: block; color: #2563eb; font-weight: 700; font-size: 1rem; }

@media (max-width: 992px) {
  .rental-detail .gallery-sticky { position: static; }
  .rental-detail .quick-specs { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .rental-detail .related-grid { grid-template-columns: 1fr; }
}

@media (max-width: 576px) {
  .rental-detail .trust-grid { grid-template-columns: 1fr; }
  .rental-detail .selected-package,
  .rental-detail .panel-head { align-items: flex-start; flex-direction: column; }
  .rental-detail .reserve-btn { justify-content: center; }
}

/* Override global de tamaño de badge -- verificado contra el padding real
   medido en produccion (~4.2px/7.8px con font-size .78rem). Vivia en el
   <style scoped> de PublicDetailView.vue cuando las 3 ramas estaban en el
   mismo archivo; al separarlas, cada hijo necesita su propia copia (el
   scoped CSS del padre ya no alcanza el markup del hijo). */
.badge { padding: 0.375rem 0.6rem; font-size: 0.78rem; }
</style>
