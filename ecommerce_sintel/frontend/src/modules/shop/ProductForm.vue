<template>
  <div>

    <!-- Banner informativo post-creacion -->
    <div v-if="isNewlyCreated" class="alert border-0 py-2 px-3 mb-3 d-flex align-items-center gap-2"
         style="background:#f0fdf4;border-left:3px solid #22c55e !important;border-radius:8px;font-size:.82rem">
      <i class="bi bi-check-circle-fill text-success flex-shrink-0"></i>
      <div>
        <strong>Producto creado.</strong>
        Ahora configura la variante por defecto: precio, descuento, logistica y costos adicionales.
      </div>
    </div>

    <!-- ================================================================
         TABS: create→ General|SEO   |   edit → General|SEO|Variantes|Costos
    ================================================================ -->
    <ul class="nav nav-tabs nav-fill mb-4" style="font-size:.82rem">
      <li class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'general' }" @click="tab = 'general'">
          <i class="bi bi-box me-1"></i>General
        </button>
      </li>
      <li class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'seo' }" @click="tab = 'seo'">
          <i class="bi bi-search me-1"></i>SEO
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'variants' }" @click="tab = 'variants'">
          <i class="bi bi-layers me-1"></i>Variantes
          <span v-if="variants.length" class="badge bg-primary-subtle text-primary ms-1">{{ variants.length }}</span>
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'costos' }" @click="tab = 'costos'">
          <i class="bi bi-tags me-1"></i>Costos
          <span v-if="activeCostRulesCount" class="badge bg-warning-subtle text-warning ms-1">{{ activeCostRulesCount }}</span>
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'imagenes' }" @click="tab = 'imagenes'">
          <i class="bi bi-images me-1"></i>Imagenes
          <span v-if="productImages.length" class="badge bg-secondary-subtle text-secondary ms-1">{{ productImages.length }}</span>
        </button>
      </li>
    </ul>

    <!-- ================================================================
         TAB: GENERAL
    ================================================================ -->
    <form v-show="tab === 'general'" @submit.prevent="submit">
      <div class="mb-3">
        <label class="form-label small fw-semibold">Nombre <span class="text-danger">*</span></label>
        <input v-model="form.name" type="text" class="form-control" required placeholder="Ej: Laptop XPS 15">
      </div>

      <div class="mb-3">
        <label class="form-label small fw-semibold">Resumen corto</label>
        <input v-model="form.short_description" type="text" class="form-control" maxlength="255"
               placeholder="Frase breve para tarjetas y resultados de busqueda">
        <div class="form-text d-flex justify-content-between">
          <span>Max 255 caracteres.</span>
          <span :class="(form.short_description || '').length > 220 ? 'text-warning' : 'text-muted'">
            {{ (form.short_description || '').length }}/255
          </span>
        </div>
      </div>

      <div class="row g-2 mb-3">
        <div class="col-8">
          <label class="form-label small fw-semibold">Categoria <span class="text-danger">*</span></label>
          <select v-model="form.category" class="form-select" required>
            <option value="" disabled>Seleccionar categoria...</option>
            <option v-for="cat in categories" :key="cat.uuid" :value="cat.uuid">{{ cat.name }}</option>
          </select>
        </div>
        <div class="col-4">
          <label class="form-label small fw-semibold">Condicion</label>
          <select v-model="form.condition" class="form-select">
            <option value="new">Nuevo</option>
            <option value="used">Usado</option>
            <option value="refurbished">Reacondicionado</option>
          </select>
        </div>
      </div>

      <div class="mb-3">
        <label class="form-label small fw-semibold">Marca</label>
        <select v-model="form.brand" class="form-select">
          <option :value="null">Sin marca</option>
          <option v-for="b in brands" :key="b.uuid" :value="b.uuid">{{ b.name }}</option>
        </select>
      </div>

      <div class="mb-3">
        <label class="form-label small fw-semibold">Descripcion</label>
        <textarea v-model="form.description" class="form-control" rows="3"
                  placeholder="Descripcion completa del producto..."></textarea>
      </div>

      <div class="mb-3">
        <label class="form-label small fw-semibold">URL de video</label>
        <input v-model="form.video_url" type="url" class="form-control"
               placeholder="https://www.youtube.com/watch?v=...">
        <div class="form-text">YouTube o Vimeo.</div>
      </div>

      <!-- Inventario inicial: solo visible en CREATE -->
      <div v-if="localMode === 'create'" class="card border-0 p-3 mb-3 rounded-3" style="background:#f8fafc">
        <p class="small fw-semibold mb-2">
          <i class="bi bi-box-seam me-1 text-success"></i>
          Inventario de la variante principal
        </p>
        <div class="row g-2">
          <div class="col-4">
            <label class="form-label smaller mb-1 fw-semibold">Stock disponible</label>
            <input v-model.number="form.stock" type="number" min="0" class="form-control form-control-sm"
                   placeholder="0">
          </div>
          <div class="col-4">
            <label class="form-label smaller mb-1 fw-semibold">Precio base <span class="text-danger">*</span></label>
            <div class="input-group input-group-sm">
              <span class="input-group-text">$</span>
              <input v-model.number="form.price" type="number" step="0.01" min="0.01" class="form-control"
                     required placeholder="0.00">
            </div>
          </div>
          <div class="col-4">
            <label class="form-label smaller mb-1 fw-semibold">Precio descuento</label>
            <div class="input-group input-group-sm">
              <span class="input-group-text">$</span>
              <input v-model.number="form.discounted_price" type="number" step="0.01" min="0"
                     class="form-control" placeholder="Opcional">
            </div>
          </div>
        </div>
        <div class="form-text mt-1">
          <i class="bi bi-info-circle me-1"></i>
          El SKU se genera automaticamente y se mostrara despues de guardar.
        </div>
      </div>

      <div class="row mb-3">
        <div class="col-6">
          <div class="form-check form-switch">
            <input v-model="form.is_active" class="form-check-input" type="checkbox" id="prodActive">
            <label class="form-check-label small" for="prodActive">Activo</label>
          </div>
        </div>
        <div class="col-6">
          <div class="form-check form-switch">
            <input v-model="form.is_featured" class="form-check-input" type="checkbox" id="prodFeatured">
            <label class="form-check-label small" for="prodFeatured">Destacado</label>
          </div>
        </div>
      </div>

      <!-- Footer CREATE: solo boton crear -->
      <div v-if="localMode === 'create'" class="d-flex gap-2 mt-3">
        <button type="submit" class="btn btn-primary flex-grow-1" :disabled="loading">
          <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
          <i v-else class="bi bi-plus-lg me-1"></i>
          Crear Producto
        </button>
        <button type="button" class="btn btn-light border" @click="$emit('cancel')" :disabled="loading">
          Cancelar
        </button>
      </div>

      <!-- Footer EDIT: guardar + cerrar -->
      <div v-else class="d-flex gap-2 mt-3">
        <button type="submit" class="btn btn-primary flex-grow-1" :disabled="loading">
          <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
          Guardar General
        </button>
        <button type="button" class="btn btn-light border" @click="closeForm">Cerrar</button>
      </div>
    </form>

    <!-- ================================================================
         TAB: SEO
    ================================================================ -->
    <div v-show="tab === 'seo'">
      <div class="rounded-3 px-3 py-2 mb-3 small" style="background:#eff6ff;border-left:3px solid #3b82f6">
        <i class="bi bi-info-circle me-1"></i>
        Mejoran el posicionamiento en buscadores (Google, Bing).
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Titulo SEO</label>
        <input v-model="form.meta_title" type="text" class="form-control" maxlength="70"
               placeholder="Titulo optimizado para buscadores">
        <div class="form-text d-flex justify-content-between">
          <span>50–70 caracteres recomendado.</span>
          <span :class="form.meta_title.length > 60 ? 'text-warning' : 'text-muted'">{{ form.meta_title.length }}/70</span>
        </div>
      </div>
      <div class="mb-3">
        <label class="form-label small fw-semibold">Meta Descripcion</label>
        <textarea v-model="form.meta_description" class="form-control" rows="3" maxlength="160"
                  placeholder="Descripcion breve para buscadores..."></textarea>
        <div class="form-text d-flex justify-content-between">
          <span>120–160 caracteres recomendado.</span>
          <span :class="form.meta_description.length > 145 ? 'text-warning' : 'text-muted'">{{ form.meta_description.length }}/160</span>
        </div>
      </div>
      <div v-if="localMode === 'edit'" class="d-flex gap-2">
        <button type="button" class="btn btn-primary flex-grow-1" @click="submit" :disabled="loading">
          <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
          Guardar SEO
        </button>
        <button type="button" class="btn btn-light border" @click="closeForm">Cerrar</button>
      </div>
    </div>

    <!-- ================================================================
         TAB: VARIANTES (solo localMode === 'edit')
    ================================================================ -->
    <div v-show="tab === 'variants' && localMode === 'edit'">

      <div class="d-flex justify-content-between align-items-center mb-3">
        <p class="text-muted small mb-0">Precio, descuento, stock y dimensiones logisticas por variante.</p>
        <button type="button" class="btn btn-sm btn-primary" @click="openNewVariantForm"
                :disabled="showVariantForm && !editingVariant">
          <i class="bi bi-plus-lg me-1"></i>Nueva Variante
        </button>
      </div>

      <!-- ── FORMULARIO NUEVA VARIANTE ── -->
      <div v-if="showVariantForm && !editingVariant" class="card border-0 bg-light p-3 mb-3 rounded-3">
        <h6 class="fw-semibold small mb-3">Nueva Variante</h6>

        <!-- Stock -->
        <div class="row g-2 mb-2">
          <div class="col-4">
            <label class="form-label smaller mb-1 fw-semibold">Stock</label>
            <input v-model.number="newVariant.stock" type="number" min="0" class="form-control form-control-sm"
                   placeholder="0">
          </div>
          <div class="col-8 d-flex align-items-end pb-1">
            <div class="form-check form-switch ms-1">
              <input v-model="newVariant.is_default" type="checkbox" class="form-check-input" id="nvDefault">
              <label class="form-check-label smaller" for="nvDefault">Variante por defecto</label>
            </div>
          </div>
        </div>

        <!-- Precio base + Precio oferta -->
        <div class="row g-2 mb-2">
          <div class="col-6">
            <label class="form-label smaller mb-1 fw-semibold">Precio base <span class="text-danger">*</span></label>
            <div class="input-group input-group-sm">
              <span class="input-group-text">$</span>
              <input v-model.number="newVariant.price" type="number" step="0.01" min="0.01" class="form-control"
                     placeholder="0.00">
            </div>
          </div>
          <div class="col-6">
            <label class="form-label smaller mb-1 fw-semibold">Precio con descuento</label>
            <div class="input-group input-group-sm">
              <span class="input-group-text">$</span>
              <input v-model.number="newVariant.discounted_price" type="number" step="0.01" min="0"
                     class="form-control" placeholder="Opcional">
            </div>
          </div>
        </div>

        <!-- Periodo de descuento temporal -->
        <div class="row g-2 mb-2">
          <div class="col-6">
            <label class="form-label smaller mb-1">Descuento desde</label>
            <input v-model="newVariant.discount_start_date" type="datetime-local"
                   class="form-control form-control-sm">
          </div>
          <div class="col-6">
            <label class="form-label smaller mb-1">Descuento hasta</label>
            <input v-model="newVariant.discount_end_date" type="datetime-local"
                   class="form-control form-control-sm">
          </div>
        </div>

        <!-- Atributos dinamicos -->
        <div class="mb-2">
          <div class="d-flex justify-content-between align-items-center mb-1">
            <label class="form-label smaller mb-0 fw-semibold">Atributos</label>
            <button type="button" class="btn btn-xs btn-outline-secondary" @click="addAttrRow(newVariant)">
              <i class="bi bi-plus"></i> Atributo
            </button>
          </div>
          <div v-for="(row, i) in newVariant.attrRows" :key="i" class="row g-1 mb-1">
            <div class="col-5">
              <input v-model="row.key" type="text" class="form-control form-control-sm"
                     placeholder="Ej: Color">
            </div>
            <div class="col-5">
              <input v-model="row.value" type="text" class="form-control form-control-sm"
                     placeholder="Ej: Rojo">
            </div>
            <div class="col-2">
              <button type="button" class="btn btn-xs btn-light border w-100"
                      @click="removeAttrRow(newVariant, i)">
                <i class="bi bi-x text-danger"></i>
              </button>
            </div>
          </div>
        </div>

        <!-- Logistica / Transporte -->
        <p class="smaller fw-semibold text-muted mb-1 mt-2">
          <i class="bi bi-truck me-1"></i>Logistica / Transporte
        </p>
        <div class="row g-2 mb-2">
          <div class="col-3">
            <label class="form-label smaller mb-1">Peso (kg)</label>
            <input v-model.number="newVariant.weight" type="number" step="0.01" min="0"
                   class="form-control form-control-sm" placeholder="0.00">
          </div>
          <div class="col-3">
            <label class="form-label smaller mb-1">Largo (cm)</label>
            <input v-model.number="newVariant.length" type="number" step="0.01" min="0"
                   class="form-control form-control-sm" placeholder="0.00">
          </div>
          <div class="col-3">
            <label class="form-label smaller mb-1">Ancho (cm)</label>
            <input v-model.number="newVariant.width" type="number" step="0.01" min="0"
                   class="form-control form-control-sm" placeholder="0.00">
          </div>
          <div class="col-3">
            <label class="form-label smaller mb-1">Alto (cm)</label>
            <input v-model.number="newVariant.height" type="number" step="0.01" min="0"
                   class="form-control form-control-sm" placeholder="0.00">
          </div>
        </div>

        <!-- Impuestos del sistema -->
        <div v-if="taxes.length" class="mb-3 p-2 rounded-2 border" style="background:#f8fafc">
          <p class="smaller fw-semibold text-muted mb-1">
            <i class="bi bi-percent me-1 text-primary"></i>Impuestos activos del sistema
            <span class="fw-normal">(se aplican automaticamente al precio efectivo)</span>
          </p>
          <div class="d-flex flex-wrap gap-1">
            <span v-for="tax in taxes" :key="tax.uuid"
                  class="badge bg-primary-subtle text-primary border border-primary-subtle"
                  style="font-size:.7rem">
              {{ tax.name }} &middot;
              {{ tax.tax_type === 'percentage' ? tax.value + '%' : '$' + formatNum(tax.value) }}
            </span>
          </div>
          <div class="mt-1" style="font-size:.68rem;color:#6b7280">
            Para impuestos y descuentos personalizados por variante, usa la pestana <strong>Costos</strong>.
          </div>
        </div>

        <div class="d-flex gap-2">
          <button type="button" class="btn btn-sm btn-primary" @click="addVariant" :disabled="variantLoading">
            <span v-if="variantLoading" class="spinner-border spinner-border-sm me-1"></span>
            Guardar Variante
          </button>
          <button type="button" class="btn btn-sm btn-light border" @click="cancelVariantForm">Cancelar</button>
        </div>
      </div>

      <!-- ── LISTA DE VARIANTES ── -->
      <div v-if="variantsLoading" class="text-center py-4">
        <div class="spinner-border spinner-border-sm text-primary"></div>
      </div>

      <div v-else-if="!variants.length && !showVariantForm" class="text-center py-4 text-muted">
        <i class="bi bi-layers fs-3 d-block mb-2 opacity-50"></i>
        <p class="small mb-2">Sin variantes. Agrega la primera con el boton.</p>
      </div>

      <div v-else-if="variants.length" class="d-flex flex-column gap-2">
        <div v-for="v in variants" :key="v.uuid" class="border rounded-3 overflow-hidden">

          <!-- MODO EDICION INLINE -->
          <div v-if="editingVariant?.uuid === v.uuid" class="p-3 bg-light">
            <h6 class="fw-semibold small mb-3">Editando: <code>{{ v.sku }}</code></h6>

            <div class="row g-2 mb-2">
              <div class="col-4">
                <label class="form-label smaller mb-1 fw-semibold">Stock</label>
                <input v-model.number="editingVariant.stock" type="number" min="0"
                       class="form-control form-control-sm">
              </div>
              <div class="col-8 d-flex align-items-end pb-1">
                <div class="form-check form-switch ms-1">
                  <input v-model="editingVariant.is_default" type="checkbox"
                         class="form-check-input" :id="'edf-' + v.uuid">
                  <label class="form-check-label smaller" :for="'edf-' + v.uuid">Default</label>
                </div>
              </div>
            </div>

            <div class="row g-2 mb-2">
              <div class="col-6">
                <label class="form-label smaller mb-1 fw-semibold">Precio base <span class="text-danger">*</span></label>
                <div class="input-group input-group-sm">
                  <span class="input-group-text">$</span>
                  <input v-model.number="editingVariant.price" type="number" step="0.01" min="0.01"
                         class="form-control">
                </div>
              </div>
              <div class="col-6">
                <label class="form-label smaller mb-1 fw-semibold">Precio con descuento</label>
                <div class="input-group input-group-sm">
                  <span class="input-group-text">$</span>
                  <input v-model.number="editingVariant.discounted_price" type="number" step="0.01"
                         min="0" class="form-control" placeholder="Opcional">
                </div>
              </div>
            </div>

            <div class="row g-2 mb-2">
              <div class="col-6">
                <label class="form-label smaller mb-0">Descuento desde</label>
                <input v-model="editingVariant.discount_start_date" type="datetime-local"
                       class="form-control form-control-sm">
              </div>
              <div class="col-6">
                <label class="form-label smaller mb-0">Descuento hasta</label>
                <input v-model="editingVariant.discount_end_date" type="datetime-local"
                       class="form-control form-control-sm">
              </div>
            </div>

            <!-- Atributos edicion -->
            <div class="mb-2">
              <div class="d-flex justify-content-between align-items-center mb-1">
                <label class="form-label smaller mb-0 fw-semibold">Atributos</label>
                <button type="button" class="btn btn-xs btn-outline-secondary"
                        @click="addAttrRow(editingVariant)">
                  <i class="bi bi-plus"></i>
                </button>
              </div>
              <div v-for="(row, i) in editingVariant.attrRows" :key="i" class="row g-1 mb-1">
                <div class="col-5">
                  <input v-model="row.key" type="text" class="form-control form-control-sm"
                         placeholder="Nombre">
                </div>
                <div class="col-5">
                  <input v-model="row.value" type="text" class="form-control form-control-sm"
                         placeholder="Valor">
                </div>
                <div class="col-2">
                  <button type="button" class="btn btn-xs btn-light border w-100"
                          @click="removeAttrRow(editingVariant, i)">
                    <i class="bi bi-x text-danger"></i>
                  </button>
                </div>
              </div>
            </div>

            <!-- Logistica edicion -->
            <p class="smaller fw-semibold text-muted mb-1 mt-2">
              <i class="bi bi-truck me-1"></i>Logistica / Transporte
            </p>
            <div class="row g-1 mb-2">
              <div class="col-3">
                <label class="form-label smaller mb-0">Peso (kg)</label>
                <input v-model.number="editingVariant.weight" type="number" step="0.01" min="0"
                       class="form-control form-control-sm">
              </div>
              <div class="col-3">
                <label class="form-label smaller mb-0">Largo (cm)</label>
                <input v-model.number="editingVariant.length" type="number" step="0.01" min="0"
                       class="form-control form-control-sm">
              </div>
              <div class="col-3">
                <label class="form-label smaller mb-0">Ancho (cm)</label>
                <input v-model.number="editingVariant.width" type="number" step="0.01" min="0"
                       class="form-control form-control-sm">
              </div>
              <div class="col-3">
                <label class="form-label smaller mb-0">Alto (cm)</label>
                <input v-model.number="editingVariant.height" type="number" step="0.01" min="0"
                       class="form-control form-control-sm">
              </div>
            </div>

            <!-- Impuestos activos -->
            <div v-if="taxes.length" class="mb-3 p-2 rounded-2 border" style="background:#f8fafc">
              <p class="smaller fw-semibold text-muted mb-1">
                <i class="bi bi-percent me-1 text-primary"></i>Impuestos del sistema
              </p>
              <div class="d-flex flex-wrap gap-1">
                <span v-for="tax in taxes" :key="tax.uuid"
                      class="badge bg-primary-subtle text-primary border border-primary-subtle"
                      style="font-size:.68rem">
                  {{ tax.name }} &middot;
                  {{ tax.tax_type === 'percentage' ? tax.value + '%' : '$' + formatNum(tax.value) }}
                </span>
              </div>
            </div>

            <div class="d-flex gap-2">
              <button type="button" class="btn btn-sm btn-primary" @click="saveVariant"
                      :disabled="variantLoading">
                <span v-if="variantLoading" class="spinner-border spinner-border-sm me-1"></span>
                Guardar Variante
              </button>
              <button type="button" class="btn btn-sm btn-light border"
                      @click="editingVariant = null; showVariantForm = false">
                Cancelar
              </button>
            </div>
          </div>

          <!-- MODO VISTA -->
          <div v-else class="p-3">
            <div class="d-flex align-items-start justify-content-between gap-2">
              <div class="flex-grow-1">

                <!-- Encabezado -->
                <div class="d-flex align-items-center gap-2 flex-wrap">
                  <code class="fw-bold text-dark">{{ v.sku }}</code>
                  <span v-if="v.is_default"
                        class="badge bg-primary-subtle text-primary border smaller">Default</span>
                  <span class="badge rounded-pill smaller"
                        :class="v.stock > 0
                          ? 'bg-success-subtle text-success'
                          : 'bg-danger-subtle text-danger'">
                    {{ v.stock }} un.
                  </span>
                  <span v-if="isDiscountActive(v)"
                        class="badge bg-warning-subtle text-warning border smaller">
                    <i class="bi bi-clock me-1"></i>Descuento activo
                  </span>
                </div>

                <!-- Precios -->
                <div class="mt-1 d-flex align-items-center gap-2">
                  <span class="fw-bold text-dark">${{ formatNum(v.price) }}</span>
                  <span v-if="v.discounted_price" class="text-success fw-semibold smaller">
                    <i class="bi bi-arrow-down-short"></i>${{ formatNum(v.discounted_price) }}
                    <span class="text-muted fw-normal">oferta</span>
                  </span>
                </div>

                <!-- Desglose financiero price_info -->
                <div v-if="v.price_info"
                     class="mt-2 p-2 rounded-2 border" style="background:#f8fafc;font-size:.72rem">
                  <div class="d-flex justify-content-between text-muted mb-1">
                    <span>Precio base</span>
                    <span class="fw-semibold text-dark">${{ formatNum(v.price_info.base_price) }}</span>
                  </div>
                  <div v-if="v.price_info.has_discount"
                       class="d-flex justify-content-between text-success mb-1">
                    <span><i class="bi bi-tag me-1"></i>Precio oferta activo</span>
                    <span class="fw-semibold">${{ formatNum(v.price_info.discounted_price) }}</span>
                  </div>
                  <template v-if="v.price_info.applied_taxes?.length">
                    <div v-for="tax in v.price_info.applied_taxes" :key="tax.name"
                         class="d-flex justify-content-between text-muted">
                      <span>
                        <i class="bi bi-percent me-1"></i>{{ tax.name }}
                        ({{ tax.rate }}{{ tax.tax_type === 'percentage' ? '%' : '$' }})
                      </span>
                      <span>+${{ formatNum(tax.amount) }}</span>
                    </div>
                  </template>
                  <div class="d-flex justify-content-between border-top mt-1 pt-1 fw-bold text-dark">
                    <span>Precio final con imp.</span>
                    <span class="text-primary">${{ formatNum(v.price_info.final_price_net) }}</span>
                  </div>
                </div>

                <!-- Dimensiones logisticas -->
                <div v-if="v.weight || v.length || v.width || v.height"
                     class="mt-1 text-muted" style="font-size:.72rem">
                  <i class="bi bi-truck me-1"></i>
                  <template v-if="v.weight">{{ v.weight }} kg</template>
                  <template v-if="v.length">
                    &nbsp;&middot;&nbsp;{{ v.length }}x{{ v.width }}x{{ v.height }} cm
                  </template>
                </div>

                <!-- Atributos -->
                <div v-if="Object.keys(v.attributes || {}).length"
                     class="mt-1 d-flex flex-wrap gap-1">
                  <span v-for="(val, key) in v.attributes" :key="key"
                        class="badge bg-secondary-subtle text-secondary border smaller">
                    {{ key }}: {{ val }}
                  </span>
                </div>

              </div>

              <!-- Acciones -->
              <div class="btn-group btn-group-sm flex-shrink-0">
                <button type="button" class="btn btn-light border-end"
                        @click="startEditVariant(v)" title="Editar">
                  <i class="bi bi-pencil text-primary" style="font-size:.75rem"></i>
                </button>
                <button type="button" class="btn btn-light"
                        @click="deleteVariant(v)" :disabled="variantLoading" title="Eliminar">
                  <i class="bi bi-trash text-danger" style="font-size:.75rem"></i>
                </button>
              </div>
            </div>
          </div>

        </div>
      </div>

      <!-- Footer Variantes -->
      <div class="d-flex justify-content-end mt-4 pt-2 border-top">
        <button type="button" class="btn btn-light border" @click="closeForm">Cerrar</button>
      </div>
    </div>

    <!-- ================================================================
         TAB: COSTOS (solo localMode === 'edit') — ProductCostRule
    ================================================================ -->
    <div v-show="tab === 'costos' && localMode === 'edit'">

      <!-- Info variante principal -->
      <div v-if="firstVariantUuid"
           class="d-flex align-items-center gap-2 mb-3 p-2 rounded-2 border"
           style="background:#f8fafc">
        <i class="bi bi-info-circle text-primary small"></i>
        <span class="small text-muted">
          Asignaciones aplican a la variante principal:
          <code class="text-dark">{{ variants[0]?.sku }}</code>
        </span>
      </div>
      <div v-else class="alert alert-warning border-0 py-2 px-3 mb-3 small">
        <i class="bi bi-exclamation-triangle me-2"></i>
        Crea al menos una variante antes de asignar reglas de costo.
      </div>

      <!-- Header -->
      <div class="d-flex align-items-center justify-content-between mb-3">
        <span class="small text-muted fw-semibold">{{ costRules.length }} regla(s) disponibles</span>
        <button type="button" class="btn btn-sm btn-primary" @click="showCostForm = !showCostForm">
          <i class="bi bi-plus-lg me-1"></i>Nueva Regla
        </button>
      </div>

      <!-- Formulario crear regla de costo -->
      <div v-if="showCostForm" class="card border-0 bg-light p-3 mb-3 rounded-3">
        <h6 class="fw-semibold small mb-3">Nueva Regla de Costo</h6>
        <div class="row g-2 mb-3">
          <div class="col-12">
            <label class="form-label small">Nombre <span class="text-danger">*</span></label>
            <input v-model="costForm.name" type="text" class="form-control form-control-sm"
                   placeholder="Ej: Flete nacional, IVA 19%, Descuento comercial">
          </div>
          <div class="col-6">
            <label class="form-label small">Tipo de costo</label>
            <select v-model="costForm.context" class="form-select form-select-sm">
              <option value="TAX">Impuesto / Cargo</option>
              <option value="DISCOUNT">Descuento</option>
            </select>
          </div>
          <div class="col-6">
            <label class="form-label small">Calculo</label>
            <select v-model="costForm.cost_type" class="form-select form-select-sm">
              <option value="PERCENTAGE">Porcentaje (%)</option>
              <option value="FIXED">Valor fijo ($)</option>
            </select>
          </div>
          <div class="col-6">
            <label class="form-label small">Valor <span class="text-danger">*</span></label>
            <div class="input-group input-group-sm">
              <span class="input-group-text">
                {{ costForm.cost_type === 'PERCENTAGE' ? '%' : '$' }}
              </span>
              <input v-model.number="costForm.value" type="number" step="0.0001" min="0"
                     class="form-control" placeholder="19.0">
            </div>
          </div>
          <div class="col-6">
            <label class="form-label small">Descripcion</label>
            <input v-model="costForm.description" type="text" class="form-control form-control-sm"
                   placeholder="Opcional">
          </div>
          <div class="col-12">
            <div class="form-check form-switch">
              <input class="form-check-input" type="checkbox"
                     v-model="costForm.applies_globally" id="shopCostGlobal">
              <label class="form-check-label small" for="shopCostGlobal">
                Aplicar globalmente a todos los productos
              </label>
            </div>
          </div>
        </div>
        <div class="d-flex gap-2">
          <button type="button" class="btn btn-sm btn-primary"
                  @click="saveCostRule" :disabled="costLoading">
            <span v-if="costLoading" class="spinner-border spinner-border-sm me-1"></span>
            Crear Regla
          </button>
          <button type="button" class="btn btn-sm btn-light border"
                  @click="showCostForm = false">Cancelar</button>
        </div>
      </div>

      <!-- Lista reglas de costo -->
      <div v-if="costRules.length" class="d-flex flex-column gap-2">
        <div v-for="rule in costRules" :key="rule.uuid"
             class="d-flex align-items-center gap-2 p-2 rounded-3 border"
             :class="rule.is_active ? 'bg-white' : 'bg-light opacity-60'">

          <span class="badge rounded-pill flex-shrink-0"
                :class="rule.context === 'TAX'
                  ? 'bg-warning-subtle text-warning border border-warning-subtle'
                  : 'bg-success-subtle text-success border border-success-subtle'"
                style="font-size:.65rem;min-width:60px;text-align:center">
            {{ rule.context === 'TAX' ? 'Impuesto' : 'Descuento' }}
          </span>

          <div class="flex-grow-1 min-w-0">
            <div class="fw-semibold small text-truncate">{{ rule.name }}</div>
            <div class="text-muted" style="font-size:.72rem">
              {{ rule.cost_type === 'PERCENTAGE' ? rule.value + '%' : '$' + formatNum(rule.value) }}
              <span v-if="rule.description" class="ms-1 opacity-75">· {{ rule.description }}</span>
              <span v-if="rule.applies_globally" class="ms-1 text-success">· Global</span>
            </div>
          </div>

          <div class="d-flex align-items-center gap-1 flex-shrink-0">
            <button type="button" class="btn btn-link p-0"
                    @click="toggleCostRule(rule)" :disabled="costLoading"
                    :title="rule.is_active ? 'Desactivar' : 'Activar'">
              <i :class="rule.is_active
                ? 'bi bi-toggle-on text-success fs-5'
                : 'bi bi-toggle-off text-muted fs-5'"></i>
            </button>
            <button v-if="firstVariantUuid && !rule.applies_globally"
                    type="button"
                    class="btn btn-sm btn-outline-secondary py-0 px-2"
                    style="font-size:.7rem"
                    @click="assignCostRule(rule.uuid)"
                    :disabled="costLoading"
                    title="Asignar a variante principal">
              <i class="bi bi-link-45deg"></i>
            </button>
            <span v-else-if="rule.applies_globally" class="text-success" style="font-size:.75rem">
              <i class="bi bi-check-circle-fill"></i>
            </span>
          </div>
        </div>
      </div>

      <div v-else-if="!showCostForm" class="text-center py-4 text-muted">
        <i class="bi bi-tags fs-3 d-block mb-2 opacity-50"></i>
        <p class="small mb-2">Sin reglas de costo. Crea la primera.</p>
        <button type="button" class="btn btn-sm btn-outline-primary" @click="showCostForm = true">
          <i class="bi bi-plus-lg me-1"></i> Crear primera regla
        </button>
      </div>

      <!-- Footer Costos -->
      <div class="d-flex justify-content-end mt-4 pt-2 border-top">
        <button type="button" class="btn btn-light border" @click="closeForm">Cerrar</button>
      </div>
    </div>

    <!-- ================================================================
         TAB: IMAGENES (solo localMode === 'edit')
    ================================================================ -->
    <div v-show="tab === 'imagenes' && localMode === 'edit'">

      <!-- Formulario subir imagen -->
      <div class="card border-0 bg-light p-3 mb-3 rounded-3">
        <h6 class="fw-semibold small mb-3">Subir imagen</h6>
        <div class="mb-2">
          <label class="form-label smaller mb-1 fw-semibold">Archivo <span class="text-danger">*</span></label>
          <input
            ref="fileInputRef"
            type="file"
            accept="image/*"
            class="form-control form-control-sm"
            @change="uploadFile = $event.target.files[0]"
          >
        </div>
        <div class="mb-2">
          <label class="form-label smaller mb-1">Texto alternativo (SEO)</label>
          <input v-model="uploadAltText" type="text" class="form-control form-control-sm"
                 placeholder="Descripcion de la imagen">
        </div>
        <button type="button" class="btn btn-sm btn-primary"
                @click="uploadImage" :disabled="uploading || !uploadFile">
          <span v-if="uploading" class="spinner-border spinner-border-sm me-1"></span>
          <i v-else class="bi bi-cloud-upload me-1"></i>
          Subir imagen
        </button>
      </div>

      <!-- Loading -->
      <div v-if="imagesLoading" class="text-center py-4">
        <div class="spinner-border spinner-border-sm text-primary"></div>
      </div>

      <!-- Sin imagenes -->
      <div v-else-if="!productImages.length" class="text-center py-4 text-muted">
        <i class="bi bi-images fs-3 d-block mb-2 opacity-50"></i>
        <p class="small mb-0">Sin imagenes. Sube la primera.</p>
      </div>

      <!-- Lista de imagenes -->
      <div v-else class="d-flex flex-column gap-2">
        <div v-for="img in productImages" :key="img.uuid"
             class="d-flex align-items-center gap-2 p-2 rounded-3 border"
             :class="img.is_primary ? 'border-primary bg-primary-subtle' : 'bg-white'">

          <img :src="img.image" :alt="img.alt_text || 'imagen'"
               class="rounded-2 object-fit-cover flex-shrink-0"
               style="width:56px;height:56px;border:1px solid #e5e7eb">

          <div class="flex-grow-1 min-w-0">
            <div class="d-flex align-items-center gap-1 flex-wrap">
              <span v-if="img.is_primary"
                    class="badge bg-primary text-white" style="font-size:.65rem">
                <i class="bi bi-star-fill me-1"></i>Principal
              </span>
              <span class="text-muted small text-truncate">{{ img.alt_text || '(sin descripcion)' }}</span>
            </div>
          </div>

          <div class="d-flex gap-1 flex-shrink-0">
            <button v-if="!img.is_primary"
                    type="button"
                    class="btn btn-sm btn-outline-primary py-0 px-2"
                    style="font-size:.75rem"
                    @click="setPrimaryImage(img)"
                    :disabled="imagesLoading"
                    title="Establecer como principal">
              <i class="bi bi-star"></i>
            </button>
            <button type="button"
                    class="btn btn-sm btn-outline-danger py-0 px-2"
                    style="font-size:.75rem"
                    @click="deleteImage(img)"
                    :disabled="imagesLoading"
                    title="Eliminar imagen">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </div>
      </div>

      <!-- Footer Imagenes -->
      <div class="d-flex justify-content-end mt-4 pt-2 border-top">
        <button type="button" class="btn btn-light border" @click="closeForm">Cerrar</button>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, watch, computed, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';

const props = defineProps({
  item: { type: Object, default: null },
  mode: { type: String, default: 'create' },
});
const emit = defineEmits(['success', 'cancel', 'itemSaved']);

const api   = useApi();
const toast = useToast();

// ─── Estado interno — permite transicion create→edit sin cerrar el offcanvas ──
const localMode      = ref(props.mode);
const localItem      = ref(props.item);
const isNewlyCreated = ref(false);
const tab            = ref('general');
const loading        = ref(false);

// ─── Catalogo ─────────────────────────────────────────────────────────────────
const categories = ref([]);
const brands     = ref([]);
const taxes      = ref([]);

// ─── Formulario general ───────────────────────────────────────────────────────
const emptyForm = () => ({
  name: '', short_description: '', description: '', video_url: '',
  is_active: true, is_featured: false,
  category: '', brand: null, condition: 'new',
  stock: 0, price: null, discounted_price: null,
  meta_title: '', meta_description: '',
});
const form = ref(emptyForm());

// ─── Variantes ────────────────────────────────────────────────────────────────
const variants        = ref([]);
const variantsLoading = ref(false);
const variantLoading  = ref(false);
const showVariantForm = ref(false);
const editingVariant  = ref(null);
const firstVariantUuid = computed(() => variants.value[0]?.uuid || null);

const emptyNewVariant = () => ({
  price: null, discounted_price: null, stock: 0, is_default: false,
  discount_start_date: '', discount_end_date: '',
  attrRows: [],
  weight: null, length: null, width: null, height: null,
});
const newVariant = ref(emptyNewVariant());

// ─── Imagenes ─────────────────────────────────────────────────────────────────
const productImages  = ref([]);
const imagesLoading  = ref(false);
const uploading      = ref(false);
const uploadFile     = ref(null);
const uploadAltText  = ref('');
const fileInputRef   = ref(null);

// ─── Reglas de Costo ──────────────────────────────────────────────────────────
const costRules          = ref([]);
const costLoading        = ref(false);
const showCostForm       = ref(false);
const activeCostRulesCount = computed(() => costRules.value.filter(r => r.is_active).length);
const costForm = reactive({
  name: '', context: 'TAX', cost_type: 'PERCENTAGE', value: '', description: '', applies_globally: false,
});

// ─── Helpers atributos ────────────────────────────────────────────────────────
const attrsToRows   = (attrs) => Object.entries(attrs || {}).map(([key, value]) => ({ key, value }));
const rowsToAttrs   = (rows) => Object.fromEntries(
  rows.filter(r => r.key?.trim()).map(r => [r.key.trim(), r.value])
);
const addAttrRow    = (target) => target.attrRows.push({ key: '', value: '' });
const removeAttrRow = (target, i) => target.attrRows.splice(i, 1);

// ─── Helpers fecha ────────────────────────────────────────────────────────────
const toLocalDT   = (iso)   => iso   ? iso.substring(0, 16) : '';
const fromLocalDT = (local) => local ? local + ':00' : null;

// ─── Limpieza numerica — NaN / '' → null ─────────────────────────────────────
const cleanNum = (val) => {
  if (val === '' || val === null || val === undefined) return null;
  if (typeof val === 'number' && Number.isNaN(val))   return null;
  return val;
};

// ─── Descuento activo ─────────────────────────────────────────────────────────
const isDiscountActive = (v) => {
  if (!v.discounted_price) return false;
  const now = new Date();
  return (
    (!v.discount_start_date || now >= new Date(v.discount_start_date)) &&
    (!v.discount_end_date   || now <= new Date(v.discount_end_date))
  );
};

// ─── Sync cuando el padre cambia item/mode (apertura desde la lista) ──────────
watch(
  [() => props.item, () => props.mode],
  ([item, mode]) => {
    localMode.value      = mode;
    localItem.value      = item;
    isNewlyCreated.value = false;
    tab.value            = 'general';
    showVariantForm.value = false;
    editingVariant.value  = null;
    showCostForm.value    = false;

    if (item && mode === 'edit') {
      form.value = {
        name:              item.name,
        short_description: item.short_description || '',
        description:       item.description || '',
        video_url:         item.video_url || '',
        is_active:         item.is_active,
        is_featured:       item.is_featured,
        category:          item.category_uuid || '',
        brand:             item.brand_uuid || null,
        condition:         item.condition || 'new',
        stock:             item.stock ?? 0,
        price: null,
        discounted_price: null,
        meta_title:        item.meta_title || '',
        meta_description:  item.meta_description || '',
      };
      fetchVariants();
      fetchCostRules();
      fetchImages();
    } else {
      form.value         = emptyForm();
      variants.value     = [];
      costRules.value    = [];
      productImages.value = [];
    }
  },
  { immediate: true },
);

// ─── Catalogo ─────────────────────────────────────────────────────────────────
async function fetchCategories() {
  try {
    const r = await api.get('dashboard/categories/');
    categories.value = r.data.results ?? r.data;
  } catch {}
}
async function fetchBrands() {
  try {
    const r = await api.get('dashboard/brands/');
    brands.value = r.data.results ?? r.data;
  } catch {}
}
async function fetchTaxes() {
  try {
    const r = await api.get('dashboard/taxes/');
    taxes.value = (r.data.results ?? r.data).filter(t => t.is_active);
  } catch {}
}

// ─── Submit General / SEO ─────────────────────────────────────────────────────
async function submit() {
  loading.value = true;
  try {
    const payload = {
      name:              form.value.name,
      short_description: form.value.short_description || null,
      description:       form.value.description,
      video_url:         form.value.video_url || null,
      is_active:         form.value.is_active,
      is_featured:       form.value.is_featured,
      category:          form.value.category,
      brand:             form.value.brand,
      condition:         form.value.condition,
      meta_title:        form.value.meta_title,
      meta_description:  form.value.meta_description,
    };

    if (localMode.value === 'create') {
      payload.stock = cleanNum(form.value.stock) ?? 0;
      payload.price = form.value.price;
      payload.discounted_price = cleanNum(form.value.discounted_price);

      const { data } = await api.post('dashboard/products/', payload);

      // ── Transicion interna create→edit (offcanvas permanece abierto) ──
      localItem.value      = data;
      localMode.value      = 'edit';
      isNewlyCreated.value = true;
      tab.value            = 'variants';
      await Promise.all([fetchVariants(), fetchCostRules()]);
      toast.success('Producto creado. Configura variantes, descuentos y logistica.');
    } else {
      const { data } = await api.patch(`dashboard/products/${localItem.value.uuid}/`, payload);
      localItem.value = data;
      emit('itemSaved', data);
      toast.success('Datos generales actualizados.');
    }
  } catch (e) {
    const err = e.response?.data;
    const msg = err?.detail || err?.name?.[0] || err?.category?.[0] || err?.price?.[0]
      || 'Error al guardar. Revisa los campos.';
    toast.error(msg);
  } finally {
    loading.value = false;
  }
}

// ─── Cerrar: notifica al padre que recargue la lista ─────────────────────────
function closeForm() {
  emit('success');
}

// ─── Variantes ────────────────────────────────────────────────────────────────
async function fetchVariants() {
  if (!localItem.value?.uuid) return;
  variantsLoading.value = true;
  try {
    const r = await api.get(`dashboard/products/${localItem.value.uuid}/variants/`);
    variants.value = r.data.results ?? r.data;
  } catch {
    toast.error('Error al cargar variantes');
  } finally {
    variantsLoading.value = false;
  }
}

function openNewVariantForm() {
  editingVariant.value  = null;
  newVariant.value      = emptyNewVariant();
  showVariantForm.value = true;
}
function cancelVariantForm() {
  showVariantForm.value = false;
  editingVariant.value  = null;
  newVariant.value      = emptyNewVariant();
}

async function addVariant() {
  const nv = newVariant.value;
  if (!nv.price || Number(nv.price) <= 0) return toast.error('Precio base requerido (> 0)');

  variantLoading.value = true;
  try {
    await api.post(`dashboard/products/${localItem.value.uuid}/variants/create/`, {
      price:               nv.price,
      discounted_price:    cleanNum(nv.discounted_price),
      stock:               cleanNum(nv.stock) ?? 0,
      is_default:          nv.is_default,
      attributes:          rowsToAttrs(nv.attrRows),
      discount_start_date: fromLocalDT(nv.discount_start_date),
      discount_end_date:   fromLocalDT(nv.discount_end_date),
      weight:  cleanNum(nv.weight),
      length:  cleanNum(nv.length),
      width:   cleanNum(nv.width),
      height:  cleanNum(nv.height),
    });
    toast.success('Variante agregada');
    cancelVariantForm();
    await fetchVariants();
  } catch (e) {
    const err = e.response?.data;
    toast.error(err?.price?.[0] || err?.detail || 'Error al agregar variante');
  } finally {
    variantLoading.value = false;
  }
}

function startEditVariant(v) {
  editingVariant.value = {
    ...v,
    price:               parseFloat(v.price) || null,
    discounted_price:    v.discounted_price ? parseFloat(v.discounted_price) : null,
    stock:               v.stock ?? 0,
    discount_start_date: toLocalDT(v.discount_start_date),
    discount_end_date:   toLocalDT(v.discount_end_date),
    attrRows:            attrsToRows(v.attributes),
  };
  showVariantForm.value = true;
}

async function saveVariant() {
  if (!editingVariant.value) return;
  variantLoading.value = true;
  try {
    const ev = editingVariant.value;
    await api.patch(
      `dashboard/products/${localItem.value.uuid}/variants/${ev.uuid}/`,
      {
        price:               ev.price,
        discounted_price:    cleanNum(ev.discounted_price),
        stock:               cleanNum(ev.stock) ?? 0,
        is_default:          ev.is_default,
        attributes:          rowsToAttrs(ev.attrRows),
        discount_start_date: fromLocalDT(ev.discount_start_date),
        discount_end_date:   fromLocalDT(ev.discount_end_date),
        weight:  cleanNum(ev.weight),
        length:  cleanNum(ev.length),
        width:   cleanNum(ev.width),
        height:  cleanNum(ev.height),
      }
    );
    toast.success('Variante actualizada');
    editingVariant.value  = null;
    showVariantForm.value = false;
    await fetchVariants();
    emit('itemSaved', localItem.value);
  } catch (e) {
    const err = e.response?.data;
    toast.error(err?.price?.[0] || err?.detail || 'Error al actualizar variante');
  } finally {
    variantLoading.value = false;
  }
}

async function deleteVariant(v) {
  variantLoading.value = true;
  try {
    await api.delete(
      `dashboard/products/${localItem.value.uuid}/variants/${v.uuid}/delete/`
    );
    toast.success('Variante eliminada');
    await fetchVariants();
  } catch {
    toast.error('Error al eliminar la variante');
  } finally {
    variantLoading.value = false;
  }
}

// ─── Reglas de Costo ──────────────────────────────────────────────────────────
async function fetchCostRules() {
  try {
    const r = await api.get('dashboard/shop-cost-rules/');
    costRules.value = r.data.results ?? r.data;
  } catch {}
}

async function saveCostRule() {
  if (!costForm.name?.trim())                           return toast.error('Nombre requerido');
  if (costForm.value === '' || costForm.value === null) return toast.error('Valor requerido');
  costLoading.value = true;
  try {
    await api.post('dashboard/shop-cost-rules/', {
      ...costForm, value: String(costForm.value),
    });
    await fetchCostRules();
    showCostForm.value = false;
    Object.assign(costForm, {
      name: '', context: 'TAX', cost_type: 'PERCENTAGE',
      value: '', description: '', applies_globally: false,
    });
    toast.success('Regla de costo creada');
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Error al crear regla');
  } finally {
    costLoading.value = false;
  }
}

async function toggleCostRule(rule) {
  costLoading.value = true;
  try {
    if (rule.is_active) {
      await api.post(`dashboard/shop-cost-rules/${rule.uuid}/deactivate/`);
    } else {
      await api.patch(`dashboard/shop-cost-rules/${rule.uuid}/update/`, { is_active: true });
    }
    await fetchCostRules();
  } catch {
    toast.error('Error al cambiar estado de la regla');
  } finally {
    costLoading.value = false;
  }
}

async function assignCostRule(ruleUuid) {
  if (!firstVariantUuid.value) return toast.error('Crea una variante primero');
  costLoading.value = true;
  try {
    await api.post(`dashboard/shop-cost-rules/${ruleUuid}/assign/`, {
      variant_uuid: firstVariantUuid.value,
    });
    toast.success('Regla asignada a la variante principal');
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Ya asignada o error al asignar');
  } finally {
    costLoading.value = false;
  }
}

// ─── Imagenes ─────────────────────────────────────────────────────────────────
async function fetchImages() {
  if (!localItem.value?.uuid) return;
  imagesLoading.value = true;
  try {
    const r = await api.get(`dashboard/products/${localItem.value.uuid}/`);
    productImages.value = r.data.images || [];
  } catch {
    toast.error('Error al cargar imagenes');
  } finally {
    imagesLoading.value = false;
  }
}

async function uploadImage() {
  if (!uploadFile.value) return toast.error('Selecciona una imagen');
  uploading.value = true;
  try {
    const fd = new FormData();
    fd.append('image', uploadFile.value);
    fd.append('alt_text', uploadAltText.value || '');
    if (!productImages.value.length) fd.append('is_primary', 'true');
    await api.post(`dashboard/products/${localItem.value.uuid}/add_image/`, fd, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    uploadFile.value    = null;
    uploadAltText.value = '';
    if (fileInputRef.value) fileInputRef.value.value = '';
    await fetchImages();
    toast.success('Imagen subida');
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Error al subir imagen');
  } finally {
    uploading.value = false;
  }
}

async function deleteImage(img) {
  imagesLoading.value = true;
  try {
    await api.delete(`dashboard/products/${localItem.value.uuid}/delete_image/${img.uuid}/`);
    await fetchImages();
    toast.success('Imagen eliminada');
  } catch {
    toast.error('Error al eliminar imagen');
  } finally {
    imagesLoading.value = false;
  }
}

async function setPrimaryImage(img) {
  imagesLoading.value = true;
  try {
    await api.post(`dashboard/products/${localItem.value.uuid}/set_primary/${img.uuid}/`);
    await fetchImages();
    toast.success('Imagen principal actualizada');
  } catch {
    toast.error('Error al establecer imagen principal');
  } finally {
    imagesLoading.value = false;
  }
}

// ─── Formato numerico ─────────────────────────────────────────────────────────
const formatNum = (val) => {
  if (val == null || val === '') return '—';
  return new Intl.NumberFormat('es-CO', { minimumFractionDigits: 0 }).format(val);
};

onMounted(() => {
  fetchCategories();
  fetchBrands();
  fetchTaxes();
});
</script>

<style scoped>
.smaller { font-size: 0.78rem; }
.btn-xs {
  padding: 0.1rem 0.35rem;
  font-size: 0.75rem;
  line-height: 1.3;
}
</style>
