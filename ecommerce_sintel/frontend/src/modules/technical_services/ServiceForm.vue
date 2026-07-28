<template>
  <div>

    <!-- Banner post-creacion -->
    <div v-if="isNewlyCreated"
         class="alert border-0 py-2 px-3 mb-3 d-flex align-items-center gap-2"
         style="background:#fffbeb;border-left:3px solid #d97706 !important;border-radius:8px;font-size:.82rem">
      <i class="bi bi-check-circle-fill flex-shrink-0" style="color:#d97706"></i>
      <div>
        <strong>Servicio creado.</strong>
        Ahora configura las variantes de precio y los costos asociados.
      </div>
    </div>

    <!-- ===================================================================
         TABS (4 consolidados: General, Imagen, Variantes, Costos)
    =================================================================== -->
    <ul class="nav nav-tabs nav-fill mb-4" style="font-size:.82rem">
      <li class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'general' }" @click="tab = 'general'">
          <i class="bi bi-tools me-1"></i>General
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'images' }" @click="tab = 'images'">
          <i class="bi bi-image me-1"></i>Imagen
          <span v-if="localImages.length" class="badge bg-secondary-subtle text-secondary ms-1">{{ localImages.length }}</span>
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
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'packages' }" @click="tab = 'packages'">
          <i class="bi bi-box-seam me-1"></i>Paquetes
          <span v-if="packagesStore.packages.length" class="badge bg-primary-subtle text-primary ms-1">{{ packagesStore.packages.length }}</span>
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'faq' }" @click="tab = 'faq'">
          <i class="bi bi-question-circle me-1"></i>FAQ
        </button>
      </li>
      <li v-if="localMode === 'edit'" class="nav-item">
        <button type="button" class="nav-link" :class="{ active: tab === 'marketing' }" @click="tab = 'marketing'">
          <i class="bi bi-megaphone me-1"></i>Marketing
        </button>
      </li>
    </ul>

    <!-- ===================================================================
         TAB 1: GENERAL
    =================================================================== -->
    <form v-show="tab === 'general'" @submit.prevent="submit">

      <!-- Nombre + Descripcion -->
      <div class="mb-3">
        <label class="form-label small fw-semibold">Nombre <span class="text-danger">*</span></label>
        <input v-model="form.name" type="text" class="form-control" required
               placeholder="Ej: Instalacion de Camaras IP">
      </div>

      <div class="mb-3">
        <label class="form-label small fw-semibold">Descripcion <span class="text-danger">*</span></label>
        <textarea v-model="form.description" class="form-control" rows="3" required
                  placeholder="Describe el alcance del servicio..."></textarea>
      </div>

      <!-- Categoria + Nivel -->
      <div class="row g-2 mb-3">
        <div class="col-7">
          <label class="form-label small fw-semibold">Categoria</label>
          <select v-model="form.category" class="form-select">
            <option :value="null">Sin categoria</option>
            <option v-for="cat in categories" :key="cat.uuid" :value="cat.uuid">{{ cat.name }}</option>
          </select>
        </div>
        <div class="col-5">
          <label class="form-label small fw-semibold">Nivel</label>
          <select v-model="form.level" class="form-select">
            <option :value="null">Sin nivel</option>
            <option v-for="lvl in levels" :key="lvl.uuid" :value="lvl.uuid">{{ lvl.name }}</option>
          </select>
        </div>
      </div>

      <!-- Toggles (Activo, Destacado, Comprable) -->
      <div class="row mb-4">
        <div class="col-4">
          <div class="form-check form-switch">
            <input v-model="form.is_active" class="form-check-input" type="checkbox" id="svcActive">
            <label class="form-check-label small" for="svcActive">Activo</label>
          </div>
        </div>
        <div class="col-4">
          <div class="form-check form-switch">
            <input v-model="form.is_featured" class="form-check-input" type="checkbox" id="svcFeatured">
            <label class="form-check-label small" for="svcFeatured">Destacado</label>
          </div>
        </div>
        <div class="col-4">
          <div class="form-check form-switch">
            <input v-model="form.is_purchasable" class="form-check-input" type="checkbox" id="svcPurchasable">
            <label class="form-check-label small" for="svcPurchasable">Comprable</label>
          </div>
        </div>
      </div>

      <!-- SEO (2026-07-18, unificacion con Renting -- solo en EDIT, replica Equipment.meta_*) -->
      <div v-if="localMode === 'edit'" class="card border-0 p-3 mb-4 rounded-3" style="background:#f8fafc">
        <div class="small fw-semibold mb-2" style="color:#334155">
          <i class="bi bi-search me-1"></i>SEO
        </div>
        <div class="mb-2">
          <label class="form-label smaller mb-1">Meta titulo</label>
          <input v-model="form.meta_title" type="text" class="form-control form-control-sm" maxlength="70" placeholder="Titulo para buscadores (max. 70 caracteres)">
        </div>
        <div class="mb-2">
          <label class="form-label smaller mb-1">Meta descripcion</label>
          <textarea v-model="form.meta_description" class="form-control form-control-sm" rows="2" placeholder="Descripcion para buscadores"></textarea>
        </div>
        <div>
          <label class="form-label smaller mb-1">Palabras clave</label>
          <input v-model="form.meta_keywords" type="text" class="form-control form-control-sm" maxlength="255" placeholder="separadas, por, coma">
        </div>
      </div>

      <!-- Variante inicial (solo en CREATE) -->
      <div v-if="localMode === 'create'" class="card border-0 p-3 mb-4 rounded-3" style="background:#fffbeb">
        <div class="d-flex align-items-center justify-content-between mb-2">
          <span class="small fw-semibold" style="color:#92400e">
            <i class="bi bi-currency-dollar me-1"></i>Variante principal
          </span>
        </div>

        <div class="mt-3">
          <!-- Estrategia pricing -->
          <div class="d-flex gap-3 mb-3" style="font-size:.82rem">
            <div class="form-check">
              <input v-model="initVar.pricing_strategy" class="form-check-input" type="radio" value="FIXED" id="initFixed">
              <label class="form-check-label" for="initFixed">Precio fijo</label>
            </div>
            <div class="form-check">
              <input v-model="initVar.pricing_strategy" class="form-check-input" type="radio" value="HOURLY" id="initHourly">
              <label class="form-check-label" for="initHourly">Por horas (SMLV)</label>
            </div>
            <div class="form-check">
              <input v-model="initVar.pricing_strategy" class="form-check-input" type="radio" value="DAILY" id="initDaily">
              <label class="form-check-label" for="initDaily">Por dias (SMLV)</label>
            </div>
          </div>

          <!-- Campos dinamicos segun estrategia -->
          <div v-if="initVar.pricing_strategy === 'FIXED'" class="row g-2">
            <div class="col-12">
              <label class="form-label smaller mb-1 fw-semibold">Precio fijo (COP)</label>
              <div class="input-group input-group-sm">
                <span class="input-group-text">$</span>
                <input v-model.number="initVar.fixed_price" type="number" step="100" min="0"
                       class="form-control" placeholder="250000">
              </div>
            </div>
          </div>

          <div v-else class="row g-2">
            <div class="col-6">
              <label class="form-label smaller mb-1 fw-semibold">
                {{ initVar.pricing_strategy === 'DAILY' ? 'Dias estimados' : 'Horas estimadas' }}
              </label>
              <input v-model.number="initVar.estimated_hours" type="number" step="0.5" min="0.5"
                     class="form-control form-control-sm" placeholder="Ej: 4">
            </div>
            <div class="col-6">
              <label class="form-label smaller mb-1 fw-semibold">Factor complejidad</label>
              <input v-model.number="initVar.complexity_factor" type="number" step="0.1" min="0.1" max="5"
                     class="form-control form-control-sm" placeholder="1.0">
            </div>
          </div>

          <div class="form-text" style="font-size:.7rem">
            El SKU y la variante default se generan automáticamente al guardar.
          </div>
        </div>
      </div>

      <!-- Botones footer -->
      <div v-if="localMode === 'create'" class="d-flex gap-2 mt-3">
        <button type="submit" class="btn btn-primary flex-grow-1" :disabled="loading">
          <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
          <i v-else class="bi bi-plus-lg me-1"></i>
          Crear Servicio
        </button>
        <button type="button" class="btn btn-light border" @click="$emit('cancel')" :disabled="loading">
          Cancelar
        </button>
      </div>

      <div v-else class="d-flex gap-2 mt-3">
        <button type="submit" class="btn btn-primary flex-grow-1" :disabled="loading">
          <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
          Guardar Cambios
        </button>
        <button type="button" class="btn btn-light border" @click="closeForm">Cerrar</button>
      </div>
    </form>

    <!-- ===================================================================
         TAB 2: IMAGEN
    =================================================================== -->
    <div v-show="tab === 'images' && localMode === 'edit'">

      <!-- Zona de carga -->
      <div
        class="upload-zone rounded-3 border-2 border-dashed d-flex flex-column align-items-center justify-content-center mb-4 p-4"
        :class="isDragging ? 'border-primary bg-primary-subtle' : 'border-secondary-subtle'"
        style="min-height:140px;cursor:pointer"
        @click="imgInput?.click()"
        @dragover.prevent="isDragging = true"
        @dragleave.prevent="isDragging = false"
        @drop.prevent="onDrop"
      >
        <i class="bi bi-cloud-upload fs-2 text-muted mb-2"></i>
        <p class="text-muted small mb-1">Arrastra una imagen aqui o haz clic para seleccionar</p>
        <p class="text-muted" style="font-size:.72rem">JPG, PNG, WEBP — Max 5 MB</p>
        <input ref="imgInput" type="file" accept="image/*" class="d-none" @change="onFileSelected">
      </div>

      <!-- Preview antes de subir -->
      <div v-if="pendingFile" class="card border-0 bg-light p-3 mb-3 rounded-3">
        <div class="d-flex align-items-center gap-3">
          <img :src="pendingPreview" class="rounded-2 object-fit-cover" style="width:64px;height:64px">
          <div class="flex-grow-1 min-w-0">
            <div class="small fw-semibold text-truncate">{{ pendingFile.name }}</div>
            <div class="text-muted" style="font-size:.72rem">{{ (pendingFile.size / 1024).toFixed(0) }} KB</div>
            <div class="form-check mt-1">
              <input v-model="pendingIsPrimary" type="checkbox" class="form-check-input" id="pendingPrimary">
              <label class="form-check-label smaller" for="pendingPrimary">Imagen principal</label>
            </div>
          </div>
          <div class="d-flex flex-column gap-1 flex-shrink-0">
            <button type="button" class="btn btn-sm btn-primary" @click="uploadPending" :disabled="imgLoading">
              <span v-if="imgLoading" class="spinner-border spinner-border-sm me-1"></span>
              <i v-else class="bi bi-cloud-upload me-1"></i>Subir
            </button>
            <button type="button" class="btn btn-sm btn-light border" @click="cancelPending">Cancelar</button>
          </div>
        </div>
      </div>

      <!-- Galeria actual -->
      <div v-if="localImages.length" class="row g-2 mb-4">
        <div v-for="img in localImages" :key="img.uuid" class="col-4 col-md-3">
          <div class="position-relative rounded-2 overflow-hidden border"
               style="aspect-ratio:1"
               :class="img.is_primary ? 'border-warning border-2' : ''">
            <img :src="img.image" :alt="img.alt_text || ''"
                 class="w-100 h-100 object-fit-cover">
            <div class="position-absolute top-0 end-0 p-1 d-flex gap-1">
              <button v-if="!img.is_primary"
                      type="button"
                      class="btn btn-xs btn-warning rounded-circle p-1"
                      style="width:22px;height:22px;font-size:.6rem;line-height:1"
                      @click="setPrimary(img)" :disabled="imgLoading" title="Hacer principal">
                <i class="bi bi-star-fill"></i>
              </button>
              <button type="button"
                      class="btn btn-xs btn-danger rounded-circle p-1"
                      style="width:22px;height:22px;font-size:.6rem;line-height:1"
                      @click="deleteImg(img)" :disabled="imgLoading" title="Eliminar">
                <i class="bi bi-trash3-fill"></i>
              </button>
            </div>
            <div v-if="img.is_primary"
                 class="position-absolute bottom-0 start-0 end-0 text-center py-1"
                 style="background:rgba(245,158,11,.85);font-size:.65rem;color:#fff;font-weight:600">
              Principal
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="!pendingFile" class="text-center py-4 text-muted">
        <i class="bi bi-image fs-3 d-block mb-2 opacity-40"></i>
        <p class="small mb-0">Sin imagenes. Sube la primera imagen representativa del servicio.</p>
      </div>

      <div class="d-flex justify-content-end pt-2 border-top">
        <button type="button" class="btn btn-light border" @click="closeForm">Cerrar</button>
      </div>
    </div>

    <!-- ===================================================================
         TAB 3: VARIANTES (tabla inline con edicion)
    =================================================================== -->
    <div v-show="tab === 'variants' && localMode === 'edit'">

      <div class="d-flex justify-content-between align-items-center mb-3">
        <p class="text-muted small mb-0">Gestiona los precios, duraciones y complejidades de este servicio.</p>
        <button type="button" class="btn btn-sm btn-primary" @click="openNewVariantForm"
                :disabled="showVariantForm && !editingVar">
          <i class="bi bi-plus-lg me-1"></i>Nueva Variante
        </button>
      </div>

      <!-- Formulario nueva variante (modal-like) -->
      <div v-if="showVariantForm && !editingVar" class="card border-0 bg-light p-3 mb-3 rounded-3">
        <h6 class="fw-semibold small mb-3">Nueva Variante</h6>

        <div class="d-flex gap-3 mb-2" style="font-size:.82rem">
          <div class="form-check">
            <input v-model="newVar.pricing_strategy" class="form-check-input" type="radio" value="FIXED" id="nvPFixed">
            <label class="form-check-label" for="nvPFixed">Precio fijo</label>
          </div>
          <div class="form-check">
            <input v-model="newVar.pricing_strategy" class="form-check-input" type="radio" value="HOURLY" id="nvPHourly">
            <label class="form-check-label" for="nvPHourly">Por horas</label>
          </div>
          <div class="form-check">
            <input v-model="newVar.pricing_strategy" class="form-check-input" type="radio" value="DAILY" id="nvPDaily">
            <label class="form-check-label" for="nvPDaily">Por dias</label>
          </div>
        </div>

        <div class="row g-2 mb-2">
          <template v-if="newVar.pricing_strategy === 'FIXED'">
            <div class="col-12">
              <label class="form-label smaller mb-1 fw-semibold">Precio fijo (COP)</label>
              <div class="input-group input-group-sm">
                <span class="input-group-text">$</span>
                <input v-model.number="newVar.fixed_price" type="number" step="100" min="0"
                       class="form-control" placeholder="0">
              </div>
            </div>
          </template>
          <template v-else>
            <div class="col-6">
              <label class="form-label smaller mb-1 fw-semibold">
                {{ newVar.pricing_strategy === 'DAILY' ? 'Dias estimados' : 'Horas estimadas' }}
              </label>
              <input v-model.number="newVar.estimated_hours" type="number" step="0.5" min="0.5"
                     class="form-control form-control-sm">
            </div>
            <div class="col-6">
              <label class="form-label smaller mb-1 fw-semibold">Complejidad</label>
              <input v-model.number="newVar.complexity_factor" type="number" step="0.1" min="0.1"
                     class="form-control form-control-sm" placeholder="1.0">
            </div>
            <div class="col-6">
              <label class="form-label smaller mb-1">
                Min. ({{ newVar.pricing_strategy === 'DAILY' ? 'd' : 'h' }})
              </label>
              <input v-model.number="newVar.min_duration" type="number" step="0.5" min="0"
                     class="form-control form-control-sm" placeholder="Sin minimo">
            </div>
            <div class="col-6">
              <label class="form-label smaller mb-1">
                Max. ({{ newVar.pricing_strategy === 'DAILY' ? 'd' : 'h' }})
              </label>
              <input v-model.number="newVar.max_duration" type="number" step="0.5" min="0"
                     class="form-control form-control-sm" placeholder="Sin maximo">
            </div>
          </template>

          <!-- Capacidad simultanea -->
          <div class="col-12 mt-1">
            <label class="form-label smaller mb-1 fw-semibold d-flex align-items-center gap-1">
              Capacidad simultanea
              <span class="badge bg-info-subtle text-info border border-info-subtle"
                    style="font-size:.6rem;cursor:help"
                    title="Cuantos servicios de este tipo se pueden atender al mismo tiempo.">
                ?
              </span>
            </label>
            <input v-model.number="newVar.simultaneous_capacity" type="number" min="1" step="1"
                   class="form-control form-control-sm" placeholder="1">
          </div>
        </div>

        <div class="d-flex align-items-center justify-content-between pt-2 border-top mt-1">
          <div class="d-flex gap-3 mb-0">
            <div class="form-check mb-0">
              <input v-model="newVar.is_default" type="checkbox" class="form-check-input" id="nvDefault">
              <label class="form-check-label smaller" for="nvDefault">Por defecto</label>
            </div>
            <div class="form-check form-switch mb-0">
              <input v-model="newVar.is_active" type="checkbox" class="form-check-input" id="nvActive" role="switch">
              <label class="form-check-label smaller" for="nvActive">
                <span :class="newVar.is_active ? 'text-success fw-semibold' : 'text-danger fw-semibold'">
                  {{ newVar.is_active ? 'Activa' : 'Inactiva' }}
                </span>
              </label>
            </div>
          </div>
          <div class="d-flex gap-2">
            <button type="button" class="btn btn-sm btn-light border" @click="cancelVariantForm">Cancelar</button>
            <button type="button" class="btn btn-sm btn-primary" @click="addVariant" :disabled="varLoading">
              <span v-if="varLoading" class="spinner-border spinner-border-sm me-1"></span>
              Guardar
            </button>
          </div>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="variantsLoading" class="text-center py-4">
        <div class="spinner-border spinner-border-sm text-primary"></div>
      </div>

      <!-- Empty state -->
      <div v-else-if="!variants.length && !showVariantForm" class="text-center py-4 text-muted">
        <i class="bi bi-layers fs-3 d-block mb-2 opacity-50"></i>
        <p class="small mb-2">Sin variantes. Agrega la primera.</p>
      </div>

      <!-- Tabla de variantes (simplificada) -->
      <div v-else-if="variants.length" class="d-flex flex-column gap-2">
        <div v-for="v in variants" :key="v.uuid" class="border rounded-3 overflow-hidden p-3">

          <!-- Modo edicion -->
          <div v-if="editingVar?.uuid === v.uuid" class="bg-light">
            <h6 class="fw-semibold small mb-3">Editando: <code>{{ v.sku }}</code></h6>

            <div class="d-flex gap-3 mb-2" style="font-size:.82rem">
              <div class="form-check">
                <input v-model="editingVar.pricing_strategy" class="form-check-input" type="radio"
                       value="FIXED" :id="'evPF-'+v.uuid">
                <label class="form-check-label" :for="'evPF-'+v.uuid">Precio fijo</label>
              </div>
              <div class="form-check">
                <input v-model="editingVar.pricing_strategy" class="form-check-input" type="radio"
                       value="HOURLY" :id="'evPH-'+v.uuid">
                <label class="form-check-label" :for="'evPH-'+v.uuid">Por horas</label>
              </div>
              <div class="form-check">
                <input v-model="editingVar.pricing_strategy" class="form-check-input" type="radio"
                       value="DAILY" :id="'evPD-'+v.uuid">
                <label class="form-check-label" :for="'evPD-'+v.uuid">Por dias</label>
              </div>
            </div>

            <div class="row g-2 mb-2">
              <template v-if="editingVar.pricing_strategy === 'FIXED'">
                <div class="col-12">
                  <label class="form-label smaller mb-1 fw-semibold">Precio fijo (COP)</label>
                  <div class="input-group input-group-sm">
                    <span class="input-group-text">$</span>
                    <input v-model.number="editingVar.fixed_price" type="number" step="100" class="form-control">
                  </div>
                </div>
              </template>
              <template v-else>
                <div class="col-6">
                  <label class="form-label smaller mb-1 fw-semibold">
                    {{ editingVar.pricing_strategy === 'DAILY' ? 'Dias estimados' : 'Horas estimadas' }}
                  </label>
                  <input v-model.number="editingVar.estimated_hours" type="number" step="0.5" min="0.5"
                         class="form-control form-control-sm">
                </div>
                <div class="col-6">
                  <label class="form-label smaller mb-1 fw-semibold">Complejidad</label>
                  <input v-model.number="editingVar.complexity_factor" type="number" step="0.1" min="0.1"
                         class="form-control form-control-sm">
                </div>
                <div class="col-6">
                  <label class="form-label smaller mb-1">
                    Min. ({{ editingVar.pricing_strategy === 'DAILY' ? 'd' : 'h' }})
                  </label>
                  <input v-model.number="editingVar.min_duration" type="number" step="0.5" min="0"
                         class="form-control form-control-sm" placeholder="Sin minimo">
                </div>
                <div class="col-6">
                  <label class="form-label smaller mb-1">
                    Max. ({{ editingVar.pricing_strategy === 'DAILY' ? 'd' : 'h' }})
                  </label>
                  <input v-model.number="editingVar.max_duration" type="number" step="0.5" min="0"
                         class="form-control form-control-sm" placeholder="Sin maximo">
                </div>
              </template>

              <!-- Capacidad (edit) -->
              <div class="col-12 mt-1">
                <label class="form-label smaller mb-1 fw-semibold">Capacidad simultanea</label>
                <input v-model.number="editingVar.simultaneous_capacity" type="number" min="1" step="1"
                       class="form-control form-control-sm" placeholder="1">
              </div>
            </div>

            <div class="d-flex align-items-center justify-content-between pt-2 border-top mt-1">
              <div class="d-flex gap-3 mb-0">
                <div class="form-check mb-0">
                  <input v-model="editingVar.is_default" type="checkbox" class="form-check-input" :id="'evDef-'+v.uuid">
                  <label class="form-check-label smaller" :for="'evDef-'+v.uuid">Por defecto</label>
                </div>
                <div class="form-check form-switch mb-0">
                  <input v-model="editingVar.is_active" type="checkbox" class="form-check-input" :id="'evAct-'+v.uuid" role="switch">
                  <label class="form-check-label smaller" :for="'evAct-'+v.uuid">
                    <span :class="editingVar.is_active ? 'text-success fw-semibold' : 'text-danger fw-semibold'">
                      {{ editingVar.is_active ? 'Activa' : 'Inactiva' }}
                    </span>
                  </label>
                </div>
              </div>
              <div class="d-flex gap-2">
                <button type="button" class="btn btn-sm btn-light border"
                        @click="editingVar = null; showVariantForm = false">
                  Cancelar
                </button>
                <button type="button" class="btn btn-sm btn-warning text-dark fw-medium"
                        @click="saveVariant" :disabled="varLoading">
                  <span v-if="varLoading" class="spinner-border spinner-border-sm me-1"></span>
                  Guardar
                </button>
              </div>
            </div>
          </div>

          <!-- Modo vista -->
          <div v-else>
            <div class="d-flex align-items-start justify-content-between gap-2">
              <div class="flex-grow-1">
                <div class="d-flex align-items-center gap-2 flex-wrap">
                  <code class="fw-bold text-dark">{{ v.sku }}</code>
                  <span v-if="v.is_default"
                        class="badge bg-primary-subtle text-primary border border-primary-subtle smaller">Default</span>
                  <span class="badge rounded-pill smaller"
                        :class="v.pricing_strategy === 'FIXED'
                          ? 'bg-success-subtle text-success'
                          : 'bg-info-subtle text-info'">
                    {{ v.pricing_strategy === 'FIXED' ? 'Fijo' : v.pricing_strategy === 'DAILY' ? 'Diario' : 'Horario' }}
                  </span>
                  <span class="badge rounded-pill smaller"
                        :class="v.is_active ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'">
                    <i :class="v.is_active ? 'bi bi-check-circle me-1' : 'bi bi-x-circle me-1'"></i>
                    {{ v.is_active ? 'Activa' : 'Inactiva' }}
                  </span>
                </div>

                <div class="mt-1">
                  <span v-if="v.pricing_strategy === 'FIXED'" class="fw-bold text-dark">
                    ${{ formatNum(v.fixed_price) }} COP
                  </span>
                  <span v-else class="fw-bold text-dark">
                    ~${{ formatNum(v.calculated_price) }}
                    <span class="text-muted fw-normal smaller">
                      ({{ v.estimated_hours }}{{ v.pricing_strategy === 'DAILY' ? 'd' : 'h' }}
                      &times; {{ v.complexity_factor }})
                    </span>
                  </span>
                  <span v-if="v.pricing_strategy !== 'FIXED' && (v.min_duration || v.max_duration)"
                        class="text-muted smaller ms-1">
                    [{{ v.min_duration || 0 }}&ndash;{{ v.max_duration || '&infin;' }}
                    {{ v.pricing_strategy === 'DAILY' ? 'd' : 'h' }}]
                  </span>
                </div>

                <!-- Desglose price_info -->
                <div v-if="v.price_info"
                     class="mt-2 p-2 rounded-2 border" style="background:#f8fafc;font-size:.72rem">
                  <div class="d-flex justify-content-between text-muted mb-1">
                    <span>Mano de obra</span>
                    <span class="fw-semibold text-dark">${{ formatNum(v.price_info.labor_cost) }}</span>
                  </div>
                  <div v-if="v.price_info.material_cost > 0"
                       class="d-flex justify-content-between text-muted mb-1">
                    <span>Materiales</span>
                    <span>${{ formatNum(v.price_info.material_cost) }}</span>
                  </div>
                  <div v-if="v.price_info.iva_amount > 0"
                       class="d-flex justify-content-between text-muted mb-1">
                    <span>IVA ({{ Number(v.price_info.iva_rate).toFixed(0) }}%)</span>
                    <span>+${{ formatNum(v.price_info.iva_amount) }}</span>
                  </div>
                  <div class="d-flex justify-content-between border-top mt-1 pt-1 fw-bold text-dark">
                    <span>Total estimado</span>
                    <span class="text-primary">${{ formatNum(v.price_info.total_price || v.price_info.total) }}</span>
                  </div>
                </div>
              </div>

              <!-- Acciones -->
              <div class="btn-group btn-group-sm flex-shrink-0">
                <button type="button" class="btn btn-light border-end"
                        @click="viewPriceHistory(v)" title="Historial de precios">
                  <i class="bi bi-clock-history text-secondary" style="font-size:.75rem"></i>
                </button>
                <button type="button" class="btn btn-light border-end"
                        @click="startEditVar(v)" title="Editar">
                  <i class="bi bi-pencil text-primary" style="font-size:.75rem"></i>
                </button>
                <button type="button" class="btn btn-light border-end"
                        @click="duplicateVariant(v)" :disabled="varLoading" title="Duplicar">
                  <i class="bi bi-copy text-info" style="font-size:.75rem"></i>
                </button>
                <button type="button" class="btn btn-light"
                        @click="deleteVariant(v)" :disabled="varLoading" title="Eliminar">
                  <i class="bi bi-trash text-danger" style="font-size:.75rem"></i>
                </button>
              </div>
            </div>
          </div>

        </div>
      </div>

      <div class="d-flex justify-content-end mt-4 pt-2 border-top">
        <button type="button" class="btn btn-light border" @click="closeForm">Cerrar</button>
      </div>
    </div>

    <!-- ===================================================================
         TAB 4: COSTOS (Smart calculation panel)
    =================================================================== -->
    <div v-show="tab === 'costos' && localMode === 'edit'" class="pb-4">

      <div v-if="variants.length" class="row g-2 mb-3">
        <div class="col-12 col-md-6">
          <label class="form-label small fw-semibold mb-1">Variante a cotizar</label>
          <select v-model="selectedCostVariantUuid" class="form-select form-select-sm">
            <option v-for="v in variants" :key="v.uuid" :value="v.uuid">
              {{ v.sku }} · {{ v.pricing_strategy }}
            </option>
          </select>
        </div>
        <div class="col-6 col-md-3">
          <label class="form-label small fw-semibold mb-1">Duración (opcional)</label>
          <input v-model.number="selectedCostDuration" type="number" min="0.5" step="0.5"
                 class="form-control form-control-sm" placeholder="Usar default">
        </div>
        <div class="col-6 col-md-3">
          <label class="form-label small fw-semibold mb-1">Descuento %</label>
          <input v-model.number="selectedCostDiscount" type="number" min="0" max="100" step="0.1"
                 class="form-control form-control-sm" placeholder="0">
        </div>
      </div>

      <div v-if="variants.length" class="mb-3">
        <CostCalculationPanel
          :variant-uuid="selectedCostVariantUuid"
          :duration="cleanNum(selectedCostDuration)"
          :discount="cleanNum(selectedCostDiscount)"
        />
      </div>

      <div v-else class="alert alert-warning border-0 py-2 px-3 mb-3 small">
        <i class="bi bi-exclamation-triangle me-2"></i>
        Crea al menos una variante para ver los detalles de costos.
      </div>

      <div class="d-flex justify-content-end pt-2 border-top">
        <button type="button" class="btn btn-light border" @click="closeForm">Cerrar</button>
      </div>
    </div>

    <!-- ===================================================================
         TAB 5: PAQUETES DE SERVICIO
    =================================================================== -->
    <div v-show="tab === 'packages' && localMode === 'edit'">
      <ServicePackagesPanel :service="localItem" @close="closeForm" />
    </div>

    <!-- ===================================================================
         TAB 6: FAQ (unificacion con Renting, 2026-07-18)
    =================================================================== -->
    <div v-show="tab === 'faq' && localMode === 'edit'">
      <ServiceFAQManager v-if="localItem?.uuid" :service-uuid="localItem.uuid" />
    </div>

    <!-- ===================================================================
         TAB 7: MARKETING (unificacion con Renting, 2026-07-18 -- replica
         RentingForm.vue, sin comparativa comprar-vs-alquilar: no aplica al
         dominio de servicios, ver ServiceMarketing en el modelo)
    =================================================================== -->
    <div v-show="tab === 'marketing' && localMode === 'edit'">
      <p class="text-muted small mb-3">
        Configuracion comercial y visual exclusiva de este servicio -- se refleja
        automaticamente en el detalle publico. Nada de esto se comparte ni se hereda
        de otros servicios.
      </p>

      <!-- Precio comercial -->
      <h6 class="fw-semibold small text-uppercase text-muted mb-2">Precio comercial</h6>
      <div class="row g-2 mb-3">
        <div class="col-6">
          <label class="form-label small">Precio de referencia (anterior)</label>
          <div class="input-group input-group-sm">
            <span class="input-group-text">$</span>
            <input v-model.number="marketingForm.reference_price" type="number" min="0" step="0.01" class="form-control" placeholder="250000">
          </div>
        </div>
        <div class="col-6">
          <label class="form-label small">Precio promocional</label>
          <div class="input-group input-group-sm">
            <span class="input-group-text">$</span>
            <input v-model.number="marketingForm.promo_price" type="number" min="0" step="0.01" class="form-control" placeholder="190000">
          </div>
        </div>
        <div class="col-12">
          <div class="form-check form-switch">
            <input class="form-check-input" type="checkbox" v-model="marketingForm.show_discount_percentage" id="svcMktShowDiscount">
            <label class="form-check-label small" for="svcMktShowDiscount">Mostrar porcentaje de descuento (calculado automaticamente)</label>
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
          <textarea v-model="marketingForm.main_message" class="form-control form-control-sm" rows="2" placeholder="Ideal para hogares, oficinas y conjuntos residenciales..."></textarea>
        </div>
        <div class="col-6">
          <label class="form-label small">Beneficio destacado</label>
          <input v-model="marketingForm.featured_benefit" type="text" class="form-control form-control-sm" placeholder="Visita tecnica sin costo">
        </div>
        <div class="col-6">
          <label class="form-label small">Mensaje de confianza</label>
          <input v-model="marketingForm.trust_message" type="text" class="form-control form-control-sm" placeholder="Tecnicos certificados">
        </div>
        <div class="col-6">
          <label class="form-label small">Mensaje de urgencia</label>
          <input v-model="marketingForm.urgency_message" type="text" class="form-control form-control-sm" placeholder="Cupos limitados esta semana">
        </div>
        <div class="col-6">
          <label class="form-label small">Prueba social</label>
          <input v-model="marketingForm.social_proof_message" type="text" class="form-control form-control-sm" placeholder="Mas de 300 servicios realizados">
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
        <input v-model="newUseCase" type="text" class="form-control" placeholder="Ej: Oficinas" @keyup.enter="addUseCase">
        <button type="button" class="btn btn-outline-secondary" @click="addUseCase">Agregar</button>
      </div>

      <!-- CTA y Banner -->
      <h6 class="fw-semibold small text-uppercase text-muted mb-2 mt-4">Llamado a la accion y banner</h6>
      <div class="row g-2 mb-3">
        <div class="col-6">
          <label class="form-label small">Texto del boton (CTA)</label>
          <input v-model="marketingForm.cta_label" type="text" class="form-control form-control-sm" placeholder="Solicitar ahora">
        </div>
        <div class="col-6">
          <label class="form-label small">Banner promocional</label>
          <input v-model="marketingForm.promo_banner_message" type="text" class="form-control form-control-sm" placeholder="Diagnostico gratis por tiempo limitado">
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
          <input v-model="newQuickBenefit.icon" type="text" class="form-control form-control-sm" placeholder="bi-shield-check (icono)">
        </div>
        <div class="col-6">
          <input v-model="newQuickBenefit.label" type="text" class="form-control form-control-sm" placeholder="Garantia de 6 meses" @keyup.enter="addQuickBenefit">
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

    <!-- ===================================================================
         MODAL: Historial de Precios
    =================================================================== -->
    <div v-if="selectedVariantForHistory" class="modal-backdrop fade show" style="z-index:1060"
         @click="closePriceHistory"></div>
    <div v-if="selectedVariantForHistory" class="modal fade show d-block" tabindex="-1" style="z-index:1070">
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content shadow-lg border-0">
          <div class="modal-header bg-light border-bottom py-3">
            <div>
              <h6 class="modal-title fw-bold mb-0 text-dark">Historial de Precios</h6>
              <span class="text-muted smaller">SKU:
                <strong class="text-primary">{{ selectedVariantForHistory.sku }}</strong>
              </span>
            </div>
            <button type="button" class="btn-close" @click="closePriceHistory"></button>
          </div>
          <div class="modal-body py-4" style="max-height:400px;overflow-y:auto">
            <div v-if="historyLoading" class="text-center py-4">
              <div class="spinner-border spinner-border-sm text-primary me-2"></div>
              <span class="text-muted small">Cargando historial...</span>
            </div>
            <div v-else-if="!priceHistory.length" class="text-muted small text-center py-4">
              <i class="bi bi-clock-history fs-3 d-block mb-2 opacity-50"></i>
              Sin cambios de precio registrados.
            </div>
            <div v-else class="timeline-container">
              <div v-for="h in priceHistory" :key="h.uuid" class="timeline-item">
                <div class="timeline-marker"></div>
                <div class="d-flex align-items-center justify-content-between mb-1">
                  <span class="badge bg-primary-subtle text-primary border border-primary-subtle fw-bold">
                    ${{ formatNum(h.new_price) }}
                  </span>
                  <span class="text-muted smaller fw-medium">{{ formatDate(h.created_at) }}</span>
                </div>
                <div class="text-muted smaller mt-2">
                  <div>Precio anterior: <del class="text-danger">${{ formatNum(h.old_price) }}</del></div>
                  <div v-if="h.changed_by_email" class="mt-1 d-flex align-items-center gap-1">
                    <i class="bi bi-person text-muted"></i>
                    Modificado por: <span class="fw-semibold text-dark">{{ h.changed_by_email }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer bg-light border-top p-2 d-flex justify-content-end">
            <button type="button" class="btn btn-sm btn-secondary px-3" @click="closePriceHistory">Cerrar</button>
          </div>
        </div>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, reactive, watch, computed, onMounted } from 'vue';
import { storeToRefs } from 'pinia';
import { useTechnicalServicesStore } from '@/store/technicalServicesAdmin/services';
import { useTechnicalServicesCatalogStore } from '@/store/technicalServicesAdmin/catalog';
import { useTechnicalServicePackagesStore } from '@/store/technicalServicesAdmin/packages';
import { useToast } from '@/composables/useToast';
import useApi from '@/composables/useApi';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { formatCOP } from '@/utils/money';
import CostCalculationPanel from './CostCalculationPanel.vue';
import ServicePackagesPanel from './ServicePackagesPanel.vue';
import ServiceFAQManager from './ServiceFAQManager.vue';

const props = defineProps({
  item: { type: Object, default: null },
  mode: { type: String, default: 'create' },
});
const emit = defineEmits(['success', 'cancel']);

const toast = useToast();
const api = useApi();
const { handleError } = useErrorHandler();
const store = useTechnicalServicesStore();
const catalogStore = useTechnicalServicesCatalogStore();
const packagesStore = useTechnicalServicePackagesStore();
const { categories, levels } = storeToRefs(catalogStore);
const { variants } = storeToRefs(store);

// ─── Estado general ───────────────────────────────────────────────────────────
const localMode      = ref(props.mode);
const localItem      = ref(props.item);
const isNewlyCreated = ref(false);
const tab            = ref('general');
const loading        = ref(false);

// ─── Formulario General ───────────────────────────────────────────────────────
const emptyForm = () => ({
  name: '', description: '',
  category: null, level: null,
  is_active: true, is_featured: false, is_purchasable: true,
  meta_title: '', meta_description: '', meta_keywords: '',
});
const form = ref(emptyForm());

// ─── Variante inicial (CREATE) ────────────────────────────────────────────────
const emptyInitVar = () => ({
  pricing_strategy: 'FIXED', fixed_price: '',
  estimated_hours: 1, complexity_factor: 1,
});
const initVar = ref(emptyInitVar());

// ─── Variantes (EDIT) ─────────────────────────────────────────────────────────
const variantsLoading = ref(false);
const varLoading      = ref(false);
const showVariantForm = ref(false);
const editingVar      = ref(null);
const selectedCostVariantUuid = ref('');
const selectedCostDuration    = ref(null);
const selectedCostDiscount    = ref(null);

const emptyNewVar = () => ({
  pricing_strategy: 'FIXED', fixed_price: '',
  estimated_hours: 1, complexity_factor: 1,
  min_duration: '', max_duration: '',
  simultaneous_capacity: 1,
  is_default: false, is_active: true,
});
const newVar = ref(emptyNewVar());

// ─── Imagenes ─────────────────────────────────────────────────────────────────
const localImages     = ref([]);
const imgLoading      = ref(false);
const isDragging      = ref(false);
const pendingFile     = ref(null);
const pendingPreview  = ref(null);
const pendingIsPrimary = ref(false);
const imgInput        = ref(null);

// ─── Historial de precios ─────────────────────────────────────────────────────
const selectedVariantForHistory = ref(null);
const priceHistory   = ref([]);
const historyLoading = ref(false);

// ─── Marketing (unificacion con Renting, 2026-07-18) ──────────────────────────
const marketingLoading = ref(false);
const hasMarketing     = ref(false);
const marketingForm    = reactive({
  reference_price: null, promo_price: null, show_discount_percentage: true,
  tags: [], main_message: '', featured_benefit: '', trust_message: '',
  urgency_message: '', social_proof_message: '', use_cases: [],
  cta_label: '', promo_banner_message: '', quick_benefits: [],
});
const marketingTagOptions = [
  { value: 'OFERTA', label: 'Oferta' },
  { value: 'NUEVO', label: 'Nuevo' },
  { value: 'MAS_SOLICITADO', label: 'Mas solicitado' },
  { value: 'PREMIUM', label: 'Premium' },
  { value: 'RECOMENDADO', label: 'Recomendado' },
  { value: 'HOT', label: 'Hot' },
  { value: 'TOP_CALIFICADO', label: 'Top calificado' },
  { value: 'IDEAL_EMPRESAS', label: 'Ideal para empresas' },
  { value: 'CUPOS_LIMITADOS', label: 'Cupos limitados' },
];
const newUseCase = ref('');
const newQuickBenefit = reactive({ icon: '', label: '' });

const marketingDiscountPreview = computed(() => {
  const { reference_price: ref_, promo_price: promo } = marketingForm;
  if (!ref_ || !promo || ref_ <= 0 || promo >= ref_) return null;
  return Math.round((1 - promo / ref_) * 100);
});

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

function resetMarketingForm() {
  Object.assign(marketingForm, {
    reference_price: null, promo_price: null, show_discount_percentage: true,
    tags: [], main_message: '', featured_benefit: '', trust_message: '',
    urgency_message: '', social_proof_message: '', use_cases: [],
    cta_label: '', promo_banner_message: '', quick_benefits: [],
  });
}

async function fetchMarketing(uuid) {
  try {
    const res = await api.get(`dashboard/services/${uuid}/marketing/`);
    if (res.data?.uuid) {
      hasMarketing.value = true;
      const d = res.data;
      Object.assign(marketingForm, {
        reference_price:          d.reference_price          != null ? parseFloat(d.reference_price) : null,
        promo_price:              d.promo_price               != null ? parseFloat(d.promo_price)     : null,
        show_discount_percentage: d.show_discount_percentage ?? true,
        tags:                     d.tags || [],
        main_message:             d.main_message || '',
        featured_benefit:         d.featured_benefit || '',
        trust_message:            d.trust_message || '',
        urgency_message:          d.urgency_message || '',
        social_proof_message:     d.social_proof_message || '',
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
    await api.put(`dashboard/services/${localItem.value.uuid}/marketing/`, { ...marketingForm });
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
    await api.delete(`dashboard/services/${localItem.value.uuid}/marketing/`);
    hasMarketing.value = false;
    resetMarketingForm();
    toast.success('Marketing eliminado');
  } catch {
    toast.error('Error al eliminar marketing');
  } finally {
    marketingLoading.value = false;
  }
}

// ─── Sync desde el padre ──────────────────────────────────────────────────────
watch(
  [() => props.item, () => props.mode],
  ([item, mode]) => {
    localMode.value      = mode;
    localItem.value      = item;
    isNewlyCreated.value = false;
    tab.value            = 'general';
    showVariantForm.value = false;
    editingVar.value      = null;

    if (item && mode === 'edit') {
      form.value = {
        name:           item.name,
        description:    item.description || '',
        category:       item.category_uuid || null,
        level:          item.level_uuid   || null,
        is_active:      item.is_active,
        is_featured:    item.is_featured,
        is_purchasable: item.is_purchasable,
        meta_title:       item.meta_title || '',
        meta_description: item.meta_description || '',
        meta_keywords:    item.meta_keywords || '',
      };
      localImages.value = item.images ? [...item.images] : [];
      fetchVariants();
      packagesStore.fetchPackages(item.uuid);
      fetchMarketing(item.uuid);
    } else {
      form.value    = emptyForm();
      initVar.value = emptyInitVar();
      localImages.value = [];
      cancelPending();
      store.$patch({ variants: [] });
      packagesStore.$patch({ packages: [] });
      hasMarketing.value = false;
      resetMarketingForm();
    }
  },
  { immediate: true },
);

// ─── Submit General ───────────────────────────────────────────────────────────
async function submit() {
  loading.value = true;
  try {
    const payload = { ...form.value };

    if (localMode.value === 'create') {
      const iv = initVar.value;
      const isFixed = iv.pricing_strategy === 'FIXED';
      payload.initial_variant = {
        pricing_strategy: iv.pricing_strategy,
        fixed_price: isFixed ? (iv.fixed_price || null) : null,
        estimated_hours: isFixed ? 1 : (iv.estimated_hours || 1),
        complexity_factor: isFixed ? 1 : (iv.complexity_factor || 1),
      };
      const res = await store.createService(payload);
      if (!res.ok) throw new Error(res.error);
      const svc = res.data;

      localItem.value      = svc;
      localMode.value      = 'edit';
      isNewlyCreated.value = true;
      localImages.value    = svc.images ? [...svc.images] : [];
      tab.value            = 'variants';
      await fetchVariants();
      toast.success('Servicio creado con variante principal automática.');
    } else {
      const res = await store.updateService(localItem.value.uuid, payload);
      if (!res.ok) throw new Error(res.error);
      toast.success('Datos generales actualizados.');
    }
  } catch (e) {
    toast.error(e.message || 'Error al guardar el servicio.');
  } finally {
    loading.value = false;
  }
}

function closeForm() {
  emit('success');
}

// ─── Imagenes ─────────────────────────────────────────────────────────────────
function onFileSelected(e) {
  const file = e.target.files[0];
  if (file) setPendingFile(file);
  e.target.value = '';
}

function onDrop(e) {
  isDragging.value = false;
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith('image/')) setPendingFile(file);
}

function setPendingFile(file) {
  pendingFile.value    = file;
  pendingIsPrimary.value = !localImages.value.length;
  pendingPreview.value = URL.createObjectURL(file);
}

function cancelPending() {
  pendingFile.value   = null;
  pendingPreview.value = null;
}

async function uploadPending() {
  if (!pendingFile.value) return;
  imgLoading.value = true;
  try {
    const res = await store.uploadImage(
      localItem.value.uuid,
      pendingFile.value,
      '',
      pendingIsPrimary.value,
    );
    if (!res.ok) throw new Error(res.error);
    localImages.value.push(res.data);
    if (pendingIsPrimary.value) {
      localImages.value.forEach(img => { img.is_primary = img.uuid === res.data.uuid; });
    }
    cancelPending();
    toast.success('Imagen subida correctamente');
  } catch (e) {
    toast.error(e.message || 'Error al subir imagen');
  } finally {
    imgLoading.value = false;
  }
}

async function deleteImg(img) {
  imgLoading.value = true;
  try {
    const res = await store.deleteImage(localItem.value.uuid, img.uuid);
    if (!res.ok) throw new Error(res.error);
    const idx = localImages.value.findIndex(i => i.uuid === img.uuid);
    if (idx !== -1) localImages.value.splice(idx, 1);
    if (img.is_primary && localImages.value.length) {
      localImages.value[0].is_primary = true;
    }
    toast.success('Imagen eliminada');
  } catch (e) {
    toast.error(e.message || 'Error al eliminar imagen');
  } finally {
    imgLoading.value = false;
  }
}

async function setPrimary(img) {
  imgLoading.value = true;
  try {
    const res = await store.setPrimaryImage(localItem.value.uuid, img.uuid);
    if (!res.ok) throw new Error(res.error);
    localImages.value.forEach(i => { i.is_primary = i.uuid === img.uuid; });
    toast.success('Imagen principal actualizada');
  } catch (e) {
    toast.error(e.message || 'Error al cambiar imagen principal');
  } finally {
    imgLoading.value = false;
  }
}

// ─── Variantes ────────────────────────────────────────────────────────────────
async function fetchVariants() {
  if (!localItem.value?.uuid) return;
  variantsLoading.value = true;
  try {
    await store.fetchVariants(localItem.value.uuid);
    if (!selectedCostVariantUuid.value && variants.value.length) {
      selectedCostVariantUuid.value = variants.value[0].uuid;
    }
  } catch {
    toast.error('Error al cargar variantes');
  } finally {
    variantsLoading.value = false;
  }
}

function openNewVariantForm() {
  editingVar.value      = null;
  newVar.value          = emptyNewVar();
  showVariantForm.value = true;
}

function cancelVariantForm() {
  showVariantForm.value = false;
  editingVar.value      = null;
  newVar.value          = emptyNewVar();
}

async function addVariant() {
  const nv = newVar.value;
  const isFixed = nv.pricing_strategy === 'FIXED';
  if (isFixed && !nv.fixed_price) return toast.error('Precio fijo requerido');
  if (!isFixed && !nv.estimated_hours) return toast.error('Horas/dias estimados requeridos');

  varLoading.value = true;
  try {
    const res = await store.createVariant({
      service:               localItem.value.uuid,
      pricing_strategy:      nv.pricing_strategy || 'FIXED',
      fixed_price:           isFixed ? (cleanNum(nv.fixed_price) || null) : null,
      estimated_hours:       !isFixed ? (cleanNum(nv.estimated_hours) || 1) : 1,
      complexity_factor:     !isFixed ? (cleanNum(nv.complexity_factor) || 1) : 1,
      min_duration:          !isFixed ? cleanNum(nv.min_duration) : null,
      max_duration:          !isFixed ? cleanNum(nv.max_duration) : null,
      simultaneous_capacity: nv.simultaneous_capacity || 1,
      is_default:            nv.is_default,
    });
    if (!res.ok) throw new Error(res.error);
    toast.success('Variante agregada');
    cancelVariantForm();
    await fetchVariants();
  } catch (e) {
    toast.error(e.message || 'Error al agregar variante');
  } finally {
    varLoading.value = false;
  }
}

function startEditVar(v) {
  editingVar.value = {
    uuid:                  v.uuid,
    sku:                   v.sku,
    pricing_strategy:      v.pricing_strategy || (v.fixed_price ? 'FIXED' : 'HOURLY'),
    fixed_price:           v.fixed_price       ? parseFloat(v.fixed_price) : '',
    estimated_hours:       v.estimated_hours   ? parseFloat(v.estimated_hours) : 1,
    complexity_factor:     v.complexity_factor ? parseFloat(v.complexity_factor) : 1,
    min_duration:          v.min_duration      ? parseFloat(v.min_duration) : '',
    max_duration:          v.max_duration      ? parseFloat(v.max_duration) : '',
    simultaneous_capacity: v.simultaneous_capacity ? parseInt(v.simultaneous_capacity) : 1,
    is_default:            v.is_default,
    is_active:             v.is_active !== undefined ? v.is_active : true,
  };
  showVariantForm.value = true;
}

async function saveVariant() {
  if (!editingVar.value) return;
  varLoading.value = true;
  try {
    const ev = editingVar.value;
    const isFixed = ev.pricing_strategy === 'FIXED';
    const res = await store.updateVariant(ev.uuid, localItem.value.uuid, {
      pricing_strategy:      ev.pricing_strategy || 'FIXED',
      fixed_price:           isFixed ? (cleanNum(ev.fixed_price) || null) : null,
      estimated_hours:       !isFixed ? (cleanNum(ev.estimated_hours) || 1) : 1,
      complexity_factor:     !isFixed ? (cleanNum(ev.complexity_factor) || 1) : 1,
      min_duration:          !isFixed ? cleanNum(ev.min_duration) : null,
      max_duration:          !isFixed ? cleanNum(ev.max_duration) : null,
      simultaneous_capacity: ev.simultaneous_capacity || 1,
      is_default:            ev.is_default,
    });
    if (!res.ok) throw new Error(res.error);
    toast.success('Variante actualizada');
    editingVar.value      = null;
    showVariantForm.value = false;
    await fetchVariants();
  } catch (e) {
    toast.error(e.message || 'Error al actualizar variante');
  } finally {
    varLoading.value = false;
  }
}

async function deleteVariant(v) {
  varLoading.value = true;
  try {
    const res = await store.deleteVariant(v.uuid, localItem.value.uuid);
    if (!res.ok) throw new Error(res.error);
    toast.success('Variante eliminada');
    await fetchVariants();
  } catch (e) {
    toast.error(e.message || 'Error al eliminar la variante');
  } finally {
    varLoading.value = false;
  }
}

async function duplicateVariant(v) {
  varLoading.value = true;
  try {
    const isFixed = v.pricing_strategy === 'FIXED';
    const res = await store.createVariant({
      service: localItem.value.uuid,
      pricing_strategy: v.pricing_strategy || 'FIXED',
      fixed_price: isFixed ? (cleanNum(v.fixed_price) || null) : null,
      estimated_hours: !isFixed ? (cleanNum(v.estimated_hours) || 1) : 1,
      complexity_factor: !isFixed ? (cleanNum(v.complexity_factor) || 1) : 1,
      min_duration: !isFixed ? cleanNum(v.min_duration) : null,
      max_duration: !isFixed ? cleanNum(v.max_duration) : null,
      simultaneous_capacity: v.simultaneous_capacity || 1,
      is_default: false,
      is_active: v.is_active !== false,
    });
    if (!res.ok) throw new Error(res.error);
    toast.success('Variante duplicada');
    await fetchVariants();
  } catch (e) {
    toast.error(e.message || 'Error al duplicar la variante');
  } finally {
    varLoading.value = false;
  }
}

async function viewPriceHistory(v) {
  selectedVariantForHistory.value = v;
  historyLoading.value = true;
  priceHistory.value = [];
  try {
    const data = await store.fetchVariantsPriceHistory(v.uuid);
    priceHistory.value = data;
  } catch {
    toast.error('Error al cargar el historial de precios');
    selectedVariantForHistory.value = null;
  } finally {
    historyLoading.value = false;
  }
}

function closePriceHistory() {
  selectedVariantForHistory.value = null;
  priceHistory.value = [];
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
const cleanNum = (val) => {
  if (val === '' || val === null || val === undefined) return null;
  if (typeof val === 'number' && Number.isNaN(val))   return null;
  return val;
};

const formatNum = (val) => {
  if (val == null || val === '') return '0';
  return formatCOP(val);
};

const formatDate = (val) => {
  if (!val) return '';
  return new Date(val).toLocaleString('es-CO', {
    year: 'numeric', month: 'short', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
};

onMounted(async () => {
  await Promise.all([catalogStore.fetchCategories(), catalogStore.fetchLevels()]);
});
</script>

<style scoped>
.smaller { font-size: 0.78rem; }
.btn-xs  { padding: 0.1rem 0.35rem; font-size: 0.75rem; line-height: 1.3; }
.object-fit-cover { object-fit: cover; }
.upload-zone { transition: border-color .2s, background .2s; }
.border-dashed { border-style: dashed !important; }

.timeline-container { position: relative; padding-left: 1rem; }
.timeline-item {
  position: relative;
  padding-bottom: 1.5rem;
  border-left: 2px dashed #e2e8f0;
  padding-left: 1.5rem;
}
.timeline-item:last-child { border-left: none; padding-bottom: 0; }
.timeline-marker {
  position: absolute; left: -6px; top: 4px;
  width: 10px; height: 10px;
  border-radius: 50%;
  background-color: #3b82f6;
  border: 2px solid #fff;
}
</style>
