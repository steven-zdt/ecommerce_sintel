<template>
  <div>

    <!-- =========================================================
         CREATE MODE — formulario basico
    ========================================================= -->
    <template v-if="localMode === 'create'">
      <div class="alert border-0 py-2 px-3 mb-4 small" style="background:#eff6ff;border-left:3px solid #3b82f6 !important;border-radius:8px">
        <i class="bi bi-info-circle me-2 text-primary"></i>
        Crea el equipo primero. Luego configura variantes, logistica y costos desde las pestanas.
      </div>

      <form @submit.prevent="submitCreate">
        <div class="mb-3">
          <label class="form-label small fw-bold">Nombre <span class="text-danger">*</span></label>
          <input v-model="form.name" type="text" class="form-control" required placeholder="Ej: Grua Hidraulica 20T">
        </div>
        <div class="mb-3">
          <label class="form-label small fw-bold">Descripcion</label>
          <textarea v-model="form.description" class="form-control" rows="3" placeholder="Descripcion del equipo..."></textarea>
        </div>
        <div class="mb-3">
          <label class="form-label small fw-bold">Categoria <span class="text-danger">*</span></label>
          <select v-model="form.category" class="form-select" required>
            <option value="">— Seleccionar —</option>
            <option v-for="cat in categories" :key="cat.uuid" :value="cat.uuid">{{ cat.name }}</option>
          </select>
        </div>
        <div class="mb-3">
          <label class="form-label small fw-bold">Marca</label>
          <select v-model="form.brand" class="form-select">
            <option value="">— Sin marca —</option>
            <option v-for="brd in brands" :key="brd.uuid" :value="brd.uuid">{{ brd.name }}</option>
          </select>
        </div>
        <div class="row g-3 mb-4">
          <div class="col-6">
            <div class="form-check form-switch">
              <input v-model="form.is_active" class="form-check-input" type="checkbox" id="eqActive">
              <label class="form-check-label small" for="eqActive">Activo</label>
            </div>
          </div>
          <div class="col-6">
            <div class="form-check form-switch">
              <input v-model="form.is_featured" class="form-check-input" type="checkbox" id="eqFeatured">
              <label class="form-check-label small" for="eqFeatured">Destacado</label>
            </div>
          </div>
        </div>
        <div class="d-flex gap-2">
          <button type="submit" class="btn btn-primary w-100" :disabled="loading">
            <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
            <i v-else class="bi bi-check-lg me-1"></i> Crear Equipo
          </button>
          <button type="button" class="btn btn-light border" @click="$emit('cancel')" :disabled="loading">Cancelar</button>
        </div>
      </form>
    </template>

    <!-- =========================================================
         EDIT MODE — tabs completos
    ========================================================= -->
    <template v-else-if="localItem">

      <!-- Header equipo -->
      <div class="d-flex align-items-center gap-3 mb-4 p-3 bg-light rounded-3">
        <div class="rounded-2 d-flex align-items-center justify-content-center bg-primary-subtle flex-shrink-0" style="width:38px;height:38px">
          <i class="bi bi-gear-wide-connected text-primary"></i>
        </div>
        <div class="flex-grow-1 min-w-0">
          <div class="fw-bold text-dark small text-truncate">{{ localItem.name }}</div>
          <div class="text-muted" style="font-size:.72rem">{{ localItem.category?.name || 'Sin categoria' }}</div>
        </div>
        <span
          v-if="isNewlyCreated"
          class="badge bg-success-subtle text-success border border-success-subtle flex-shrink-0"
          style="font-size:.68rem"
        >
          <i class="bi bi-check-circle me-1"></i>Creado
        </span>
        <span
          v-if="!localItem.is_active"
          class="badge bg-warning-subtle text-warning border border-warning-subtle flex-shrink-0"
          style="font-size:.68rem"
        >Inactivo</span>
      </div>

      <!-- Tabs -->
      <ul class="nav nav-tabs mb-4" style="flex-wrap:nowrap;overflow-x:auto">
        <li class="nav-item" v-for="tab in tabs" :key="tab.key">
          <button
            class="nav-link d-flex align-items-center gap-1 text-nowrap"
            :class="{ active: activeTab === tab.key }"
            @click="activeTab = tab.key"
            type="button"
          >
            <i :class="['bi', tab.icon]" style="font-size:.8rem"></i>
            <span class="small fw-medium">{{ tab.label }}</span>
            <span v-if="tab.badge" class="ms-1 badge rounded-pill" :class="tab.badgeClass" style="font-size:.6rem">{{ tab.badge }}</span>
          </button>
        </li>
      </ul>

      <!-- ======= TAB: DATOS ======= -->
      <div v-show="activeTab === 'datos'">
        <form @submit.prevent="submitUpdate">
          <div class="mb-3">
            <label class="form-label small fw-bold">Nombre <span class="text-danger">*</span></label>
            <input v-model="form.name" type="text" class="form-control" required placeholder="Nombre del equipo">
          </div>
          <div class="mb-3">
            <label class="form-label small fw-bold">Descripcion</label>
            <textarea v-model="form.description" class="form-control" rows="3"></textarea>
          </div>
          <div class="row g-3 mb-3">
            <div class="col-6">
              <label class="form-label small fw-bold">Categoria <span class="text-danger">*</span></label>
              <select v-model="form.category" class="form-select" required>
                <option value="">— Seleccionar —</option>
                <option v-for="cat in categories" :key="cat.uuid" :value="cat.uuid">{{ cat.name }}</option>
              </select>
            </div>
            <div class="col-6">
              <label class="form-label small fw-bold">Marca</label>
              <select v-model="form.brand" class="form-select">
                <option value="">— Sin marca —</option>
                <option v-for="brd in brands" :key="brd.uuid" :value="brd.uuid">{{ brd.name }}</option>
              </select>
            </div>
          </div>
          <div class="row g-3 mb-4">
            <div class="col-6">
              <div class="form-check form-switch">
                <input v-model="form.is_active" class="form-check-input" type="checkbox" id="eqActive2">
                <label class="form-check-label small" for="eqActive2">Activo</label>
              </div>
            </div>
            <div class="col-6">
              <div class="form-check form-switch">
                <input v-model="form.is_featured" class="form-check-input" type="checkbox" id="eqFeatured2">
                <label class="form-check-label small" for="eqFeatured2">Destacado</label>
              </div>
            </div>
          </div>
          <button type="submit" class="btn btn-primary w-100" :disabled="loading">
            <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
            Guardar Cambios
          </button>
        </form>
      </div>

      <!-- ======= TAB: VARIANTES ======= -->
      <div v-show="activeTab === 'variantes'">
        <div class="d-flex align-items-center justify-content-between mb-3">
          <div>
            <p class="text-muted small mb-0">Define SKU, precio/dia, precio/hora y stock disponible.</p>
          </div>
          <button
            type="button"
            class="btn btn-sm btn-primary"
            @click="openVariantForm"
            :disabled="showVariantForm"
          >
            <i class="bi bi-plus-lg me-1"></i> Nueva Variante
          </button>
        </div>

        <!-- Form nueva variante -->
        <div v-if="showVariantForm" class="card border-0 bg-light p-3 mb-3 rounded-3">
          <h6 class="fw-semibold small mb-3">{{ editingVariant ? 'Editar Variante' : 'Nueva Variante' }}</h6>
          <div class="row g-2 mb-3">
            <div class="col-12">
              <label class="form-label small">SKU <span class="text-danger">*</span></label>
              <input
                v-model="vForm.sku"
                type="text"
                class="form-control form-control-sm"
                placeholder="Ej: GA110-STD"
              >
            </div>
            <div class="col-6">
              <label class="form-label small">Precio / Dia</label>
              <div class="input-group input-group-sm">
                <span class="input-group-text">$</span>
                <input v-model.number="vForm.rental_price_per_day" type="number" step="0.01" min="0" class="form-control" placeholder="0.00">
              </div>
            </div>
            <div class="col-6">
              <label class="form-label small">Precio / Hora</label>
              <div class="input-group input-group-sm">
                <span class="input-group-text">$</span>
                <input v-model.number="vForm.rental_price_per_hour" type="number" step="0.01" min="0" class="form-control" placeholder="0.00">
              </div>
            </div>
            <div class="col-6">
              <label class="form-label small">Stock</label>
              <input v-model.number="vForm.stock" type="number" min="0" class="form-control form-control-sm" placeholder="0">
            </div>
            <div class="col-6 d-flex align-items-end pb-1">
              <div class="form-check form-switch ms-1">
                <input v-model="vForm.is_active" class="form-check-input" type="checkbox" id="vActive">
                <label class="form-check-label small" for="vActive">Activa</label>
              </div>
            </div>
          </div>
          <div class="d-flex gap-2">
            <button type="button" class="btn btn-sm btn-primary" @click="saveVariant" :disabled="vLoading">
              <span v-if="vLoading" class="spinner-border spinner-border-sm me-1"></span>
              {{ editingVariant ? 'Guardar' : 'Agregar' }}
            </button>
            <button type="button" class="btn btn-sm btn-light border" @click="cancelVariantForm">Cancelar</button>
          </div>
        </div>

        <!-- Lista variantes -->
        <div v-if="variants.length" class="list-group list-group-flush">
          <div v-for="v in variants" :key="v.uuid" class="list-group-item px-0 py-2">
            <div class="d-flex align-items-start justify-content-between gap-2">
              <div class="flex-grow-1">
                <div class="d-flex align-items-center gap-2">
                  <code class="small fw-bold text-dark">{{ v.sku }}</code>
                  <span
                    class="badge rounded-pill"
                    :class="v.stock > 0 ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'"
                    style="font-size:.65rem"
                  >{{ v.stock }} und</span>
                  <span v-if="!v.is_active" class="badge bg-secondary-subtle text-secondary" style="font-size:.65rem">Inactiva</span>
                  <span v-if="v.uuid === firstVariantUuid && variants.length > 1" class="badge bg-primary-subtle text-primary" style="font-size:.65rem">Principal</span>
                </div>
                <div class="text-muted mt-1" style="font-size:.75rem">
                  <span v-if="v.rental_price_per_day"><i class="bi bi-calendar3 me-1"></i>{{ formatCOP(v.rental_price_per_day) }}/dia</span>
                  <span v-if="v.rental_price_per_day && v.rental_price_per_hour" class="mx-2">·</span>
                  <span v-if="v.rental_price_per_hour"><i class="bi bi-clock me-1"></i>{{ formatCOP(v.rental_price_per_hour) }}/hora</span>
                </div>
              </div>
              <div class="btn-group btn-group-sm flex-shrink-0">
                <button type="button" class="btn btn-light border-end" @click="startEditVariant(v)" title="Editar">
                  <i class="bi bi-pencil text-primary"></i>
                </button>
                <button type="button" class="btn btn-light" @click="deleteVariant(v)" :disabled="vLoading" title="Eliminar">
                  <i class="bi bi-trash text-danger"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
        <div v-else-if="!showVariantForm" class="text-center py-4 text-muted">
          <i class="bi bi-layers fs-3 d-block mb-2 opacity-50"></i>
          <p class="small mb-2">Sin variantes registradas.</p>
          <button type="button" class="btn btn-sm btn-outline-primary" @click="openVariantForm">
            <i class="bi bi-plus-lg me-1"></i> Crear primera variante
          </button>
        </div>
      </div>

      <!-- ======= TAB: LOGISTICA ======= -->
      <div v-show="activeTab === 'logistica'">
        <p class="text-muted small mb-3">
          Costos predefinidos de transporte y puesta en marcha. Se pre-rellenaran en la solicitud del cliente.
        </p>

        <div class="row g-3 mb-3">
          <div class="col-6" v-for="field in logisticsFields" :key="field.key">
            <label class="form-label small fw-semibold">{{ field.label }}</label>
            <div class="input-group input-group-sm">
              <span class="input-group-text">$</span>
              <input
                v-model.number="logisticsForm[field.key]"
                type="number"
                min="0"
                step="0.01"
                class="form-control"
                placeholder="0"
              >
            </div>
          </div>
          <div class="col-12">
            <label class="form-label small fw-semibold">Notas internas</label>
            <textarea v-model="logisticsForm.notes" class="form-control form-control-sm" rows="2" placeholder="Observaciones de logistica..."></textarea>
          </div>
        </div>

        <div class="d-flex gap-2">
          <button type="button" class="btn btn-primary w-100" @click="saveLogistics" :disabled="logisticsLoading">
            <span v-if="logisticsLoading" class="spinner-border spinner-border-sm me-2"></span>
            <i v-else class="bi bi-floppy me-1"></i>
            {{ hasLogistics ? 'Actualizar Logistica' : 'Guardar Logistica' }}
          </button>
          <button
            v-if="hasLogistics"
            type="button"
            class="btn btn-outline-danger"
            @click="deleteLogistics"
            :disabled="logisticsLoading"
            title="Eliminar configuracion"
          >
            <i class="bi bi-trash"></i>
          </button>
        </div>

        <div v-if="hasLogistics" class="mt-3">
          <span class="badge bg-success-subtle text-success border border-success-subtle" style="font-size:.72rem">
            <i class="bi bi-check-circle me-1"></i>Logistica configurada
          </span>
        </div>
      </div>

      <!-- ======= TAB: GALERIA ======= -->
      <div v-show="activeTab === 'galeria'">
        <GalleryManager :equipment-uuid="localItem.uuid" />
      </div>

      <!-- ======= TAB: INCLUYE ======= -->
      <div v-show="activeTab === 'incluye'">
        <CatalogListManager
          :equipment-uuid="localItem.uuid"
          endpoint="dashboard/rental-included-items/"
          resource="included-items"
          resource-label="Item incluido"
          resource-label-plural="Items incluidos"
          hint="Que trae el alquiler (equipo principal, cables, maletin, soporte, etc.)."
          empty-icon="bi-check2-circle"
          :fields="[
            { key: 'title', label: 'Titulo', required: true },
            { key: 'description', label: 'Descripcion', type: 'textarea', col: 'col-12' },
            { key: 'icon', label: 'Icono', type: 'icon', placeholder: 'bi-check-circle' },
          ]"
        />
      </div>

      <!-- ======= TAB: NO INCLUYE ======= -->
      <div v-show="activeTab === 'no-incluye'">
        <CatalogListManager
          :equipment-uuid="localItem.uuid"
          endpoint="dashboard/rental-excluded-items/"
          resource="excluded-items"
          resource-label="Item no incluido"
          resource-label-plural="Items no incluidos"
          hint="Que NO cubre el alquiler (consumibles, obra civil, licencias, etc.)."
          empty-icon="bi-x-circle"
          :fields="[
            { key: 'title', label: 'Titulo', required: true },
            { key: 'description', label: 'Descripcion', type: 'textarea', col: 'col-12' },
            { key: 'icon', label: 'Icono', type: 'icon', placeholder: 'bi-x-circle' },
          ]"
        />
      </div>

      <!-- ======= TAB: CARACTERISTICAS ======= -->
      <div v-show="activeTab === 'caracteristicas'">
        <CatalogListManager
          :equipment-uuid="localItem.uuid"
          endpoint="dashboard/rental-features/"
          resource="features"
          resource-label="Caracteristica"
          resource-label-plural="Caracteristicas"
          hint="Atributos destacados del equipo (ej. Potencia: 20T)."
          empty-icon="bi-stars"
          :fields="[
            { key: 'title', label: 'Titulo', required: true, col: 'col-6' },
            { key: 'value', label: 'Valor', col: 'col-6' },
            { key: 'icon', label: 'Icono', type: 'icon', placeholder: 'bi-lightning-charge' },
          ]"
        />
      </div>

      <!-- ======= TAB: ESPECIFICACIONES ======= -->
      <div v-show="activeTab === 'especificaciones'">
        <SpecificationsManager :equipment-uuid="localItem.uuid" />
      </div>

      <!-- ======= TAB: SERVICIOS INCLUIDOS ======= -->
      <div v-show="activeTab === 'servicios-incluidos'">
        <CatalogListManager
          :equipment-uuid="localItem.uuid"
          endpoint="dashboard/rental-services-included/"
          resource="services-included"
          resource-label="Servicio incluido"
          resource-label-plural="Servicios incluidos"
          hint="Servicios que ya vienen en el precio del alquiler (ej. entrega basica)."
          empty-icon="bi-hand-thumbs-up"
          :fields="[
            { key: 'title', label: 'Titulo', required: true },
            { key: 'description', label: 'Descripcion', type: 'textarea', col: 'col-12' },
            { key: 'icon', label: 'Icono', type: 'icon', placeholder: 'bi-truck' },
          ]"
        />
      </div>

      <!-- ======= TAB: SERVICIOS OPCIONALES ======= -->
      <div v-show="activeTab === 'servicios-opcionales'">
        <CatalogListManager
          :equipment-uuid="localItem.uuid"
          endpoint="dashboard/rental-optional-services/"
          resource="optional-services"
          resource-label="Servicio opcional"
          resource-label-plural="Servicios opcionales"
          hint="Servicios adicionales que el cliente puede contratar por un costo extra."
          empty-icon="bi-plus-circle"
          :fields="[
            { key: 'title', label: 'Titulo', required: true },
            { key: 'description', label: 'Descripcion', type: 'textarea', col: 'col-12' },
            { key: 'price', label: 'Precio', type: 'price', col: 'col-6' },
            { key: 'icon', label: 'Icono', type: 'icon', col: 'col-6' },
          ]"
        />
      </div>

      <!-- ======= TAB: REQUISITOS ======= -->
      <div v-show="activeTab === 'requisitos'">
        <CatalogListManager
          :equipment-uuid="localItem.uuid"
          endpoint="dashboard/rental-requirements/"
          resource="requirements"
          resource-label="Requisito"
          resource-label-plural="Requisitos"
          hint="Condiciones necesarias para rentar el equipo (acceso vehicular, punto electrico, etc.)."
          empty-icon="bi-clipboard-check"
          :fields="[
            { key: 'title', label: 'Titulo', required: true },
            { key: 'description', label: 'Descripcion', type: 'textarea', col: 'col-12' },
          ]"
        />
      </div>

      <!-- ======= TAB: DOCUMENTACION ======= -->
      <div v-show="activeTab === 'documentacion'">
        <DocumentsManager :equipment-uuid="localItem.uuid" />
      </div>

      <!-- ======= TAB: VIDEOS ======= -->
      <div v-show="activeTab === 'videos'">
        <VideosManager :equipment-uuid="localItem.uuid" />
      </div>

      <!-- ======= TAB: FAQ ======= -->
      <div v-show="activeTab === 'faq'">
        <CatalogListManager
          :equipment-uuid="localItem.uuid"
          endpoint="dashboard/rental-faqs/"
          resource="faqs"
          resource-label="Pregunta"
          resource-label-plural="Preguntas frecuentes"
          hint="Preguntas frecuentes mostradas en el detalle publico del equipo."
          empty-icon="bi-question-circle"
          primary-field="question"
          secondary-field="answer"
          :fields="[
            { key: 'question', label: 'Pregunta', required: true, col: 'col-12' },
            { key: 'answer', label: 'Respuesta', type: 'textarea', required: true, col: 'col-12' },
          ]"
        />
      </div>

      <!-- ======= TAB: SEO ======= -->
      <div v-show="activeTab === 'seo'">
        <SeoManager :equipment="localItem" @updated="(data) => Object.assign(localItem, data)" />
      </div>

      <!-- ======= TAB: MARKETING ======= -->
      <div v-show="activeTab === 'marketing'">
        <p class="text-muted small mb-3">
          Configuracion comercial y visual exclusiva de este equipo -- se refleja automaticamente
          en el detalle publico. Nada de esto se comparte ni se hereda de otros equipos.
        </p>

        <!-- Precio Base de Referencia (desde variante) -->
        <div v-if="variants.length" class="alert alert-info border-0 p-3 mb-3 rounded-3" style="background-color:#dbeafe;border-left:3px solid #0284c7 !important">
          <div class="d-flex align-items-start gap-2">
            <i class="bi bi-info-circle-fill text-info mt-1" style="font-size:.9rem;flex-shrink:0"></i>
            <div class="flex-grow-1 small">
              <div class="fw-semibold text-dark mb-1">Precio base (desde variante principal)</div>
              <div class="text-muted mb-2">SKU: <code class="text-dark">{{ variants[0]?.sku }}</code></div>
              <div v-if="variants[0]?.rental_price_per_day" class="text-dark fw-semibold">
                <i class="bi bi-tag me-1"></i>{{ formatCOP(variants[0].rental_price_per_day) }} por día
                <span v-if="variants[0]?.rental_price_per_hour" class="ms-2">
                  <i class="bi bi-clock me-1"></i>{{ formatCOP(variants[0].rental_price_per_hour) }} por hora
                </span>
              </div>
              <div v-else class="text-warning small">
                <i class="bi bi-exclamation-circle me-1"></i>No has configurado precios en la variante
              </div>
            </div>
          </div>
        </div>
        <div v-else class="alert alert-warning border-0 p-3 mb-3 rounded-3" style="background-color:#fef3c7;border-left:3px solid #f59e0b !important">
          <i class="bi bi-exclamation-triangle me-2 text-warning"></i>
          <span class="small">Crea una variante primero para establecer el precio base de marketing</span>
        </div>

        <!-- Precio comercial -->
        <h6 class="fw-semibold small text-uppercase text-muted mb-2">Precio comercial</h6>
        <div class="row g-2 mb-3">
          <div class="col-6">
            <label class="form-label small">Precio de referencia (anterior)</label>
            <div class="input-group input-group-sm">
              <span class="input-group-text">$</span>
              <input v-model.number="marketingForm.reference_price" type="number" min="0" step="0.01" class="form-control" placeholder="850000">
            </div>
            <small class="text-muted mt-1 d-block">
              <i class="bi bi-lightbulb me-1"></i>
              <span v-if="variants[0]?.rental_price_per_day">
                Sugerencia: usa {{ formatCOP(variants[0].rental_price_per_day) }} como referencia
              </span>
              <span v-else>Completa el precio en la variante principal</span>
            </small>
          </div>
          <div class="col-6">
            <label class="form-label small">Precio promocional</label>
            <div class="input-group input-group-sm">
              <span class="input-group-text">$</span>
              <input v-model.number="marketingForm.promo_price" type="number" min="0" step="0.01" class="form-control" placeholder="520000">
            </div>
          </div>
          <div class="col-12">
            <div class="form-check form-switch">
              <input class="form-check-input" type="checkbox" v-model="marketingForm.show_discount_percentage" id="mktShowDiscount">
              <label class="form-check-label small" for="mktShowDiscount">Mostrar porcentaje de descuento (calculado automaticamente)</label>
            </div>
            <span v-if="marketingDiscountPreview" class="badge bg-danger-subtle text-danger border border-danger-subtle mt-1">
              AHORRA {{ marketingDiscountPreview }}%
            </span>
          </div>
        </div>

        <!-- Etiquetas comerciales -->
        <h6 class="fw-semibold small text-uppercase text-muted mb-2 mt-4">Etiquetas comerciales</h6>
        <div class="d-flex flex-wrap gap-2 mb-3">
          <button
            v-for="opt in marketingTagOptions" :key="opt.value"
            type="button"
            class="btn btn-sm"
            :class="marketingForm.tags.includes(opt.value) ? 'btn-primary' : 'btn-outline-secondary'"
            @click="toggleMarketingTag(opt.value)"
          >{{ opt.label }}</button>
        </div>

        <!-- Mensajes de conversion -->
        <h6 class="fw-semibold small text-uppercase text-muted mb-2 mt-4">Mensajes de conversion</h6>
        <div class="row g-2 mb-3">
          <div class="col-12">
            <label class="form-label small">Mensaje principal</label>
            <textarea v-model="marketingForm.main_message" class="form-control form-control-sm" rows="2" placeholder="Ideal para conciertos, ferias, eventos empresariales..."></textarea>
          </div>
          <div class="col-6">
            <label class="form-label small">Beneficio destacado</label>
            <input v-model="marketingForm.featured_benefit" type="text" class="form-control form-control-sm" placeholder="Entrega inmediata">
          </div>
          <div class="col-6">
            <label class="form-label small">Mensaje de confianza</label>
            <input v-model="marketingForm.trust_message" type="text" class="form-control form-control-sm" placeholder="Equipo certificado">
          </div>
          <div class="col-6">
            <label class="form-label small">Mensaje de urgencia</label>
            <input v-model="marketingForm.urgency_message" type="text" class="form-control form-control-sm" placeholder="Ultimas unidades disponibles">
          </div>
          <div class="col-6">
            <label class="form-label small">Prueba social</label>
            <input v-model="marketingForm.social_proof_message" type="text" class="form-control form-control-sm" placeholder="Mas de 500 alquileres realizados">
          </div>
        </div>

        <!-- Comparativa economica -->
        <h6 class="fw-semibold small text-uppercase text-muted mb-2 mt-4">Comparativa economica (comprar vs alquilar)</h6>
        <div class="row g-2 mb-3">
          <div class="col-6">
            <label class="form-label small">Precio estimado de compra</label>
            <div class="input-group input-group-sm">
              <span class="input-group-text">$</span>
              <input v-model.number="marketingForm.purchase_price_reference" type="number" min="0" step="0.01" class="form-control" placeholder="12500000">
            </div>
          </div>
          <div class="col-6">
            <label class="form-label small">Mensaje financiero</label>
            <input v-model="marketingForm.financial_message" type="text" class="form-control form-control-sm" placeholder="Ahorra comprando vs alquilar">
          </div>
          <div v-if="marketingSavingsPreview" class="col-12">
            <span class="badge bg-success-subtle text-success border border-success-subtle">
              Ahorras {{ marketingSavingsPreview }}% alquilando
            </span>
          </div>
        </div>

        <!-- Casos de uso -->
        <h6 class="fw-semibold small text-uppercase text-muted mb-2 mt-4">Casos de uso</h6>
        <div class="d-flex flex-wrap gap-2 mb-2">
          <span v-for="(uc, idx) in marketingForm.use_cases" :key="idx" class="badge bg-light text-dark border d-flex align-items-center gap-1">
            {{ uc }}
            <i class="bi bi-x-lg" style="cursor:pointer;font-size:.65rem" @click="removeUseCase(idx)"></i>
          </span>
        </div>
        <div class="input-group input-group-sm mb-3" style="max-width:320px">
          <input v-model="newUseCase" type="text" class="form-control" placeholder="Ej: Eventos" @keyup.enter="addUseCase">
          <button type="button" class="btn btn-outline-secondary" @click="addUseCase">Agregar</button>
        </div>

        <!-- CTA y Banner -->
        <h6 class="fw-semibold small text-uppercase text-muted mb-2 mt-4">Llamado a la accion y banner</h6>
        <div class="row g-2 mb-3">
          <div class="col-6">
            <label class="form-label small">Texto del boton (CTA)</label>
            <input v-model="marketingForm.cta_label" type="text" class="form-control form-control-sm" placeholder="Reservar ahora">
          </div>
          <div class="col-6">
            <label class="form-label small">Banner promocional</label>
            <input v-model="marketingForm.promo_banner_message" type="text" class="form-control form-control-sm" placeholder="Transporte incluido por tiempo limitado">
          </div>
        </div>

        <!-- Beneficios rapidos -->
        <h6 class="fw-semibold small text-uppercase text-muted mb-2 mt-4">Beneficios rapidos</h6>
        <div class="d-flex flex-column gap-1 mb-2">
          <div v-for="(b, idx) in marketingForm.quick_benefits" :key="idx" class="d-flex align-items-center gap-2 p-1 rounded border bg-white">
            <i :class="['bi', b.icon || 'bi-check-circle']"></i>
            <span class="small flex-grow-1">{{ b.label }}</span>
            <i class="bi bi-trash text-danger" style="cursor:pointer" @click="removeQuickBenefit(idx)"></i>
          </div>
        </div>
        <div class="row g-2 mb-3">
          <div class="col-4">
            <input v-model="newQuickBenefit.icon" type="text" class="form-control form-control-sm" placeholder="bi-truck (icono)">
          </div>
          <div class="col-6">
            <input v-model="newQuickBenefit.label" type="text" class="form-control form-control-sm" placeholder="Transporte incluido" @keyup.enter="addQuickBenefit">
          </div>
          <div class="col-2">
            <button type="button" class="btn btn-sm btn-outline-secondary w-100" @click="addQuickBenefit">
              <i class="bi bi-plus-lg"></i>
            </button>
          </div>
        </div>

        <div class="d-flex gap-2 mt-4">
          <button type="button" class="btn btn-primary w-100" @click="saveMarketing" :disabled="marketingLoading">
            <span v-if="marketingLoading" class="spinner-border spinner-border-sm me-2"></span>
            <i v-else class="bi bi-floppy me-1"></i>
            {{ hasMarketing ? 'Actualizar Marketing' : 'Guardar Marketing' }}
          </button>
          <button
            v-if="hasMarketing"
            type="button"
            class="btn btn-outline-danger"
            @click="deleteMarketing"
            :disabled="marketingLoading"
            title="Eliminar configuracion"
          >
            <i class="bi bi-trash"></i>
          </button>
        </div>
      </div>

      <!-- ======= TAB: COSTOS ======= -->
      <div v-show="activeTab === 'costos'">

        <!-- Info variante principal -->
        <div v-if="firstVariantUuid" class="d-flex align-items-center gap-2 mb-3 p-2 rounded-2 border" style="background:#f8fafc">
          <i class="bi bi-info-circle text-primary small"></i>
          <span class="small text-muted">Las asignaciones aplican a la variante principal:
            <code class="text-dark">{{ variants[0]?.sku }}</code>
          </span>
        </div>
        <div v-else class="alert alert-warning border-0 py-2 px-3 mb-3 small">
          <i class="bi bi-exclamation-triangle me-2"></i>
          Registra al menos una variante en la pestana "Variantes" para poder asignar reglas.
        </div>

        <!-- Header -->
        <div class="d-flex align-items-center justify-content-between mb-3">
          <span class="small text-muted fw-semibold">{{ costRules.length }} regla(s) definidas</span>
          <button
            type="button"
            class="btn btn-sm btn-primary"
            @click="showCostForm = !showCostForm"
          >
            <i class="bi bi-plus-lg me-1"></i> Nueva Regla
          </button>
        </div>

        <!-- Formulario crear regla -->
        <div v-if="showCostForm" class="card border-0 bg-light p-3 mb-3 rounded-3">
          <h6 class="fw-semibold small mb-3">Nueva Regla de Costo</h6>
          <div class="row g-2 mb-3">
            <div class="col-12">
              <label class="form-label small">Nombre <span class="text-danger">*</span></label>
              <input v-model="costForm.name" type="text" class="form-control form-control-sm" placeholder="Ej: IVA 19%, Seguro basico...">
            </div>
            <div class="col-6">
              <label class="form-label small">Contexto</label>
              <select v-model="costForm.context" class="form-select form-select-sm">
                <option value="TAX">IVA / Impuesto</option>
                <option value="DISCOUNT">Descuento</option>
                <option value="DEPOSIT">Deposito</option>
                <option value="INSURANCE">Seguro</option>
                <option value="SURCHARGE">Recargo</option>
              </select>
            </div>
            <div class="col-6">
              <label class="form-label small">Tipo</label>
              <select v-model="costForm.cost_type" class="form-select form-select-sm">
                <option value="PERCENTAGE">Porcentaje (%)</option>
                <option value="FIXED">Valor Fijo ($)</option>
              </select>
            </div>
            <div class="col-6">
              <label class="form-label small">Valor <span class="text-danger">*</span></label>
              <div class="input-group input-group-sm">
                <span class="input-group-text">{{ costForm.cost_type === 'PERCENTAGE' ? '%' : '$' }}</span>
                <input v-model.number="costForm.value" type="number" step="0.0001" min="0" class="form-control" placeholder="19.0">
              </div>
            </div>
            <div class="col-6">
              <label class="form-label small">Descripcion</label>
              <input v-model="costForm.description" type="text" class="form-control form-control-sm" placeholder="Opcional">
            </div>
          </div>
          <div class="d-flex gap-2">
            <button type="button" class="btn btn-sm btn-primary" @click="saveCostRule" :disabled="costLoading">
              <span v-if="costLoading" class="spinner-border spinner-border-sm me-1"></span>
              Crear Regla
            </button>
            <button type="button" class="btn btn-sm btn-light border" @click="showCostForm = false">Cancelar</button>
          </div>
        </div>

        <!-- Lista reglas -->
        <div v-if="costRules.length" class="d-flex flex-column gap-2">
          <div
            v-for="rule in costRules"
            :key="rule.uuid"
            class="d-flex align-items-center gap-2 p-2 rounded-3 border"
            :class="rule.is_active ? 'bg-white' : 'bg-light opacity-60'"
          >
            <span
              class="badge rounded-pill flex-shrink-0"
              :class="contextBadge(rule.context)"
              style="font-size:.65rem;min-width:56px;text-align:center"
            >{{ contextLabel(rule.context) }}</span>

            <div class="flex-grow-1 min-w-0">
              <div class="fw-semibold small text-truncate">{{ rule.name }}</div>
              <div class="text-muted" style="font-size:.72rem">
                {{ rule.cost_type === 'PERCENTAGE' ? rule.value + '%' : formatCOP(rule.value) }}
              </div>
            </div>

            <div class="d-flex align-items-center gap-1 flex-shrink-0">
              <!-- Toggle activa -->
              <button
                type="button"
                class="btn btn-link p-0"
                :title="rule.is_active ? 'Desactivar' : 'Activar'"
                @click="toggleCostRule(rule)"
                :disabled="costLoading"
              >
                <i
                  :class="rule.is_active ? 'bi bi-toggle-on text-success fs-5' : 'bi bi-toggle-off text-muted fs-5'"
                ></i>
              </button>

              <!-- Reasignar a variante (por si se desvinculo) -->
              <button
                v-if="firstVariantUuid"
                type="button"
                class="btn btn-sm btn-outline-secondary py-0 px-2"
                style="font-size:.7rem"
                @click="assignCostRule(rule.uuid)"
                :disabled="costLoading"
                title="Asignar a variante principal"
              >
                <i class="bi bi-link-45deg"></i>
              </button>

              <!-- Eliminar -->
              <button
                type="button"
                class="btn btn-link p-0 text-danger"
                title="Eliminar regla"
                @click="deleteCostRule(rule)"
                :disabled="costLoading"
              >
                <i class="bi bi-trash fs-6"></i>
              </button>
            </div>
          </div>
        </div>

        <div v-else-if="!showCostForm" class="text-center py-4 text-muted">
          <i class="bi bi-tags fs-3 d-block mb-2 opacity-50"></i>
          <p class="small mb-2">No existen reglas configuradas para este equipo.</p>
          <button type="button" class="btn btn-sm btn-outline-primary" @click="showCostForm = true">
            <i class="bi bi-plus-lg me-1"></i> Crear primera regla
          </button>
        </div>
      </div>

      <!-- Footer acciones globales -->
      <div class="d-flex justify-content-between align-items-center mt-5 pt-3 border-top">
        <span class="text-muted" style="font-size:.73rem">
          <i class="bi bi-floppy me-1"></i>Los cambios se guardan por seccion
        </span>
        <button type="button" class="btn btn-sm btn-outline-secondary" @click="$emit('success')">
          <i class="bi bi-x-lg me-1"></i> Cerrar
        </button>
      </div>
    </template>

  </div>
</template>

<script setup>
import { ref, reactive, watch, computed, onMounted } from 'vue';
import { formatCOP as formatCOPBase } from '@/utils/money';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import CatalogListManager from '@/modules/renting/catalog/CatalogListManager.vue';
import SpecificationsManager from '@/modules/renting/catalog/SpecificationsManager.vue';
import GalleryManager from '@/modules/renting/catalog/GalleryManager.vue';
import DocumentsManager from '@/modules/renting/catalog/DocumentsManager.vue';
import VideosManager from '@/modules/renting/catalog/VideosManager.vue';
import SeoManager from '@/modules/renting/catalog/SeoManager.vue';

const props = defineProps({
  item: { type: Object, default: null },
  mode: { type: String, default: 'create' },
});
const emit = defineEmits(['success', 'cancel']);

const api   = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();

// Estado interno — permite transicion create→edit sin involucrar al padre
const localMode       = ref(props.mode);
const localItem       = ref(props.item);
const isNewlyCreated  = ref(false);
const activeTab       = ref('datos');
const loading         = ref(false);

const tabs = computed(() => [
  { key: 'datos',     label: 'Datos',     icon: 'bi-file-text' },
  { key: 'galeria',   label: 'Galeria',   icon: 'bi-images' },
  { key: 'incluye',   label: 'Incluye',   icon: 'bi-check2-circle' },
  { key: 'no-incluye', label: 'No incluye', icon: 'bi-x-circle' },
  { key: 'caracteristicas', label: 'Caracteristicas', icon: 'bi-stars' },
  { key: 'especificaciones', label: 'Especificaciones', icon: 'bi-card-list' },
  { key: 'requisitos', label: 'Requisitos', icon: 'bi-clipboard-check' },
  { key: 'servicios-incluidos', label: 'Serv. incluidos', icon: 'bi-hand-thumbs-up' },
  { key: 'servicios-opcionales', label: 'Serv. opcionales', icon: 'bi-plus-circle' },
  { key: 'documentacion', label: 'Documentacion', icon: 'bi-file-earmark-arrow-up' },
  { key: 'videos',    label: 'Videos',    icon: 'bi-camera-reels' },
  { key: 'faq',       label: 'FAQ',       icon: 'bi-question-circle' },
  { key: 'seo',       label: 'SEO',       icon: 'bi-search' },
  { key: 'marketing', label: 'Marketing', icon: 'bi-megaphone',
    badge: hasMarketing.value ? null : null, badgeClass: '' },
  { key: 'variantes', label: 'Variantes', icon: 'bi-layers',
    badge: variants.value.length || null, badgeClass: 'bg-primary-subtle text-primary' },
  { key: 'logistica', label: 'Logistica', icon: 'bi-truck',
    badge: hasLogistics.value ? null : null, badgeClass: '' },
  { key: 'costos',    label: 'Costos',    icon: 'bi-tags',
    badge: costRules.value.filter(r => r.is_active).length || null, badgeClass: 'bg-warning-subtle text-warning' },
]);

// ─── Catalogo ─────────────────────────────────────────────────────────────────
const categories = ref([]);
const brands     = ref([]);

// ─── Formulario basico ────────────────────────────────────────────────────────
const form = ref({ name: '', description: '', category: '', brand: '', is_active: true, is_featured: false });

// ─── Variantes ────────────────────────────────────────────────────────────────
const variants       = ref([]);
const vLoading       = ref(false);
const showVariantForm = ref(false);
const editingVariant  = ref(null);
const vForm = ref({ sku: '', rental_price_per_day: null, rental_price_per_hour: null, stock: 0, is_active: true });

const firstVariantUuid = computed(() => variants.value[0]?.uuid || null);

const marketingDiscountPreview = computed(() => {
  const { reference_price: ref_, promo_price: promo } = marketingForm;
  if (!ref_ || !promo || ref_ <= 0 || promo >= ref_) return null;
  return Math.round((1 - promo / ref_) * 100);
});
const marketingSavingsPreview = computed(() => {
  const purchase = marketingForm.purchase_price_reference;
  if (!purchase || purchase <= 0) return null;
  const effective = marketingForm.promo_price || marketingForm.reference_price
    || variants.value[0]?.rental_price_per_day;
  if (!effective || effective >= purchase) return null;
  return Math.round((1 - effective / purchase) * 100);
});

// ─── Logistica ────────────────────────────────────────────────────────────────
const logisticsLoading = ref(false);
const hasLogistics     = ref(false);
const logisticsForm    = reactive({
  delivery_cost: null, pickup_cost: null, installation_cost: null,
  calibration_cost: null, training_cost: null, startup_cost: null, notes: '',
});
const logisticsFields = [
  { key: 'delivery_cost',     label: 'Costo Entrega' },
  { key: 'pickup_cost',       label: 'Costo Recogida' },
  { key: 'installation_cost', label: 'Instalacion' },
  { key: 'calibration_cost',  label: 'Calibracion' },
  { key: 'training_cost',     label: 'Capacitacion' },
  { key: 'startup_cost',      label: 'Puesta en Marcha' },
];

// ─── Marketing ────────────────────────────────────────────────────────────────
const marketingLoading = ref(false);
const hasMarketing     = ref(false);
const marketingForm    = reactive({
  reference_price: null, promo_price: null, show_discount_percentage: true,
  tags: [], main_message: '', featured_benefit: '', trust_message: '',
  urgency_message: '', social_proof_message: '', purchase_price_reference: null,
  financial_message: '', use_cases: [], cta_label: '', promo_banner_message: '',
  quick_benefits: [],
});
const marketingTagOptions = [
  { value: 'OFERTA', label: 'Oferta' },
  { value: 'NUEVO', label: 'Nuevo' },
  { value: 'MAS_ALQUILADO', label: 'Mas alquilado' },
  { value: 'PREMIUM', label: 'Premium' },
  { value: 'RECOMENDADO', label: 'Recomendado' },
  { value: 'HOT', label: 'Hot' },
  { value: 'TOP_VENTAS', label: 'Top ventas' },
  { value: 'IDEAL_EVENTOS', label: 'Ideal para eventos' },
  { value: 'ULTIMAS_UNIDADES', label: 'Ultimas unidades' },
];
const newUseCase = ref('');
const newQuickBenefit = reactive({ icon: '', label: '' });

function toggleMarketingTag(value) {
  const idx = marketingForm.tags.indexOf(value);
  if (idx === -1) marketingForm.tags.push(value);
  else marketingForm.tags.splice(idx, 1);
}
function addUseCase() {
  const val = newUseCase.value.trim();
  if (val && !marketingForm.use_cases.includes(val)) marketingForm.use_cases.push(val);
  newUseCase.value = '';
}
function removeUseCase(idx) {
  marketingForm.use_cases.splice(idx, 1);
}
function addQuickBenefit() {
  if (!newQuickBenefit.label.trim()) return;
  marketingForm.quick_benefits.push({ icon: newQuickBenefit.icon.trim() || 'bi-check-circle', label: newQuickBenefit.label.trim() });
  newQuickBenefit.icon = '';
  newQuickBenefit.label = '';
}
function removeQuickBenefit(idx) {
  marketingForm.quick_benefits.splice(idx, 1);
}

// ─── Reglas de Costo ──────────────────────────────────────────────────────────
const costRules   = ref([]);
const costLoading = ref(false);
const showCostForm = ref(false);
const costForm = reactive({
  name: '', context: 'TAX', cost_type: 'PERCENTAGE', value: '', description: '',
});

// ─── Sincronizar desde props del padre ────────────────────────────────────────
watch(
  () => [props.mode, props.item],
  ([m, i]) => {
    localMode.value      = m;
    localItem.value      = i;
    isNewlyCreated.value = false;
    activeTab.value      = 'datos';
    showCostForm.value   = false;
    showVariantForm.value = false;
    editingVariant.value = null;
    if (i && m === 'edit') {
      syncBasicForm(i);
      loadEditData(i.uuid);
    } else {
      form.value = { name: '', description: '', category: '', brand: '', is_active: true, is_featured: false };
      resetEditState();
    }
  },
  { immediate: true },
);

// ─── Sincronizar precio de variante principal con marketing.reference_price ───
watch(
  () => variants.value[0]?.rental_price_per_day,
  (newPrice) => {
    if (newPrice != null && newPrice > 0) {
      // Auto-actualizar reference_price con el precio de la variante principal
      marketingForm.reference_price = parseFloat(newPrice);
    }
  },
);

function syncBasicForm(item) {
  form.value = {
    name:        item.name,
    description: item.description || '',
    category:    item.category_uuid || item.category?.uuid || '',
    brand:       item.brand_uuid    || item.brand?.uuid    || '',
    is_active:   item.is_active,
    is_featured: item.is_featured,
  };
}

function resetEditState() {
  variants.value = [];
  vForm.value    = { sku: '', rental_price_per_day: null, rental_price_per_hour: null, stock: 0, is_active: true };
  hasLogistics.value = false;
  Object.assign(logisticsForm, {
    delivery_cost: null, pickup_cost: null, installation_cost: null,
    calibration_cost: null, training_cost: null, startup_cost: null, notes: '',
  });
  costRules.value = [];
  hasMarketing.value = false;
  Object.assign(marketingForm, {
    reference_price: null, promo_price: null, show_discount_percentage: true,
    tags: [], main_message: '', featured_benefit: '', trust_message: '',
    urgency_message: '', social_proof_message: '', purchase_price_reference: null,
    financial_message: '', use_cases: [], cta_label: '', promo_banner_message: '',
    quick_benefits: [],
  });
}

async function loadEditData(uuid) {
  await Promise.all([fetchVariants(uuid), fetchLogistics(uuid), fetchCostRules(uuid), fetchMarketing(uuid)]);
}

async function loadCatalog() {
  try {
    const [catRes, brdRes] = await Promise.all([
      api.get('dashboard/renting-categories/'),
      api.get('dashboard/renting-brands/'),
    ]);
    categories.value = catRes.data.results || catRes.data;
    brands.value     = brdRes.data.results || brdRes.data;
  } catch {}
}

// ─── Crear equipo (create mode) ───────────────────────────────────────────────
async function submitCreate() {
  loading.value = true;
  try {
    const { data } = await api.post('dashboard/equipment/', {
      name:        form.value.name,
      description: form.value.description,
      category:    form.value.category,
      brand:       form.value.brand || null,
      is_active:   form.value.is_active,
      is_featured: form.value.is_featured,
    });
    // Transicion interna a edit sin cerrar el offcanvas
    localItem.value      = data;
    localMode.value      = 'edit';
    isNewlyCreated.value = true;
    syncBasicForm(data);
    resetEditState();
    await loadEditData(data.uuid);
    activeTab.value = 'variantes';
    toast.success('Equipo creado. Ahora agrega variantes y configura precios.');
  } catch (e) {
    handleError(e, 'Error al crear el equipo');
  } finally {
    loading.value = false;
  }
}

// ─── Actualizar equipo (edit mode → tab datos) ────────────────────────────────
async function submitUpdate() {
  loading.value = true;
  try {
    const { data } = await api.patch(`dashboard/equipment/${localItem.value.uuid}/`, {
      name:        form.value.name,
      description: form.value.description,
      category:    form.value.category,
      brand:       form.value.brand || null,
      is_active:   form.value.is_active,
      is_featured: form.value.is_featured,
    });
    localItem.value = { ...localItem.value, ...data };
    toast.success('Datos del equipo actualizados');
  } catch (e) {
    handleError(e, 'Error al actualizar');
  } finally {
    loading.value = false;
  }
}

// ─── Variantes ────────────────────────────────────────────────────────────────
async function fetchVariants(uuid) {
  try {
    const res = await api.get(`dashboard/equipment/${uuid}/variants/`);
    variants.value = res.data.results || res.data;
  } catch {}
}

function openVariantForm() {
  editingVariant.value = null;
  vForm.value = { sku: '', rental_price_per_day: null, rental_price_per_hour: null, stock: 0, is_active: true };
  showVariantForm.value = true;
}

function startEditVariant(v) {
  editingVariant.value  = v;
  vForm.value = {
    sku: v.sku,
    rental_price_per_day:  v.rental_price_per_day  ? parseFloat(v.rental_price_per_day)  : null,
    rental_price_per_hour: v.rental_price_per_hour ? parseFloat(v.rental_price_per_hour) : null,
    stock:     v.stock,
    is_active: v.is_active,
  };
  showVariantForm.value = true;
}

function cancelVariantForm() {
  showVariantForm.value = false;
  editingVariant.value  = null;
  vForm.value = { sku: '', rental_price_per_day: null, rental_price_per_hour: null, stock: 0, is_active: true };
}

async function saveVariant() {
  if (!vForm.value.sku?.trim()) return toast.error('SKU es requerido');
  if (!vForm.value.rental_price_per_day && !vForm.value.rental_price_per_hour) {
    return toast.error('Ingresa precio por dia o por hora');
  }
  vLoading.value = true;
  try {
    const payload = {
      equipment:            localItem.value.uuid,
      sku:                  vForm.value.sku,
      rental_price_per_day:  vForm.value.rental_price_per_day  || null,
      rental_price_per_hour: vForm.value.rental_price_per_hour || null,
      stock:     vForm.value.stock || 0,
      is_active: vForm.value.is_active,
    };
    if (editingVariant.value) {
      await api.patch(
        `dashboard/equipment/${localItem.value.uuid}/variants/${editingVariant.value.uuid}/`,
        payload,
      );
      toast.success('Variante actualizada');
    } else {
      await api.post(`dashboard/equipment/${localItem.value.uuid}/variants/create/`, payload);
      toast.success('Variante agregada');
    }
    cancelVariantForm();
    await fetchVariants(localItem.value.uuid);
  } catch (e) {
    handleError(e, 'Error al guardar variante');
  } finally {
    vLoading.value = false;
  }
}

async function deleteVariant(v) {
  vLoading.value = true;
  try {
    await api.delete(`dashboard/equipment/${localItem.value.uuid}/variants/${v.uuid}/delete/`);
    await fetchVariants(localItem.value.uuid);
    toast.success('Variante eliminada');
  } catch {
    toast.error('No se pudo eliminar la variante');
  } finally {
    vLoading.value = false;
  }
}

// ─── Logistica ────────────────────────────────────────────────────────────────
async function fetchLogistics(uuid) {
  try {
    const res = await api.get(`dashboard/equipment/${uuid}/logistics/`);
    if (res.data?.uuid) {
      hasLogistics.value = true;
      const d = res.data;
      Object.assign(logisticsForm, {
        delivery_cost:     d.delivery_cost     != null ? parseFloat(d.delivery_cost)     : null,
        pickup_cost:       d.pickup_cost       != null ? parseFloat(d.pickup_cost)       : null,
        installation_cost: d.installation_cost != null ? parseFloat(d.installation_cost) : null,
        calibration_cost:  d.calibration_cost  != null ? parseFloat(d.calibration_cost)  : null,
        training_cost:     d.training_cost     != null ? parseFloat(d.training_cost)     : null,
        startup_cost:      d.startup_cost      != null ? parseFloat(d.startup_cost)      : null,
        notes:             d.notes || '',
      });
    } else {
      hasLogistics.value = false;
    }
  } catch {
    hasLogistics.value = false;
  }
}

async function saveLogistics() {
  logisticsLoading.value = true;
  try {
    await api.put(`dashboard/equipment/${localItem.value.uuid}/logistics/`, { ...logisticsForm });
    hasLogistics.value = true;
    toast.success('Costos de logistica guardados');
  } catch (e) {
    handleError(e, 'Error al guardar logistica');
  } finally {
    logisticsLoading.value = false;
  }
}

async function deleteLogistics() {
  logisticsLoading.value = true;
  try {
    await api.delete(`dashboard/equipment/${localItem.value.uuid}/logistics/`);
    hasLogistics.value = false;
    Object.assign(logisticsForm, {
      delivery_cost: null, pickup_cost: null, installation_cost: null,
      calibration_cost: null, training_cost: null, startup_cost: null, notes: '',
    });
    toast.success('Configuracion de logistica eliminada');
  } catch {
    toast.error('Error al eliminar logistica');
  } finally {
    logisticsLoading.value = false;
  }
}

// ─── Marketing ────────────────────────────────────────────────────────────────
async function fetchMarketing(uuid) {
  try {
    const res = await api.get(`dashboard/equipment/${uuid}/marketing/`);
    if (res.data?.uuid) {
      hasMarketing.value = true;
      const d = res.data;
      Object.assign(marketingForm, {
        reference_price:          d.reference_price          != null ? parseFloat(d.reference_price)          : null,
        promo_price:              d.promo_price               != null ? parseFloat(d.promo_price)              : null,
        show_discount_percentage: d.show_discount_percentage ?? true,
        tags:                     d.tags || [],
        main_message:             d.main_message || '',
        featured_benefit:         d.featured_benefit || '',
        trust_message:            d.trust_message || '',
        urgency_message:          d.urgency_message || '',
        social_proof_message:     d.social_proof_message || '',
        purchase_price_reference: d.purchase_price_reference != null ? parseFloat(d.purchase_price_reference) : null,
        financial_message:        d.financial_message || '',
        use_cases:                d.use_cases || [],
        cta_label:                d.cta_label || '',
        promo_banner_message:     d.promo_banner_message || '',
        quick_benefits:           d.quick_benefits || [],
      });
    } else {
      hasMarketing.value = false;
    }
  } catch {
    hasMarketing.value = false;
  }
}

async function saveMarketing() {
  marketingLoading.value = true;
  try {
    await api.put(`dashboard/equipment/${localItem.value.uuid}/marketing/`, { ...marketingForm });
    hasMarketing.value = true;
    toast.success('Marketing guardado');
  } catch (e) {
    handleError(e, 'Error al guardar marketing');
  } finally {
    marketingLoading.value = false;
  }
}

async function deleteMarketing() {
  marketingLoading.value = true;
  try {
    await api.delete(`dashboard/equipment/${localItem.value.uuid}/marketing/`);
    hasMarketing.value = false;
    Object.assign(marketingForm, {
      reference_price: null, promo_price: null, show_discount_percentage: true,
      tags: [], main_message: '', featured_benefit: '', trust_message: '',
      urgency_message: '', social_proof_message: '', purchase_price_reference: null,
      financial_message: '', use_cases: [], cta_label: '', promo_banner_message: '',
      quick_benefits: [],
    });
    toast.success('Configuracion de marketing eliminada');
  } catch {
    toast.error('Error al eliminar marketing');
  } finally {
    marketingLoading.value = false;
  }
}

// ─── Reglas de Costo ──────────────────────────────────────────────────────────
// Regla arquitectonica: NO existen reglas globales/heredadas en Renting. Cada
// regla pertenece exclusivamente al Equipment donde se creo -- el listado
// SIEMPRE se filtra por equipment, nunca se pide el catalogo completo.
async function fetchCostRules(equipmentUuid) {
  try {
    const res = await api.get('dashboard/rental-cost-rules/', { params: { equipment: equipmentUuid } });
    costRules.value = res.data.results || res.data;
  } catch {}
}

async function saveCostRule() {
  if (!costForm.name?.trim())       return toast.error('Nombre requerido');
  if (!costForm.value && costForm.value !== 0) return toast.error('Valor requerido');
  costLoading.value = true;
  try {
    await api.post('dashboard/rental-cost-rules/', {
      ...costForm, value: String(costForm.value), equipment: localItem.value.uuid,
    });
    await fetchCostRules(localItem.value.uuid);
    showCostForm.value = false;
    Object.assign(costForm, {
      name: '', context: 'TAX', cost_type: 'PERCENTAGE', value: '', description: '',
    });
    toast.success('Regla de costo creada');
  } catch (e) {
    handleError(e, 'Error al crear regla');
  } finally {
    costLoading.value = false;
  }
}

async function toggleCostRule(rule) {
  costLoading.value = true;
  try {
    if (rule.is_active) {
      await api.post(`dashboard/rental-cost-rules/${rule.uuid}/deactivate/`);
    } else {
      await api.patch(`dashboard/rental-cost-rules/${rule.uuid}/update/`, { is_active: true });
    }
    await fetchCostRules();
  } catch {
    toast.error('Error al cambiar estado de la regla');
  } finally {
    costLoading.value = false;
  }
}

async function deleteCostRule(rule) {
  if (!confirm(`¿Eliminar la regla "${rule.name}"? Esta accion no se puede deshacer.`)) return;
  costLoading.value = true;
  try {
    await api.delete(`dashboard/rental-cost-rules/${rule.uuid}/`);
    await fetchCostRules();
    toast.success('Regla eliminada');
  } catch (e) {
    handleError(e, 'Error al eliminar la regla');
  } finally {
    costLoading.value = false;
  }
}

async function assignCostRule(ruleUuid) {
  if (!firstVariantUuid.value) return toast.error('Registra una variante primero');
  costLoading.value = true;
  try {
    await api.post(`dashboard/rental-cost-rules/${ruleUuid}/assign/`, {
      variant_uuid: firstVariantUuid.value,
    });
    toast.success('Regla asignada a la variante principal');
  } catch (e) {
    handleError(e, 'Ya asignada o error al asignar');
  } finally {
    costLoading.value = false;
  }
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function formatCOP(value) {
  if (value == null || value === '') return null;
  return formatCOPBase(value, { withSymbol: true });
}

function contextLabel(ctx) {
  const map = { TAX: 'IVA', DISCOUNT: 'Descuento', DEPOSIT: 'Deposito', INSURANCE: 'Seguro', SURCHARGE: 'Recargo' };
  return map[ctx] || ctx;
}

function contextBadge(ctx) {
  const map = {
    TAX:       'bg-warning-subtle text-warning border border-warning-subtle',
    DISCOUNT:  'bg-success-subtle text-success border border-success-subtle',
    DEPOSIT:   'bg-info-subtle text-info border border-info-subtle',
    INSURANCE: 'bg-primary-subtle text-primary border border-primary-subtle',
    SURCHARGE: 'bg-danger-subtle text-danger border border-danger-subtle',
  };
  return map[ctx] || 'bg-secondary-subtle text-secondary';
}

onMounted(loadCatalog);
</script>
