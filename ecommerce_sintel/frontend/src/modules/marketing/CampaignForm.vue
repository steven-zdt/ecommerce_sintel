<template>
  <div class="campaign-form">
    <form @submit.prevent="handleSubmit">
      <!-- Origen de la campaña (Fase 3: Desde catálogo / Desde cero) -->
      <div class="mb-4">
        <label class="form-label fw-semibold small text-uppercase text-muted">Origen de la Campaña</label>
        <div class="btn-group w-100" role="group">
          <button
            type="button"
            class="btn"
            :class="sourceMode === 'scratch' ? 'btn-primary' : 'btn-outline-secondary'"
            @click="setSourceMode('scratch')"
          >
            <i class="bi bi-pencil-square me-1"></i>Desde cero
          </button>
          <button
            type="button"
            class="btn"
            :class="sourceMode === 'catalog' ? 'btn-primary' : 'btn-outline-secondary'"
            @click="setSourceMode('catalog')"
          >
            <i class="bi bi-box-seam me-1"></i>Desde catálogo
          </button>
        </div>
      </div>

      <!-- Items de catalogo (Fase 7, campanas compuestas): lista repetible, "02 camaras" es
           UN item con quantity=2, no dos filas. Cada item puede ser Producto/Servicio/Renting. -->
      <div v-if="sourceMode === 'catalog'" class="mb-4 p-3 bg-light rounded-3">
        <label class="form-label fw-semibold small text-uppercase text-muted">Items de la Campaña</label>

        <ul v-if="items.length" class="list-group mb-3">
          <li v-for="(it, idx) in items" :key="idx" class="list-group-item d-flex align-items-center gap-3">
            <img
              v-if="itemImage(it)"
              :src="itemImage(it)"
              alt=""
              style="width: 48px; height: 48px; object-fit: cover; border-radius: 0.4rem;"
            />
            <div class="flex-grow-1">
              <div class="fw-semibold">{{ itemName(it) }}</div>
              <div class="small text-muted text-capitalize">{{ it.type }}</div>
            </div>
            <input
              type="number" min="1" class="form-control form-control-sm" style="max-width: 80px;"
              v-model.number="it.quantity" aria-label="Cantidad"
            />
            <button type="button" class="btn btn-sm btn-outline-danger" @click="removeItem(idx)">
              <i class="bi bi-x-lg"></i>
            </button>
          </li>
        </ul>

        <!-- Sub-formulario "agregar item" -->
        <div class="p-3 bg-white rounded-3 border">
          <div class="btn-group w-100 mb-2" role="group">
            <button type="button" class="btn btn-sm" :class="draftType === 'product' ? 'btn-primary' : 'btn-outline-secondary'" @click="setDraftType('product')">
              <i class="bi bi-box-seam me-1"></i>Producto
            </button>
            <button type="button" class="btn btn-sm" :class="draftType === 'service' ? 'btn-primary' : 'btn-outline-secondary'" @click="setDraftType('service')">
              <i class="bi bi-tools me-1"></i>Servicio
            </button>
            <button type="button" class="btn btn-sm" :class="draftType === 'renting' ? 'btn-primary' : 'btn-outline-secondary'" @click="setDraftType('renting')">
              <i class="bi bi-camera-reels me-1"></i>Renting
            </button>
          </div>

          <!-- Buscar Producto -->
          <div v-if="draftType === 'product'">
            <input
              v-if="!draftSelection"
              v-model="productSearchQuery" type="text" class="form-control"
              placeholder="Buscar producto por nombre, SKU..." @input="onProductSearchInput" aria-label="Buscar producto"
            />
            <ul v-if="!draftSelection && productSearchResults.length" class="list-group mt-2">
              <li v-for="p in productSearchResults" :key="p.uuid" class="list-group-item list-group-item-action" role="button" @click="selectDraft(p)">
                {{ p.name }} <span class="text-muted small">({{ p.brand_name || 'Sin marca' }})</span>
              </li>
            </ul>
            <div v-else-if="!draftSelection && productSearchQuery && !productSearchLoading" class="form-text text-muted mt-2">Sin resultados.</div>
          </div>

          <!-- Buscar Servicio -->
          <div v-if="draftType === 'service'">
            <input
              v-if="!draftSelection"
              v-model="serviceSearchQuery" type="text" class="form-control"
              placeholder="Buscar servicio por nombre..." @input="onServiceSearchInput" aria-label="Buscar servicio"
            />
            <ul v-if="!draftSelection && serviceSearchResults.length" class="list-group mt-2">
              <li v-for="s in serviceSearchResults" :key="s.uuid" class="list-group-item list-group-item-action" role="button" @click="selectDraftService(s)">
                {{ s.name }} <span class="text-muted small">({{ s.category_name || 'Sin categoría' }})</span>
              </li>
            </ul>
            <div v-else-if="!draftSelection && serviceSearchQuery && !serviceSearchLoading" class="form-text text-muted mt-2">Sin resultados.</div>
          </div>

          <!-- Buscar Equipo/Variante de Renting -->
          <div v-if="draftType === 'renting'">
            <div v-if="!draftEquipment">
              <input
                v-model="equipmentSearchQuery" type="text" class="form-control"
                placeholder="Buscar equipo por nombre..." @input="onEquipmentSearchInput" aria-label="Buscar equipo"
              />
              <ul v-if="equipmentSearchResults.length" class="list-group mt-2">
                <li v-for="e in equipmentSearchResults" :key="e.uuid" class="list-group-item list-group-item-action" role="button" @click="selectDraftEquipment(e)">
                  {{ e.name }} <span class="text-muted small">({{ e.brand?.name || 'Sin marca' }})</span>
                </li>
              </ul>
              <div v-else-if="equipmentSearchQuery && !equipmentSearchLoading" class="form-text text-muted mt-2">Sin resultados.</div>
            </div>
            <div v-else-if="!draftSelection">
              <div class="small text-muted mb-2">
                Equipo: <strong>{{ draftEquipment.name }}</strong>
                <button type="button" class="btn btn-sm btn-link p-0 ms-2" @click="draftEquipment = null">cambiar</button>
              </div>
              <label class="form-label small">Selecciona la variante</label>
              <ul class="list-group">
                <li v-for="v in draftEquipment.variants || []" :key="v.uuid" class="list-group-item list-group-item-action" role="button" @click="selectDraftVariant(v)">
                  {{ v.sku }} — tarifa: {{ formatCOP(Number(v.rental_price_per_day || v.rental_price_per_hour || 0), { withSymbol: true }) }}
                  <span class="text-muted small">(stock: {{ v.stock }})</span>
                </li>
              </ul>
              <div v-if="!(draftEquipment.variants || []).length" class="form-text text-muted mt-2">Este equipo no tiene variantes activas.</div>
            </div>
          </div>

          <!-- Preview de la seleccion actual + boton agregar -->
          <div v-if="draftSelection" class="d-flex align-items-center gap-3 p-2 bg-light rounded-3 border mt-2">
            <img v-if="draftPreviewImage" :src="draftPreviewImage" alt="" style="width: 48px; height: 48px; object-fit: cover; border-radius: 0.4rem;" />
            <div class="flex-grow-1">
              <div class="fw-semibold">{{ draftPreviewName }}</div>
              <div class="small text-muted">{{ draftPreviewSubtitle }}</div>
            </div>
            <input type="number" min="1" class="form-control form-control-sm" style="max-width: 80px;" v-model.number="draftQuantity" aria-label="Cantidad" />
            <button type="button" class="btn btn-sm btn-outline-secondary" @click="clearDraft">
              <i class="bi bi-x-lg"></i>
            </button>
            <button type="button" class="btn btn-sm btn-primary" @click="addItemFromDraft">
              <i class="bi bi-plus-lg me-1"></i>Agregar
            </button>
          </div>
        </div>
      </div>

      <!-- Beneficios (Fase 8, set minimo) -->
      <div class="mb-4 p-3 bg-light rounded-3">
        <label class="form-label fw-semibold small text-uppercase text-muted">Beneficios</label>
        <div class="d-flex flex-column gap-2">
          <div class="form-check">
            <input
              class="form-check-input" type="checkbox" id="benFreeShipping"
              :checked="hasBenefit('FREE_SHIPPING')" @change="toggleBenefit('FREE_SHIPPING', 'Transporte gratis')"
            >
            <label class="form-check-label" for="benFreeShipping">Transporte gratis</label>
          </div>
          <div class="form-check">
            <input
              class="form-check-input" type="checkbox" id="benFreeInstallation"
              :checked="hasBenefit('FREE_INSTALLATION')" @change="toggleBenefit('FREE_INSTALLATION', 'Instalación gratis')"
            >
            <label class="form-check-label" for="benFreeInstallation">Instalación gratis</label>
          </div>
          <div class="d-flex align-items-center gap-2">
            <div class="form-check mb-0">
              <input
                class="form-check-input" type="checkbox" id="benDiscountPercent"
                :checked="hasBenefit('DISCOUNT_PERCENT')" @change="toggleBenefit('DISCOUNT_PERCENT', 'Descuento porcentual')"
              >
              <label class="form-check-label" for="benDiscountPercent">Descuento %</label>
            </div>
            <input
              v-if="hasBenefit('DISCOUNT_PERCENT')"
              type="number" class="form-control form-control-sm" style="max-width: 100px;"
              :value="benefitValue('DISCOUNT_PERCENT')" @input="setBenefitValue('DISCOUNT_PERCENT', $event.target.value)"
              placeholder="%" min="0" max="100"
            />
          </div>
          <div class="d-flex align-items-center gap-2">
            <div class="form-check mb-0">
              <input
                class="form-check-input" type="checkbox" id="benDiscountFixed"
                :checked="hasBenefit('DISCOUNT_FIXED')" @change="toggleBenefit('DISCOUNT_FIXED', 'Descuento fijo')"
              >
              <label class="form-check-label" for="benDiscountFixed">Descuento fijo ($)</label>
            </div>
            <input
              v-if="hasBenefit('DISCOUNT_FIXED')"
              type="number" class="form-control form-control-sm" style="max-width: 120px;"
              :value="benefitValue('DISCOUNT_FIXED')" @input="setBenefitValue('DISCOUNT_FIXED', $event.target.value)"
              placeholder="$" min="0"
            />
          </div>
        </div>
      </div>

      <!-- Media (Fase 11-14): galeria imagen/video. Requiere una campana ya guardada (el
           endpoint de subida necesita un uuid real) -- en modo "create" se avisa que hay que
           guardar primero, sin bloquear el resto del formulario. -->
      <div class="mb-4 p-3 bg-light rounded-3">
        <label class="form-label fw-semibold small text-uppercase text-muted">Imagen / Video</label>

        <div v-if="!campaignUuid" class="text-muted small">
          <i class="bi bi-info-circle me-1"></i>Guarda la campaña primero para poder agregar imágenes o video.
        </div>

        <template v-else>
          <ul v-if="mediaItems.length" class="list-group mb-3">
            <li
              v-for="(m, idx) in mediaItems" :key="m.uuid"
              class="list-group-item d-flex align-items-center gap-3"
              :class="{ 'opacity-50': !m.is_active }"
            >
              <img
                v-if="m.media_type === 'IMAGE'" :src="m.file" alt=""
                style="width: 56px; height: 56px; object-fit: cover; border-radius: 0.4rem;"
              />
              <video
                v-else :src="m.file" controls
                style="width: 96px; height: 56px; object-fit: cover; border-radius: 0.4rem;"
              ></video>
              <div class="flex-grow-1">
                <div class="fw-semibold small">{{ m.media_type === 'IMAGE' ? 'Imagen' : 'Video' }}</div>
                <div class="text-muted smaller">{{ (m.size / 1024).toFixed(0) }} KB<span v-if="m.width"> · {{ m.width }}×{{ m.height }}</span></div>
              </div>
              <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="idx === 0" @click="moveMedia(idx, -1)">
                <i class="bi bi-arrow-up"></i>
              </button>
              <button type="button" class="btn btn-sm btn-outline-secondary" :disabled="idx === mediaItems.length - 1" @click="moveMedia(idx, 1)">
                <i class="bi bi-arrow-down"></i>
              </button>
              <button type="button" class="btn btn-sm" :class="m.is_active ? 'btn-outline-warning' : 'btn-outline-success'" @click="handleToggleMedia(m.uuid)">
                <i class="bi" :class="m.is_active ? 'bi-eye-slash' : 'bi-eye'"></i>
              </button>
              <button type="button" class="btn btn-sm btn-outline-danger" @click="handleDeleteMedia(m.uuid)">
                <i class="bi bi-x-lg"></i>
              </button>
            </li>
          </ul>

          <div class="d-flex gap-2">
            <label class="btn btn-sm btn-outline-primary mb-0">
              <i class="bi bi-image me-1"></i>Subir imagen
              <input type="file" accept="image/jpeg,image/png,image/webp" class="d-none" @change="handleMediaUpload($event, 'IMAGE')" />
            </label>
            <label class="btn btn-sm btn-outline-primary mb-0">
              <i class="bi bi-camera-video me-1"></i>Subir video
              <input type="file" accept="video/mp4" class="d-none" @change="handleMediaUpload($event, 'VIDEO')" />
            </label>
            <span v-if="mediaUploading" class="small text-muted align-self-center">
              <i class="bi bi-hourglass-split me-1"></i>Subiendo...
            </span>
          </div>
          <div v-if="mediaError" class="form-text text-danger small mt-2">
            <i class="bi bi-exclamation-circle me-1"></i>{{ mediaError }}
          </div>
        </template>
      </div>

      <!-- Título -->
      <div class="mb-4">
        <label class="form-label fw-semibold small text-uppercase text-muted">Título de la Campaña</label>
        <input 
          v-model="campaignForm.title.value" 
          type="text" 
          class="form-control form-control-lg"
          :class="{ 'is-invalid': campaignForm.titleError && campaignForm.titleTouched }"
          placeholder="Ej: Ofertas de Verano"
          @blur="touchField('title')"
          aria-label="Título de la Campaña"
          :aria-invalid="!!campaignForm.titleError && campaignForm.titleTouched"
          :aria-describedby="campaignForm.titleError && campaignForm.titleTouched ? 'title-error' : undefined"
        />
        <div 
          v-if="campaignForm.titleError && campaignForm.titleTouched" 
          id="title-error"
          class="form-text text-danger small mt-1"
        >
          <i class="bi bi-exclamation-circle me-1"></i>{{ campaignForm.titleError }}
        </div>
      </div>

      <!-- Contenido -->
      <div class="mb-4">
        <label class="form-label fw-semibold small text-uppercase text-muted">Contenido del Mensaje</label>
        <textarea 
          v-model="campaignForm.content.value" 
          class="form-control form-control-lg" 
          :class="{ 'is-invalid': campaignForm.contentError && campaignForm.contentTouched }"
          rows="5"
          placeholder="Escribe el cuerpo del mensaje..."
          @blur="touchField('content')"
          aria-label="Contenido del Mensaje"
          :aria-invalid="!!campaignForm.contentError && campaignForm.contentTouched"
          :aria-describedby="campaignForm.contentError && campaignForm.contentTouched ? 'content-error' : 'content-hint'"
        ></textarea>
        <div class="form-text smaller text-muted mt-1" id="content-hint">
          {{ campaignForm.contentLength }}/500 caracteres
        </div>
        <div 
          v-if="campaignForm.contentError && campaignForm.contentTouched" 
          id="content-error"
          class="form-text text-danger small mt-1"
        >
          <i class="bi bi-exclamation-circle me-1"></i>{{ campaignForm.contentError }}
        </div>
      </div>

      <!-- Fase 9+10: descripcion/subtitulo/CTA/condiciones/vigencia -- todos opcionales,
           aplican a cualquier campana (con o sin items de catalogo). -->
      <div class="mb-4">
        <label class="form-label fw-semibold small text-uppercase text-muted">Descripción breve (opcional)</label>
        <input v-model="extraFields.description" type="text" class="form-control" maxlength="500"
          placeholder="Resumen corto para listados/previsualización" />
      </div>

      <div class="mb-4">
        <label class="form-label fw-semibold small text-uppercase text-muted">Subtítulo (opcional)</label>
        <input v-model="extraFields.subheadline" type="text" class="form-control" maxlength="255"
          placeholder="Frase de apoyo debajo del título" />
      </div>

      <div class="row mb-4">
        <div class="col-md-6">
          <label class="form-label fw-semibold small text-uppercase text-muted">Texto del CTA (opcional)</label>
          <input v-model="extraFields.cta_label" type="text" class="form-control" maxlength="100"
            placeholder="Ej: Solicitar información" />
        </div>
        <div class="col-md-6">
          <label class="form-label fw-semibold small text-uppercase text-muted">URL del CTA (opcional)</label>
          <input v-model="extraFields.cta_url" type="url" class="form-control"
            placeholder="https://..." />
        </div>
      </div>

      <div class="mb-4">
        <label class="form-label fw-semibold small text-uppercase text-muted">Condiciones (opcional)</label>
        <textarea v-model="extraFields.terms" class="form-control" rows="2"
          placeholder="Términos y condiciones de la oferta"></textarea>
      </div>

      <div class="row mb-4">
        <div class="col-md-6">
          <label class="form-label fw-semibold small text-uppercase text-muted">Vigente desde (opcional)</label>
          <input v-model="extraFields.valid_from" type="datetime-local" class="form-control" />
        </div>
        <div class="col-md-6">
          <label class="form-label fw-semibold small text-uppercase text-muted">Vigente hasta (opcional)</label>
          <input v-model="extraFields.valid_until" type="datetime-local" class="form-control" />
        </div>
        <div v-if="validityError" class="form-text text-danger small mt-1">
          <i class="bi bi-exclamation-circle me-1"></i>{{ validityError }}
        </div>
      </div>

      <!-- Canales -->
      <div class="mb-4">
        <label class="form-label fw-semibold small text-uppercase text-muted">Canales de Envío</label>
        <div class="d-flex flex-wrap gap-3 p-3 bg-light rounded-3" :class="{ 'border border-danger': campaignForm.channelsError && campaignForm.channelsTouched }">
          <div class="form-check">
            <input 
              class="form-check-input" 
              type="checkbox" 
              value="email" 
              v-model="campaignForm.channels.value" 
              id="chEmail"
              @blur="touchField('channels')"
            >
            <label class="form-check-label small fw-500" for="chEmail">
              <i class="bi bi-envelope me-1"></i>Email
            </label>
          </div>
          <div class="form-check">
            <input 
              class="form-check-input" 
              type="checkbox" 
              value="whatsapp" 
              v-model="campaignForm.channels.value" 
              id="chWA"
              @blur="touchField('channels')"
            >
            <label class="form-check-label small fw-500" for="chWA">
              <i class="bi bi-chat-dots me-1"></i>WhatsApp
            </label>
          </div>
          <div class="form-check" v-for="ch in _broadcastChannelOptions" :key="ch.value">
            <input
              class="form-check-input"
              type="checkbox"
              :value="ch.value"
              v-model="campaignForm.channels.value"
              :id="`ch-${ch.value}`"
              @blur="touchField('channels')"
            >
            <label class="form-check-label small fw-500" :for="`ch-${ch.value}`">
              <i :class="`bi ${ch.icon} me-1`"></i>{{ ch.label }}
            </label>
          </div>
        </div>
        <!-- Fase 15 (2026-09-23): "SMS" quitado -- no existe adapter real (marketing/channels/
        registry.py, 8 canales reales confirmados), era un checkbox sin backend detras. Los 6
        canales de broadcast que faltaban aqui (antes solo se mostraban email/whatsapp) se agregan
        arriba via _broadcastChannelOptions -- ver MARKETING_GAPS.md. -->
        <p class="form-text small text-muted mt-1">
          Facebook/Instagram/YouTube/TikTok/X/Google Business publican a la pagina o cuenta
          conectada (no a un destinatario individual).
        </p>
        <div 
          v-if="campaignForm.channelsError && campaignForm.channelsTouched" 
          class="form-text text-danger small mt-2"
        >
          <i class="bi bi-exclamation-circle me-1"></i>{{ campaignForm.channelsError }}
        </div>
      </div>

      <!-- Fecha Programada -->
      <div class="mb-4">
        <label class="form-label fw-semibold small text-uppercase text-muted">Fecha y Hora Programada</label>
        <input 
          v-model="campaignForm.scheduledAt.value" 
          type="datetime-local" 
          class="form-control form-control-lg"
          :class="{ 'is-invalid': campaignForm.scheduledAtError && campaignForm.scheduledAtTouched }"
          @blur="touchField('scheduled_at')"
          aria-label="Fecha y Hora Programada"
          :aria-invalid="!!campaignForm.scheduledAtError && campaignForm.scheduledAtTouched"
          :aria-describedby="campaignForm.scheduledAtError && campaignForm.scheduledAtTouched ? 'scheduled-at-error' : undefined"
        />
        <div 
          v-if="campaignForm.scheduledAtError && campaignForm.scheduledAtTouched" 
          id="scheduled-at-error"
          class="form-text text-danger small mt-1"
        >
          <i class="bi bi-exclamation-circle me-1"></i>{{ campaignForm.scheduledAtError }}
        </div>
      </div>

      <!-- Botones de Acción -->
      <div class="pt-4 border-top">
        <div class="d-grid gap-2">
          <button type="submit" class="btn btn-primary btn-lg" :disabled="saving || !isValid">
            <span v-if="saving" class="spinner-border spinner-border-sm me-2"></span>
            <i v-else class="bi me-2" :class="mode === 'create' ? 'bi-plus-circle' : 'bi-check-circle'"></i>
            {{ mode === 'create' ? 'Crear Campaña' : 'Guardar Cambios' }}
          </button>
        </div>
        <div class="text-center mt-3">
          <button type="button" class="btn btn-link btn-sm text-muted" @click="resetForm">
            Limpiar formulario
          </button>
        </div>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useFormValidation, campaignValidationSchema } from '@/composables/useFormValidation';
import { useMarketingAdminStore } from '@/store/marketingAdmin';
import { useShopAdminStore } from '@/store/shopAdmin';
import { useTechnicalServicesStore } from '@/store/technicalServicesAdmin/services';
import { useRentingCatalogAdminStore } from '@/store/rentingAdmin/catalog';
import { formatCOP } from '@/utils/money';

const props = defineProps({
  campaign: { type: Object, default: null },
  mode:     { type: String, default: 'create' }
});

const emit = defineEmits(['saved']);
const toast = useToast();
const { handleError } = useErrorHandler();
const store = useMarketingAdminStore();
const shopStore = useShopAdminStore();
const servicesStore = useTechnicalServicesStore();
const rentingCatalogStore = useRentingCatalogAdminStore();
const { actionLoading: saving } = storeToRefs(store);

// Fase 15 (2026-09-23): los 6 canales de broadcast reales de
// marketing/channels/registry.py::BROADCAST_CHANNELS -- publican a la pagina/cuenta
// conectada, no a un destinatario individual (email/whatsapp ya tenian checkbox propio arriba).
const _broadcastChannelOptions = [
  { value: 'facebook', label: 'Facebook', icon: 'bi-facebook' },
  { value: 'instagram', label: 'Instagram', icon: 'bi-instagram' },
  { value: 'youtube', label: 'YouTube', icon: 'bi-youtube' },
  { value: 'tiktok', label: 'TikTok', icon: 'bi-tiktok' },
  { value: 'x', label: 'X', icon: 'bi-twitter-x' },
  { value: 'google_business', label: 'Google Business', icon: 'bi-google' },
];

// PLAN_SINTEL_MARKETING_CAMPANAS_CRUD_CATALOG_MEDIA_CANALES_LOOP.md, Fase 3/4/8 (2026-09-23,
// Producto) + Fase 5/6 (2026-09-23, Servicio/Renting) + Fase 7 (2026-09-23, campanas
// compuestas) -- estado local, fuera del schema yup (campaignValidationSchema solo valida
// title/content/channels/scheduled_at), se mezcla al payload en handleSubmit.
//
// Fase 7: 'items' reemplaza la seleccion singular (selectedProduct/selectedService/etc.) --
// "02 camaras" es UN item con quantity=2, no dos filas (ver CampaignItem en el backend). El
// "draft" (draftType/draftSelection/draftEquipment/draftQuantity) es el sub-formulario de
// "agregar item": junta una seleccion real del catalogo antes de empujarla a `items`.
const sourceMode = ref('scratch'); // 'scratch' | 'catalog'
const items = ref([]); // [{ type, uuid, quantity, preview }]

// Fase 9+10 (2026-09-23): campos opcionales, sin schema de vee-validate propio (nada aqui es
// requerido) -- refs simples mezcladas al payload en handleSubmit, mismo criterio que
// items/benefits ya usaban antes de esta fase.
const extraFields = ref({
  description: '', subheadline: '', cta_label: '', cta_url: '', terms: '',
  valid_from: '', valid_until: '',
});
const validityError = computed(() => {
  const { valid_from, valid_until } = extraFields.value;
  if (valid_from && valid_until && new Date(valid_until) < new Date(valid_from)) {
    return 'La fecha "hasta" no puede ser anterior a "desde".';
  }
  return '';
});

const draftType = ref('product'); // 'product' | 'service' | 'renting'
const draftSelection = ref(null); // objeto real (Product/Service/EquipmentVariant), nunca copiado a texto libre
const draftEquipment = ref(null); // paso intermedio de renting: equipo elegido, antes de la variante
const draftQuantity = ref(1);

const productSearchQuery = ref('');
const productSearchResults = ref([]);
const productSearchLoading = ref(false);

const serviceSearchQuery = ref('');
const serviceSearchResults = ref([]);
const serviceSearchLoading = ref(false);

const equipmentSearchQuery = ref('');
const equipmentSearchResults = ref([]);
const equipmentSearchLoading = ref(false);

const benefits = ref([]); // [{ benefit_type, label, value }]

// Fase 11-14 (2026-09-23): galeria de media. A diferencia de items/benefits (locales al
// formulario, se envian recien al Guardar), media se sube/borra/reordena en VIVO contra el
// backend -- requiere que la campana ya exista (props.campaign.uuid). Por eso mediaItems se
// inicializa desde props.campaign.media (ya resuelto por el serializer) y cada accion llama
// al store de inmediato, sin esperar al submit del formulario -- mismo criterio que
// shop/renting/technical_services usan para sus galerias de imagen/video.
const campaignUuid = computed(() => props.campaign?.uuid || null);
const mediaItems = ref(props.campaign?.media ? [...props.campaign.media] : []);
const mediaUploading = ref(false);
const mediaError = ref('');

async function handleMediaUpload(event, mediaType) {
  const file = event.target.files?.[0];
  event.target.value = ''; // permite re-seleccionar el mismo archivo despues de un error
  if (!file || !campaignUuid.value) return;
  mediaError.value = '';
  mediaUploading.value = true;
  const result = await store.uploadCampaignMedia(campaignUuid.value, file, mediaType);
  mediaUploading.value = false;
  if (!result.ok) {
    mediaError.value = result.error?.response?.data?.detail || 'No se pudo subir el archivo.';
    return;
  }
  mediaItems.value.push(result.data);
}

async function handleDeleteMedia(mediaUuid) {
  if (!campaignUuid.value) return;
  const result = await store.deleteCampaignMedia(campaignUuid.value, mediaUuid);
  if (result.ok) {
    mediaItems.value = mediaItems.value.filter((m) => m.uuid !== mediaUuid);
  } else {
    toast.error('No se pudo eliminar el archivo.');
  }
}

async function handleToggleMedia(mediaUuid) {
  if (!campaignUuid.value) return;
  const result = await store.toggleCampaignMedia(campaignUuid.value, mediaUuid);
  if (result.ok) {
    const media = mediaItems.value.find((m) => m.uuid === mediaUuid);
    if (media) media.is_active = !media.is_active;
  } else {
    toast.error('No se pudo actualizar el archivo.');
  }
}

async function moveMedia(index, direction) {
  const target = index + direction;
  if (target < 0 || target >= mediaItems.value.length) return;
  const reordered = [...mediaItems.value];
  [reordered[index], reordered[target]] = [reordered[target], reordered[index]];
  mediaItems.value = reordered;
  const result = await store.reorderCampaignMedia(campaignUuid.value, reordered.map((m) => m.uuid));
  if (!result.ok) toast.error('No se pudo reordenar la galería.');
}

function imageOf(obj) {
  const img = obj?.images?.find((i) => i.is_primary) || obj?.images?.[0];
  return img?.image || null;
}

const draftPreviewImage = computed(() => {
  if (draftType.value === 'renting') return imageOf(draftEquipment.value);
  return imageOf(draftSelection.value);
});
const draftPreviewName = computed(() => {
  if (draftType.value === 'renting') return draftEquipment.value?.name || '';
  return draftSelection.value?.name || '';
});
const draftPreviewSubtitle = computed(() => {
  if (draftType.value === 'product') {
    const variant = draftSelection.value?.variants?.find((v) => v.is_default) || draftSelection.value?.variants?.[0];
    const price = variant ? formatCOP(Number(variant.price), { withSymbol: true }) : '';
    return `${draftSelection.value?.brand_name || 'Sin marca'} — ${price}`;
  }
  if (draftType.value === 'service') {
    const variant = draftSelection.value?.variants?.find((v) => v.is_default) || draftSelection.value?.variants?.[0];
    const price = variant?.fixed_price ? formatCOP(Number(variant.fixed_price), { withSymbol: true }) : '';
    return `${draftSelection.value?.category?.name || 'Sin categoría'} — ${price}`;
  }
  if (draftType.value === 'renting' && draftSelection.value) {
    const price = formatCOP(Number(draftSelection.value.rental_price_per_day || draftSelection.value.rental_price_per_hour || 0), { withSymbol: true });
    return `${draftSelection.value.sku} — ${price} (stock: ${draftSelection.value.stock})`;
  }
  return '';
});

function itemImage(it) {
  return imageOf(it.preview);
}
function itemName(it) {
  return it.preview?.name || it.uuid;
}

function setSourceMode(newMode) {
  sourceMode.value = newMode;
  if (newMode === 'scratch') items.value = [];
}

function setDraftType(newType) {
  draftType.value = newType;
  clearDraft();
}

function clearDraft() {
  draftSelection.value = null;
  draftEquipment.value = null;
  draftQuantity.value = 1;
  productSearchQuery.value = ''; productSearchResults.value = [];
  serviceSearchQuery.value = ''; serviceSearchResults.value = [];
  equipmentSearchQuery.value = ''; equipmentSearchResults.value = [];
}

function addItemFromDraft() {
  const uuid = draftType.value === 'renting' ? draftSelection.value?.uuid : draftSelection.value?.uuid;
  if (!uuid) return;
  const preview = draftType.value === 'renting'
    ? { ...draftEquipment.value, selected_variant: draftSelection.value }
    : draftSelection.value;
  items.value.push({ type: draftType.value, uuid, quantity: draftQuantity.value || 1, preview });
  clearDraft();
}

function removeItem(idx) {
  items.value.splice(idx, 1);
}

let productSearchTimer = null;
function onProductSearchInput() {
  clearTimeout(productSearchTimer);
  productSearchTimer = setTimeout(async () => {
    if (!productSearchQuery.value) {
      productSearchResults.value = [];
      return;
    }
    productSearchLoading.value = true;
    try {
      await shopStore.fetchProducts({ search: productSearchQuery.value, is_active: 'true' });
      productSearchResults.value = shopStore.products;
    } finally {
      productSearchLoading.value = false;
    }
  }, 400);
}

function selectDraft(product) {
  draftSelection.value = product;
  productSearchResults.value = [];
  productSearchQuery.value = '';
}

// dashboard/services/ no soporta ?search= server-side (verificado en el ViewSet real) --
// se trae la lista completa una vez y se filtra en el cliente, mismo criterio de debounce
// que el resto de buscadores para consistencia de UX.
let serviceSearchTimer = null;
function onServiceSearchInput() {
  clearTimeout(serviceSearchTimer);
  serviceSearchTimer = setTimeout(async () => {
    if (!serviceSearchQuery.value) {
      serviceSearchResults.value = [];
      return;
    }
    serviceSearchLoading.value = true;
    try {
      if (!servicesStore.services.length) await servicesStore.fetchServices();
      const q = serviceSearchQuery.value.toLowerCase();
      serviceSearchResults.value = servicesStore.services.filter(
        (s) => s.is_active && s.name?.toLowerCase().includes(q)
      );
    } finally {
      serviceSearchLoading.value = false;
    }
  }, 400);
}

async function selectDraftService(service) {
  // El listado (TechnicalServiceSerializer) no trae 'variants' completas -- se pide el
  // detalle real (TechnicalServiceDetailSerializer, mismo shape que resuelve el backend en el
  // preview) para que el precio mostrado sea el real, no un placeholder.
  const detail = await servicesStore.fetchServiceDetail(service.uuid);
  draftSelection.value = detail || service;
  serviceSearchResults.value = [];
  serviceSearchQuery.value = '';
}

let equipmentSearchTimer = null;
function onEquipmentSearchInput() {
  clearTimeout(equipmentSearchTimer);
  equipmentSearchTimer = setTimeout(async () => {
    if (!equipmentSearchQuery.value) {
      equipmentSearchResults.value = [];
      return;
    }
    equipmentSearchLoading.value = true;
    try {
      await rentingCatalogStore.fetchEquipment({ search: equipmentSearchQuery.value });
      equipmentSearchResults.value = rentingCatalogStore.equipment;
    } finally {
      equipmentSearchLoading.value = false;
    }
  }, 400);
}

function selectDraftEquipment(equipment) {
  draftEquipment.value = equipment;
  equipmentSearchResults.value = [];
  equipmentSearchQuery.value = '';
}

function selectDraftVariant(variant) {
  draftSelection.value = variant;
}

function hasBenefit(type) {
  return benefits.value.some((b) => b.benefit_type === type);
}

function benefitValue(type) {
  return benefits.value.find((b) => b.benefit_type === type)?.value ?? '';
}

function toggleBenefit(type, label) {
  if (hasBenefit(type)) {
    benefits.value = benefits.value.filter((b) => b.benefit_type !== type);
  } else {
    benefits.value.push({ benefit_type: type, label, value: null });
  }
}

function setBenefitValue(type, value) {
  const benefit = benefits.value.find((b) => b.benefit_type === type);
  if (benefit) benefit.value = value;
}

// VeeValidate form validation
const { 
  values, 
  errors, 
  onSubmit,
  campaignForm,
  hasErrors,
  isValid,
  isTouched,
  reset,
  setValues,
  touchField,
  touchAllFields
} = useFormValidation(campaignValidationSchema);

/**
 * Submit handler with VeeValidate validation
 */
const handleSubmit = onSubmit(async (formValues) => {
  if (validityError.value) {
    toast.error(validityError.value);
    return;
  }
  const payload = {
    ...formValues,
    items: sourceMode.value === 'catalog'
      ? items.value.map(({ type, uuid, quantity }) => ({ type, uuid, quantity }))
      : [],
    benefits: benefits.value.map(({ benefit_type, label, value }) => ({ benefit_type, label, value })),
    // Fase 9+10: campos opcionales, string vacio -> no se envia (deja el default del backend)
    ...Object.fromEntries(
      Object.entries(extraFields.value).filter(([, v]) => v !== '')
    ),
  };
  const res = props.mode === 'create'
    ? await store.createCampaign(payload)
    : await store.updateCampaign(props.campaign.uuid, payload);

  if (res.ok) {
    toast.success(props.mode === 'create' ? 'Campaña creada exitosamente.' : 'Campaña actualizada.');
    emit('saved');
    reset();
  } else {
    handleError(res.error, 'Error al guardar la campaña. Verifique los datos.');
  }
});

function resetForm() {
  reset();
  sourceMode.value = 'scratch';
  items.value = [];
  clearDraft();
  benefits.value = [];
  extraFields.value = {
    description: '', subheadline: '', cta_label: '', cta_url: '', terms: '',
    valid_from: '', valid_until: '',
  };
}

onMounted(() => {
  if (props.campaign && props.mode === 'edit') {
    const scheduled = props.campaign.scheduled_at
      ? new Date(props.campaign.scheduled_at).toISOString().slice(0, 16)
      : '';

    setValues({
      title: props.campaign.title || '',
      content: props.campaign.content || '',
      channels: [...(props.campaign.channels || ['email'])],
      scheduled_at: scheduled
    });

    // Fase 3/4/8 (Producto) + Fase 5/6 (Servicio/Renting) + Fase 7 (compuestas): el backend ya
    // resuelve items[]/preview/benefits reales -- no se re-derivan, solo se reflejan en el
    // estado local del form.
    const realItems = props.campaign.items || [];
    if (realItems.length) {
      sourceMode.value = 'catalog';
      items.value = realItems.map((it) => ({ type: it.type, uuid: it.uuid, quantity: it.quantity, preview: it.preview }));
    }
    benefits.value = (props.campaign.benefits || []).map((b) => ({
      benefit_type: b.benefit_type, label: b.label, value: b.value,
    }));

    // Fase 9+10: campos opcionales, reflejan el valor real ya persistido.
    extraFields.value = {
      description: props.campaign.description || '',
      subheadline: props.campaign.subheadline || '',
      cta_label: props.campaign.cta_label || '',
      cta_url: props.campaign.cta_url || '',
      terms: props.campaign.terms || '',
      valid_from: props.campaign.valid_from
        ? new Date(props.campaign.valid_from).toISOString().slice(0, 16) : '',
      valid_until: props.campaign.valid_until
        ? new Date(props.campaign.valid_until).toISOString().slice(0, 16) : '',
    };
  }
});
</script>

<style scoped>
.smaller { font-size: 0.75rem; }

.form-label {
  display: block;
  font-size: 0.8rem;
  letter-spacing: 0.5px;
}

.form-control, .form-control-lg {
  border-radius: 0.5rem;
  border: 1px solid var(--bs-border-color);
  transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
}

.form-control:focus {
  border-color: var(--bs-primary);
  box-shadow: 0 0 0 0.2rem rgba(13, 110, 253, 0.15);
}

.form-control[aria-invalid="true"] {
  border-color: var(--bs-danger);
}

.form-check-input {
  width: 1.25rem;
  height: 1.25rem;
  border: 2px solid var(--bs-border-color);
  border-radius: 0.3rem;
  cursor: pointer;
}

.form-check-input:checked {
  background-color: var(--bs-primary);
  border-color: var(--bs-primary);
}

.campaign-form {
  animation: slideIn 0.2s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
</style>
