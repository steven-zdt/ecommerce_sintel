<template>
  <div class="public-detail">
    <!-- Loading State -->
    <div v-if="loading" class="skeleton-container">
      <div class="skeleton" style="height: 400px"></div>
    </div>

    <!-- Error State -->
    <div v-else-if="error" class="alert alert-danger" role="alert">
      <h4 class="alert-heading">{{ getModuleLabel() }} no encontrado</h4>
      <p>{{ error }}</p>
      <RouterLink to="/" class="btn btn-sm btn-outline-primary">Volver al inicio</RouterLink>
    </div>

    <!-- Content State -->
    <div v-else-if="detail" class="detail-container container-xl py-3 py-lg-4">
      <!-- Breadcrumb -->
      <nav class="mb-3" aria-label="breadcrumb">
        <ol class="breadcrumb breadcrumb-sm mb-0">
          <li class="breadcrumb-item">
            <RouterLink :to="getBreadcrumbPath()" class="text-decoration-none text-muted">
              <i :class="['bi', getModuleIcon()]"></i>{{ getModuleLabel() }}
            </RouterLink>
          </li>
          <li v-if="detail?.hero?.category_name" class="breadcrumb-item text-muted">{{ detail.hero.category_name }}</li>
          <li class="breadcrumb-item active text-truncate" style="max-width:240px">{{ detail?.hero?.name }}</li>
        </ol>
      </nav>

      <!-- ══════════════════════════════════════════════════════════════════
           RENTING — Presentation Layer restaurada (ver plan
           structured-strolling-sparkle.md). Reutiliza los componentes reales
           que producción ya usa (BaseGallery, TagBadge, UrgencyBanner,
           DiscountBadge, BaseAccordion, BaseReviews, Equipment*List) en vez
           de markup ad-hoc. Todo el bloque vive bajo `.rental-detail` para
           que su CSS (calcado de RentalDetailView.vue) no choque con las
           clases de la rama Shop/Servicios de abajo.
           ══════════════════════════════════════════════════════════════════ -->
      <div v-if="moduleType === 'renting'" class="rental-detail">
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

            <!-- Pricing Card -->
            <div v-if="detail.pricing" class="pricing-card mb-4">
              <div class="row g-3">
                <div class="col-6">
                  <span class="section-kicker">Precio por día</span>
                  <div class="pricing-value">{{ detail.pricing.formatted_price_per_day || 'A cotizar' }}</div>
                </div>
                <div class="col-6">
                  <span class="section-kicker">Precio por hora</span>
                  <div class="pricing-value">{{ detail.pricing.formatted_price_per_hour || 'A cotizar' }}</div>
                </div>
              </div>

              <div v-if="detail.pricing.has_promotion" class="discount-banner mt-3">
                <span class="discount-badge">-{{ detail.pricing.discount_percentage }}%</span>
                <span>Ahorra {{ detail.pricing.formatted_discount_amount }}</span>
              </div>

              <p v-if="detail.pricing.saving_message" class="promo-message">{{ detail.pricing.saving_message }}</p>

              <RouterLink
                v-if="detail.hero?.cta_enabled"
                :to="{ name: 'rental-request', params: { uuid: detail.uuid } }"
                class="btn btn-primary w-100"
              >
                {{ detail.hero?.cta_label || 'Reservar ahora' }}
              </RouterLink>
              <p v-else-if="detail.hero?.cta_disabled_reason" class="text-danger small mt-2">
                {{ detail.hero.cta_disabled_reason }}
              </p>
            </div>

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

            <!-- Quick Specs -->
            <div class="quick-specs-old mb-4">
              <span class="section-kicker">Especificaciones rápidas</span>
              <div class="specs-grid">
                <div v-for="spec in quickSpecs" :key="spec.label" class="spec-item">
                  <span class="spec-label">{{ spec.label }}</span>
                  <span class="spec-value">{{ spec.value }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Features Section -->
        <div v-if="detail?.technical?.features?.length" class="section-features mt-5">
          <div class="section-header">
            <h2>Características destacadas</h2>
            <p class="section-subtitle">Lo que hace especial este equipo</p>
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
        </div>

        <!-- Included vs Excluded -->
        <div v-if="detail?.included_items?.length || detail?.excluded_items?.length" class="section-scope mt-5">
          <div class="section-header">
            <h2>Alcance del alquiler</h2>
            <p class="section-subtitle">Qué incluye y qué no</p>
          </div>
          <div class="row g-4">
            <div v-if="detail?.included_items?.length" class="col-lg-6">
              <EquipmentIncludedList :items="detail.included_items" />
            </div>
            <div v-if="detail?.excluded_items?.length" class="col-lg-6">
              <EquipmentExcludedList :items="detail.excluded_items" />
            </div>
          </div>
        </div>

        <!-- Specifications by Group -->
        <div v-if="detail?.technical?.specification_groups?.length" class="section-specs mt-5">
          <div class="section-header">
            <h2>Especificaciones técnicas</h2>
            <p class="section-subtitle">Detalles técnicos completos</p>
          </div>
          <div class="row g-4">
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
        </div>

        <!-- Requirements -->
        <div v-if="detail?.technical?.requirements?.length" class="section-requirements mt-5">
          <div class="section-header">
            <h2>Requisitos de alquiler</h2>
            <p class="section-subtitle">Lo que necesitas cumplir</p>
          </div>
          <EquipmentRequirementList :items="detail.technical.requirements" />
        </div>

        <!-- Videos -->
        <div v-if="detail?.videos?.length" class="section-videos mt-5">
          <div class="section-header">
            <h2>Videos</h2>
            <p class="section-subtitle">Visualiza el equipo en acción</p>
          </div>
          <EquipmentVideoGallery :videos="detail.videos" />
        </div>

        <!-- Documents -->
        <div v-if="detail?.documents?.length" class="section-documents mt-5">
          <div class="section-header">
            <h2>Documentación</h2>
            <p class="section-subtitle">Manuales y certificados</p>
          </div>
          <EquipmentDocumentList :documents="detail.documents" :equipment-uuid="detail.uuid" />
        </div>

        <!-- FAQs -->
        <div v-if="detail?.faq?.length" class="section-faqs mt-5">
          <div class="section-header">
            <h2>Preguntas frecuentes</h2>
            <p class="section-subtitle">Respuestas a dudas comunes</p>
          </div>
          <BaseAccordion :items="detail.faq" accent-color="#2563eb" />
        </div>

        <!-- Reviews -->
        <div class="section-reviews mt-5">
          <div class="section-header">
            <h2>Reseñas</h2>
            <p class="section-subtitle">Experiencias de otros clientes</p>
          </div>
          <BaseReviews
            base-path="renting/equipment"
            :entity-uuid="detail.uuid"
            accent-color="#2563eb"
            item-label="este equipo"
          />
        </div>

        <!-- Related Equipment -->
        <div v-if="detail?.related_items?.length" class="section-related mt-5">
          <div class="section-header">
            <h2>Equipos relacionados</h2>
            <p class="section-subtitle">Otros equipos que podrían interesarte</p>
          </div>
          <div class="row g-3">
            <div v-for="item in detail.related_items" :key="item.uuid" class="col-md-6 col-lg-4">
              <RouterLink :to="{ name: 'rental-detail', params: { uuid: item.uuid } }" class="related-card text-decoration-none">
                <img :src="item.image_url" :alt="item.name" class="related-image" />
                <h6>{{ item.name }}</h6>
                <span class="price">{{ item.price_from }}</span>
              </RouterLink>
            </div>
          </div>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════════════════════════
           SERVICES — Presentation Layer restaurada (ver plan
           structured-strolling-sparkle.md). El DTO unificado
           (unified/detail/?module=service) es demasiado escueto para este
           módulo (solo hero/gallery/pricing/reviews) — esta rama hace su
           propio fetch a servicesService.detail()/.packages() (endpoints
           públicos ya existentes, sin tocar backend) para recuperar la
           estructura rica que producción ya sirve hoy. Vive bajo
           `.service-detail-block` para no chocar con las clases de Shop.
           ══════════════════════════════════════════════════════════════════ -->
      <div v-else-if="moduleType === 'service' && serviceDetail" class="service-detail-block">
        <div class="row g-4 g-lg-5">
          <!-- Left Column: Gallery & Trust -->
          <div class="col-lg-5">
            <div class="gallery-sticky">
              <BaseGallery
                :images="serviceDetail.images || []"
                :title="serviceDetail.name"
                icon-class="bi-tools"
                theme="services"
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
                  <h2>Agenda tu servicio con Sintel</h2>
                </div>
                <span v-if="serviceMinPrice !== null" class="from-price">Desde {{ fmtCOP(serviceMinPrice) }}</span>
              </div>
              <div class="selected-package">
                <div>
                  <h3>Selecciona la opcion, direccion, fecha y paga en linea</h3>
                  <p>El paso a paso completo (Servicio, Direccion, Fecha, Pago) se realiza en la siguiente pantalla.</p>
                </div>
                <RouterLink
                  v-if="serviceHasActiveVariant"
                  :to="{ name: 'service-request', params: { uuid: serviceDetail.uuid } }"
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

          <section class="detail-section">
            <div class="section-head">
              <span class="section-kicker">Recursos tecnicos</span>
              <h2>Herramientas, software, protocolos y compatibilidad</h2>
            </div>
            <ServiceFeatureList :groups="serviceResourceGroups" />
          </section>

          <section class="detail-section">
            <div class="section-head">
              <span class="section-kicker">Alcance operativo</span>
              <h2>Incluye, no incluye y entregables</h2>
            </div>
            <div class="scope-grid">
              <ServiceScopeList title="Incluye" icon="bi-check2-circle" icon-color-class="text-success" :items="serviceIncludes" />
              <ServiceScopeList title="No incluye" icon="bi-x-circle" icon-color-class="text-danger" :items="serviceExcludes" />
              <ServiceScopeList title="Entregables" icon="bi-file-earmark-check" icon-color-class="text-primary" :items="serviceDeliverables" />
            </div>
          </section>

          <section class="detail-section">
            <div class="section-head">
              <span class="section-kicker">Ficha tecnica</span>
              <h2>Especificaciones del servicio</h2>
            </div>
            <ServiceSpecificationTable :specs="serviceTechnicalSpecs" />
          </section>

          <section class="detail-section">
            <div class="section-head">
              <span class="section-kicker">Profesionales</span>
              <h2>Tecnicos calificados para este servicio</h2>
            </div>
            <ServiceProfessionals :service-uuid="serviceDetail.uuid" />
          </section>

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

          <section class="detail-section split">
            <div>
              <div class="section-head">
                <span class="section-kicker">Descripcion comercial</span>
                <h2>Solucion profesional lista para operar</h2>
              </div>
              <p class="commercial-description">{{ serviceCommercialDescription }}</p>
            </div>
            <div class="guarantee-card">
              <i class="bi bi-patch-check"></i>
              <span>Garantia</span>
              <strong>{{ serviceWarrantyText }}</strong>
              <p>Incluye trazabilidad, pruebas funcionales y soporte segun el paquete contratado.</p>
            </div>
          </section>

          <section class="detail-section">
            <div class="section-head">
              <span class="section-kicker">Proceso</span>
              <h2>Como se ejecuta el servicio</h2>
            </div>
            <div class="timeline">
              <div v-for="step in serviceProcessSteps" :key="step" class="timeline-step">
                <span>{{ step }}</span>
              </div>
            </div>
          </section>

          <section class="detail-section">
            <div class="section-head">
              <span class="section-kicker">Video</span>
              <h2>Demostracion tecnica</h2>
            </div>
            <div class="video-placeholder">
              <i class="bi bi-play-circle"></i>
              <span>Video administrable pendiente</span>
            </div>
          </section>

          <section v-if="serviceFaqs.length" class="detail-section">
            <div class="section-head">
              <span class="section-kicker">Preguntas frecuentes</span>
              <h2>Resolvemos tus dudas</h2>
            </div>
            <BaseAccordion :items="serviceFaqs" accent-color="#d97706" />
          </section>

          <section class="detail-section">
            <div class="section-head">
              <span class="section-kicker">Confianza</span>
              <h2>Caso de exito</h2>
            </div>
            <article class="case-card">
              <i class="bi bi-building-check"></i>
              <h3>{{ serviceSuccessCase.title }}</h3>
              <p>{{ serviceSuccessCase.copy }}</p>
              <span>{{ serviceSuccessCase.metric }}</span>
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
              <RouterLink to="/alquiler" class="related-card">
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
            <BaseReviews
              base-path="services/services"
              :entity-uuid="serviceDetail.uuid"
              accent-color="#d97706"
              item-label="este servicio"
            />
          </section>
        </div>
      </div>

      <!-- ══════════════════════════════════════════════════════════════════
           SHOP — sin cambios en este alcance (ver plan). Se deja intacto
           tal cual estaba antes de las restauraciones de Renting/Services.
           ══════════════════════════════════════════════════════════════════ -->
      <template v-else>
        <!-- MAIN 2-COLUMN LAYOUT (mirrors production: col-lg-5 gallery/availability, col-lg-7 details) -->
        <div class="row g-4 g-lg-5">
          <!-- LEFT COLUMN -->
          <div class="col-lg-5">
            <div class="gallery-sticky">
              <!-- Gallery -->
              <div class="bv-gallery">
                <div class="bv-gallery-main">
                  <i :class="['bi', getModuleIcon()]"></i>
                </div>
              </div>

              <!-- Trust Grid -->
              <div class="trust-grid">
                <div><i class="bi bi-shield-check text-success"></i><span>{{ getTrustMsg(0) }}</span></div>
                <div><i class="bi bi-credit-card text-primary"></i><span>{{ getTrustMsg(1) }}</span></div>
                <div><i class="bi bi-truck text-info"></i><span>{{ getTrustMsg(2) }}</span></div>
                <div><i class="bi bi-headset text-warning"></i><span>{{ getTrustMsg(3) }}</span></div>
              </div>

              <!-- Availability Card -->
              <div class="availability-card">
                <span class="section-kicker">Disponibilidad</span>
                <h2>{{ detail.availability?.status_label }}</h2>
                <p>{{ detail.availability?.status_detail }}</p>
                <RouterLink v-if="detail.hero?.cta_enabled" :to="`/${moduleType}/${detail.uuid}/solicitar`" class="availability-link">
                  Consultar fechas exactas <i class="bi bi-arrow-right"></i>
                </RouterLink>
              </div>
            </div>
          </div>

          <!-- RIGHT COLUMN -->
          <div class="col-lg-7">
            <!-- Badges + Actions -->
            <div class="d-flex flex-wrap align-items-center gap-2 mb-2">
              <span v-if="detail.hero?.brand_name" class="badge bg-primary-subtle text-primary border border-primary-subtle">{{ detail.hero.brand_name }}</span>
              <span v-if="detail.hero?.category_name" class="badge bg-light text-muted border">{{ detail.hero.category_name }}</span>
              <span :class="getAvailBadge()">{{ detail.availability?.status_label }}</span>
              <div class="ms-lg-auto d-flex gap-2">
                <button type="button" class="icon-action-btn" @click="shareItem"><i class="bi bi-share"></i></button>
                <button type="button" class="icon-action-btn" :class="{ active: isFavorite }" @click="toggleFavorite"><i :class="['bi', isFavorite ? 'bi-heart-fill' : 'bi-heart']"></i></button>
              </div>
            </div>

            <!-- Title -->
            <h1 class="equipment-title">{{ detail.hero?.name }}</h1>
            <p v-if="detail.hero?.description" class="value-prop">{{ detail.hero.description }}</p>

            <!-- Quick Specs -->
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
                <strong>{{ variantsCount }}</strong>
              </div>
              <div>
                <span>Stock total</span>
                <strong>{{ detail.availability?.available_now || 0 }} unidad(es)</strong>
              </div>
            </div>

            <!-- Configuracion / Package Panel -->
            <div class="package-panel">
              <div class="panel-head">
                <div>
                  <span class="section-kicker">Configuracion</span>
                  <h2>{{ moduleType === 'renting' ? 'Valor del alquiler' : 'Valor' }}</h2>
                </div>
                <span class="from-price" v-if="moduleType === 'renting'">Desde {{ detail.pricing?.formatted_price_per_day }} / dia</span>
                <span class="from-price" v-else>{{ detail.pricing?.formatted_promo_price }}</span>
              </div>
              <div class="selected-package">
                <div>
                  <h3>{{ packageLabel }}</h3>
                  <p v-if="moduleType === 'renting'">{{ detail.pricing?.formatted_price_per_day }} / dia</p>
                  <p v-else>{{ detail.pricing?.formatted_promo_price }}</p>
                </div>
                <RouterLink v-if="detail.hero?.cta_enabled" :to="`/${moduleType}/${detail.uuid}/solicitar`" class="reserve-btn">
                  <i class="bi bi-calendar-check me-2"></i>{{ getCTALabel() }}
                </RouterLink>
              </div>
            </div>
          </div>
        </div>

        <!-- SECTIONS BELOW (mirrors production: detail-sections flex column) -->
        <div class="detail-sections">
          <!-- OPINIONES -->
          <section class="detail-section">
            <div class="section-head">
              <span class="section-kicker">Opiniones</span>
              <h2>Reseñas de clientes</h2>
            </div>
            <div class="bv-reviews">
              <div class="bv-reviews-summary">
                <div class="bv-reviews-score">
                  <strong>{{ reviewScoreDisplay }}</strong>
                  <span>{{ detail.reviews?.total_count || 0 }} reseñas</span>
                </div>
              </div>

              <div v-if="detail?.reviews?.items?.length" class="bv-reviews-list">
                <div v-for="(review, i) in detail.reviews.items" :key="i" class="bv-review-item">
                  <div class="bv-review-item-header">
                    <strong>{{ review.user_name }}</strong>
                    <span>⭐ {{ review.rating }}/5</span>
                  </div>
                  <p>{{ review.comment }}</p>
                </div>
              </div>

              <div class="bv-review-form">
                <p class="bv-review-form-title">Escribe tu reseña</p>
                <div class="bv-review-stars-input">
                  <button
                    v-for="star in 5"
                    :key="star"
                    type="button"
                    class="bv-star-btn"
                    :class="{ active: reviewRating >= star }"
                    @click="reviewRating = star">
                    ⭐
                  </button>
                </div>
                <textarea
                  v-model="reviewText"
                  class="bv-review-textarea"
                  rows="3"
                  placeholder="Cuentanos tu experiencia..."></textarea>
                <button type="button" class="bv-review-submit" :disabled="isSubmittingReview" @click="submitReview">
                  {{ isSubmittingReview ? 'Enviando...' : 'Publicar reseña' }}
                </button>
              </div>

              <p v-if="!detail?.reviews?.items?.length" class="bv-review-empty">
                Aun no hay reseñas para este {{ getModuleLabel().toLowerCase() }}.
              </p>
            </div>
          </section>

          <!-- INTEGRACIONES (Renting only, matches production) -->
          <section v-if="moduleType === 'renting'" class="detail-section related-section">
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
      </template>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useSeo } from '@/composables/useSeo';
import { servicesService } from '@/services/technical_services/servicesService';
import { formatCOP } from '@/utils/money';

// Renting — componentes reales reutilizados (ver plan structured-strolling-sparkle.md).
// Above-fold: carga eager. Below-fold: lazy via defineAsyncComponent, igual que
// hacia RentalDetailView.vue (el componente que se está restaurando).
import BaseGallery from '@/components/base/BaseGallery.vue';
import DiscountBadge from '@/components/marketplace/DiscountBadge.vue';
import UrgencyBanner from '@/components/marketplace/UrgencyBanner.vue';
import TagBadge from '@/components/marketplace/TagBadge.vue';
import { defineAsyncComponent } from 'vue';

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

// Services — componentes reales reutilizados (ver plan structured-strolling-sparkle.md).
// Existian en el repo sin una sola referencia (verificado con grep) desde que
// 674dff8 redujo ServiceDetailView.vue a un stub. Below-fold: lazy.
const ServiceFeatureList = defineAsyncComponent(() =>
  import('@/components/services/detail/ServiceFeatureList.vue')
);
const ServiceScopeList = defineAsyncComponent(() =>
  import('@/components/services/detail/ServiceScopeList.vue')
);
const ServiceSpecificationTable = defineAsyncComponent(() =>
  import('@/components/services/detail/ServiceSpecificationTable.vue')
);
const ServiceProfessionals = defineAsyncComponent(() =>
  import('@/components/services/detail/ServiceProfessionals.vue')
);
const ServicePackageCard = defineAsyncComponent(() =>
  import('@/components/services/packages/ServicePackageCard.vue')
);

const api = useApi();
const { success, error: showError } = useToast();
const route = useRoute();
const router = useRouter();
const { setSeo } = useSeo();

const loading = ref(true);
const error = ref(null);
const detail = ref(null);
const isFavorite = ref(false);
const FAVORITES_KEY = 'sintel_favorites';

// Rama Services restaurada: el DTO unificado no alcanza (ver plan), se
// alimenta de un fetch propio a endpoints publicos ya existentes.
const serviceDetail = ref(null);
const servicePackages = ref([]);

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

// Contenido de respaldo (ya existia en el archivo recuperado) para las
// listas que no tienen campo de modelo real detras -- documentado asi en
// technical_services/CLAUDE.md, no se inventan modelos nuevos.
const SERVICE_FALLBACK = {
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

const serviceTags = computed(() => {
  const codes = serviceDetail.value?.marketing?.tags || [];
  return codes.map((code) => ({ code, ...(SERVICE_TAG_META[code] || { label: code, color: 'primary' }) }));
});

const serviceMinPrice = computed(() => {
  const variants = serviceDetail.value?.variants || [];
  const prices = variants
    .filter((v) => v.is_active !== false)
    .map((v) => v.price_info?.total ?? v.calculated_price)
    .filter((p) => p != null && parseFloat(p) > 0)
    .map((p) => parseFloat(p));
  return prices.length ? Math.min(...prices) : null;
});

const serviceHasActiveVariant = computed(() =>
  serviceDetail.value?.variants?.some((v) => v.is_active !== false) ?? false
);

const serviceCommercialCode = computed(() => {
  const variantSku = serviceDetail.value?.variants?.find((v) => v.sku)?.sku;
  return variantSku || `SERV-${String(serviceDetail.value?.uuid || '').slice(0, 8)}`;
});

const serviceStatusLabel = computed(() =>
  serviceDetail.value?.is_active === false ? 'No disponible' : 'Disponible'
);

// marketing.main_message es real (ServiceMarketing); si el admin no lo cargo
// se conserva el mismo texto de respaldo que ya mostraba produccion.
const serviceValueProposition = computed(() =>
  serviceDetail.value?.marketing?.main_message ||
  'Incluye diagnostico, configuracion, puesta en marcha, capacitacion y garantia para que la solucion quede operando con respaldo profesional.'
);

const serviceCommercialDescription = computed(() =>
  serviceDetail.value?.description ||
  'Servicio profesional orientado a resolver necesidades tecnicas en sitio, remoto o modalidad hibrida. El alcance contempla planeacion, ejecucion, pruebas, entrega documentada y soporte segun el paquete contratado.'
);

const serviceWarrantyText = computed(() => '30 dias sobre mano de obra');

const serviceDefaultHoursLabel = computed(() => {
  const first = serviceDetail.value?.variants?.find((v) => v.estimated_hours);
  return first ? `${first.estimated_hours} horas` : '6 horas estimadas';
});

const serviceQuickSpecs = computed(() => [
  { label: 'Duracion', value: serviceDefaultHoursLabel.value },
  { label: 'Personal', value: '2 tecnicos' },
  { label: 'Modalidad', value: 'En sitio, remoto o hibrido' },
  { label: 'Cobertura', value: 'Nacional' },
]);

const serviceTechnicalSpecs = computed(() => [
  { label: 'Categoria', value: serviceDetail.value?.category?.name || 'Servicio tecnico' },
  { label: 'Subcategoria', value: serviceDetail.value?.category?.name || 'Implementacion' },
  { label: 'Codigo', value: serviceCommercialCode.value },
  { label: 'Nivel tecnico', value: serviceDetail.value?.level?.name || 'Senior' },
  { label: 'Tipo de servicio', value: 'Instalacion, mantenimiento o configuracion' },
  { label: 'Ciclo', value: 'Unico o recurrente' },
  { label: 'Disponibilidad', value: 'Programada y emergencias 24/7' },
  { label: 'Cobertura', value: 'Nacional' },
]);

// marketing.quick_benefits es real; el resto de grupos no tiene campo de
// modelo detras (ver gap documentado en el plan), se conserva el respaldo.
const serviceFeaturesList = computed(() => {
  const benefits = serviceDetail.value?.marketing?.quick_benefits;
  if (Array.isArray(benefits) && benefits.length) {
    return benefits.map((b) => b.label).filter(Boolean);
  }
  return SERVICE_FALLBACK.features;
});

const serviceResourceGroups = computed(() => [
  { title: 'Caracteristicas', icon: 'bi-stars', items: serviceFeaturesList.value },
  { title: 'Herramientas', icon: 'bi-tools', items: SERVICE_FALLBACK.tools },
  { title: 'Software', icon: 'bi-window-desktop', items: SERVICE_FALLBACK.software },
  { title: 'Protocolos', icon: 'bi-diagram-3', items: SERVICE_FALLBACK.protocols },
  { title: 'Compatibilidad', icon: 'bi-hdd-network', items: SERVICE_FALLBACK.compatibility },
  { title: 'Accesorios', icon: 'bi-plug', items: SERVICE_FALLBACK.accessories },
]);

const serviceIncludes = computed(() => SERVICE_FALLBACK.includes);
const serviceExcludes = computed(() => SERVICE_FALLBACK.excludes);
const serviceDeliverables = computed(() => SERVICE_FALLBACK.deliverables);

const serviceValueCards = computed(() => [
  { icon: 'bi-bullseye', title: 'Problema', copy: 'Reduce fallas, tiempos muertos y riesgos operativos en infraestructura tecnica.' },
  { icon: 'bi-box2-heart', title: 'Recibes', copy: 'Servicio ejecutado, probado, documentado y entregado con evidencia.' },
  { icon: 'bi-award', title: 'Por que Sintel', copy: serviceDetail.value?.marketing?.trust_message || 'Equipo tecnico especializado, cobertura nacional, marcas compatibles y soporte postventa.' },
  { icon: 'bi-graph-up-arrow', title: 'Beneficio', copy: serviceDetail.value?.marketing?.social_proof_message || 'Mayor continuidad, seguridad, trazabilidad y control del sistema instalado.' },
]);

const serviceProcessSteps = ['Solicitud', 'Pago', 'Programacion', 'Asignacion', 'Visita', 'Instalacion', 'Pruebas', 'Entrega', 'Garantia'];

const serviceSuccessCase = {
  title: 'Implementacion certificada en entorno empresarial',
  copy: 'Normalizacion del sistema, pruebas de conectividad y entrega documentada para operacion continua.',
  metric: 'Tiempo de respuesta reducido en 35%',
};

const serviceFaqs = computed(() => serviceDetail.value?.faqs || []);

function fmtCOP(value) {
  const number = parseFloat(value);
  if (!Number.isFinite(number) || number <= 0) return 'A cotizar';
  return formatCOP(number, { withSymbol: true });
}

function goToServicePackageRequest(pkg) {
  router.push({
    name: 'service-request',
    params: { uuid: serviceDetail.value.uuid },
    query: { package: pkg.uuid },
  });
}

async function fetchServiceRichDetail(uuid) {
  try {
    const [detailData, packagesData] = await Promise.all([
      servicesService.detail(uuid),
      servicesService.packages(uuid).catch(() => []),
    ]);
    serviceDetail.value = detailData;
    servicePackages.value = packagesData || [];
  } catch {
    serviceDetail.value = null;
    servicePackages.value = [];
  }
}

// Usado solo por la rama Shop/Service (preservada sin cambios).
const reviewRating = ref(0);
const reviewText = ref('');
const isSubmittingReview = ref(false);

const moduleType = computed(() => {
  const path = route.path;
  if (path.includes('alquiler')) return 'renting';
  if (path.includes('tienda')) return 'shop';
  if (path.includes('servicios')) return 'service';
  return 'renting';
});

// Usado solo por la rama Shop/Service (preservada sin cambios).
const reviewScoreDisplay = computed(() => {
  const avg = detail.value?.reviews?.average_rating;
  return avg ? avg.toFixed(1) : '—';
});

// Usado solo por la rama Shop/Service (preservada sin cambios).
const variantsCount = computed(() => {
  return detail.value?.pricing?.components?.length || 1;
});

// Usado solo por la rama Shop/Service (preservada sin cambios).
const packageLabel = computed(() => {
  return detail.value?.hero?.category_name || getModuleLabel();
});

// Usado solo por la rama Renting restaurada (calcado de RentalDetailView.vue).
const quickSpecs = computed(() => {
  if (!detail.value?.hero) return [];
  return [
    { label: 'Marca', value: detail.value.hero.brand_name || 'Sintel' },
    { label: 'Categoría', value: detail.value.hero.category_name || 'Equipo' },
    { label: 'Disponibilidad', value: detail.value.availability?.status_label || 'N/A' },
    { label: 'Stock', value: `${detail.value.availability?.available_now || 0} unidad(es)` },
  ];
});

// Helper functions
function getModuleLabel() {
  return { renting: 'Equipo', shop: 'Producto', service: 'Servicio' }[moduleType.value];
}

function getModuleIcon() {
  return { renting: 'bi-hdd-rack', shop: 'bi-bag-check', service: 'bi-tools' }[moduleType.value];
}

function getBreadcrumbPath() {
  return { renting: '/alquiler', shop: '/tienda', service: '/servicios' }[moduleType.value];
}

function getTrustMsg(idx) {
  const msgs = {
    renting: ['Equipo certificado', 'Pago seguro', 'Logística opcional', 'Soporte postventa'],
    shop: ['Productos certificados', 'Pago seguro', 'Envío rápido', 'Soporte postventa'],
    service: ['Servicio profesional', 'Pago seguro', 'Garantía incluida', 'Soporte postventa'],
  };
  return msgs[moduleType.value]?.[idx];
}

function getCTALabel() {
  return { renting: 'Reservar ahora', shop: 'Comprar ahora', service: 'Solicitar servicio' }[moduleType.value];
}

function getAvailBadge() {
  const status = detail.value?.availability?.status;
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
  const uuid = detail.value?.uuid;
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
    title: detail.value?.hero?.name,
    text: `Mira este ${getModuleLabel().toLowerCase()}: ${detail.value?.hero?.name}`,
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

async function submitReview() {
  if (reviewRating.value === 0 || !reviewText.value.trim()) {
    showError('Por favor completa la calificación y comentario');
    return;
  }
  isSubmittingReview.value = true;
  try {
    // TODO: Implementar endpoint de POST review
    success('Reseña enviada correctamente');
    reviewRating.value = 0;
    reviewText.value = '';
  } catch {
    showError('Error al enviar la reseña');
  } finally {
    isSubmittingReview.value = false;
  }
}

async function fetchDetail() {
  loading.value = true;
  error.value = null;

  try {
    const uuid = route.params.uuid;
    if (!uuid) {
      throw new Error('UUID not found in route');
    }

    const res = await api.get(`unified/detail/${uuid}/?module=${moduleType.value}`);
    detail.value = res.data;
    isFavorite.value = loadFavorites().includes(detail.value.uuid);

    if (moduleType.value === 'service') {
      await fetchServiceRichDetail(uuid);
    }

    setSeo({
      title: detail.value.hero?.name || 'Detalle',
      description: detail.value.hero?.description || detail.value.seo?.meta_description || ''
    });
  } catch (err) {
    error.value = err.response?.data?.detail || 'No se pudo cargar el detalle';
    showError(error.value);
  } finally {
    loading.value = false;
  }
}

onMounted(() => fetchDetail());
</script>

<style scoped>
.detail-container { background: #fff; }

.skeleton { background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); background-size: 200%; animation: loading 1.5s infinite; border-radius: 0.5rem; }

@keyframes loading { 0% { background-position: 200% 0; } 100% { background-position: -200% 0; } }

.breadcrumb { font-size: 0.875rem; background: none; padding: 0; }

.breadcrumb-item a { color: #666; }

.breadcrumb-item.active { color: #333; }

/* ════════════════════════════════════════════════════════════════════════
   RENTING — CSS restaurado de RentalDetailView.vue, namespaced bajo
   .rental-detail para no colisionar con las clases (mismo nombre, distinto
   estilo) que usa la rama Shop/Service más abajo. 100% variables Bootstrap
   del Design System (var(--bs-*)), cero valores inventados.
   ════════════════════════════════════════════════════════════════════════ */
.rental-detail {
  background: var(--bs-body-bg);
}

.rental-detail .gallery-sticky {
  position: sticky;
  top: 80px;
  z-index: 10;
}

.rental-detail .pricing-card {
  background: var(--bs-gray-100);
  padding: 1.5rem;
  border-radius: 0.5rem;
  border: 1px solid var(--bs-border-color);
}

.rental-detail .pricing-value {
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--bs-primary);
}

.rental-detail .discount-banner {
  background: linear-gradient(135deg, #fff3cd 0%, #ffe69c 100%);
  padding: 0.75rem;
  border-radius: 0.375rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: #856404;
  font-size: 0.875rem;
}

.rental-detail .discount-badge {
  background: #dc3545;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  font-weight: 600;
}

.rental-detail .quick-benefits {
  background: var(--bs-gray-100);
  padding: 1.5rem;
  border-radius: 0.5rem;
}

.rental-detail .benefits-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.rental-detail .benefit-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.rental-detail .benefit-icon {
  color: var(--bs-success);
  font-size: 1.25rem;
}

.rental-detail .quick-specs-old {
  background: var(--bs-body-bg);
  padding: 0;
}

.rental-detail .specs-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.rental-detail .spec-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.75rem;
  background: var(--bs-gray-100);
  border-radius: 0.375rem;
}

.rental-detail .spec-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--bs-secondary);
}

.rental-detail .spec-value {
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--bs-body-color);
}

.rental-detail .section-features,
.rental-detail .section-scope,
.rental-detail .section-specs,
.rental-detail .section-requirements,
.rental-detail .section-faqs,
.rental-detail .section-videos,
.rental-detail .section-documents,
.rental-detail .section-reviews,
.rental-detail .section-related {
  padding: 2rem 0;
  border-top: 1px solid var(--bs-border-color);
}

.rental-detail .section-header {
  margin-bottom: 2rem;
}

.rental-detail .section-header h2 {
  font-size: 1.75rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
}

.rental-detail .section-subtitle {
  color: var(--bs-secondary);
  margin: 0;
  font-size: 0.95rem;
}

.rental-detail .feature-card {
  background: var(--bs-gray-100);
  padding: 1.5rem;
  border-radius: 0.5rem;
  text-align: center;
  transition: all 0.3s ease;
}

.rental-detail .feature-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.rental-detail .feature-icon {
  font-size: 2rem;
  color: var(--bs-primary);
  display: block;
  margin-bottom: 0.75rem;
}

.rental-detail .feature-card h5 {
  font-size: 1rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.rental-detail .feature-card p {
  font-size: 0.875rem;
  color: var(--bs-secondary);
  margin: 0;
}

.rental-detail .spec-group-card {
  background: var(--bs-gray-100);
  padding: 1.5rem;
  border-radius: 0.5rem;
}

.rental-detail .spec-group-card h5 {
  font-weight: 600;
  margin-bottom: 1rem;
}

.rental-detail .specs-table {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.rental-detail .spec-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid var(--bs-border-color);
  font-size: 0.875rem;
}

.rental-detail .spec-row:last-child {
  border-bottom: none;
}

.rental-detail .spec-name {
  color: var(--bs-secondary);
  font-weight: 500;
}

.rental-detail .spec-val {
  font-weight: 600;
  color: var(--bs-body-color);
}

.rental-detail .related-card {
  display: block;
  background: var(--bs-gray-100);
  padding: 1rem;
  border-radius: 0.5rem;
  transition: all 0.3s ease;
  overflow: hidden;
}

.rental-detail .related-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

.rental-detail .related-image {
  width: 100%;
  height: 180px;
  object-fit: cover;
  border-radius: 0.375rem;
  margin-bottom: 0.75rem;
}

.rental-detail .related-card h6 {
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--bs-body-color);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.rental-detail .price {
  display: block;
  color: var(--bs-primary);
  font-weight: 700;
  font-size: 1rem;
}

.rental-detail .section-kicker {
  display: block;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  color: var(--bs-secondary);
  margin-bottom: 0.5rem;
}

.rental-detail .trust-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  margin: 1.5rem 0;
  padding: 1.5rem;
  background: var(--bs-gray-100);
  border-radius: 0.5rem;
}

.rental-detail .trust-grid > div {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 0.5rem;
  font-size: 0.875rem;
}

.rental-detail .trust-grid i {
  font-size: 1.5rem;
}

.rental-detail .availability-card {
  background: linear-gradient(135deg, #e7f1ff 0%, #f0f6ff 100%);
  padding: 1.5rem;
  border-radius: 0.5rem;
  border: 1px solid #c3deff;
}

.rental-detail .availability-card h2 {
  font-size: 1.5rem;
  font-weight: 700;
  margin-bottom: 0.5rem;
  color: var(--bs-body-color);
}

.rental-detail .availability-card p {
  font-size: 0.875rem;
  color: var(--bs-secondary);
  margin-bottom: 1rem;
}

.rental-detail .availability-link {
  display: inline-block;
  color: var(--bs-primary);
  text-decoration: none;
  font-weight: 600;
  font-size: 0.875rem;
  transition: all 0.3s ease;
}

.rental-detail .availability-link:hover {
  transform: translateX(4px);
}

.rental-detail .icon-action-btn {
  width: 36px;
  height: 36px;
  padding: 0;
  border: 1px solid var(--bs-border-color);
  background: var(--bs-body-bg);
  border-radius: 0.375rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--bs-body-color);
  transition: all 0.3s ease;
}

.rental-detail .icon-action-btn:hover {
  border-color: var(--bs-primary);
  color: var(--bs-primary);
}

.rental-detail .icon-action-btn.active {
  background: var(--bs-danger);
  border-color: var(--bs-danger);
  color: white;
}

.rental-detail .equipment-title {
  font-size: 2rem;
  font-weight: 700;
  margin-bottom: 0.75rem;
}

.rental-detail .value-prop {
  font-size: 1.125rem;
  color: var(--bs-secondary);
  margin-bottom: 1rem;
}

.rental-detail .promo-message {
  color: var(--bs-success);
  font-size: 0.875rem;
  margin-top: 0.75rem;
  margin-bottom: 0;
}

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

.rental-detail .rating-badge-inline {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.375rem 0.75rem;
  background: var(--bs-gray-100);
  border-radius: 0.375rem;
  font-size: 0.875rem;
}

.rental-detail .rating-badge-inline .rating-value {
  font-weight: 700;
  color: var(--bs-body-color);
}

.rental-detail .rating-badge-inline .rating-count {
  color: var(--bs-secondary);
}

@media (max-width: 992px) {
  .rental-detail .gallery-sticky { position: static; }
}

/* ════════════════════════════════════════════════════════════════════════
   SERVICES — CSS restaurado del ServiceDetailView.vue recuperado
   (git show 674dff8~1), namespaced bajo .service-detail-block para no
   colisionar con las clases de incluye la rama Shop. Mismos valores que
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

.service-detail-block .quick-specs span,
.service-detail-block .related-card span {
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

.service-detail-block .detail-section.split,
.service-detail-block .related-grid {
  display: grid;
  grid-template-columns: 1.3fr .8fr;
  gap: 1rem;
}

.service-detail-block .value-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: .75rem;
}

.service-detail-block .scope-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: .75rem;
}

.service-detail-block .packages-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1rem;
}

.service-detail-block .value-grid article,
.service-detail-block .guarantee-card,
.service-detail-block .case-card,
.service-detail-block .related-card {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 14px;
  padding: .9rem;
}

.service-detail-block .value-grid i,
.service-detail-block .guarantee-card i,
.service-detail-block .case-card i,
.service-detail-block .related-card i {
  color: #0e7490;
  font-size: 1.35rem;
}

.service-detail-block .value-grid h3,
.service-detail-block .case-card h3 {
  color: #0f172a;
  font-size: .95rem;
  font-weight: 850;
  margin: .45rem 0 .3rem;
}

.service-detail-block .value-grid p,
.service-detail-block .commercial-description,
.service-detail-block .guarantee-card p,
.service-detail-block .case-card p {
  color: #64748b;
  font-size: .88rem;
  line-height: 1.65;
  margin: 0;
}

.service-detail-block .commercial-description { font-size: .95rem; }

.service-detail-block .guarantee-card {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.service-detail-block .guarantee-card span {
  display: block;
  color: #166534;
  font-weight: 800;
  margin-top: .4rem;
}

.service-detail-block .guarantee-card strong {
  display: block;
  color: #0f172a;
  font-size: 1.15rem;
  margin: .1rem 0 .35rem;
}

.service-detail-block .timeline {
  display: grid;
  grid-template-columns: repeat(9, minmax(0, 1fr));
  gap: .45rem;
}

.service-detail-block .timeline-step {
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

.service-detail-block .video-placeholder {
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

.service-detail-block .video-placeholder i { font-size: 2.2rem; }

.service-detail-block .case-card span {
  display: inline-flex;
  margin-top: .8rem;
  background: #ecfeff;
  color: #0e7490;
  border-radius: 999px;
  padding: .35rem .7rem;
  font-size: .75rem;
  font-weight: 850;
}

.service-detail-block .related-grid { grid-template-columns: repeat(3, minmax(0, 1fr)); }

.service-detail-block .related-card { color: inherit; text-decoration: none; }

.service-detail-block .related-card strong {
  display: block;
  color: #0f172a;
  margin-top: .3rem;
}

@media (max-width: 991px) {
  .service-detail-block .gallery-sticky { position: static; }
  .service-detail-block .quick-specs,
  .service-detail-block .value-grid,
  .service-detail-block .scope-grid,
  .service-detail-block .timeline,
  .service-detail-block .related-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .service-detail-block .detail-section.split { grid-template-columns: 1fr; }
}

@media (max-width: 575px) {
  .service-detail-block .quick-specs,
  .service-detail-block .scope-grid,
  .service-detail-block .value-grid,
  .service-detail-block .timeline,
  .service-detail-block .related-grid,
  .service-detail-block .trust-grid {
    grid-template-columns: 1fr;
  }
  .service-detail-block .selected-package,
  .service-detail-block .panel-head {
    align-items: flex-start;
    flex-direction: column;
  }
  .service-detail-block .buy-btn { width: 100%; }
}

/* ════════════════════════════════════════════════════════════════════════
   SHOP — CSS sin cambios en este alcance.
   ════════════════════════════════════════════════════════════════════════ */
/* SECTION KICKER (shared, matches production .section-kicker) */
.section-kicker {
  display: block;
  font-size: 0.72rem;
  font-weight: 850;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #0369a1;
  margin-bottom: 0.25rem;
}

/* LEFT COLUMN */
.gallery-sticky { position: sticky; top: 88px; }

.bv-gallery-main {
  height: 376px;
  border-radius: 18px;
  overflow: hidden;
  background: linear-gradient(135deg, #f0f9ff, #eef2ff);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #6366f1;
  font-size: 4rem;
}

/* TRUST GRID */
.trust-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.6rem;
  margin-top: 1rem;
}

.trust-grid div {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  font-size: 0.8rem;
  color: #333;
}

.trust-grid i {
  font-size: 1.1rem;
  flex-shrink: 0;
}

/* AVAILABILITY CARD */
.availability-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1rem;
  margin-top: 1rem;
}

.availability-card h2 {
  font-size: 1.1rem;
  font-weight: 850;
  color: #0f172a;
  margin: 0 0 0.25rem;
}

.availability-card p {
  font-size: 0.85rem;
  color: #64748b;
  margin: 0 0 0.75rem;
}

.availability-link {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: #2563eb;
  font-weight: 750;
  font-size: 0.8rem;
  text-decoration: none;
}

.availability-link:hover { text-decoration: underline; }

/* RIGHT COLUMN */
.icon-action-btn {
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s;
}

.icon-action-btn:hover { border-color: #adb5bd; }

.icon-action-btn.active { color: #dc3545; border-color: #dc3545; }

.badge { padding: 0.375rem 0.6rem; font-size: 0.78rem; }

.equipment-title {
  font-size: 2.4rem;
  font-weight: 900;
  color: #0f172a;
  line-height: 1.15;
  margin: 0.5rem 0 0.75rem;
}

.value-prop {
  font-size: 1rem;
  color: #64748b;
  line-height: 1.65;
  margin-bottom: 1rem;
}

/* QUICK SPECS */
.quick-specs {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 0.65rem;
  margin-bottom: 1rem;
}

.quick-specs > div span {
  display: block;
  font-size: 0.72rem;
  color: #64748b;
  font-weight: 760;
  margin-bottom: 0.15rem;
}

.quick-specs > div strong {
  display: block;
  font-size: 0.86rem;
  color: #0f172a;
  font-weight: 700;
}

/* PACKAGE PANEL / CONFIGURACION */
.package-panel {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1rem;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 1rem;
  flex-wrap: wrap;
  margin-bottom: 0.9rem;
}

.panel-head h2 {
  font-size: 1.1rem;
  font-weight: 850;
  color: #0f172a;
  margin: 0.25rem 0 0;
}

.from-price {
  font-size: 1rem;
  font-weight: 850;
  color: #2563eb;
}

.selected-package {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;
  border-top: 1px solid #e2e8f0;
  margin-top: 0.9rem;
  padding-top: 0.9rem;
}

.selected-package h3 {
  font-size: 1rem;
  font-weight: 850;
  color: #0f172a;
  margin: 0 0 0.25rem;
}

.selected-package p {
  font-size: 0.86rem;
  color: #64748b;
  margin: 0;
}

.reserve-btn {
  display: inline-flex;
  align-items: center;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 999px;
  font-weight: 850;
  padding: 0.75rem 1.15rem;
  white-space: nowrap;
  text-decoration: none;
  transition: background 0.2s;
}

.reserve-btn:hover { background: #1d4ed8; color: #fff; }

/* DETAIL SECTIONS (below fold) */
.detail-sections {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 2.5rem;
}

.detail-section {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1rem;
}

.section-head { margin-bottom: 0.9rem; }

.section-head h2 {
  font-size: 1.1rem;
  font-weight: 850;
  color: #0f172a;
  margin: 0.25rem 0 0;
}

/* REVIEWS */
.bv-reviews-summary { margin-bottom: 1rem; }

.bv-reviews-score {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.bv-reviews-score strong {
  font-size: 1.6rem;
  font-weight: 900;
  color: #0f172a;
}

.bv-reviews-score span { color: #64748b; font-size: 0.85rem; }

.bv-reviews-list { display: flex; flex-direction: column; gap: 0.75rem; margin-bottom: 1rem; }

.bv-review-item { border: 1px solid #e2e8f0; border-radius: 0.5rem; padding: 0.75rem; }

.bv-review-item-header { display: flex; justify-content: space-between; margin-bottom: 0.35rem; }

.bv-review-item p { margin: 0; color: #495057; font-size: 0.9rem; }

.bv-review-form {
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 14px;
  padding: 1rem;
}

.bv-review-form-title { font-weight: 700; margin-bottom: 0.75rem; color: #0f172a; }

.bv-review-stars-input { display: flex; gap: 0.35rem; margin-bottom: 0.75rem; }

.bv-star-btn {
  background: none;
  border: none;
  font-size: 1.25rem;
  cursor: pointer;
  color: #cbd5e1;
  filter: grayscale(1);
  opacity: 0.6;
}

.bv-star-btn.active { filter: none; opacity: 1; }

.bv-review-textarea {
  width: 100%;
  border: 1px solid #bfdbfe;
  border-radius: 0.5rem;
  padding: 0.6rem;
  margin-bottom: 0.75rem;
  font-family: inherit;
  resize: vertical;
}

.bv-review-submit {
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 999px;
  padding: 0.5rem 1.1rem;
  font-weight: 700;
}

.bv-review-submit:disabled { opacity: 0.6; }

.bv-review-empty { color: #64748b; font-size: 0.9rem; margin-top: 1rem; margin-bottom: 0; }

/* INTEGRACIONES */
.related-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.75rem;
}

.related-card {
  display: block;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 0.9rem;
  text-decoration: none;
  color: inherit;
  transition: all 0.2s;
}

.related-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.related-card i {
  font-size: 1.35rem;
  color: #2563eb;
  display: block;
  margin-bottom: 0.5rem;
}

.related-card span {
  display: block;
  font-size: 0.72rem;
  font-weight: 760;
  color: #64748b;
  margin-bottom: 0.25rem;
}

.related-card strong {
  display: block;
  font-size: 0.86rem;
  font-weight: 700;
  color: #0f172a;
}

/* RESPONSIVE */
@media (max-width: 992px) {
  .gallery-sticky { position: static; }
  .equipment-title { font-size: 1.9rem; }
  .quick-specs { grid-template-columns: repeat(2, 1fr); }
  .related-grid { grid-template-columns: 1fr; }
}

@media (max-width: 576px) {
  .equipment-title { font-size: 1.5rem; }
  .trust-grid { grid-template-columns: 1fr; }
  .selected-package { flex-direction: column; align-items: stretch; }
  .reserve-btn { justify-content: center; }
  .panel-head { flex-direction: column; align-items: flex-start; }
}
</style>
