<template>
  <div class="srw-root">

    <!-- ESTADO: LOADING -->
    <div v-if="loading" class="srw-loading">
      <div class="spinner-border text-violet" role="status"></div>
      <div class="text-muted small mt-2">Cargando servicio...</div>
    </div>

    <!-- ESTADO: ERROR -->
    <div v-else-if="!service" class="srw-empty">
      <p class="text-muted">No se encontro el servicio.</p>
      <RouterLink to="/servicios" class="btn btn-outline-secondary btn-sm">Volver</RouterLink>
    </div>

    <!-- ESTADO: ORDEN CREADA (pago en modal) -->
    <div v-else-if="orderCreated" class="srw-payment-screen">
      <div class="srw-payment-inner">
        <div class="text-center mb-4">
          <div class="srw-success-icon mx-auto mb-3">
            <i class="bi bi-check-lg text-white fs-2"></i>
          </div>
          <h2 class="fw-bold mb-1">Solicitud enviada</h2>
          <p class="text-muted">Completa el pago para confirmar tu solicitud de servicio.</p>
        </div>

        <div class="d-flex gap-2 justify-content-center flex-wrap mt-2">
          <RouterLink to="/mi-cuenta/pedidos" class="btn btn-outline-secondary btn-sm px-4">Ver mis pedidos</RouterLink>
          <RouterLink to="/servicios" class="btn btn-outline-secondary btn-sm px-4">Ver mas servicios</RouterLink>
        </div>
      </div>

      <ServiceCheckoutModal />
    </div>

    <!-- WIZARD -->
    <template v-else>

      <!-- Barra de progreso sticky -->
      <div class="srw-progress-bar-wrap">
        <div class="container-xl">
          <CheckoutStepper :steps="STEPS" :current="step" aria-label="Progreso de la solicitud de servicio" />
        </div>
      </div>

      <!-- PASO 1: Servicio -->
      <div v-if="step === 1" class="srw-step-screen">
        <div class="container-xl">
          <div class="srw-step-header">
            <RouterLink :to="`/servicios/${route.params.uuid}`" class="srw-back-link">
              <i class="bi bi-arrow-left me-1"></i> Volver al servicio
            </RouterLink>
            <h2 class="srw-step-title">{{ service.name }}</h2>
            <p class="srw-step-sub">Revisa los detalles y selecciona una opcion</p>
          </div>

          <div class="row g-4 justify-content-center">
            <!-- Selector de variante/paquete -- sin panel de info del servicio
                 (esa info ya se muestra en /servicios/{uuid}, un click atras via
                 "Volver al servicio"; duplicarla aqui era redundante). -->
            <div class="col-lg-8">
              <h5 class="fw-bold mb-3">Selecciona una opcion</h5>
              <div v-if="!service.variants?.length" class="alert alert-warning">No hay opciones disponibles.</div>
              <div v-else class="d-flex flex-column gap-3">
                <div
                  v-for="v in service.variants"
                  :key="v.uuid"
                  class="srw-variant-card"
                  :class="{ 'srw-variant-card--selected': selectedVariant?.uuid === v.uuid, 'srw-variant-card--disabled': !v.is_active }"
                  :role="v.is_active ? 'button' : undefined"
                  @click="v.is_active && (selectedVariant = v)"
                >
                  <div class="d-flex justify-content-between align-items-start mb-2">
                    <div>
                      <code class="text-muted small d-block mb-1">{{ v.sku }}</code>
                      <div class="d-flex gap-1 flex-wrap">
                        <span v-if="v.is_default" class="badge bg-warning text-dark">Estandar</span>
                        <span v-if="v.pricing_strategy === 'CONTRACTOR_RATES'" class="badge bg-primary">Profesional</span>
                      </div>
                    </div>
                    <div class="text-end">
                      <div v-if="v.pricing_strategy === 'CONTRACTOR_RATES'" class="fw-bold text-primary fs-5">A convenir</div>
                      <div v-else class="fw-bold text-violet fs-5">${{ fmt(v.price_info?.total ?? v.calculated_price) }}</div>
                      <div class="text-muted small">COP - IVA incl.</div>
                    </div>
                  </div>

                  <div v-if="v.pricing_strategy !== 'CONTRACTOR_RATES' && v.price_info" class="srw-price-breakdown mb-2">
                    <div class="d-flex justify-content-between"><span>Base</span><span>${{ fmt(v.price_info.base) }}</span></div>
                    <div class="d-flex justify-content-between"><span>IVA {{ v.price_info.iva_rate }}%</span><span>${{ fmt(v.price_info.iva_amount) }}</span></div>
                  </div>

                  <div class="text-muted small mb-2"><i class="bi bi-clock me-1"></i>{{ v.estimated_hours }} h estimadas</div>

                  <div v-if="v.materials?.length" class="srw-materials">
                    <div class="srw-mat-label">Incluye:</div>
                    <div v-for="m in v.materials" :key="m.product_variant_uuid" class="srw-mat-item">
                      <i class="bi bi-dot"></i>{{ m.product_name }}
                    </div>
                  </div>

                  <div v-if="!v.is_active" class="srw-unavailable">No disponible temporalmente</div>
                  <div v-if="selectedVariant?.uuid === v.uuid" class="srw-selected-check">
                    <i class="bi bi-check-circle-fill text-violet"></i> Seleccionado
                  </div>
                </div>
              </div>

              <div class="mt-4">
                <PackageSelector
                  :service-uuid="route.params.uuid"
                  :variant-uuid="selectedVariant?.uuid"
                  :initial-package-uuid="route.query.package || ''"
                  @packages-loaded="onPackagesLoaded"
                  @selection-change="onPackageSelectionChange"
                />
              </div>

              <div class="d-flex justify-content-end mt-4">
                <button class="btn btn-violet fw-bold px-5 py-3" :disabled="!selectedVariant" @click="step = 2">
                  Continuar <i class="bi bi-arrow-right ms-2"></i>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- PASO 2: Direccion -->
      <div v-if="step === 2" class="srw-step-screen">
        <div class="container-xl">
          <div class="srw-step-header">
            <h2 class="srw-step-title">Direccion y contacto</h2>
            <p class="srw-step-sub">Confirma donde se realizara el servicio y quien recibira al tecnico.</p>
          </div>

          <div class="row">
            <div class="col-lg-8">

              <!-- Card 1: Informacion Personal -->
              <div class="srw-card mb-4">
                <div class="srw-card-header">
                  <i class="bi bi-person-fill me-2 text-primary"></i>
                  <span>Informacion Personal</span>
                  <span class="badge bg-danger-subtle text-danger border-0 ms-auto small">Obligatorio</span>
                </div>
                <div class="srw-card-body">
                  <div class="row g-3">
                    <div class="col-12">
                      <label class="form-label fw-semibold">Nombre completo <span class="text-danger">*</span></label>
                      <input v-model="personal.full_name" type="text" class="form-control" :class="{ 'is-invalid': personalErrors.full_name }" placeholder="Nombre y apellidos">
                      <div class="invalid-feedback">{{ personalErrors.full_name }}</div>
                    </div>
                    <div class="col-sm-5">
                      <label class="form-label fw-semibold">Tipo de documento <span class="text-danger">*</span></label>
                      <select v-model="personal.document_type" class="form-select" :class="{ 'is-invalid': personalErrors.document_type }" @change="personal.document_number = ''">
                        <option value="">-- Selecciona --</option>
                        <option value="CC">Cedula de Ciudadania</option>
                        <option value="CE">Cedula de Extranjeria</option>
                        <option value="PP">Pasaporte</option>
                        <option value="TI">Tarjeta de Identidad</option>
                        <option value="NIT">NIT</option>
                        <option value="OTRO">Otro</option>
                      </select>
                      <div class="invalid-feedback">{{ personalErrors.document_type }}</div>
                    </div>
                    <div class="col-sm-7">
                      <label class="form-label fw-semibold">Numero de documento <span class="text-danger">*</span></label>
                      <input :value="personal.document_number" type="text" class="form-control" :class="{ 'is-invalid': personalErrors.document_number }" :placeholder="docPlaceholder" maxlength="20" @input="onDocInput">
                      <div class="invalid-feedback">{{ personalErrors.document_number }}</div>
                    </div>
                    <div class="col-sm-6">
                      <label class="form-label fw-semibold">Correo electronico <span class="text-danger">*</span></label>
                      <input v-model="personal.email" type="email" class="form-control" :class="{ 'is-invalid': personalErrors.email }" placeholder="correo@empresa.com">
                      <div class="invalid-feedback">{{ personalErrors.email }}</div>
                    </div>
                    <div class="col-sm-6">
                      <label class="form-label fw-semibold">Celular <span class="text-danger">*</span></label>
                      <input :value="personal.phone" type="tel" class="form-control" :class="{ 'is-invalid': personalErrors.phone }" placeholder="3001234567" inputmode="numeric" maxlength="10" @input="onPhoneInput">
                      <div class="invalid-feedback">{{ personalErrors.phone }}</div>
                    </div>
                    <div class="col-sm-6">
                      <label class="form-label fw-semibold">Empresa</label>
                      <input v-model="personal.company" type="text" class="form-control" placeholder="Nombre de la empresa (opcional)">
                    </div>
                    <div class="col-sm-6">
                      <label class="form-label fw-semibold">Cargo</label>
                      <input v-model="personal.cargo" type="text" class="form-control" placeholder="Cargo o funcion (opcional)">
                    </div>
                  </div>
                </div>
              </div>

              <!-- Card 2: Ubicacion -->
              <div class="srw-card mb-4">
                <div class="srw-card-header">
                  <i class="bi bi-geo-alt-fill me-2 text-danger"></i>
                  <span>Ubicacion</span>
                  <span class="badge bg-danger-subtle text-danger border-0 ms-auto small">Obligatorio</span>
                </div>
                <div class="srw-card-body">
                  <div class="row g-3">
                    <div class="col-sm-6">
                      <label class="form-label fw-semibold">Departamento <span class="text-danger">*</span></label>
                      <select v-model="location.department" class="form-select" :class="{ 'is-invalid': locationErrors.department }" @change="location.city = ''">
                        <option value="">-- Departamento --</option>
                        <option v-for="dep in departmentList" :key="dep" :value="dep">{{ dep }}</option>
                      </select>
                      <div class="invalid-feedback">{{ locationErrors.department }}</div>
                    </div>
                    <div class="col-sm-6">
                      <label class="form-label fw-semibold">Ciudad / Municipio <span class="text-danger">*</span></label>
                      <select v-model="location.city" class="form-select" :class="{ 'is-invalid': locationErrors.city }" :disabled="!location.department">
                        <option value="">{{ location.department ? '-- Ciudad --' : 'Elige departamento' }}</option>
                        <option v-for="c in citiesFor" :key="c" :value="c">{{ c }}</option>
                      </select>
                      <div class="invalid-feedback">{{ locationErrors.city }}</div>
                    </div>
                    <!-- Constructor de direccion -->
                    <div class="col-12">
                      <label class="form-label fw-semibold">Direccion <span class="text-danger">*</span></label>
                      <div class="srw-addr-builder">
                        <div class="row g-2 mb-2 align-items-center">
                          <div class="col-sm-3 col-6">
                            <select v-model="addr.via_type" class="form-select form-select-sm">
                              <option>Calle</option><option>Carrera</option><option>Avenida</option>
                              <option>Transversal</option><option>Diagonal</option><option>Circular</option>
                            </select>
                          </div>
                          <div class="col-sm-2 col-6">
                            <input v-model="addr.via_number" type="text" class="form-control form-control-sm" placeholder="85A">
                          </div>
                          <div class="col-auto"><span class="fw-bold fs-5 text-muted">#</span></div>
                          <div class="col-sm-2 col-5">
                            <input v-model="addr.generadora" type="text" class="form-control form-control-sm" placeholder="45">
                          </div>
                          <div class="col-auto"><span class="fw-bold fs-5 text-muted">-</span></div>
                          <div class="col-sm-2 col-5">
                            <input v-model="addr.placa" type="text" class="form-control form-control-sm" placeholder="20">
                          </div>
                        </div>
                        <div class="row g-2">
                          <div class="col-sm-7">
                            <input v-model="addr.complement" type="text" class="form-control form-control-sm" placeholder="Complemento: Apto, Piso, Local (opcional)">
                          </div>
                          <div class="col-sm-5">
                            <input v-model="addr.barrio" type="text" class="form-control form-control-sm" placeholder="Barrio (opcional)">
                          </div>
                        </div>
                        <div v-if="computedAddress" class="srw-addr-preview mt-2">
                          <span class="small text-muted me-1">Vista previa:</span>
                          <span class="small fw-semibold text-violet">{{ computedAddress }}</span>
                        </div>
                        <div v-else class="text-muted small mt-2">
                          <i class="bi bi-info-circle me-1"></i>Completa via, numero y placa para ver la direccion.
                        </div>
                        <div v-if="locationErrors.address" class="text-danger small mt-1">{{ locationErrors.address }}</div>
                      </div>
                    </div>
                    <div class="col-sm-8">
                      <label class="form-label fw-semibold">Punto de referencia</label>
                      <input v-model="location.reference" type="text" class="form-control" placeholder="Junto al parque, frente al banco, etc.">
                    </div>
                    <div class="col-sm-4">
                      <label class="form-label fw-semibold">Codigo postal</label>
                      <input v-model="location.postal_code" type="text" class="form-control" placeholder="Opcional" maxlength="10">
                    </div>
                    <div class="col-12">
                      <button type="button" class="btn btn-outline-secondary btn-sm" @click="tryGeolocation">
                        <i class="bi bi-crosshair me-1"></i>Usar mi ubicacion
                      </button>
                      <span v-if="geoStatus" class="ms-2 small text-muted">{{ geoStatus }}</span>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Card 3: Notas opcionales -->
              <div class="srw-card mb-4">
                <div class="srw-card-header">
                  <i class="bi bi-clipboard-fill me-2 text-violet"></i>
                  <span>Notas para el tecnico</span>
                  <span class="badge bg-secondary-subtle text-secondary border-0 ms-auto small">Opcional</span>
                </div>
                <div class="srw-card-body">
                  <div class="row g-3">
                    <div class="col-12">
                      <label class="form-label fw-semibold">Indicaciones o contexto</label>
                      <textarea v-model="serviceInfo.description" class="form-control" rows="3" placeholder="Ej: equipo instalado, marca, acceso, horarios internos o detalles utiles..." maxlength="2000"></textarea>
                      <div class="d-flex justify-content-between mt-1">
                        <span class="text-muted" style="font-size:.7rem">{{ serviceInfo.description.length }}/2000</span>
                      </div>
                    </div>
                    <div class="col-12">
                      <label class="form-label fw-semibold">Problema o necesidad especifica</label>
                      <textarea v-model="serviceInfo.problem" class="form-control" rows="2" placeholder="Opcional: falla, objetivo o resultado esperado..." maxlength="1000"></textarea>
                    </div>
                    <div class="col-sm-6">
                      <label class="form-label fw-semibold">Desde cuando ocurre?</label>
                      <input v-model="serviceInfo.since_when" type="text" class="form-control" placeholder="Ej: hace 2 semanas, desde el lunes...">
                    </div>
                    <div class="col-sm-6">
                      <label class="form-label fw-semibold">Nivel de urgencia <span class="text-danger">*</span></label>
                      <div class="d-flex gap-2 mt-1">
                        <div v-for="u in URGENCY_OPTIONS" :key="u.value" class="srw-urgency-pill" :class="['srw-urgency-pill--' + u.value.toLowerCase(), serviceInfo.urgency === u.value ? 'srw-urgency-pill--active' : '']" role="button" @click="serviceInfo.urgency = u.value">
                          {{ u.label }}
                        </div>
                      </div>
                    </div>
                    <div class="col-12">
                      <label class="form-label fw-semibold">Adjuntos</label>
                      <div class="text-muted small mb-2">Fotografias, planos, manuales, videos - hasta 10 archivos / 100 MB total</div>
                      <ServiceAttachmentsUploader v-model="attachments" />
                    </div>
                  </div>
                </div>
              </div>

              <div class="d-flex justify-content-between mt-2">
                <button class="btn btn-outline-secondary" @click="step = 1">
                  <i class="bi bi-arrow-left me-1"></i> Atras
                </button>
                <button class="btn btn-violet fw-bold px-5 py-3" @click="validateStep2AndContinue">
                  Continuar <i class="bi bi-arrow-right ms-2"></i>
                </button>
              </div>
            </div>
            <div class="col-lg-4 d-none d-lg-block">
              <ServiceRequestSummary
                :service-name="service.name"
                :variant="selectedVariant"
                :pkg="selectedPackageState.package"
                :price-info="summaryPriceInfo"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- PASO 3: Programacion -->
      <div v-if="step === 3" class="srw-step-screen">
        <div class="container-xl">
          <div class="srw-step-header">
            <h2 class="srw-step-title">Fecha y jornada</h2>
            <p class="srw-step-sub">Elige cuando prefieres recibir el servicio. La asignacion tecnica ocurre en segundo plano.</p>
          </div>

          <div class="row">
            <div class="col-lg-8">

              <div class="srw-card mb-4">
                <div class="srw-card-header">
                  <i class="bi bi-calendar-check-fill me-2 text-primary"></i>
                  <span>Fecha y jornada preferida</span>
                  <span class="badge bg-danger-subtle text-danger border-0 ms-auto small">Obligatorio</span>
                </div>
                <div class="srw-card-body">
                  <label class="form-label fw-semibold">Fecha preferida <span class="text-danger">*</span></label>
                  <input v-model="scheduling.preferred_date" type="date" class="form-control mb-3" :class="{ 'is-invalid': schedErrors.preferred_date }" :min="minDate">
                  <div class="invalid-feedback d-block mt-n2 mb-3">{{ schedErrors.preferred_date }}</div>

                  <label class="form-label fw-semibold">Jornada <span class="text-danger">*</span></label>
                  <div class="d-flex flex-wrap gap-2">
                    <div
                      v-for="j in JORNADA_OPTIONS"
                      :key="j.value"
                      class="srw-jornada-pill"
                      :class="{ 'srw-jornada-pill--active': scheduling.jornada === j.value }"
                      role="button"
                      @click="scheduling.jornada = j.value"
                    >
                      <div class="fw-semibold">{{ j.label }}</div>
                      <div class="small text-muted">{{ j.hint }}</div>
                    </div>
                  </div>

                  <div class="srw-schedule-info mt-3">
                    <i class="bi bi-info-circle-fill text-primary me-2 flex-shrink-0"></i>
                    <div class="small">
                      <strong>Fecha y jornada como preferencia.</strong> Nuestro equipo asignara tecnico y hora exacta segun disponibilidad dentro de esa jornada. Recibiras una notificacion cuando el servicio sea confirmado.
                    </div>
                  </div>
                </div>
              </div>

              <div class="srw-card mb-4">
                <div class="srw-card-header">
                  <i class="bi bi-telephone-fill me-2 text-success"></i>
                  <span>Contacto durante la visita</span>
                </div>
                <div class="srw-card-body">
                  <p class="text-muted small mb-3">Persona que estara presente o disponible durante la ejecucion del servicio.</p>
                  <div class="row g-3">
                    <div class="col-sm-6">
                      <label class="form-label fw-semibold">Nombre <span class="text-danger">*</span></label>
                      <input v-model="scheduling.visit_name" type="text" class="form-control" :class="{ 'is-invalid': schedErrors.visit_name }" placeholder="Nombre del contacto">
                      <div class="invalid-feedback">{{ schedErrors.visit_name }}</div>
                    </div>
                    <div class="col-sm-6">
                      <label class="form-label fw-semibold">Cargo <span class="text-danger">*</span></label>
                      <input v-model="scheduling.visit_cargo" type="text" class="form-control" :class="{ 'is-invalid': schedErrors.visit_cargo }" placeholder="Cargo o rol">
                      <div class="invalid-feedback">{{ schedErrors.visit_cargo }}</div>
                    </div>
                    <div class="col-sm-6">
                      <label class="form-label fw-semibold">Celular <span class="text-danger">*</span></label>
                      <input :value="scheduling.visit_phone" type="tel" class="form-control" :class="{ 'is-invalid': schedErrors.visit_phone }" placeholder="3001234567" inputmode="numeric" maxlength="10" @input="onVisitPhoneInput">
                      <div class="invalid-feedback">{{ schedErrors.visit_phone }}</div>
                    </div>
                    <div class="col-sm-6">
                      <label class="form-label fw-semibold">Correo</label>
                      <input v-model="scheduling.visit_email" type="email" class="form-control" placeholder="correo@empresa.com (opcional)">
                    </div>
                  </div>
                </div>
              </div>

              <div class="srw-card mb-4">
                <div class="srw-card-header">
                  <i class="bi bi-door-open-fill me-2 text-secondary"></i>
                  <span>Acceso e indicaciones</span>
                </div>
                <div class="srw-card-body">
                  <label class="form-label fw-semibold">Indicaciones para ingresar</label>
                  <textarea v-model="scheduling.access_notes" class="form-control" rows="3" placeholder="Porteria, piso, torre, parqueadero, permisos especiales, protocolo de seguridad..."></textarea>
                  <div class="form-check mt-3">
                    <input v-model="scheduling.allow_schedule_changes" type="checkbox" class="form-check-input" id="allowSchedule">
                    <label class="form-check-label small" for="allowSchedule">
                      Acepto recibir propuestas de horarios alternativos si no hay disponibilidad en mi fecha preferida
                    </label>
                  </div>
                </div>
              </div>

              <div class="d-flex justify-content-between mt-2">
                <button class="btn btn-outline-secondary" @click="step = 2">
                  <i class="bi bi-arrow-left me-1"></i> Atras
                </button>
                <button class="btn btn-violet fw-bold px-5 py-3" @click="validateStep3AndContinue">
                  Continuar al pago <i class="bi bi-arrow-right ms-2"></i>
                </button>
              </div>
            </div>
            <div class="col-lg-4 d-none d-lg-block">
              <ServiceRequestSummary
                :service-name="service.name"
                :variant="selectedVariant"
                :pkg="selectedPackageState.package"
                :price-info="summaryPriceInfo"
                :schedule-label="scheduleSummaryLabel"
              />
            </div>
          </div>
        </div>
      </div>

      <!-- PASO 4: Pago -->
      <div v-if="step === 4" class="srw-step-screen">
        <div class="container-xl">
          <div class="srw-step-header">
            <h2 class="srw-step-title">Confirmar y pagar</h2>
            <p class="srw-step-sub">Revisa el resumen y completa el pago para reservar la programacion.</p>
          </div>

          <div class="row justify-content-center">
            <div class="col-lg-8">

              <div class="srw-card mb-3">
                <div class="srw-card-header">
                  <i class="bi bi-tools me-2 text-violet"></i>
                  <span>Servicio</span>
                  <button class="btn btn-link btn-sm p-0 ms-auto text-violet" @click="step = 1">Editar</button>
                </div>
                <div class="srw-card-body">
                  <div class="d-flex justify-content-between align-items-center">
                    <div>
                      <div class="fw-bold">{{ service.name }}</div>
                      <code class="text-muted small">{{ selectedVariant?.sku }}</code>
                    </div>
                    <div class="text-end">
                      <div v-if="selectedVariant?.pricing_strategy === 'CONTRACTOR_RATES'" class="fw-bold text-primary fs-5">A convenir</div>
                      <div v-else class="fw-bold text-violet fs-5">${{ fmt(selectedVariant?.price_info?.total ?? selectedVariant?.calculated_price) }}</div>
                      <div class="text-muted small">{{ selectedVariant?.estimated_hours }} h - IVA incl.</div>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="selectedPackageState.package" class="srw-card mb-3">
                <div class="srw-card-header">
                  <i class="bi bi-box-seam-fill me-2 text-violet"></i>
                  <span>Paquete</span>
                  <button class="btn btn-link btn-sm p-0 ms-auto text-violet" @click="step = 1">Editar</button>
                </div>
                <div class="srw-card-body">
                  <PackageSummary :pkg="selectedPackageState.package" :selected-costs="selectedPackageState.additionalCosts" />
                  <PackageCostBreakdown v-if="selectedPackageState.breakdown" :breakdown="selectedPackageState.breakdown" class="mt-3" />
                </div>
              </div>

              <div class="srw-card mb-3">
                <div class="srw-card-header">
                  <i class="bi bi-person-fill me-2 text-primary"></i>
                  <span>Datos Personales</span>
                  <button class="btn btn-link btn-sm p-0 ms-auto text-violet" @click="step = 2">Editar</button>
                </div>
                <div class="srw-card-body">
                  <div class="row g-1">
                    <div class="col-4 text-muted small">Nombre</div><div class="col-8 small fw-semibold">{{ personal.full_name }}</div>
                    <div class="col-4 text-muted small">Documento</div><div class="col-8 small">{{ personal.document_type }} {{ personal.document_number }}</div>
                    <div class="col-4 text-muted small">Correo</div><div class="col-8 small">{{ personal.email }}</div>
                    <div class="col-4 text-muted small">Celular</div><div class="col-8 small">{{ personal.phone }}</div>
                    <template v-if="personal.company">
                      <div class="col-4 text-muted small">Empresa</div><div class="col-8 small">{{ personal.company }}<span v-if="personal.cargo"> - {{ personal.cargo }}</span></div>
                    </template>
                  </div>
                </div>
              </div>

              <div class="srw-card mb-3">
                <div class="srw-card-header">
                  <i class="bi bi-geo-alt-fill me-2 text-danger"></i>
                  <span>Ubicacion</span>
                  <button class="btn btn-link btn-sm p-0 ms-auto text-violet" @click="step = 2">Editar</button>
                </div>
                <div class="srw-card-body">
                  <div class="fw-semibold small">{{ computedAddress }}</div>
                  <div class="text-muted small mt-1">{{ location.city }}, {{ location.department }}</div>
                  <div v-if="location.reference" class="text-muted small mt-1"><i class="bi bi-pin-map me-1"></i>{{ location.reference }}</div>
                </div>
              </div>

              <div class="srw-card mb-3">
                <div class="srw-card-header">
                  <i class="bi bi-calendar-check-fill me-2 text-primary"></i>
                  <span>Programacion</span>
                  <button class="btn btn-link btn-sm p-0 ms-auto text-violet" @click="step = 3">Editar</button>
                </div>
                <div class="srw-card-body">
                  <div class="row g-1">
                    <div class="col-4 text-muted small">Fecha preferida</div><div class="col-8 small fw-semibold">{{ fmtDate(scheduling.preferred_date) }}</div>
                    <div class="col-4 text-muted small">Jornada</div><div class="col-8 small fw-semibold">{{ jornadaLabel }}</div>
                    <div class="col-4 text-muted small">Contacto visita</div><div class="col-8 small">{{ scheduling.visit_name }} - {{ scheduling.visit_phone }}</div>
                    <template v-if="scheduling.access_notes">
                      <div class="col-4 text-muted small">Acceso</div>
                      <div class="col-8 small text-muted" style="white-space:pre-line">{{ scheduling.access_notes }}</div>
                    </template>
                  </div>
                </div>
              </div>

              <div v-if="attachments.length" class="srw-card mb-3">
                <div class="srw-card-header">
                  <i class="bi bi-paperclip me-2 text-secondary"></i>
                  <span>Adjuntos</span>
                  <span class="badge bg-secondary-subtle text-secondary ms-auto">{{ attachments.length }}</span>
                  <button class="btn btn-link btn-sm p-0 ms-2 text-violet" @click="step = 2">Editar</button>
                </div>
                <div class="srw-card-body">
                  <div class="d-flex flex-wrap gap-2">
                    <div v-for="entry in attachments" :key="entry.id" class="srw-thumb-mini" :title="entry.file.name">
                      <img v-if="entry.preview" :src="entry.preview" class="srw-thumb-mini-img" />
                      <i v-else :class="fileIcon(entry.file)" class="srw-thumb-mini-icon"></i>
                    </div>
                  </div>
                </div>
              </div>

              <div v-if="serviceInfo.description || serviceInfo.problem" class="srw-card mb-4">
                <div class="srw-card-header">
                  <i class="bi bi-clipboard-fill me-2 text-violet"></i>
                  <span>Notas para el tecnico</span>
                  <button class="btn btn-link btn-sm p-0 ms-auto text-violet" @click="step = 2">Editar</button>
                </div>
                <div class="srw-card-body">
                  <div class="d-flex align-items-center gap-2 mb-2">
                    <span class="badge" :class="urgencyBadgeClass">{{ urgencyLabel }}</span>
                  </div>
                  <p class="small text-dark mb-1" style="white-space:pre-line">{{ serviceInfo.description }}</p>
                  <p class="small text-muted mb-0" v-if="serviceInfo.problem"><strong>Problema:</strong> {{ serviceInfo.problem }}</p>
                </div>
              </div>

              <div class="srw-process-notice mb-4">
                <i class="bi bi-info-circle-fill text-primary me-2 flex-shrink-0 mt-1"></i>
                <div class="small text-muted">
                  <strong class="text-dark">Despues del pago:</strong> {{ brandName }} confirma disponibilidad, asigna el tecnico y te notifica la programacion definitiva. Si no hay cupo en tu jornada preferida, recibiras alternativas.
                </div>
              </div>

              <div v-if="!authStore.isAuthenticated" class="alert alert-warning mb-3">
                <i class="bi bi-exclamation-triangle me-2"></i>
                Debes iniciar sesion para enviar la solicitud.
                <RouterLink to="/login" class="alert-link ms-2">Iniciar sesion</RouterLink>
              </div>

              <div class="mb-3">
                <ServiceTermsCard v-model="termsAccepted" />
              </div>

              <div class="d-flex justify-content-between mt-2">
                <button class="btn btn-outline-secondary" @click="step = 3">
                  <i class="bi bi-arrow-left me-1"></i> Atras
                </button>
                <button
                  class="btn btn-violet fw-bold px-5 py-3 fs-5"
                  :disabled="submitting || !authStore.isAuthenticated || !termsAccepted"
                  @click="submitRequest"
                >
                  <span v-if="submitting" class="spinner-border spinner-border-sm me-2"></span>
                  <i v-else class="bi bi-credit-card me-2"></i>
                  {{ submitting ? 'Preparando pago...' : 'Confirmar y pagar' }}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

    </template>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue';
import { isValidEmail } from '@/utils/validators';
import { useRoute, RouterLink } from 'vue-router';
import { servicesService } from '@/services/technical_services/servicesService';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useAuthStore } from '@/store/auth';
import { useAppConfigStore } from '@/store/appConfig';
import { formatCOP } from '@/utils/money';
import ServiceAttachmentsUploader from '@/components/services/ServiceAttachmentsUploader.vue';
import ServiceTermsCard from '@/components/customer/services/ServiceTermsCard.vue';
import ServiceCheckoutModal from '@/components/customer/services/ServiceCheckoutModal.vue';
import { useServiceCheckoutStore } from '@/store/services/serviceCheckoutStore';
import PackageSelector from '@/components/services/packages/PackageSelector.vue';
import PackageSummary from '@/components/services/packages/PackageSummary.vue';
import PackageCostBreakdown from '@/components/services/packages/PackageCostBreakdown.vue';
import CheckoutStepper from '@/components/shared/checkout/CheckoutStepper.vue';
import ServiceRequestSummary from '@/components/customer/services/ServiceRequestSummary.vue';
import { COLOMBIA_LOCATIONS } from '@/data/colombiaLocations';

const route     = useRoute();
const toast     = useToast();
const { handleError } = useErrorHandler();
const authStore = useAuthStore();
// White-label F7 (2026-08-14): antes 'Sintel' hardcodeado en el texto de "Despues del pago".
const appConfigStore = useAppConfigStore();
const brandName = computed(() => appConfigStore.brand.site_name || 'la plataforma');
const checkoutStore = useServiceCheckoutStore();

// Estado global
const loading      = ref(true);
const service      = ref(null);
const step         = ref(1);
const submitting   = ref(false);
const orderCreated = ref(false);
const createdOrder = ref(null);
const selectedVariant = ref(null);

// Paso 1 - paquete (opcional; solo aplica si el servicio tiene paquetes configurados)
const selectedPackageState = reactive({ package: null, additionalCosts: [], breakdown: null });
function onPackagesLoaded() { /* no-op: PackageSelector maneja su propio estado de visibilidad */ }
function onPackageSelectionChange(payload) {
  selectedPackageState.package = payload.package;
  selectedPackageState.additionalCosts = payload.additionalCosts;
  selectedPackageState.breakdown = payload.breakdown;
}

const STEPS = ['Servicio', 'Direccion', 'Fecha', 'Pago'];
const termsAccepted = ref(false);

// Paso 2 - personal
const personal = reactive({ full_name: '', document_type: '', document_number: '', email: '', phone: '', company: '', cargo: '' });
const personalErrors = reactive({ full_name: '', document_type: '', document_number: '', email: '', phone: '' });

// Paso 2 - ubicacion
const location  = reactive({ department: '', city: '', reference: '', postal_code: '' });
const addr      = reactive({ via_type: 'Calle', via_number: '', generadora: '', placa: '', complement: '', barrio: '' });
const locationErrors = reactive({ department: '', city: '', address: '' });
const geoStatus = ref('');

// Paso 2 - notas opcionales para el tecnico
const serviceInfo = reactive({ description: '', problem: '', since_when: '', urgency: 'NORMAL' });

// Paso 2 - adjuntos
const attachments = ref([]);

// Paso 3 - programacion
// Jornada en vez de hora exacta (Fase 5, 2026-07-14): el sistema busca tecnico
// y horario dentro de la jornada elegida -- el cliente ya no negocia una hora
// puntual. preferred_time se sigue enviando al backend (campo ya existente,
// sin cambios de API) como la hora de inicio representativa de la jornada.
const scheduling = reactive({
  preferred_date: '', jornada: 'MANANA',
  visit_name: '', visit_cargo: '', visit_phone: '', visit_email: '',
  access_notes: '', allow_schedule_changes: true,
});
const schedErrors = reactive({ preferred_date: '', visit_name: '', visit_cargo: '', visit_phone: '' });

const JORNADA_OPTIONS = [
  { value: 'MANANA',      label: 'Mañana',      hint: '7:00 am - 12:00 m',  time: '07:00' },
  { value: 'TARDE',       label: 'Tarde',        hint: '12:00 m - 6:00 pm',  time: '13:00' },
  { value: 'TODO_EL_DIA', label: 'Todo el día',  hint: '7:00 am - 6:00 pm',  time: '07:00' },
];
const jornadaLabel = computed(() => JORNADA_OPTIONS.find((j) => j.value === scheduling.jornada)?.label || '');

// Sidebar de resumen persistente (pasos 2-3, Fase 5 del plan de unificacion con
// Renting -- equivalente a RentalCostsCard+AvailabilityPill). Prioriza el
// desglose del paquete (si se eligio uno) sobre el de la variante sola.
const summaryPriceInfo = computed(() => selectedPackageState.breakdown || selectedVariant.value?.price_info || null);
const scheduleSummaryLabel = computed(() => {
  if (!scheduling.preferred_date) return '';
  return `${fmtDate(scheduling.preferred_date)} - ${jornadaLabel.value}`;
});

const URGENCY_OPTIONS = [
  { value: 'NORMAL',  label: 'Normal' },
  { value: 'ALTA',    label: 'Alta' },
  { value: 'CRITICA', label: 'Critica' },
];

// Computadas
const departmentList = computed(() => Object.keys(COLOMBIA_LOCATIONS).sort((a, b) => a.localeCompare(b)));
const citiesFor = computed(() => location.department ? (COLOMBIA_LOCATIONS[location.department] || []).sort((a, b) => a.localeCompare(b)) : []);

const computedAddress = computed(() => {
  const n = addr.via_number.trim();
  const g = addr.generadora.trim();
  const p = addr.placa.trim();
  if (!n || !g || !p) return '';
  const street = `${addr.via_type} ${n} # ${g} - ${p}`;
  const extra  = [addr.complement.trim(), addr.barrio.trim()].filter(Boolean).join(', ');
  return extra ? `${street}, ${extra}` : street;
});

const minDate = computed(() => {
  const d = new Date();
  d.setDate(d.getDate() + 1);
  return d.toISOString().split('T')[0];
});

const urgencyLabel = computed(() => ({ NORMAL: 'Normal', ALTA: 'Alta', CRITICA: 'Critica' }[serviceInfo.urgency] || 'Normal'));
const urgencyBadgeClass = computed(() => ({ NORMAL: 'bg-secondary', ALTA: 'bg-warning text-dark', CRITICA: 'bg-danger' }[serviceInfo.urgency]));

const docPlaceholder = computed(() => {
  const m = { CC: '1234567890', NIT: '900123456', CE: '123456789', TI: '1234567890', PP: 'AB123456' };
  return m[personal.document_type] || 'Numero de identificacion';
});

// Handlers de input
function onPhoneInput(e) { personal.phone = e.target.value.replace(/\D/g, '').slice(0, 10); }
function onVisitPhoneInput(e) { scheduling.visit_phone = e.target.value.replace(/\D/g, '').slice(0, 10); }
function onDocInput(e) {
  const numericTypes = ['CC', 'NIT', 'CE', 'TI'];
  personal.document_number = numericTypes.includes(personal.document_type)
    ? e.target.value.replace(/\D/g, '').slice(0, 20)
    : e.target.value.slice(0, 20);
}

// Geolocalizacion
function tryGeolocation() {
  if (!navigator.geolocation) { geoStatus.value = 'No soportado en este dispositivo.'; return; }
  geoStatus.value = 'Obteniendo ubicacion...';
  navigator.geolocation.getCurrentPosition(
    (pos) => { geoStatus.value = `Lat ${pos.coords.latitude.toFixed(5)}, Lon ${pos.coords.longitude.toFixed(5)} (completa la direccion manualmente)`; },
    () => { geoStatus.value = 'No se pudo obtener la ubicacion.'; },
  );
}

// Validaciones
function validateStep2() {
  let ok = true;
  personalErrors.full_name      = personal.full_name.trim()      ? '' : 'Requerido';
  personalErrors.document_type  = personal.document_type          ? '' : 'Requerido';
  personalErrors.document_number = personal.document_number.trim() ? '' : 'Requerido';
  personalErrors.email = isValidEmail(personal.email) ? '' : 'Correo invalido';
  personalErrors.phone = /^\d{10}$/.test(personal.phone) ? '' : 'Debe tener 10 digitos';
  if (Object.values(personalErrors).some(Boolean)) ok = false;
  locationErrors.department = location.department ? '' : 'Requerido';
  locationErrors.city       = location.city       ? '' : 'Requerido';
  locationErrors.address    = computedAddress.value ? '' : 'Completa la nomenclatura (via, numero y placa)';
  if (Object.values(locationErrors).some(Boolean)) ok = false;
  return ok;
}

function validateStep3() {
  let ok = true;
  schedErrors.preferred_date = scheduling.preferred_date ? '' : 'Requerido';
  // jornada siempre tiene un valor por defecto (pill-selector) -- no requiere validacion.
  schedErrors.visit_name     = scheduling.visit_name.trim()  ? '' : 'Requerido';
  schedErrors.visit_cargo    = scheduling.visit_cargo.trim() ? '' : 'Requerido';
  schedErrors.visit_phone    = /^\d{10}$/.test(scheduling.visit_phone) ? '' : 'Debe tener 10 digitos';
  if (Object.values(schedErrors).some(Boolean)) ok = false;
  return ok;
}

function validateStep2AndContinue() {
  if (!validateStep2()) { toast.error('Revisa los campos marcados en rojo.'); return; }
  step.value = 3;
}

function validateStep3AndContinue() {
  if (!validateStep3()) { toast.error('Revisa los campos marcados en rojo.'); return; }
  step.value = 4;
}

// Helpers
const fmt = (v) => formatCOP(Math.round(parseFloat(v) || 0));

function fmtDate(val) {
  if (!val) return '';
  const [y, m, d] = val.split('-');
  return `${d}/${m}/${y}`;
}

function fileIcon(f) {
  if (f.type.startsWith('image/'))  return 'bi bi-file-earmark-image text-primary';
  if (f.type === 'application/pdf') return 'bi bi-file-earmark-pdf text-danger';
  if (f.type.includes('word'))      return 'bi bi-file-earmark-word text-primary';
  if (f.type.includes('excel') || f.type.includes('spreadsheet')) return 'bi bi-file-earmark-excel text-success';
  if (f.type.startsWith('video/'))  return 'bi bi-file-earmark-play text-warning';
  return 'bi bi-file-earmark text-secondary';
}

// Carga del servicio
async function fetchService() {
  loading.value = true;
  try {
    const [serviceData, packagesData] = await Promise.all([
      servicesService.detail(route.params.uuid),
      servicesService.packages(route.params.uuid).catch(() => []),
    ]);
    service.value = serviceData;
    const variantUuid = route.query.variant;
    if (variantUuid) {
      selectedVariant.value = service.value.variants?.find(v => v.uuid === variantUuid) || null;
    } else if (service.value.variants?.length === 1) {
      selectedVariant.value = service.value.variants[0];
    } else {
      selectedVariant.value = service.value.variants?.find(v => v.is_default) || null;
    }

    // Paso 1 ("Servicio") solo tiene una decision real que tomar si existe mas
    // de una variante activa o al menos un paquete comercial disponible -- de
    // lo contrario es pura informacion duplicada de /servicios/{uuid} (bug
    // real reportado por el usuario 2026-07-18). Si no hay nada que elegir,
    // se salta directo al paso 2 con la variante ya auto-seleccionada arriba.
    const activeVariants = (service.value.variants || []).filter(v => v.is_active);
    const needsChoice = activeVariants.length > 1 || packagesData.length > 0;
    if (!needsChoice && selectedVariant.value) {
      step.value = 2;
    }
  } catch {
    toast.error('Error al cargar el servicio.');
  } finally {
    loading.value = false;
  }
}

// Envio de solicitud
async function submitRequest() {
  if (!authStore.isAuthenticated) { toast.error('Inicia sesion.'); return; }

  const combinedDescription = [
    serviceInfo.description.trim() || `Solicitud de ${service.value?.name || 'servicio tecnico'}.`,
    serviceInfo.problem.trim() ? `\nProblema: ${serviceInfo.problem.trim()}` : '',
    serviceInfo.since_when.trim() ? `Desde cuando: ${serviceInfo.since_when.trim()}` : '',
  ].filter(Boolean).join('\n');

  const fullAddress = computedAddress.value
    ? `${computedAddress.value}, ${location.city}, ${location.department}`
    : '';

  const urgencyToPriority = { NORMAL: 'low', ALTA: 'high', CRITICA: 'critical' };

  const visitContactNote = scheduling.visit_name
    ? `Contacto visita: ${scheduling.visit_name} (${scheduling.visit_cargo}) - ${scheduling.visit_phone}${scheduling.visit_email ? ' - ' + scheduling.visit_email : ''}`
    : '';

  // Jornada (Fase 5): se envia como preferred_time (campo ya existente en el
  // backend, sin cambios de API) usando la hora de inicio representativa de la
  // jornada elegida, mas una nota legible para el admin que revise la solicitud.
  const jornadaOption = JORNADA_OPTIONS.find((j) => j.value === scheduling.jornada);
  const jornadaNote = jornadaOption ? `Jornada preferida: ${jornadaOption.label} (${jornadaOption.hint})` : '';

  const payload = {
    variant_uuid:           selectedVariant.value.uuid,
    quantity:               1,
    priority:               urgencyToPriority[serviceInfo.urgency] || 'medium',
    description:            combinedDescription,
    address:                fullAddress,
    preferred_date:         scheduling.preferred_date || null,
    preferred_time:         jornadaOption?.time || null,
    neighborhood:           addr.barrio.trim(),
    location_reference:     [location.reference.trim(), visitContactNote].filter(Boolean).join('\n'),
    service_notes:          [jornadaNote, scheduling.access_notes.trim()].filter(Boolean).join('\n'),
    allow_schedule_changes: scheduling.allow_schedule_changes,
    contact_person: {
      full_name:       personal.full_name.trim(),
      document_type:   personal.document_type,
      document_number: personal.document_number.trim(),
      email:           personal.email.trim(),
      phone:           personal.phone.trim(),
      company:         personal.company.trim(),
      cargo:           personal.cargo.trim() || scheduling.visit_cargo.trim() || '',
      phone_alt:       scheduling.visit_phone,
      access_notes:    scheduling.access_notes.trim(),
    },
  };

  if (selectedPackageState.package) {
    payload.package_uuid = selectedPackageState.package.uuid;
    payload.additional_costs = selectedPackageState.additionalCosts.map((entry) => ({
      additional_cost_uuid: entry.cost.uuid,
      quantity: entry.quantity,
    }));
  }

  submitting.value = true;
  try {
    const data = await servicesService.createOrder(payload);
    createdOrder.value = data;
    await uploadAttachments(data.uuid);
    orderCreated.value = true;
    checkoutStore.openFor({
      order:          data,
      serviceName:    service.value?.name,
      variantSku:     selectedVariant.value?.sku,
      priceInfo:      selectedVariant.value?.price_info,
      technicianName: '',
      durationHours:  selectedVariant.value?.estimated_hours,
    });
  } catch (err) {
    handleError(err, 'Error al enviar la solicitud.');
  } finally {
    submitting.value = false;
  }
}

async function uploadAttachments(orderUuid) {
  if (!attachments.value.length) return;
  const failed = [];
  for (const entry of attachments.value) {
    try {
      await servicesService.uploadAttachment(orderUuid, entry.file, entry.doc_type);
    } catch {
      failed.push(entry.file.name);
    }
  }
  if (failed.length) toast.error(`No se pudieron subir: ${failed.join(', ')}`);
}


// Precarga Informacion Personal desde el perfil ya autenticado -- antes el
// cliente reescribia nombre/correo/celular a mano en cada solicitud pese a
// tener sesion iniciada. Solo rellena campos que esten vacios, para no pisar
// nada si el usuario ya empezo a escribir (ej. volviendo de un paso anterior).
function prefillPersonalFromProfile() {
  const user = authStore.user;
  if (!user) return;
  if (!personal.full_name) personal.full_name = authStore.fullName || '';
  if (!personal.email) personal.email = user.email || '';
  if (!personal.phone) personal.phone = (user.phone_number || '').replace(/\D/g, '').slice(-10);
}

onMounted(() => {
  fetchService();
  prefillPersonalFromProfile();
});
</script>

<style scoped>
/* Root */
.srw-root { min-height: 100vh; background: #f9fafb; }

/* Loading / empty */
.srw-loading,
.srw-empty {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; min-height: 60vh; gap: 8px;
}

/* Pantalla de pago */
.srw-payment-screen { display: flex; justify-content: center; padding: 40px 16px; }
.srw-payment-inner  { width: 100%; max-width: 520px; }
.srw-success-icon {
  width: 72px; height: 72px; background: #16a34a; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  box-shadow: 0 4px 16px rgba(22,163,74,.3);
}

/* Barra de progreso */
.srw-progress-bar-wrap {
  background: #fff; border-bottom: 1px solid #e5e7eb;
  padding: 14px 0; position: sticky; top: 0; z-index: 100;
  box-shadow: 0 2px 8px rgba(0,0,0,.04);
}

/* Pantalla de paso */
.srw-step-screen { padding: 40px 16px 80px; }
.srw-step-header { margin-bottom: 32px; }
.srw-back-link { color: #6b7280; text-decoration: none; font-size: .88rem; display: inline-flex; align-items: center; gap: 4px; margin-bottom: 12px; }
.srw-back-link:hover { color: #374151; }
.srw-step-title { font-size: 1.75rem; font-weight: 800; color: #111827; margin-bottom: 6px; }
.srw-step-sub   { color: #6b7280; font-size: .95rem; margin: 0; }

/* Tarjeta de servicio (paso 1) */
.srw-service-card { border-radius: 14px; overflow: hidden; box-shadow: 0 4px 16px rgba(0,0,0,.07); border: 1px solid #e5e7eb; background: #fff; }
.srw-svc-img-wrap { height: 200px; overflow: hidden; }
.srw-svc-img { width: 100%; height: 100%; object-fit: cover; }
.srw-svc-img-placeholder { width: 100%; height: 100%; background: #f3f4f6; display: flex; align-items: center; justify-content: center; }
.srw-svc-desc { color: #374151; font-size: .9rem; line-height: 1.6; }
.srw-svc-features { display: flex; flex-direction: column; gap: 8px; }
.srw-svc-feat { display: flex; align-items: center; gap: 8px; font-size: .88rem; color: #374151; }

/* Variantes (paso 1) */
.srw-variant-card {
  background: #fff; border: 2px solid #e5e7eb; border-radius: 12px;
  padding: 16px; cursor: pointer; transition: all .18s;
}
.srw-variant-card:hover { border-color: #c4b5fd; background: #faf5ff; }
.srw-variant-card--selected { border-color: #7c3aed !important; background: #f5f3ff; box-shadow: 0 0 0 3px rgba(124,58,237,.15); }
.srw-variant-card--disabled { opacity: .5; cursor: not-allowed; }
.srw-variant-card--disabled:hover { border-color: #e5e7eb !important; background: #fff !important; }
.srw-price-breakdown { background: #f9fafb; border-radius: 6px; padding: 6px 8px; font-size: .75rem; color: #6b7280; }
.srw-materials { background: #f0fdf4; border-radius: 6px; padding: 6px 10px; }
.srw-mat-label { font-size: .72rem; font-weight: 700; color: #166534; margin-bottom: 2px; }
.srw-mat-item { font-size: .75rem; color: #166534; }
.srw-unavailable { font-size: .78rem; color: #6b7280; font-style: italic; margin-top: 6px; }
.srw-selected-check { font-size: .82rem; color: #7c3aed; font-weight: 600; margin-top: 8px; }

/* Cards informativos (pasos 2-4) */
.srw-card { background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; overflow: hidden; box-shadow: 0 1px 6px rgba(0,0,0,.04); }
.srw-card-header { display: flex; align-items: center; padding: 12px 18px; background: #f9fafb; border-bottom: 1px solid #e5e7eb; font-weight: 700; font-size: .9rem; color: #111827; }
.srw-card-body { padding: 20px 18px; }

/* Constructor de direccion */
.srw-addr-builder { background: #f8f5ff; border: 1.5px solid #ddd6fe; border-radius: 10px; padding: 14px; }
.srw-addr-preview { background: #ede9fe; border: 1px solid #c4b5fd; border-radius: 7px; padding: 7px 10px; }

/* Urgencia */
.srw-urgency-pill {
  padding: 5px 14px; border-radius: 20px; font-size: .8rem; font-weight: 600;
  border: 1.5px solid #e5e7eb; background: #f9fafb; cursor: pointer; transition: all .15s;
}
.srw-urgency-pill--normal.srw-urgency-pill--active  { background: #dbeafe; border-color: #93c5fd; color: #1e40af; }
.srw-urgency-pill--alta.srw-urgency-pill--active    { background: #fef3c7; border-color: #fbbf24; color: #92400e; }
.srw-urgency-pill--critica.srw-urgency-pill--active { background: #fee2e2; border-color: #fca5a5; color: #991b1b; }

/* Jornada (Paso 3, Fase 5) */
.srw-jornada-pill {
  padding: 10px 18px; border-radius: 12px;
  border: 1.5px solid #e5e7eb; background: #f9fafb; cursor: pointer; transition: all .15s;
  min-width: 150px; text-align: center;
}
.srw-jornada-pill--active { background: #f5f3ff; border-color: #7c3aed; box-shadow: 0 0 0 3px rgba(124,58,237,.12); }
.srw-jornada-pill--active .fw-semibold { color: #6d28d9; }

/* Horario info */
.srw-schedule-info { background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 8px; padding: 12px 14px; display: flex; align-items: flex-start; gap: 8px; }

/* Aviso de proceso */
.srw-process-notice { background: #f0fdf4; border: 1px solid #bbf7d0; border-radius: 10px; padding: 14px 16px; display: flex; align-items: flex-start; gap: 8px; }

/* Miniaturas (paso 4) */
.srw-thumb-mini { width: 48px; height: 48px; border-radius: 7px; overflow: hidden; background: #f3f4f6; display: flex; align-items: center; justify-content: center; border: 1px solid #e5e7eb; }
.srw-thumb-mini-img  { width: 100%; height: 100%; object-fit: cover; }
.srw-thumb-mini-icon { font-size: 1.3rem; }

/* Color violeta — sistema unificado con alquiler */
.text-violet { color: #7c3aed !important; }
.btn-violet {
  background: #7c3aed; color: #fff; border: none;
  transition: background .15s;
}
.btn-violet:hover:not(:disabled) { background: #6d28d9; color: #fff; }
.btn-violet:disabled { background: #c4b5fd; color: #fff; cursor: not-allowed; }
</style>
