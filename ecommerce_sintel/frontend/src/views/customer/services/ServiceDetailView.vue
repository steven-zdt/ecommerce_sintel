<template>
  <div class="service-detail">
    <div class="container-xl py-3 py-lg-4">

      <nav class="mb-3" aria-label="breadcrumb">
        <ol class="breadcrumb breadcrumb-sm mb-0">
          <li class="breadcrumb-item">
            <RouterLink to="/servicios" class="text-decoration-none text-muted">
              <i class="bi bi-tools me-1"></i>Servicios
            </RouterLink>
          </li>
          <li v-if="service?.category?.name" class="breadcrumb-item text-muted">
            {{ service.category.name }}
          </li>
          <li class="breadcrumb-item active text-truncate" style="max-width:260px">
            {{ service?.name }}
          </li>
        </ol>
      </nav>

      <div v-if="loading" class="row g-4">
        <div class="col-lg-5">
          <div class="skeleton rounded-3" style="height:420px"></div>
          <div class="d-flex gap-2 mt-2">
            <div v-for="i in 4" :key="i" class="skeleton rounded-2" style="width:72px;height:72px"></div>
          </div>
        </div>
        <div class="col-lg-7">
          <div class="skeleton rounded mb-3" style="height:34px;width:72%"></div>
          <div class="skeleton rounded mb-2" style="height:18px;width:42%"></div>
          <div class="skeleton rounded mb-4" style="height:86px"></div>
          <div class="skeleton rounded" style="height:260px"></div>
        </div>
      </div>

      <div v-else-if="service" class="row g-4 g-lg-5">
        <div class="col-lg-5">
          <div class="gallery-sticky">
            <BaseGallery :images="allImages" :title="service.name" :icon-class="service.icon_class || 'bi-tools'" theme="services">
              <template #badge>
                <span v-if="service.is_featured" class="sv-gallery-badge">
                  <i class="bi bi-star-fill me-1"></i>Destacado
                </span>
              </template>
            </BaseGallery>

            <div class="trust-grid">
              <div>
                <i class="bi bi-shield-check text-success"></i>
                <span>Garantia tecnica</span>
              </div>
              <div>
                <i class="bi bi-credit-card text-primary"></i>
                <span>Pago seguro</span>
              </div>
              <div>
                <i class="bi bi-file-earmark-check text-info"></i>
                <span>Entregables</span>
              </div>
              <div>
                <i class="bi bi-headset text-warning"></i>
                <span>Soporte postventa</span>
              </div>
            </div>
          </div>
        </div>

        <div class="col-lg-7">
          <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
            <span v-if="service.category?.name" class="badge bg-primary-subtle text-primary border border-primary-subtle">
              {{ service.category.name }}
            </span>
            <span v-if="service.level?.name" class="badge bg-light text-muted border">
              Nivel {{ service.level.name }}
            </span>
            <span class="badge bg-success-subtle text-success border border-success-subtle">
              {{ serviceStatus }}
            </span>
            <span v-if="commercialCode" class="text-muted small ms-lg-auto">
              <i class="bi bi-upc me-1"></i>{{ commercialCode }}
            </span>
          </div>

          <h1 class="service-title">{{ service.name }}</h1>
          <p class="value-prop">{{ valueProposition }}</p>

          <div class="quick-specs">
            <div v-for="spec in quickSpecs" :key="spec.label">
              <span>{{ spec.label }}</span>
              <strong>{{ spec.value }}</strong>
            </div>
          </div>

          <div class="package-panel">
            <div class="panel-head">
              <div>
                <span class="section-kicker">Solicitar servicio</span>
                <h2>Agenda tu servicio con Sintel</h2>
              </div>
              <span v-if="minPrice !== null" class="from-price">Desde {{ fmtCOP(minPrice) }}</span>
            </div>

            <div class="selected-package">
              <div>
                <h3>Selecciona la opcion, direccion, fecha y paga en linea</h3>
                <p>El paso a paso completo (Servicio, Direccion, Fecha, Pago) se realiza en la siguiente pantalla.</p>
              </div>
              <RouterLink
                v-if="hasActiveVariant"
                :to="`/servicios/${service.uuid}/solicitar`"
                class="buy-btn"
              >
                <i class="bi bi-bag-check me-2"></i>Solicitar servicio
              </RouterLink>
              <div v-else class="unavailable">
                <i class="bi bi-clock me-1"></i>No disponible
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="service && !loading" class="detail-sections">
        <section v-if="packages.length" class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Paquetes comerciales</span>
            <h2>Paquetes disponibles</h2>
          </div>
          <div class="packages-grid">
            <ServicePackageCard
              v-for="pkg in packages"
              :key="pkg.uuid"
              :pkg="pkg"
              @contract="goToPackageRequest"
            />
          </div>
        </section>

        <section class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Recursos tecnicos</span>
            <h2>Herramientas, software, protocolos y compatibilidad</h2>
          </div>
          <ServiceFeatureList :groups="resourceGroups" />
        </section>

        <section class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Alcance operativo</span>
            <h2>Incluye, no incluye y entregables</h2>
          </div>
          <div class="scope-grid">
            <ServiceScopeList title="Incluye" icon="bi-check2-circle" icon-color-class="text-success" :items="includes" />
            <ServiceScopeList title="No incluye" icon="bi-x-circle" icon-color-class="text-danger" :items="excludes" />
            <ServiceScopeList title="Entregables" icon="bi-file-earmark-check" icon-color-class="text-primary" :items="deliverables" />
          </div>
        </section>

        <section class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Ficha tecnica</span>
            <h2>Especificaciones del servicio</h2>
          </div>
          <ServiceSpecificationTable :specs="technicalSpecs" />
        </section>

        <section class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Profesionales</span>
            <h2>Tecnicos calificados para este servicio</h2>
          </div>
          <ServiceProfessionals :service-uuid="service.uuid" />
        </section>

        <section class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Oferta de valor</span>
            <h2>Que problema resuelve</h2>
          </div>
          <div class="value-grid">
            <article v-for="item in valueCards" :key="item.title">
              <i :class="['bi', item.icon]"></i>
              <h3>{{ item.title }}</h3>
              <p>{{ item.copy }}</p>
            </article>
          </div>
        </section>

        <section class="detail-section split">
          <div>
            <div class="section-head">
              <span class="section-kicker">Descripcion comercial</span>
              <h2>Solucion profesional lista para operar</h2>
            </div>
            <p class="commercial-description">{{ commercialDescription }}</p>
          </div>
          <div class="guarantee-card">
            <i class="bi bi-patch-check"></i>
            <span>Garantia</span>
            <strong>{{ warrantyText }}</strong>
            <p>Incluye trazabilidad, pruebas funcionales y soporte segun el paquete contratado.</p>
          </div>
        </section>

        <section class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Proceso</span>
            <h2>Como se ejecuta el servicio</h2>
          </div>
          <div class="timeline">
            <div v-for="step in serviceProcess" :key="step" class="timeline-step">
              <span>{{ step }}</span>
            </div>
          </div>
        </section>

        <section class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Video</span>
            <h2>Demostracion tecnica</h2>
          </div>
          <div v-if="embedUrl" class="ratio ratio-16x9 rounded-3 overflow-hidden">
            <iframe
              :src="embedUrl"
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
              allowfullscreen
              title="Video del servicio"
            ></iframe>
          </div>
          <div v-else class="video-placeholder">
            <i class="bi bi-play-circle"></i>
            <span>Video administrable pendiente</span>
          </div>
        </section>

        <section v-if="faqs.length" class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Preguntas frecuentes</span>
            <h2>Resolvemos tus dudas</h2>
          </div>
          <BaseAccordion :items="faqs" accent-color="#d97706" />
        </section>

        <section class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Confianza</span>
            <h2>Caso de exito</h2>
          </div>
          <article class="case-card">
            <i class="bi bi-building-check"></i>
            <h3>{{ successCase.title }}</h3>
            <p>{{ successCase.copy }}</p>
            <span>{{ successCase.metric }}</span>
          </article>
        </section>

        <section class="detail-section related-section">
          <div class="section-head">
            <span class="section-kicker">Cross selling</span>
            <h2>Servicios y productos relacionados</h2>
          </div>
          <div class="related-grid">
            <RouterLink to="/servicios" class="related-card">
              <i class="bi bi-tools"></i>
              <span>Servicios complementarios</span>
              <strong>Mantenimiento, soporte y diagnostico</strong>
            </RouterLink>
            <RouterLink to="/tienda" class="related-card">
              <i class="bi bi-box-seam"></i>
              <span>Productos compatibles</span>
              <strong>Camara, cableado, rack, UPS y accesorios</strong>
            </RouterLink>
            <RouterLink to="/renting" class="related-card">
              <i class="bi bi-hdd-rack"></i>
              <span>Equipos en renting</span>
              <strong>Infraestructura disponible por demanda</strong>
            </RouterLink>
          </div>
        </section>

        <section class="detail-section">
          <div class="section-head">
            <span class="section-kicker">Opiniones</span>
            <h2>Reseñas de clientes</h2>
          </div>
          <BaseReviews base-path="services/services" :entity-uuid="service.uuid" accent-color="#d97706" item-label="este servicio" />
        </section>
      </div>

      <div v-else-if="!loading" class="text-center py-5">
        <i class="bi bi-exclamation-circle display-4 text-muted d-block mb-3 opacity-25"></i>
        <p class="text-muted">Servicio no encontrado.</p>
        <RouterLink to="/servicios" class="btn btn-outline-warning btn-sm">Volver a servicios</RouterLink>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { servicesService } from '@/services/technical_services/servicesService';
import { useToast } from '@/composables/useToast';
import { formatCOP } from '@/utils/money';
import ServicePackageCard from '@/components/services/packages/ServicePackageCard.vue';
import BaseReviews from '@/components/base/BaseReviews.vue';
import BaseGallery from '@/components/base/BaseGallery.vue';
import ServiceFeatureList from '@/components/services/detail/ServiceFeatureList.vue';
import ServiceScopeList from '@/components/services/detail/ServiceScopeList.vue';
import ServiceSpecificationTable from '@/components/services/detail/ServiceSpecificationTable.vue';
import BaseAccordion from '@/components/base/BaseAccordion.vue';
import ServiceProfessionals from '@/components/services/detail/ServiceProfessionals.vue';

const toast = useToast();
const route = useRoute();
const router = useRouter();

const loading = ref(true);
const service = ref(null);
const packages = ref([]);
const fallback = {
  features: ['Instalacion certificada', 'Configuracion remota', 'Optimizacion de red', 'Actualizacion de firmware', 'Capacitacion operativa', 'Garantia documentada'],
  tools: ['Taladro', 'Multimetro', 'Crimpadora', 'Tester', 'Laptop', 'Escalera'],
  software: ['SADP', 'iVMS', 'ConfigTool', 'Winbox', 'UniFi', 'Windows', 'Linux'],
  protocols: ['ONVIF', 'RTSP', 'TCP', 'UDP', 'HTTP', 'HTTPS', 'Modbus', 'OSDP'],
  compatibility: ['Hikvision', 'Dahua', 'Axis', 'Bosch', 'ZKTeco', 'Akuvox', 'Ubiquiti'],
  accessories: ['Canaleta', 'Conectores', 'Patch Cord', 'RJ45', 'Gabinete', 'Fuente', 'Rack', 'UPS'],
  includes: ['Levantamiento inicial', 'Configuracion del sistema', 'Pruebas funcionales', 'Capacitacion basica', 'Acta de entrega'],
  excludes: ['Obra civil no especificada', 'Equipos o repuestos no incluidos', 'Licencias externas', 'Trabajos fuera de cobertura acordada'],
  deliverables: ['Informe tecnico', 'Registro fotografico', 'Credenciales de administracion', 'Recomendaciones de mantenimiento', 'Certificado de garantia'],
};

const allImages = computed(() => {
  const imgs = service.value?.images || [];
  return imgs.map((img) => img.image).filter(Boolean);
});

const minPrice = computed(() => {
  const variants = service.value?.variants || [];
  const prices = variants
    .filter((variant) => variant.is_active !== false)
    .map((variant) => variant.price_info?.total ?? variant.calculated_price)
    .filter((price) => price != null && parseFloat(price) > 0)
    .map((price) => parseFloat(price));
  return prices.length ? Math.min(...prices) : null;
});

const hasActiveVariant = computed(() =>
  service.value?.variants?.some((variant) => variant.is_active !== false) ?? false
);

const commercialCode = computed(() => {
  const variantSku = service.value?.variants?.find((variant) => variant.sku)?.sku;
  return service.value?.sku || service.value?.code || variantSku || `SERV-${String(service.value?.uuid || '').slice(0, 8)}`;
});

const serviceStatus = computed(() => service.value?.is_active === false ? 'No disponible' : 'Disponible');

const valueProposition = computed(() =>
  service.value?.value_proposition ||
  service.value?.short_description ||
  'Incluye diagnostico, configuracion, puesta en marcha, capacitacion y garantia para que la solucion quede operando con respaldo profesional.'
);

const commercialDescription = computed(() =>
  service.value?.commercial_description ||
  service.value?.description ||
  'Servicio profesional orientado a resolver necesidades tecnicas en sitio, remoto o modalidad hibrida. El alcance contempla planeacion, ejecucion, pruebas, entrega documentada y soporte segun el paquete contratado.'
);

const warrantyText = computed(() => service.value?.warranty?.name || service.value?.warranty || '30 dias sobre mano de obra');

const quickSpecs = computed(() => [
  { label: 'Duracion', value: service.value?.estimated_time || defaultHoursLabel.value },
  { label: 'Personal', value: service.value?.required_staff || '2 tecnicos' },
  { label: 'Modalidad', value: service.value?.modality || 'En sitio, remoto o hibrido' },
  { label: 'Cobertura', value: service.value?.coverage || 'Nacional' },
]);

const technicalSpecs = computed(() => [
  { label: 'Categoria', value: service.value?.category?.name || 'Servicio tecnico' },
  { label: 'Subcategoria', value: service.value?.subcategory?.name || service.value?.category?.name || 'Implementacion' },
  { label: 'Codigo', value: commercialCode.value },
  { label: 'Nivel tecnico', value: service.value?.level?.name || 'Senior' },
  { label: 'Tipo de servicio', value: service.value?.service_type || 'Instalacion, mantenimiento o configuracion' },
  { label: 'Ciclo', value: service.value?.cycle || 'Unico o recurrente' },
  { label: 'Disponibilidad', value: service.value?.availability || 'Programada y emergencias 24/7' },
  { label: 'Cobertura', value: service.value?.coverage || 'Nacional' },
]);

const defaultHoursLabel = computed(() => {
  const first = service.value?.variants?.find((variant) => variant.estimated_hours);
  return first ? `${first.estimated_hours} horas` : '6 horas estimadas';
});


const valueCards = computed(() => [
  { icon: 'bi-bullseye', title: 'Problema', copy: service.value?.problem_solved || 'Reduce fallas, tiempos muertos y riesgos operativos en infraestructura tecnica.' },
  { icon: 'bi-box2-heart', title: 'Recibes', copy: 'Servicio ejecutado, probado, documentado y entregado con evidencia.' },
  { icon: 'bi-award', title: 'Por que Sintel', copy: 'Equipo tecnico especializado, cobertura nacional, marcas compatibles y soporte postventa.' },
  { icon: 'bi-graph-up-arrow', title: 'Beneficio', copy: 'Mayor continuidad, seguridad, trazabilidad y control del sistema instalado.' },
]);

const includes = computed(() => pickList(['includes', 'activities_included'], fallback.includes));
const excludes = computed(() => pickList(['excludes', 'not_included'], fallback.excludes));
const deliverables = computed(() => pickList(['deliverables'], fallback.deliverables));

const resourceGroups = computed(() => [
  { title: 'Caracteristicas', icon: 'bi-stars', items: pickList(['features', 'characteristics', 'benefits'], fallback.features) },
  { title: 'Herramientas', icon: 'bi-tools', items: pickList(['tools'], fallback.tools) },
  { title: 'Software', icon: 'bi-window-desktop', items: pickList(['software'], fallback.software) },
  { title: 'Protocolos', icon: 'bi-diagram-3', items: pickList(['protocols'], fallback.protocols) },
  { title: 'Compatibilidad', icon: 'bi-hdd-network', items: pickList(['compatibilities', 'compatible_equipment'], fallback.compatibility) },
  { title: 'Accesorios', icon: 'bi-plug', items: pickList(['accessories', 'materials_included'], fallback.accessories) },
]);

const serviceProcess = computed(() =>
  pickList(['process_steps'], ['Solicitud', 'Pago', 'Programacion', 'Asignacion', 'Visita', 'Instalacion', 'Pruebas', 'Entrega', 'Garantia'])
);

const embedUrl = computed(() => toEmbedUrl(service.value?.video_url || service.value?.youtube_url));

const successCase = computed(() => ({
  title: service.value?.success_case?.title || 'Implementacion certificada en entorno empresarial',
  copy: service.value?.success_case?.copy || 'Normalizacion del sistema, pruebas de conectividad y entrega documentada para operacion continua.',
  metric: service.value?.success_case?.metric || 'Tiempo de respuesta reducido en 35%',
}));

const faqs = computed(() => {
  const adminFaqs = service.value?.faqs || service.value?.questions || [];
  if (Array.isArray(adminFaqs) && adminFaqs.length) {
    return adminFaqs.map((faq) => ({ q: faq.question || faq.q || faq.title, a: faq.answer || faq.a || faq.description }));
  }
  return [
    { q: 'El servicio incluye materiales?', a: 'Incluye los materiales indicados en el paquete. Repuestos, licencias o equipos adicionales se cotizan por separado.' },
    { q: 'Puedo programar una visita?', a: 'Si. Despues del pago eliges direccion, fecha y jornada disponible.' },
    { q: 'Recibo documentacion?', a: 'Si. Se entrega informe tecnico, evidencia y recomendaciones segun el alcance.' },
  ];
});

function pickList(keys, defaultValue) {
  for (const key of keys) {
    const value = service.value?.[key];
    if (Array.isArray(value) && value.length) return value.map(normalizeItem).filter(Boolean);
    if (typeof value === 'string' && value.trim()) return value.split(/\r?\n|,/).map((item) => item.trim()).filter(Boolean);
  }
  return defaultValue;
}

function normalizeItem(item) {
  if (typeof item === 'string') return item;
  return item?.name || item?.title || item?.label || item?.description || '';
}

function toEmbedUrl(url) {
  if (!url) return '';
  const match = String(url).match(/(?:youtube\.com\/watch\?v=|youtu\.be\/)([^&?/]+)/);
  return match ? `https://www.youtube.com/embed/${match[1]}` : url;
}

function fmtCOP(value) {
  const number = parseFloat(value);
  if (!Number.isFinite(number) || number <= 0) return 'A cotizar';
  return formatCOP(number, { withSymbol: true });
}

async function fetchService() {
  loading.value = true;
  try {
    const uuid = route.params.uuid;
    service.value = await servicesService.detail(uuid);
    packages.value = await servicesService.packages(uuid) || [];
  } catch {
    toast.error('Error al cargar el servicio');
  } finally {
    loading.value = false;
  }
}

function goToPackageRequest(pkg) {
  router.push({
    path: `/servicios/${service.value.uuid}/solicitar`,
    query: { package: pkg.uuid },
  });
}

onMounted(fetchService);
</script>

<style scoped>
.service-detail {
  background: #f8fafc;
  min-height: 100vh;
}
.breadcrumb-sm { font-size: .82rem; }
.gallery-sticky {
  position: sticky;
  top: 88px;
}
.sv-gallery-badge {
  position: absolute; top: .8rem; right: .8rem;
  background: #f59e0b; color: #0f172a;
  border-radius: 999px; padding: .28rem .7rem;
  font-size: .72rem; font-weight: 800;
}
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
.service-title {
  color: #0f172a;
  font-size: clamp(1.65rem, 3vw, 2.45rem);
  font-weight: 900;
  letter-spacing: 0;
  line-height: 1.08;
  margin: 0 0 .75rem;
}
.value-prop {
  color: #475569;
  font-size: 1rem;
  line-height: 1.65;
  margin-bottom: 1rem;
}
.quick-specs {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: .65rem;
  margin-bottom: 1rem;
}
.quick-specs div,
.package-panel,
.detail-section {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
}
.quick-specs div {
  padding: .75rem;
}
.quick-specs span,
.spec-table span,
.related-card span {
  display: block;
  color: #64748b;
  font-size: .72rem;
  font-weight: 700;
}
.quick-specs strong,
.spec-table strong {
  display: block;
  color: #0f172a;
  font-size: .86rem;
  margin-top: .18rem;
}
.package-panel {
  padding: 1rem;
  box-shadow: 0 14px 30px rgba(15,23,42,.06);
}
.panel-head,
.section-head {
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: .9rem;
}
.section-head { display: block; }
.section-kicker {
  display: block;
  color: #0f766e;
  font-size: .72rem;
  font-weight: 850;
  letter-spacing: .08em;
  text-transform: uppercase;
  margin-bottom: .25rem;
}
.panel-head h2,
.section-head h2 {
  color: #0f172a;
  font-size: 1.25rem;
  font-weight: 850;
  letter-spacing: 0;
  margin: 0;
}
.from-price {
  color: #0f766e;
  font-weight: 850;
  white-space: nowrap;
}
.selected-package {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  border-top: 1px solid #e2e8f0;
  margin-top: .9rem;
  padding-top: .9rem;
}
.selected-package h3 {
  color: #0f172a;
  font-size: 1rem;
  font-weight: 850;
  margin: 0 0 .2rem;
}
.selected-package p {
  color: #64748b;
  font-size: .86rem;
  margin: 0;
}
.buy-btn {
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
.buy-btn:hover { background: #115e59; color: #fff; }
.unavailable {
  color: #64748b;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  padding: .7rem 1rem;
}
.detail-sections {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1.25rem;
}
.detail-section {
  padding: 1.1rem;
}
.detail-section.split,
.media-grid,
.trust-split,
.related-grid {
  display: grid;
  grid-template-columns: 1.3fr .8fr;
  gap: 1rem;
}
.value-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: .75rem;
}
.scope-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: .75rem;
}
.packages-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1rem;
}
.value-grid article,
.guarantee-card,
.case-card,
.related-card {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 14px;
  padding: .9rem;
}
.value-grid i,
.guarantee-card i,
.case-card i,
.related-card i {
  color: #0e7490;
  font-size: 1.35rem;
}
.value-grid h3,
.case-card h3 {
  color: #0f172a;
  font-size: .95rem;
  font-weight: 850;
  margin: .45rem 0 .3rem;
}
.value-grid p,
.commercial-description,
.guarantee-card p,
.case-card p {
  color: #64748b;
  font-size: .88rem;
  line-height: 1.65;
  margin: 0;
}
.commercial-description { font-size: .95rem; }
.guarantee-card {
  background: #f0fdf4;
  border-color: #bbf7d0;
}
.guarantee-card span {
  display: block;
  color: #166534;
  font-weight: 800;
  margin-top: .4rem;
}
.guarantee-card strong {
  display: block;
  color: #0f172a;
  font-size: 1.15rem;
  margin: .1rem 0 .35rem;
}
.timeline {
  display: grid;
  grid-template-columns: repeat(9, minmax(0, 1fr));
  gap: .45rem;
}
.timeline-step {
  min-height: 48px;
  background: #eff6ff;
  border: 1px solid #dbeafe;
  border-radius: 12px;
  color: #1e40af;
  display: flex;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-size: .73rem;
  font-weight: 800;
}
.video-placeholder {
  min-height: 205px;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: .45rem;
  background: #0f172a;
  color: #fff;
}
.video-placeholder i { font-size: 2.2rem; }
.case-card span {
  display: inline-flex;
  margin-top: .8rem;
  background: #ecfeff;
  color: #0e7490;
  border-radius: 999px;
  padding: .35rem .7rem;
  font-size: .75rem;
  font-weight: 850;
}
.related-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.related-card {
  color: inherit;
  text-decoration: none;
}
.related-card strong {
  display: block;
  color: #0f172a;
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
  .value-grid,
  .scope-grid,
  .timeline,
  .related-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .detail-section.split {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 575px) {
  .quick-specs,
  .scope-grid,
  .value-grid,
  .timeline,
  .related-grid,
  .trust-grid {
    grid-template-columns: 1fr;
  }
  .selected-package,
  .panel-head {
    align-items: flex-start;
    flex-direction: column;
  }
  .buy-btn { width: 100%; }
}
</style>
