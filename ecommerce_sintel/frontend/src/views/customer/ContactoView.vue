<template>
  <div class="ctc-view">
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
    </div>

    <div v-else-if="error" class="container py-5 text-center">
      <i class="bi bi-exclamation-circle text-danger fs-1"></i>
      <p class="text-muted mt-2">No pudimos cargar esta pagina. Intenta de nuevo mas tarde.</p>
      <button class="btn btn-outline-primary btn-sm" @click="fetchContent">Reintentar</button>
    </div>

    <template v-else>
      <!-- Hero -->
      <section class="ctc-hero">
        <div class="container">
          <h1 class="ctc-hero-title">Contacto</h1>
          <p class="ctc-hero-subtitle">Escribenos, llamanos o solicita una cotizacion — te respondemos en horario habil.</p>
        </div>
      </section>

      <div class="container py-5">
        <div class="row g-4">
          <!-- Datos de contacto -->
          <div class="col-md-7">
            <div class="ctc-card h-100">
              <h2 class="ctc-section-title"><i class="bi bi-headset me-2"></i>Datos de contacto</h2>

              <div v-if="contact" class="ctc-info-list">
                <div v-if="contact.phone" class="ctc-info-row">
                  <i class="bi bi-telephone ctc-info-icon"></i>
                  <div>
                    <div class="ctc-info-label">Telefono</div>
                    <a :href="`tel:${contact.phone}`" class="ctc-info-value">{{ contact.phone }}</a>
                  </div>
                </div>
                <div v-if="contact.email" class="ctc-info-row">
                  <i class="bi bi-envelope ctc-info-icon"></i>
                  <div>
                    <div class="ctc-info-label">Correo</div>
                    <a :href="`mailto:${contact.email}`" class="ctc-info-value">{{ contact.email }}</a>
                  </div>
                </div>
                <div v-if="contact.address" class="ctc-info-row">
                  <i class="bi bi-geo-alt ctc-info-icon"></i>
                  <div>
                    <div class="ctc-info-label">Cobertura</div>
                    <span class="ctc-info-value">{{ contact.address }}</span>
                  </div>
                </div>
                <div v-if="contact.working_hours" class="ctc-info-row">
                  <i class="bi bi-clock ctc-info-icon"></i>
                  <div>
                    <div class="ctc-info-label">Horario de atencion</div>
                    <span class="ctc-info-value">{{ contact.working_hours }}</span>
                  </div>
                </div>
              </div>
              <p v-else class="text-muted mb-0">Informacion de contacto no disponible por el momento.</p>

              <div v-if="socialLinks.length" class="ctc-social">
                <a
                  v-for="link in socialLinks"
                  :key="link.uuid"
                  :href="link.url"
                  target="_blank"
                  rel="noopener"
                  class="ctc-social-btn"
                  :title="link.title"
                >
                  <i :class="`bi ${link.icon_class}`"></i>
                </a>
              </div>
            </div>
          </div>

          <!-- CTA cotizacion -->
          <div class="col-md-5">
            <div class="ctc-card ctc-cta h-100">
              <i class="bi bi-file-earmark-text ctc-cta-icon"></i>
              <h2 class="ctc-section-title">Solicita una cotizacion</h2>
              <p class="ctc-text">
                Cuentanos que necesitas y te enviamos una propuesta ajustada a tu proyecto: compra,
                renting o servicios tecnicos.
              </p>
              <RouterLink to="/cotizar" class="btn btn-primary rounded-pill px-4">
                Solicitar cotizacion <i class="bi bi-arrow-right ms-1"></i>
              </RouterLink>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { RouterLink } from 'vue-router';
import useApi from '@/composables/useApi';

const api = useApi();
const loading = ref(true);
const error = ref(false);
const contact = ref(null);
const socialLinks = ref([]);

async function fetchContent() {
  loading.value = true;
  error.value = false;
  try {
    const { data } = await api.get('core/footer/');
    contact.value = data.contact || null;
    socialLinks.value = data.social_links || [];
  } catch (err) {
    error.value = true;
  } finally {
    loading.value = false;
  }
}

onMounted(fetchContent);
</script>

<style scoped>
.ctc-hero {
  background: linear-gradient(135deg, #0f172a, #1d4ed8);
  color: #fff;
  padding: 5rem 0 4rem;
  text-align: center;
}
.ctc-hero-title { font-size: 2.25rem; font-weight: 800; margin-bottom: .5rem; }
.ctc-hero-subtitle { font-size: 1.1rem; color: rgba(255,255,255,.85); max-width: 640px; margin: 0 auto; }

.ctc-card {
  background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 16px;
  padding: 2rem;
}
.ctc-section-title { font-size: 1.35rem; font-weight: 700; color: #111827; margin-bottom: 1.25rem; }
.ctc-text { color: #4b5563; line-height: 1.7; }

.ctc-info-list { display: flex; flex-direction: column; gap: 1.25rem; }
.ctc-info-row { display: flex; align-items: flex-start; gap: .85rem; }
.ctc-info-icon { font-size: 1.25rem; color: #1d4ed8; margin-top: .15rem; }
.ctc-info-label { font-size: .8rem; color: #6b7280; text-transform: uppercase; letter-spacing: .03em; }
.ctc-info-value { font-size: 1rem; color: #111827; font-weight: 600; text-decoration: none; }
.ctc-info-value:hover { color: #1d4ed8; }

.ctc-social { display: flex; gap: .6rem; margin-top: 1.75rem; }
.ctc-social-btn {
  display: flex; align-items: center; justify-content: center;
  width: 40px; height: 40px; border-radius: 50%;
  background: #fff; border: 1px solid #e5e7eb; color: #1d4ed8;
  font-size: 1.1rem; transition: transform .15s, box-shadow .15s;
}
.ctc-social-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,.08); color: #1d4ed8; }

.ctc-cta { display: flex; flex-direction: column; align-items: flex-start; justify-content: center; }
.ctc-cta-icon { font-size: 2rem; color: #1d4ed8; margin-bottom: .75rem; }
</style>
