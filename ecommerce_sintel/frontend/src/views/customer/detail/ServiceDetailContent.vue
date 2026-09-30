<template>
  <!-- ══════════════════════════════════════════════════════════════════════
       SERVICES — Presentation Layer (extraida de PublicDetailView.vue,
       item P2-2 de la auditoria). El DTO unificado
       (unified/detail/?module=service) es demasiado escueto para este
       modulo (solo hero/gallery/pricing/reviews) -- el padre complementa
       con un fetch a servicesService.detail()/.packages() (endpoints
       publicos ya existentes, sin tocar backend) y entrega el resultado ya
       resuelto via props, exactamente en la misma secuencia que antes de la
       descomposicion. Vive bajo `.service-detail-block` para no chocar con
       las clases de Shop.

       Reingenieria SDP (2026-08-05): las secciones que antes leian
       SERVICE_FALLBACK (datos inventados, nunca conectados a un modelo real)
       ahora se alimentan del catalogo enriquecido real
       (TechnicalServiceDetailSerializer) y se orquestan con content_blocks
       (orden/visibilidad, mismo mecanismo que ShopDetailContent.vue) -- ver
       technical_services/.AGENT/docs/UI_MODULO_SERVICES.md.
       ══════════════════════════════════════════════════════════════════════ -->
  <div class="service-detail-block">
    <div class="row g-4 g-lg-5">
      <!-- Left Column: Gallery & Trust -->
      <div class="col-lg-5">
        <div class="gallery-sticky">
          <BaseGallery
            :images="serviceDetail.images || []"
            :title="serviceDetail.name"
            icon-class="bi-tools"
            theme="services"
            show-caption
          >
            <template #badge>
              <span v-if="serviceDetail.is_featured" class="sv-gallery-badge">
                <i class="bi bi-star-fill me-1"></i>Destacado
              </span>
            </template>
          </BaseGallery>

          <div class="trust-grid">
            <div><i class="bi bi-shield-check text-success"></i><span>Garantia tecnica</span></div>
            <div><i class="bi bi-credit-card text-primary"></i><span>Pago seguro</span></div>
            <div><i class="bi bi-file-earmark-check text-info"></i><span>Entregables</span></div>
            <div><i class="bi bi-headset text-warning"></i><span>Soporte postventa</span></div>
          </div>
        </div>
      </div>

      <!-- Right Column: Details & CTA -->
      <div class="col-lg-7">
        <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
          <TagBadge v-for="tag in serviceTags" :key="tag.code" :tag="tag" />
          <span v-if="serviceDetail.category?.name" class="badge bg-primary-subtle text-primary border border-primary-subtle">
            {{ serviceDetail.category.name }}
          </span>
          <span v-if="serviceDetail.level?.name" class="badge bg-light text-muted border">
            Nivel {{ serviceDetail.level.name }}
          </span>
          <span class="badge bg-success-subtle text-success border border-success-subtle">
            {{ serviceStatusLabel }}
          </span>
          <span class="text-muted small ms-lg-auto">
            <i class="bi bi-upc me-1"></i>{{ serviceCommercialCode }}
          </span>
        </div>

        <h1 class="service-title">{{ serviceDetail.name }}</h1>
        <p class="value-prop">{{ serviceValueProposition }}</p>

        <div class="quick-specs">
          <div v-for="spec in serviceQuickSpecs" :key="spec.label">
            <span>{{ spec.label }}</span>
            <strong>{{ spec.value }}</strong>
          </div>
        </div>

        <div class="package-panel">
          <div class="panel-head">
            <div>
              <span class="section-kicker">Solicitar servicio</span>
              <h2>Agenda tu servicio con {{ brandName }}</h2>
            </div>
            <span v-if="serviceMinPrice !== null" class="from-price">Desde {{ fmtCOP(serviceMinPrice) }}</span>
          </div>
          <div class="selected-package">
            <div>
              <h3>Selecciona la opcion, direccion, fecha y paga en linea</h3>
              <p>El paso a paso completo (Servicio, Direccion, Fecha, Pago) se realiza en la siguiente pantalla.</p>
            </div>
            <div class="cta-actions">
              <RouterLink
                v-if="serviceHasActiveVariant"
                :to="{ name: 'service-request', params: { uuid: serviceDetail.uuid } }"
                class="buy-btn"
              >
                <i :class="serviceIsFree ? 'bi bi-calendar-check me-2' : 'bi bi-bag-check me-2'"></i>{{ serviceIsFree ? 'Agendar visita' : 'Solicitar servicio' }}
              </RouterLink>
              <div v-else class="unavailable">
                <i class="bi bi-clock me-1"></i>No disponible
              </div>
              <button
                v-if="serviceHasActiveVariant && isWhatsAppReady"
                type="button"
                class="whatsapp-btn"
                @click="scheduleViaWhatsApp"
              >
                <i class="bi bi-whatsapp me-2"></i>Agendar por WhatsApp
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div class="detail-sections">
      <section v-if="servicePackages.length" class="detail-section">
        <div class="section-head">
          <span class="section-kicker">Paquetes comerciales</span>
          <h2>Paquetes disponibles</h2>
        </div>
        <div class="packages-grid">
          <ServicePackageCard
            v-for="pkg in servicePackages"
            :key="pkg.uuid"
            :pkg="pkg"
            @contract="goToServicePackageRequest"
          />
        </div>
      </section>

      <!-- Descripcion -->
      <section v-if="blockVisible('description') && serviceDetail.description" class="detail-section" :style="blockStyle('description')">
        <div class="section-head">
          <span class="section-kicker">Servicio</span>
          <h2>Descripcion</h2>
        </div>
        <DescriptionSection :text="serviceDetail.description" />
      </section>

      <!-- Alcance -->
      <section v-if="blockVisible('scope') && serviceDetail.scope" class="detail-section" :style="blockStyle('scope')">
        <div class="section-head">
          <span class="section-kicker">Servicio</span>
          <h2>Alcance</h2>
        </div>
        <DescriptionSection :text="serviceDetail.scope" />
      </section>

      <!-- Que incluye -->
      <section v-if="blockVisible('included') && serviceDetail.included_items?.length" class="detail-section" :style="blockStyle('included')">
        <div class="section-head">
          <span class="section-kicker">Alcance</span>
          <h2>Que incluye</h2>
        </div>
        <EquipmentIncludedList :items="serviceDetail.included_items" />
      </section>

      <!-- Que NO incluye -->
      <section v-if="blockVisible('excluded') && serviceDetail.excluded_items?.length" class="detail-section" :style="blockStyle('excluded')">
        <div class="section-head">
          <span class="section-kicker">Alcance</span>
          <h2>Que NO incluye</h2>
        </div>
        <EquipmentExcludedList :items="serviceDetail.excluded_items" />
      </section>

      <!-- Requisitos / Instalacion -->
      <section v-if="blockVisible('installation') && serviceDetail.requirements?.length" class="detail-section" :style="blockStyle('installation')">
        <div class="section-head">
          <span class="section-kicker">Instalacion</span>
          <h2>Requisitos previos</h2>
        </div>
        <EquipmentRequirementList :items="serviceDetail.requirements" />
      </section>

      <!-- Beneficios -->
      <section v-if="blockVisible('benefits') && serviceBenefitsList.length" class="detail-section" :style="blockStyle('benefits')">
        <div class="section-head">
          <span class="section-kicker">Beneficios</span>
          <h2>Por que elegir este servicio</h2>
        </div>
        <div class="row g-2">
          <div v-for="b in serviceBenefitsList" :key="b" class="col-6 col-md-4">
            <div class="benefit-chip"><i class="bi bi-check-circle-fill me-1"></i>{{ b }}</div>
          </div>
        </div>
      </section>

      <!-- Oferta de valor (copy comercial fijo, no forma parte de los bloques orquestables) -->
      <section class="detail-section">
        <div class="section-head">
          <span class="section-kicker">Oferta de valor</span>
          <h2>Que problema resuelve</h2>
        </div>
        <div class="value-grid">
          <article v-for="item in serviceValueCards" :key="item.title">
            <i :class="['bi', item.icon]"></i>
            <h3>{{ item.title }}</h3>
            <p>{{ item.copy }}</p>
          </article>
        </div>
      </section>

      <!-- Garantia -->
      <section v-if="blockVisible('warranty') && serviceDetail.warranty" class="detail-section" :style="blockStyle('warranty')">
        <div class="section-head">
          <span class="section-kicker">Servicio</span>
          <h2>Garantia</h2>
        </div>
        <DescriptionSection :text="serviceDetail.warranty" />
      </section>

      <!-- Cobertura -->
      <section v-if="blockVisible('coverage') && serviceDetail.coverage_notes" class="detail-section" :style="blockStyle('coverage')">
        <div class="section-head">
          <span class="section-kicker">Servicio</span>
          <h2>Cobertura</h2>
        </div>
        <DescriptionSection :text="serviceDetail.coverage_notes" />
      </section>

      <!-- Ficha tecnica -->
      <section v-if="blockVisible('specs') && serviceDetail.specification_groups?.length" class="detail-section" :style="blockStyle('specs')">
        <div class="section-head">
          <span class="section-kicker">Ficha tecnica</span>
          <h2>Especificaciones del servicio</h2>
        </div>
        <EquipmentSpecificationTable :groups="serviceDetail.specification_groups" />
      </section>

      <!-- Proceso -->
      <section v-if="blockVisible('process') && serviceDetail.process_steps?.length" class="detail-section" :style="blockStyle('process')">
        <div class="section-head">
          <span class="section-kicker">Proceso</span>
          <h2>Como se ejecuta el servicio</h2>
        </div>
        <div class="process-steps">
          <div v-for="step in serviceDetail.process_steps" :key="step.uuid" class="process-step-card">
            <img v-if="step.image" :src="step.image" alt="" class="process-step-img">
            <span class="process-step-number">{{ step.step_number }}</span>
            <h4>{{ step.title }}</h4>
            <p v-if="step.description">{{ step.description }}</p>
            <span v-if="step.estimated_time" class="process-step-time"><i class="bi bi-clock me-1"></i>{{ step.estimated_time }}</span>
          </div>
        </div>
      </section>

      <!-- Materiales utilizados -->
      <section v-if="blockVisible('materials') && serviceDetail.materials?.length" class="detail-section" :style="blockStyle('materials')">
        <div class="section-head">
          <span class="section-kicker">Materiales</span>
          <h2>Materiales utilizados</h2>
        </div>
        <div class="d-flex flex-column gap-2">
          <div v-for="m in serviceDetail.materials" :key="m.product_variant_uuid" class="material-row">
            <span>{{ m.product_name }} <code class="text-muted">{{ m.product_sku }}</code></span>
            <strong>x{{ m.quantity }}</strong>
          </div>
        </div>
      </section>

      <!-- Profesionales (ya existia, ahora orquestable) -->
      <section v-if="blockVisible('technicians')" class="detail-section" :style="blockStyle('technicians')">
        <div class="section-head">
          <span class="section-kicker">Profesionales</span>
          <h2>Tecnicos calificados para este servicio</h2>
        </div>
        <ServiceProfessionals :service-uuid="serviceDetail.uuid" />
      </section>

      <!-- Documentacion -->
      <section v-if="blockVisible('documents') && serviceDetail.documents?.length" class="detail-section" :style="blockStyle('documents')">
        <div class="section-head">
          <span class="section-kicker">Documentacion</span>
          <h2>Manuales y certificados</h2>
        </div>
        <div class="d-flex flex-column gap-3">
          <EquipmentManualList :documents="serviceDetail.documents" :equipment-uuid="serviceDetail.uuid" base-path="services/services" />
          <EquipmentDocumentList :documents="serviceDetail.documents" :equipment-uuid="serviceDetail.uuid" base-path="services/services" />
          <EquipmentDownloadSection :documents="serviceDetail.documents" :equipment-uuid="serviceDetail.uuid" base-path="services/services" />
        </div>
      </section>

      <!-- Videos -->
      <section v-if="blockVisible('videos') && serviceDetail.videos?.length" class="detail-section" :style="blockStyle('videos')">
        <div class="section-head">
          <span class="section-kicker">Video</span>
          <h2>Demostracion tecnica</h2>
        </div>
        <EquipmentVideoGallery :videos="serviceDetail.videos" />
      </section>

      <!-- FAQ -->
      <section v-if="blockVisible('faq') && serviceFaqs.length" class="detail-section" :style="blockStyle('faq')">
        <div class="section-head">
          <span class="section-kicker">Preguntas frecuentes</span>
          <h2>Resolvemos tus dudas</h2>
        </div>
        <BaseAccordion :items="serviceFaqs" accent-color="#d97706" />
      </section>

      <!-- Servicios compatibles -->
      <section v-if="blockVisible('compatible') && serviceDetail.compatible_services?.length" class="detail-section" :style="blockStyle('compatible')">
        <div class="section-head">
          <span class="section-kicker">Compatibilidad</span>
          <h2>Servicios compatibles</h2>
        </div>
        <div class="row g-3">
          <div v-for="s in serviceDetail.compatible_services" :key="s.uuid" class="col-6 col-md-3">
            <ItemCard :item="s" type="service" @view="goToService(s)" />
          </div>
        </div>
      </section>

      <!-- Servicios relacionados -->
      <section v-if="blockVisible('related') && serviceDetail.related_services?.length" class="detail-section" :style="blockStyle('related')">
        <div class="section-head">
          <span class="section-kicker">Tambien te puede interesar</span>
          <h2>Servicios relacionados</h2>
        </div>
        <div class="row g-3">
          <div v-for="s in serviceDetail.related_services" :key="s.uuid" class="col-6 col-md-3">
            <ItemCard :item="s" type="service" @view="goToService(s)" />
          </div>
        </div>
      </section>

      <!-- Productos recomendados (cross-module, shop.Product) -->
      <section v-if="blockVisible('recommended_products') && serviceDetail.recommended_products?.length" class="detail-section" :style="blockStyle('recommended_products')">
        <div class="section-head">
          <span class="section-kicker">Extras</span>
          <h2>Productos recomendados</h2>
        </div>
        <div class="row g-3">
          <div v-for="p in serviceDetail.recommended_products" :key="p.uuid" class="col-6 col-md-3">
            <ItemCard :item="p" type="product" @view="goToProduct(p)" @add-to-cart="quickAddToCart(p)" />
          </div>
        </div>
      </section>

      <section class="detail-section">
        <div class="section-head">
          <span class="section-kicker">Opiniones</span>
          <h2>Reseñas de clientes</h2>
        </div>
        <BaseReviews
          base-path="services/services"
          :entity-uuid="serviceDetail.uuid"
          accent-color="#d97706"
          item-label="este servicio"
        />
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, defineAsyncComponent, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { formatCOP } from '@/utils/money';
import { useToast } from '@/composables/useToast';
import { useCommunication } from '@/composables/useCommunication';
import { useCartStore } from '@/store/cart';
import { useAuthStore } from '@/store/auth';
import { useAppConfigStore } from '@/store/appConfig';

import BaseGallery from '@/components/base/BaseGallery.vue';
import TagBadge from '@/components/marketplace/TagBadge.vue';

// Below-fold: lazy. Reingenieria SDP (2026-08-05): reusa los mismos
// componentes genericos que ya comparten Renting/Shop (forma de dato
// title/description/icon/uuid, ya generica) en vez de duplicarlos --
// ServiceScopeList/ServiceFeatureList (string-only, construidos para
// SERVICE_FALLBACK) quedan sin uso porque los datos reales ya vienen con
// uuid/icon/description. DescriptionSection e ItemCard se reusan de Shop.
const ServiceProfessionals = defineAsyncComponent(() =>
  import('@/components/services/detail/ServiceProfessionals.vue')
);
const ServicePackageCard = defineAsyncComponent(() =>
  import('@/components/services/packages/ServicePackageCard.vue')
);
const BaseAccordion = defineAsyncComponent(() =>
  import('@/components/base/BaseAccordion.vue')
);
const BaseReviews = defineAsyncComponent(() =>
  import('@/components/base/BaseReviews.vue')
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
const EquipmentRequirementList = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentRequirementList.vue')
);
const EquipmentSpecificationTable = defineAsyncComponent(() =>
  import('@/components/renting/detail/EquipmentSpecificationTable.vue')
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

const props = defineProps({
  // Detalle rico ya resuelto por el padre (servicesService.detail()).
  serviceDetail: { type: Object, required: true },
  // Paquetes comerciales ya resueltos por el padre (servicesService.packages()).
  servicePackages: { type: Array, default: () => [] },
});

const router = useRouter();
// El numero de WhatsApp sale de organization.ContactInfo (via core/footer/), nunca
// hardcodeado; el boton solo aparece cuando ya se cargo un numero real.
const { isWhatsAppReady, ensurePhoneLoaded, openWhatsApp } = useCommunication();
onMounted(ensurePhoneLoaded);
const { success, error: showError, info } = useToast();
const cartStore = useCartStore();
const authStore = useAuthStore();
// White-label F7 (2026-08-14): antes 'Sintel' hardcodeado 2 veces en esta vista.
const appConfigStore = useAppConfigStore();
const brandName = computed(() => appConfigStore.brand.site_name || 'la plataforma');

const SERVICE_TAG_META = {
  OFERTA: { label: 'Oferta', color: 'danger' },
  NUEVO: { label: 'Nuevo', color: 'info' },
  MAS_SOLICITADO: { label: 'Mas solicitado', color: 'warning' },
  PREMIUM: { label: 'Premium', color: 'primary' },
  RECOMENDADO: { label: 'Recomendado', color: 'success' },
  HOT: { label: 'Hot', color: 'danger' },
  TOP_CALIFICADO: { label: 'Top calificado', color: 'warning' },
  IDEAL_EMPRESAS: { label: 'Ideal para empresas', color: 'primary' },
  CUPOS_LIMITADOS: { label: 'Cupos limitados', color: 'danger' },
};

const serviceTags = computed(() => {
  const codes = props.serviceDetail?.marketing?.tags || [];
  return codes.map((code) => ({ code, ...(SERVICE_TAG_META[code] || { label: code, color: 'primary' }) }));
});

const serviceMinPrice = computed(() => {
  const variants = props.serviceDetail?.variants || [];
  const prices = variants
    .filter((v) => v.is_active !== false)
    .map((v) => v.price_info?.total ?? v.calculated_price)
    .filter((p) => p != null && parseFloat(p) > 0)
    .map((p) => parseFloat(p));
  return prices.length ? Math.min(...prices) : null;
});

// Auditoria FASE 7 (2026-08-14): antes solo miraba la variante -- un servicio
// con is_active/is_purchasable=false pero con alguna variante activa seguia
// mostrando "Solicitar servicio", dejando que el cliente completara el wizard
// para recien ahi chocar con el rechazo de ServiceCommands.request_service()
// (`variant.service.is_purchasable`, ver services/commands.py:26). Ahora la
// condicion de nivel-servicio se evalua primero.
const serviceHasActiveVariant = computed(() =>
  props.serviceDetail?.is_active !== false &&
  props.serviceDetail?.is_purchasable !== false &&
  (props.serviceDetail?.variants?.some((v) => v.is_active !== false) ?? false)
);

// Servicio sin costo (visita diagnostica / levantamiento de informacion): todas
// las variantes activas valen 0 -> el CTA pasa a "Agendar visita".
const serviceIsFree = computed(() => {
  const active = (props.serviceDetail?.variants || []).filter((v) => v.is_active !== false);
  if (!active.length) return false;
  return active.every((v) => parseFloat(v.price_info?.total ?? v.calculated_price) === 0);
});

function scheduleViaWhatsApp() {
  const name = props.serviceDetail?.name || 'servicio';
  const verb = serviceIsFree.value ? 'agendar una visita' : 'agendar el servicio';
  openWhatsApp(`Hola, quiero ${verb}: ${name}.\n${window.location.href}`);
}

const serviceCommercialCode = computed(() => {
  const variantSku = props.serviceDetail?.variants?.find((v) => v.sku)?.sku;
  return variantSku || `SERV-${String(props.serviceDetail?.uuid || '').slice(0, 8)}`;
});

const serviceStatusLabel = computed(() =>
  props.serviceDetail?.is_active === false ? 'No disponible' : 'Disponible'
);

// marketing.main_message es real (ServiceMarketing); si el admin no lo cargo
// se conserva el mismo texto de respaldo que ya mostraba produccion.
const serviceValueProposition = computed(() =>
  props.serviceDetail?.marketing?.main_message ||
  'Incluye diagnostico, configuracion, puesta en marcha, capacitacion y garantia para que la solucion quede operando con respaldo profesional.'
);

const serviceDefaultHoursLabel = computed(() => {
  const first = props.serviceDetail?.variants?.find((v) => v.estimated_hours);
  return first ? `${first.estimated_hours} horas` : '6 horas estimadas';
});

// "Cobertura" del quick-spec ahora usa el campo real (coverage_notes) cuando
// existe -- antes era el texto fijo "Nacional" sin ningun dato detras.
const serviceQuickSpecs = computed(() => [
  { label: 'Duracion', value: serviceDefaultHoursLabel.value },
  { label: 'Personal', value: '2 tecnicos' },
  { label: 'Modalidad', value: 'En sitio, remoto o hibrido' },
  { label: 'Cobertura', value: props.serviceDetail?.coverage_notes?.trim() ? props.serviceDetail.coverage_notes : 'Nacional' },
]);

// marketing.quick_benefits es real (JSON [{icon,label}]).
const serviceBenefitsList = computed(() => {
  const benefits = props.serviceDetail?.marketing?.quick_benefits;
  if (Array.isArray(benefits)) {
    return benefits.map((b) => b.label).filter(Boolean);
  }
  return [];
});

const serviceValueCards = computed(() => [
  { icon: 'bi-bullseye', title: 'Problema', copy: 'Reduce fallas, tiempos muertos y riesgos operativos en infraestructura tecnica.' },
  { icon: 'bi-box2-heart', title: 'Recibes', copy: 'Servicio ejecutado, probado, documentado y entregado con evidencia.' },
  { icon: 'bi-award', title: `Por que ${brandName.value}`, copy: props.serviceDetail?.marketing?.trust_message || 'Equipo tecnico especializado, cobertura nacional, marcas compatibles y soporte postventa.' },
  { icon: 'bi-graph-up-arrow', title: 'Beneficio', copy: props.serviceDetail?.marketing?.social_proof_message || 'Mayor continuidad, seguridad, trazabilidad y control del sistema instalado.' },
]);

const serviceFaqs = computed(() => props.serviceDetail?.faqs || []);

// Orquestacion de bloques de contenido (reingenieria SDP, 2026-08-05) --
// content_blocks ya viene resuelto (order + visibilidad, con defaults propios
// de servicios, 18 bloques -- ajustado de 19 en la auditoria FASE 7
// 2026-08-14 al quitar 'support', ver shared/models.py SERVICE_DEFAULT_ORDER)
// desde TechnicalServiceDetailSerializer.
const serviceBlockMeta = computed(() => {
  const map = {};
  for (const block of props.serviceDetail?.content_blocks || []) {
    map[block.block_type] = block;
  }
  return map;
});
function blockVisible(type) {
  return serviceBlockMeta.value[type]?.is_visible !== false;
}
function blockStyle(type) {
  const order = serviceBlockMeta.value[type]?.display_order;
  return order != null ? { order } : {};
}

function fmtCOP(value) {
  const number = parseFloat(value);
  if (!Number.isFinite(number) || number <= 0) return 'A cotizar';
  return formatCOP(number, { withSymbol: true });
}

function goToServicePackageRequest(pkg) {
  router.push({
    name: 'service-request',
    params: { uuid: props.serviceDetail.uuid },
    query: { package: pkg.uuid },
  });
}

function goToService(service) {
  router.push({ name: 'service-detail', params: { uuid: service.uuid } });
}

function goToProduct(product) {
  router.push({ name: 'product-detail', params: { uuid: product.uuid } });
}

async function quickAddToCart(product) {
  const variant = product.variants?.find((v) => v.is_default) || product.variants?.[0];
  if (!variant) return;
  if (!authStore.isAuthenticated) {
    info('Inicia sesion para agregar al carrito');
    router.push('/login');
    return;
  }
  try {
    await cartStore.addItem(variant.uuid, 1);
    success(`"${product.name}" agregado al carrito`);
  } catch {
    showError('No se pudo agregar al carrito');
  }
}
</script>

<style scoped>
/* ════════════════════════════════════════════════════════════════════════
   SERVICES — CSS restaurado del ServiceDetailView.vue recuperado
   (git show 674dff8~1), namespaced bajo .service-detail-block para no
   colisionar con las clases de la rama Shop. Mismos valores que
   producción sirve hoy (acento teal #0f766e, acento ámbar #d97706 para
   FAQ/reseñas, radios 14-16px) — cero color inventado.
   ════════════════════════════════════════════════════════════════════════ */
.service-detail-block {
  background: #f8fafc;
}

.service-detail-block .gallery-sticky { position: sticky; top: 88px; }

.service-detail-block .sv-gallery-badge {
  position: absolute; top: .8rem; right: .8rem;
  background: #f59e0b; color: #0f172a;
  border-radius: 999px; padding: .28rem .7rem;
  font-size: .72rem; font-weight: 800;
}

.service-detail-block .trust-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: .55rem;
  margin-top: .9rem;
}

.service-detail-block .trust-grid div {
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

.service-detail-block .service-title {
  color: #0f172a;
  font-size: clamp(1.65rem, 3vw, 2.45rem);
  font-weight: 900;
  line-height: 1.08;
  margin: 0 0 .75rem;
}

.service-detail-block .value-prop {
  color: #475569;
  font-size: 1rem;
  line-height: 1.65;
  margin-bottom: 1rem;
}

.service-detail-block .quick-specs {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: .65rem;
  margin-bottom: 1rem;
}

.service-detail-block .quick-specs div,
.service-detail-block .package-panel,
.service-detail-block .detail-section {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
}

.service-detail-block .quick-specs div { padding: .75rem; }

.service-detail-block .quick-specs span {
  display: block;
  color: #64748b;
  font-size: .72rem;
  font-weight: 700;
}

.service-detail-block .quick-specs strong {
  display: block;
  color: #0f172a;
  font-size: .86rem;
  margin-top: .18rem;
}

.service-detail-block .package-panel {
  padding: 1rem;
  box-shadow: 0 14px 30px rgba(15,23,42,.06);
}

.service-detail-block .panel-head,
.service-detail-block .section-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: .9rem;
}

.service-detail-block .section-head { display: block; }

.service-detail-block .section-kicker {
  display: block;
  color: #0f766e;
  font-size: .72rem;
  font-weight: 850;
  letter-spacing: .08em;
  text-transform: uppercase;
  margin-bottom: .25rem;
}

.service-detail-block .panel-head h2,
.service-detail-block .section-head h2 {
  color: #0f172a;
  font-size: 1.25rem;
  font-weight: 850;
  margin: 0;
}

.service-detail-block .from-price {
  color: #0f766e;
  font-weight: 850;
  white-space: nowrap;
}

.service-detail-block .selected-package {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  border-top: 1px solid #e2e8f0;
  margin-top: .9rem;
  padding-top: .9rem;
}

.service-detail-block .selected-package h3 {
  color: #0f172a;
  font-size: 1rem;
  font-weight: 850;
  margin: 0 0 .2rem;
}

.service-detail-block .selected-package p {
  color: #64748b;
  font-size: .86rem;
  margin: 0;
}

.service-detail-block .buy-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #0f766e;
  color: #fff;
  text-decoration: none;
  border-radius: 999px;
  padding: .75rem 1.15rem;
  font-weight: 850;
  white-space: nowrap;
}

.service-detail-block .buy-btn:hover { background: #115e59; color: #fff; }

.service-detail-block .cta-actions {
  display: flex;
  flex-wrap: wrap;
  gap: .6rem;
  justify-content: flex-end;
}

.service-detail-block .whatsapp-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  color: #128c7e;
  border: 1.5px solid #25d366;
  border-radius: 999px;
  padding: .75rem 1.15rem;
  font-weight: 850;
  white-space: nowrap;
  cursor: pointer;
}

.service-detail-block .whatsapp-btn:hover { background: #25d366; color: #fff; }

.service-detail-block .unavailable {
  color: #64748b;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  padding: .7rem 1rem;
}

.service-detail-block .detail-sections {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1.25rem;
}

.service-detail-block .detail-section { padding: 1.1rem; }

.service-detail-block .value-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: .75rem;
}

.service-detail-block .packages-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1rem;
}

.service-detail-block .value-grid article {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 14px;
  padding: .9rem;
}

.service-detail-block .value-grid i {
  color: #0e7490;
  font-size: 1.35rem;
}

.service-detail-block .value-grid h3 {
  color: #0f172a;
  font-size: .95rem;
  font-weight: 850;
  margin: .45rem 0 .3rem;
}

.service-detail-block .value-grid p {
  color: #64748b;
  font-size: .88rem;
  line-height: 1.65;
  margin: 0;
}

.service-detail-block .benefit-chip {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
  border-radius: 12px;
  padding: .6rem .8rem;
  font-size: .85rem;
  font-weight: 700;
  height: 100%;
  display: flex;
  align-items: center;
}

.service-detail-block .process-steps {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: .75rem;
}

.service-detail-block .process-step-card {
  position: relative;
  background: #eff6ff;
  border: 1px solid #dbeafe;
  border-radius: 14px;
  padding: 1rem .9rem .8rem;
}

.service-detail-block .process-step-img {
  width: 100%;
  height: 90px;
  object-fit: cover;
  border-radius: 10px;
  margin-bottom: .5rem;
}

.service-detail-block .process-step-number {
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

.service-detail-block .process-step-card h4 {
  color: #0f172a;
  font-size: .88rem;
  font-weight: 800;
  margin: 0 0 .25rem;
}

.service-detail-block .process-step-card p {
  color: #475569;
  font-size: .8rem;
  line-height: 1.5;
  margin: 0 0 .4rem;
}

.service-detail-block .process-step-time {
  display: inline-flex;
  align-items: center;
  color: #1e40af;
  font-size: .72rem;
  font-weight: 700;
}

.service-detail-block .material-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: .6rem .8rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  font-size: .86rem;
}

.service-detail-block .material-row strong { color: #0f172a; }

@media (max-width: 991px) {
  .service-detail-block .gallery-sticky { position: static; }
  .service-detail-block .quick-specs,
  .service-detail-block .value-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 575px) {
  .service-detail-block .quick-specs,
  .service-detail-block .value-grid,
  .service-detail-block .trust-grid {
    grid-template-columns: 1fr;
  }
  .service-detail-block .selected-package,
  .service-detail-block .panel-head {
    align-items: flex-start;
    flex-direction: column;
  }
  .service-detail-block .buy-btn,
  .service-detail-block .whatsapp-btn { width: 100%; }
  .service-detail-block .cta-actions { width: 100%; }
}

/* Override global de tamaño de badge -- verificado contra el padding real
   medido en produccion (~4.2px/7.8px con font-size .78rem). Vivia en el
   <style scoped> de PublicDetailView.vue cuando las 3 ramas estaban en el
   mismo archivo; al separarlas, cada hijo necesita su propia copia (el
   scoped CSS del padre ya no alcanza el markup del hijo). */
.badge { padding: 0.375rem 0.6rem; font-size: 0.78rem; }
</style>
