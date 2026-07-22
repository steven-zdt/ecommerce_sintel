<template>
  <div class="rental-detail">
    <div class="container-xl py-3 py-lg-4">
      <nav class="mb-3" aria-label="breadcrumb">
        <ol class="breadcrumb breadcrumb-sm mb-0">
          <li class="breadcrumb-item">
            <RouterLink to="/alquiler" class="text-decoration-none text-muted">
              <i class="bi bi-hdd-rack me-1"></i>Renting
            </RouterLink>
          </li>
          <li v-if="categoryName" class="breadcrumb-item text-muted">{{ categoryName }}</li>
          <li class="breadcrumb-item active text-truncate" style="max-width:240px">{{ equipment?.name }}</li>
        </ol>
      </nav>

      <div v-if="loading" class="row g-4">
        <div class="col-lg-5">
          <div class="skeleton rounded-3" style="height:420px"></div>
        </div>
        <div class="col-lg-7">
          <div class="skeleton rounded mb-3" style="height:34px;width:76%"></div>
          <div class="skeleton rounded mb-4" style="height:92px"></div>
          <div class="skeleton rounded" style="height:260px"></div>
        </div>
      </div>

      <div v-else-if="equipment" class="row g-4 g-lg-5">
        <div class="col-lg-5">
          <div class="gallery-sticky">
            <BaseGallery :images="equipment.images || []" :title="equipment.name" icon-class="bi-hdd-rack" theme="renting">
              <template #badge="{ activeImage }">
                <span v-if="activeImage" class="eq-gallery-type-badge">{{ activeImage.image_type_display }}</span>
              </template>
            </BaseGallery>

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
                <span>Logistica opcional</span>
              </div>
              <div>
                <i class="bi bi-headset text-warning"></i>
                <span>Soporte postventa</span>
              </div>
            </div>

            <div class="availability-card">
              <span class="section-kicker">Disponibilidad</span>
              <h2>{{ availabilityLabel }}</h2>
              <p>{{ availabilityDetail }}</p>
              <RouterLink
                v-if="equipment.is_active"
                :to="{ name: 'rental-request', params: { uuid: equipment.uuid }, query: { variant: selectedVariant?.uuid } }"
                class="availability-link"
              >
                Consultar fechas exactas <i class="bi bi-arrow-right"></i>
              </RouterLink>
            </div>
          </div>
        </div>

        <div class="col-lg-7">
          <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
            <span v-if="brandName" class="badge bg-primary-subtle text-primary border border-primary-subtle">{{ brandName }}</span>
            <span v-if="categoryName" class="badge bg-light text-muted border">{{ categoryName }}</span>
            <span class="badge bg-success-subtle text-success border border-success-subtle">{{ equipment.is_active ? 'Disponible' : 'No disponible' }}</span>
            <span v-if="reviewSummary" class="text-muted small">
              <i class="bi bi-star-fill text-warning me-1"></i>{{ reviewSummary }}
            </span>
            <div class="ms-lg-auto d-flex gap-2">
              <button type="button" class="icon-action-btn" title="Compartir" @click="shareEquipment">
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

          <h1 class="equipment-title">{{ equipment.name }}</h1>
          <p v-if="equipment.description" class="value-prop">{{ equipment.description }}</p>

          <div v-if="marketing?.featured_benefit || marketing?.trust_message" class="d-flex flex-wrap gap-2 mb-3">
            <span v-if="marketing.featured_benefit" class="badge bg-primary-subtle text-primary border border-primary-subtle">
              <i class="bi bi-lightning-charge-fill me-1"></i>{{ marketing.featured_benefit }}
            </span>
            <span v-if="marketing.trust_message" class="badge bg-success-subtle text-success border border-success-subtle">
              <i class="bi bi-patch-check-fill me-1"></i>{{ marketing.trust_message }}
            </span>
          </div>

          <div class="quick-specs">
            <div v-for="spec in quickSpecs" :key="spec.label">
              <span>{{ spec.label }}</span>
              <strong>{{ spec.value }}</strong>
            </div>
          </div>

          <div class="package-panel">
            <div class="panel-head">
              <div>
                <span class="section-kicker">Configuracion</span>
                <h2>{{ variants.length > 1 ? 'Selecciona la variante del equipo' : 'Valor del alquiler' }}</h2>
              </div>
              <span v-if="fromPrice" class="from-price">Desde {{ fromPrice }}</span>
            </div>

            <div v-if="variants.length > 1" class="package-grid">
              <button
                v-for="variant in variants"
                :key="variant.uuid"
                class="package-card"
                :class="{ active: selectedVariant?.uuid === variant.uuid }"
                @click="selectedVariant = variant"
              >
                <span class="pack-name">{{ variant.sku }}</span>
                <strong>{{ priceSummary(variant) }}</strong>
                <small>{{ variant.stock }} unidad(es) disponibles</small>
              </button>
            </div>

            <div class="selected-package">
              <div>
                <h3>{{ selectedVariant ? selectedVariant.sku : equipment.name }}</h3>
                <p v-if="!hasPromoPricing">{{ priceSummary(selectedVariant) }}</p>
                <div v-else class="promo-price-block">
                  <span class="old-price">{{ moneyCompact(marketing.reference_price) }}</span>
                  <span class="promo-price">{{ moneyCompact(marketing.promo_price) }}</span>
                  <span v-if="marketing.discount_percentage" class="discount-badge">
                    AHORRA {{ marketing.discount_percentage }}%
                  </span>
                </div>
              </div>
              <button class="reserve-btn" :disabled="!selectedVariant || !equipment.is_active" @click="requestRental">
                <i class="bi bi-calendar-check me-2"></i>{{ ctaLabel }}
              </button>
            </div>

            <p v-if="marketing?.urgency_message" class="urgency-message">
              <i class="bi bi-alarm me-1"></i>{{ marketing.urgency_message }}
            </p>
          </div>

          <div v-if="marketing?.promo_banner_message" class="promo-banner">
            <i class="bi bi-megaphone-fill me-2"></i>{{ marketing.promo_banner_message }}
          </div>

          <div v-if="marketingTags.length" class="d-flex flex-wrap gap-2 mt-2">
            <span v-for="tag in marketingTags" :key="tag.code" class="badge marketing-tag" :class="tag.cls">
              {{ tag.label }}
            </span>
          </div>

          <p v-if="marketing?.main_message" class="marketing-main-message">{{ marketing.main_message }}</p>

          <p v-if="marketing?.social_proof_message" class="social-proof">
            <i class="bi bi-people-fill me-1"></i>{{ marketing.social_proof_message }}
          </p>
        </div>
      </div>

      <div v-if="equipment && !loading" class="detail-sections">
        <section v-if="marketing?.quick_benefits?.length" class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Beneficios</span>
            <h2>Lo que incluye tu alquiler</h2>
          </div>
          <div class="quick-benefits-grid">
            <div v-for="(b, idx) in marketing.quick_benefits" :key="idx" class="quick-benefit-card">
              <i :class="['bi', b.icon || 'bi-check-circle']"></i>
              <span>{{ b.label }}</span>
            </div>
          </div>
        </section>

        <section v-if="marketing?.use_cases?.length" class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Casos de uso</span>
            <h2>Donde puedes utilizar este equipo</h2>
          </div>
          <div class="use-cases-grid">
            <span v-for="uc in marketing.use_cases" :key="uc" class="use-case-chip">{{ uc }}</span>
          </div>
        </section>

        <section v-if="marketing?.purchase_price_reference" class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Comparativa economica</span>
            <h2>Comprar vs. Alquilar</h2>
          </div>
          <div class="compare-grid">
            <div class="compare-card">
              <span class="compare-label">Comprar</span>
              <strong>{{ moneyCompact(marketing.purchase_price_reference) }}</strong>
            </div>
            <i class="bi bi-arrow-right compare-arrow"></i>
            <div class="compare-card compare-card--highlight">
              <span class="compare-label">Alquilar</span>
              <strong>{{ moneyCompact(marketing.promo_price || marketing.reference_price || selectedVariant?.rental_price_per_day) }}</strong>
            </div>
            <div v-if="marketing.savings_percentage" class="compare-savings">
              Ahorras {{ marketing.savings_percentage }}%
            </div>
          </div>
          <p v-if="marketing.financial_message" class="text-muted small mt-2 mb-0">{{ marketing.financial_message }}</p>
        </section>

        <section v-if="equipment.included_items?.length || equipment.excluded_items?.length" class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Alcance del alquiler</span>
            <h2>Que incluye y que no incluye</h2>
          </div>
          <div class="scope-grid">
            <EquipmentIncludedList :items="equipment.included_items || []" />
            <EquipmentExcludedList :items="equipment.excluded_items || []" />
          </div>
        </section>

        <section v-if="equipment.features?.length" class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Caracteristicas</span>
            <h2>Lo que distingue a este equipo</h2>
          </div>
          <EquipmentFeatureTable :features="equipment.features || []" />
        </section>

        <section v-if="equipment.specification_groups?.length" class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Ficha tecnica</span>
            <h2>Especificaciones profesionales</h2>
          </div>
          <EquipmentSpecificationTable :groups="equipment.specification_groups || []" />
        </section>

        <section v-if="equipment.services_included?.length || equipment.optional_services?.length" class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Servicios</span>
            <h2>Servicios incluidos y opcionales</h2>
          </div>
          <EquipmentServiceList
            :included-services="equipment.services_included || []"
            :optional-services="equipment.optional_services || []"
          />
        </section>

        <section v-if="equipment.requirements?.length" class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Requisitos</span>
            <h2>Condiciones para el alquiler</h2>
          </div>
          <EquipmentRequirementList :items="equipment.requirements || []" />
        </section>

        <section v-if="hasDocumentation" class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Documentacion</span>
            <h2>Manuales, fichas y archivos</h2>
          </div>
          <div class="doc-columns">
            <div v-if="manualsCount">
              <h3 class="doc-subhead"><i class="bi bi-journal-text me-2"></i>Manuales</h3>
              <EquipmentManualList :documents="equipment.documents || []" :equipment-uuid="equipment.uuid" />
            </div>
            <div v-if="datasheetsCount">
              <h3 class="doc-subhead"><i class="bi bi-file-earmark-richtext me-2"></i>Fichas tecnicas</h3>
              <EquipmentDocumentList :documents="equipment.documents || []" :equipment-uuid="equipment.uuid" />
            </div>
            <div v-if="otherFilesCount">
              <h3 class="doc-subhead"><i class="bi bi-folder2-open me-2"></i>Archivos</h3>
              <EquipmentDownloadSection :documents="equipment.documents || []" :equipment-uuid="equipment.uuid" />
            </div>
          </div>
        </section>

        <section v-if="equipment.videos?.length" class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Video</span>
            <h2>Demostraciones</h2>
          </div>
          <EquipmentVideoGallery :videos="equipment.videos || []" />
        </section>

        <section v-if="equipment.faqs?.length" class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Preguntas frecuentes</span>
            <h2>Resolvemos tus dudas</h2>
          </div>
          <BaseAccordion :items="equipment.faqs || []" accent-color="#2563eb" />
        </section>

        <section class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Opiniones</span>
            <h2>Reseñas de clientes</h2>
          </div>
          <BaseReviews base-path="renting/equipment" :entity-uuid="equipment.uuid" accent-color="#2563eb" item-label="este equipo" />
        </section>

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

      <div v-else-if="!loading" class="text-center py-5">
        <i class="bi bi-exclamation-circle display-4 text-muted"></i>
        <p class="mt-3 text-muted">Equipo no encontrado.</p>
        <RouterLink to="/alquiler" class="btn btn-primary btn-sm">Volver a alquiler</RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useAuthStore } from '@/store/auth';
import { useSeo } from '@/composables/useSeo';

import BaseGallery from '@/components/base/BaseGallery.vue';
import EquipmentIncludedList from '@/components/renting/detail/EquipmentIncludedList.vue';
import EquipmentExcludedList from '@/components/renting/detail/EquipmentExcludedList.vue';
import EquipmentFeatureTable from '@/components/renting/detail/EquipmentFeatureTable.vue';
import EquipmentSpecificationTable from '@/components/renting/detail/EquipmentSpecificationTable.vue';
import EquipmentServiceList from '@/components/renting/detail/EquipmentServiceList.vue';
import EquipmentRequirementList from '@/components/renting/detail/EquipmentRequirementList.vue';
import EquipmentManualList from '@/components/renting/detail/EquipmentManualList.vue';
import EquipmentDocumentList from '@/components/renting/detail/EquipmentDocumentList.vue';
import EquipmentDownloadSection from '@/components/renting/detail/EquipmentDownloadSection.vue';
import EquipmentVideoGallery from '@/components/renting/detail/EquipmentVideoGallery.vue';
import BaseAccordion from '@/components/base/BaseAccordion.vue';
import BaseReviews from '@/components/base/BaseReviews.vue';

const api = useApi();
const toast = useToast();
const authStore = useAuthStore();
const route = useRoute();
const router = useRouter();
const { setSeo } = useSeo();

const loading = ref(true);
const equipment = ref(null);
const variants = ref([]);
const selectedVariant = ref(null);

const brandName = computed(() => equipment.value?.brand?.name || '');
const categoryName = computed(() => equipment.value?.category?.name || '');

// ─── Marketing (EquipmentMarketing) ────────────────────────────────────────────
// Toda esta seccion es 100% data-driven desde equipment.marketing -- si el
// admin no configuro nada, marketing es null y ninguno de estos bloques
// se muestra (ver v-if en el template). Nada hardcodeado por equipo.
const marketing = computed(() => equipment.value?.marketing || null);

const MARKETING_TAG_LABELS = {
  OFERTA: 'Oferta', NUEVO: 'Nuevo', MAS_ALQUILADO: 'Mas alquilado', PREMIUM: 'Premium',
  RECOMENDADO: 'Recomendado', HOT: 'Hot', TOP_VENTAS: 'Top ventas',
  IDEAL_EVENTOS: 'Ideal para eventos', ULTIMAS_UNIDADES: 'Ultimas unidades',
};
const MARKETING_TAG_STYLES = {
  OFERTA: 'bg-danger-subtle text-danger border-danger-subtle',
  NUEVO: 'bg-info-subtle text-info border-info-subtle',
  MAS_ALQUILADO: 'bg-primary-subtle text-primary border-primary-subtle',
  PREMIUM: 'bg-dark-subtle text-dark border-dark-subtle',
  RECOMENDADO: 'bg-success-subtle text-success border-success-subtle',
  HOT: 'bg-danger-subtle text-danger border-danger-subtle',
  TOP_VENTAS: 'bg-warning-subtle text-warning border-warning-subtle',
  IDEAL_EVENTOS: 'bg-primary-subtle text-primary border-primary-subtle',
  ULTIMAS_UNIDADES: 'bg-danger-subtle text-danger border-danger-subtle',
};
const marketingTags = computed(() => (marketing.value?.tags || []).map((code) => ({
  code, label: MARKETING_TAG_LABELS[code] || code, cls: MARKETING_TAG_STYLES[code] || 'bg-light text-dark border',
})));

// Precio efectivo mostrado en el panel principal: promo_price configurado
// gana sobre el precio de la variante -- si no hay marketing, se conserva el
// comportamiento anterior (priceSummary de la variante seleccionada).
const hasPromoPricing = computed(() => !!(marketing.value?.reference_price && marketing.value?.promo_price));
const ctaLabel = computed(() => marketing.value?.cta_label || 'Reservar ahora');

const totalStock = computed(() => variants.value.reduce((sum, v) => sum + (v.stock || 0), 0));

const isFavorite = ref(false);
const FAVORITES_KEY = 'sintel_renting_favorites';

function loadFavorites() {
  try {
    return JSON.parse(localStorage.getItem(FAVORITES_KEY) || '[]');
  } catch {
    return [];
  }
}

function toggleFavorite() {
  const favorites = loadFavorites();
  const uuid = equipment.value?.uuid;
  const index = favorites.indexOf(uuid);
  if (index >= 0) {
    favorites.splice(index, 1);
    isFavorite.value = false;
    toast.info('Eliminado de favoritos');
  } else {
    favorites.push(uuid);
    isFavorite.value = true;
    toast.success('Agregado a favoritos');
  }
  localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
}

async function shareEquipment() {
  const shareData = {
    title: equipment.value?.name,
    text: `Mira este equipo en alquiler: ${equipment.value?.name}`,
    url: window.location.href,
  };
  try {
    if (navigator.share) {
      await navigator.share(shareData);
    } else {
      await navigator.clipboard.writeText(window.location.href);
      toast.success('Enlace copiado al portapapeles');
    }
  } catch {
    // Usuario cancelo el dialogo nativo de compartir -- no es un error real.
  }
}

const quickSpecs = computed(() => [
  { label: 'Marca', value: brandName.value || 'Sintel' },
  { label: 'Categoria', value: categoryName.value || 'Equipo' },
  { label: 'Variantes', value: `${variants.value.length || 1}` },
  { label: 'Stock total', value: `${totalStock.value} unidad(es)` },
]);

const availabilityLabel = computed(() => {
  if (!equipment.value?.is_active || totalStock.value <= 0) return 'Sin disponibilidad activa';
  return 'Disponible para reserva';
});
const availabilityDetail = computed(() =>
  `${totalStock.value} unidad(es) en total. El motor de disponibilidad valida fechas exactas al momento de reservar.`,
);

const reviewSummary = computed(() => {
  const reviews = equipment.value?.reviews || [];
  if (!reviews.length) return '';
  const avg = reviews.reduce((sum, r) => sum + r.rating, 0) / reviews.length;
  return `${avg.toFixed(1)} (${reviews.length} reseña${reviews.length === 1 ? '' : 's'})`;
});

const manualsCount = computed(() => (equipment.value?.documents || []).filter((d) => d.document_type === 'MANUAL').length);
const datasheetsCount = computed(() => (equipment.value?.documents || []).filter((d) => d.document_type === 'FICHA_TECNICA').length);
const otherFilesCount = computed(() =>
  (equipment.value?.documents || []).filter((d) => d.document_type !== 'MANUAL' && d.document_type !== 'FICHA_TECNICA').length,
);
const hasDocumentation = computed(() => manualsCount.value || datasheetsCount.value || otherFilesCount.value);

function money(value) {
  const number = parseFloat(value);
  if (!Number.isFinite(number) || number <= 0) return 'A cotizar';
  return new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP', maximumFractionDigits: 0 }).format(number);
}

// Formato compacto ("520.000 COP") sin simbolo "$" repetido -- para usar
// cuando se muestran varios precios juntos en la misma tarjeta (comparativa
// comprar/alquilar, precio anterior + promocional).
function moneyCompact(value) {
  const number = parseFloat(value);
  if (!Number.isFinite(number) || number <= 0) return 'A cotizar';
  return `${new Intl.NumberFormat('es-CO', { maximumFractionDigits: 0 }).format(number)} COP`;
}

function priceSummary(variant) {
  if (!variant) return 'A cotizar';
  if (variant.rental_price_per_day) return `${money(variant.rental_price_per_day)} / dia`;
  if (variant.rental_price_per_hour) return `${money(variant.rental_price_per_hour)} / hora`;
  return 'A cotizar';
}

const fromPrice = computed(() => {
  const prices = variants.value
    .map((v) => parseFloat(v.rental_price_per_day || v.rental_price_per_hour || 0))
    .filter((p) => p > 0);
  if (!prices.length) return '';
  const cheapest = variants.value.find((v) => parseFloat(v.rental_price_per_day || v.rental_price_per_hour || 0) === Math.min(...prices));
  return priceSummary(cheapest);
});

async function fetchEquipment() {
  loading.value = true;
  try {
    const uuid = route.params.uuid;
    const res = await api.get(`renting/equipment/${uuid}/`);
    equipment.value = res.data;
    variants.value = res.data.variants || [];
    selectedVariant.value = variants.value.find((variant) => variant.uuid === route.query.variant) || variants.value[0] || null;
    isFavorite.value = loadFavorites().includes(equipment.value.uuid);

    setSeo({
      title: equipment.value.meta_title || equipment.value.name,
      description: equipment.value.meta_description || equipment.value.description,
      ogImage: equipment.value.og_image,
      jsonLd: {
        '@context': 'https://schema.org',
        '@type': 'Product',
        name: equipment.value.name,
        description: equipment.value.description,
        image: equipment.value.images?.[0]?.image,
        brand: brandName.value || undefined,
        offers: selectedVariant.value ? {
          '@type': 'Offer',
          priceCurrency: 'COP',
          price: selectedVariant.value.rental_price_per_day || selectedVariant.value.rental_price_per_hour || undefined,
          availability: equipment.value.is_active ? 'https://schema.org/InStock' : 'https://schema.org/OutOfStock',
        } : undefined,
      },
    });
  } catch {
    toast.error('Error al cargar el equipo');
  } finally {
    loading.value = false;
  }
}

function requestRental() {
  if (!authStore.isAuthenticated) {
    toast.info('Inicia sesion para realizar una reserva');
    router.push('/login');
    return;
  }
  router.push({
    name: 'rental-request',
    params: { uuid: equipment.value.uuid },
    query: { variant: selectedVariant.value?.uuid || undefined },
  });
}

onMounted(fetchEquipment);
</script>

<style scoped>
.rental-detail { background: #f8fafc; min-height: 100vh; }
.breadcrumb-sm { font-size: .82rem; }
.gallery-sticky { position: sticky; top: 88px; }
.eq-gallery-type-badge {
  position: absolute; top: .8rem; left: .8rem;
  background: rgba(15, 23, 42, .75); color: #fff;
  border-radius: 999px; padding: .25rem .65rem;
  font-size: .68rem; font-weight: 700;
}
.availability-card,
.package-panel,
.detail-section {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
}
.availability-card { padding: 1rem; margin-top: .9rem; }
.trust-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: .55rem;
  margin-top: .9rem;
}
.trust-grid div {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: .65rem;
  display: flex;
  align-items: center;
  gap: .45rem;
  color: #475569;
  font-size: .78rem;
  font-weight: 700;
}
.icon-action-btn {
  width: 38px;
  height: 38px;
  border-radius: 999px;
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #64748b;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: color .15s ease, border-color .15s ease, background .15s ease;
}
.icon-action-btn:hover { color: #2563eb; border-color: #bfdbfe; background: #eff6ff; }
.icon-action-btn.active { color: #e11d48; border-color: #fecdd3; background: #fff1f2; }
.section-kicker {
  display: block;
  color: #0369a1;
  font-size: .72rem;
  font-weight: 850;
  text-transform: uppercase;
  letter-spacing: .08em;
  margin-bottom: .25rem;
}
.availability-card h2,
.panel-head h2,
.section-head h2 {
  color: #0f172a;
  font-size: 1.1rem;
  font-weight: 850;
  letter-spacing: 0;
  margin: 0;
}
.availability-card p {
  color: #64748b;
  font-size: .85rem;
  line-height: 1.6;
  margin: .5rem 0 0;
}
.availability-link {
  display: inline-flex;
  align-items: center;
  gap: .35rem;
  margin-top: .6rem;
  color: #2563eb;
  font-size: .8rem;
  font-weight: 750;
  text-decoration: none;
}
.value-prop {
  color: #64748b;
  font-size: 1rem;
  line-height: 1.65;
  margin-bottom: 1rem;
}
.equipment-title {
  color: #0f172a;
  font-size: clamp(1.65rem, 3vw, 2.45rem);
  font-weight: 900;
  letter-spacing: 0;
  line-height: 1.08;
  margin: 0 0 .75rem;
}
.quick-specs {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: .65rem;
  margin-bottom: 1rem;
}
.quick-specs div {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: .75rem;
}
.quick-specs span {
  display: block;
  color: #64748b;
  font-size: .72rem;
  font-weight: 760;
}
.quick-specs strong {
  display: block;
  color: #0f172a;
  font-size: .86rem;
  margin-top: .18rem;
}
.package-panel { padding: 1rem; box-shadow: 0 14px 30px rgba(15, 23, 42, .06); }
.panel-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: .9rem;
}
.from-price { color: #2563eb; font-weight: 850; white-space: nowrap; }
.package-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: .65rem;
}
.package-card {
  text-align: left;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 14px;
  padding: .8rem;
  min-height: 104px;
}
.package-card.active {
  background: #eff6ff;
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37, 99, 235, .13);
}
.pack-name { display: block; color: #475569; font-size: .75rem; font-weight: 800; }
.package-card strong { display: block; color: #0f172a; font-size: 1.05rem; margin-top: .25rem; }
.package-card small { display: block; color: #64748b; margin-top: .15rem; }
.selected-package {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  border-top: 1px solid #e2e8f0;
  margin-top: .9rem;
  padding-top: .9rem;
}
.selected-package h3 { color: #0f172a; font-size: 1rem; font-weight: 850; margin: 0 0 .2rem; }
.selected-package p { color: #64748b; font-size: .86rem; margin: 0; }
.promo-price-block { display: flex; align-items: baseline; flex-wrap: wrap; gap: .5rem; }
.old-price { color: #94a3b8; font-size: .82rem; text-decoration: line-through; }
.promo-price { color: #2563eb; font-size: 1.35rem; font-weight: 900; }
.discount-badge {
  background: #dc2626; color: #fff; font-size: .68rem; font-weight: 850;
  padding: .18rem .5rem; border-radius: 999px; letter-spacing: .02em;
}
.urgency-message {
  color: #dc2626; font-size: .82rem; font-weight: 750; margin: .6rem 0 0;
}
.promo-banner {
  background: #fffbeb; border: 1px solid #fde68a; color: #92400e;
  border-radius: 12px; padding: .6rem .9rem; font-size: .82rem; font-weight: 700;
  margin-top: .9rem;
}
.marketing-tag { font-size: .7rem; font-weight: 750; }
.marketing-main-message {
  color: #334155; font-size: .9rem; line-height: 1.6; margin-top: .9rem; margin-bottom: 0;
}
.social-proof { color: #475569; font-size: .8rem; font-weight: 700; margin: .6rem 0 0; }
.quick-benefits-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: .65rem;
}
.quick-benefit-card {
  display: flex; align-items: center; gap: .5rem;
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 12px; padding: .75rem;
  color: #334155; font-size: .82rem; font-weight: 700;
}
.quick-benefit-card i { color: #2563eb; font-size: 1.1rem; }
.use-cases-grid { display: flex; flex-wrap: wrap; gap: .5rem; }
.use-case-chip {
  background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe;
  border-radius: 999px; padding: .35rem .85rem; font-size: .8rem; font-weight: 700;
}
.compare-grid {
  display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;
}
.compare-card {
  background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 14px;
  padding: .9rem 1.25rem; text-align: center; min-width: 160px;
}
.compare-card--highlight { background: #eff6ff; border-color: #2563eb; }
.compare-label { display: block; color: #64748b; font-size: .75rem; font-weight: 750; margin-bottom: .25rem; }
.compare-card strong { display: block; color: #0f172a; font-size: 1.15rem; }
.compare-card--highlight strong { color: #2563eb; }
.compare-arrow { color: #94a3b8; font-size: 1.25rem; }
.compare-savings {
  background: #dcfce7; color: #166534; font-weight: 850; font-size: .85rem;
  border-radius: 999px; padding: .4rem 1rem;
}
.reserve-btn {
  border: 0;
  background: #2563eb;
  color: #fff;
  border-radius: 999px;
  padding: .75rem 1.15rem;
  font-weight: 850;
  white-space: nowrap;
}
.reserve-btn:disabled { opacity: .55; cursor: not-allowed; }
.detail-sections { display: flex; flex-direction: column; gap: 1rem; margin-top: 1.25rem; }
.section-head { margin-bottom: .9rem; }
.detail-section { padding: 1rem; }
.scope-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: .75rem;
}
.doc-columns { display: flex; flex-direction: column; gap: 1.25rem; }
.doc-subhead {
  color: #0f172a;
  font-size: .88rem;
  font-weight: 800;
  margin: 0 0 .6rem;
}
.related-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: .75rem;
}
.related-card {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: .9rem;
  color: inherit;
  text-decoration: none;
}
.related-card i { color: #2563eb; font-size: 1.35rem; }
.related-card span {
  display: block;
  color: #64748b;
  font-size: .72rem;
  font-weight: 760;
  margin-top: .45rem;
}
.related-card strong {
  display: block;
  color: #0f172a;
  font-size: .86rem;
  margin-top: .3rem;
}
.skeleton {
  background: linear-gradient(90deg, #f1f5f9 25%, #e2e8f0 37%, #f1f5f9 63%);
  background-size: 400% 100%;
  animation: shimmer 1.4s infinite;
}
@keyframes shimmer {
  0% { background-position: 100% 50%; }
  100% { background-position: 0 50%; }
}
@media (max-width: 991px) {
  .gallery-sticky { position: static; }
  .quick-specs,
  .package-grid,
  .scope-grid,
  .quick-benefits-grid,
  .related-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
@media (max-width: 575px) {
  .quick-specs,
  .package-grid,
  .scope-grid,
  .trust-grid,
  .quick-benefits-grid,
  .related-grid { grid-template-columns: 1fr; }
  .panel-head,
  .selected-package { flex-direction: column; align-items: flex-start; }
  .reserve-btn { width: 100%; }
  .compare-grid { flex-direction: column; align-items: stretch; }
  .compare-arrow { transform: rotate(90deg); align-self: center; }
}
</style>
