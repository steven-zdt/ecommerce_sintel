<template>
  <div class="abu-view">
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
    </div>

    <div v-else-if="error" class="container py-5 text-center">
      <i class="bi bi-exclamation-circle text-danger fs-1"></i>
      <p class="text-muted mt-2">No pudimos cargar esta pagina. Intenta de nuevo mas tarde.</p>
      <button class="btn btn-outline-primary btn-sm" @click="fetchContent">Reintentar</button>
    </div>

    <template v-else-if="config?.is_visible">
      <!-- Hero -->
      <section class="abu-hero" :style="heroStyle">
        <div class="container">
          <h1 class="abu-hero-title">{{ config.title }}</h1>
          <p v-if="config.subtitle" class="abu-hero-subtitle">{{ config.subtitle }}</p>
        </div>
      </section>

      <div class="container py-5">
        <!-- Historia -->
        <section v-if="config.history" class="abu-section">
          <h2 class="abu-section-title"><i class="bi bi-book me-2"></i>Nuestra historia</h2>
          <p class="abu-text">{{ config.history }}</p>
        </section>

        <!-- Mision / Vision -->
        <section v-if="config.mission || config.vision" class="row g-4 abu-section">
          <div v-if="config.mission" class="col-md-6">
            <div class="abu-card">
              <i class="bi bi-bullseye abu-card-icon"></i>
              <h3 class="abu-card-title">Mision</h3>
              <p class="abu-text mb-0">{{ config.mission }}</p>
            </div>
          </div>
          <div v-if="config.vision" class="col-md-6">
            <div class="abu-card">
              <i class="bi bi-eye abu-card-icon"></i>
              <h3 class="abu-card-title">Vision</h3>
              <p class="abu-text mb-0">{{ config.vision }}</p>
            </div>
          </div>
        </section>

        <!-- Valores -->
        <section v-if="values.length" class="abu-section">
          <h2 class="abu-section-title text-center"><i class="bi bi-gem me-2"></i>Nuestros valores</h2>
          <div class="row g-4 mt-2">
            <div v-for="value in values" :key="value.uuid" class="col-md-4 col-sm-6">
              <div class="abu-value-card">
                <IconRenderer :icon="normalizeIconInput(value.icon_class)" size="2rem" class="abu-value-icon" />
                <h4 class="abu-value-title">{{ value.title }}</h4>
                <p class="abu-text small mb-0">{{ value.description }}</p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import useApi from '@/composables/useApi';
import IconRenderer from '@/components/ui/IconRenderer.vue';
import { normalizeIconInput } from '@/utils/iconShorthand';

const api = useApi();
const loading = ref(true);
const error = ref(false);
const config = ref(null);
const values = ref([]);

const heroStyle = computed(() => {
  if (!config.value?.hero_image) return {};
  return {
    backgroundImage: `linear-gradient(180deg, rgba(15,23,42,.55), rgba(15,23,42,.55)), url(${config.value.hero_image})`,
  };
});

async function fetchContent() {
  loading.value = true;
  error.value = false;
  try {
    const { data } = await api.get('core/about-us/');
    config.value = data.config;
    values.value = data.values || [];
  } catch (err) {
    error.value = true;
  } finally {
    loading.value = false;
  }
}

onMounted(fetchContent);
</script>

<style scoped>
.abu-hero {
  background: linear-gradient(135deg, #0f172a, #1d4ed8);
  background-size: cover;
  background-position: center;
  color: #fff;
  padding: 5rem 0 4rem;
  text-align: center;
}
.abu-hero-title { font-size: 2.25rem; font-weight: 800; margin-bottom: .5rem; }
.abu-hero-subtitle { font-size: 1.1rem; color: rgba(255,255,255,.85); max-width: 640px; margin: 0 auto; }

.abu-section { margin-bottom: 3rem; }
.abu-section:last-child { margin-bottom: 0; }
.abu-section-title { font-size: 1.5rem; font-weight: 700; color: #111827; margin-bottom: 1rem; }
.abu-text { color: #4b5563; line-height: 1.7; white-space: pre-line; }

.abu-card {
  background: #f8fafc; border: 1px solid #e5e7eb; border-radius: 16px;
  padding: 2rem; height: 100%;
}
.abu-card-icon { font-size: 1.75rem; color: #1d4ed8; margin-bottom: .75rem; display: block; }
.abu-card-title { font-size: 1.15rem; font-weight: 700; margin-bottom: .5rem; }

.abu-value-card {
  text-align: center; padding: 1.75rem 1.25rem; border-radius: 16px;
  border: 1px solid #e5e7eb; height: 100%;
  transition: transform .15s, box-shadow .15s;
}
.abu-value-card:hover { transform: translateY(-3px); box-shadow: 0 8px 24px rgba(0,0,0,.06); }
.abu-value-icon { color: #1d4ed8; margin-bottom: .75rem; }
.abu-value-title { font-size: 1.05rem; font-weight: 700; margin-bottom: .4rem; }
</style>
