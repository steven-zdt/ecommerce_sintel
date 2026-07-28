<template>
  <div class="bv-reviews" :style="accentStyle">
    <div class="bv-reviews-summary">
      <div class="bv-reviews-score">
        <strong>{{ averageRating || '—' }}</strong>
        <div class="bv-reviews-stars">
          <i v-for="n in 5" :key="n" class="bi" :class="n <= Math.round(averageRating) ? 'bi-star-fill' : 'bi-star'"></i>
        </div>
        <span>{{ reviews.length }} reseña{{ reviews.length === 1 ? '' : 's' }}</span>
      </div>
    </div>

    <div v-if="authStore.isAuthenticated && !myReview" class="bv-review-form">
      <p class="bv-review-form-title">Escribe tu reseña</p>
      <div class="bv-review-stars-input">
        <button
          v-for="n in 5"
          :key="n"
          type="button"
          class="bv-star-btn"
          :class="{ active: form.rating >= n }"
          @click="form.rating = n"
        >
          <i class="bi bi-star-fill"></i>
        </button>
      </div>
      <textarea
        v-model="form.comment"
        class="bv-review-textarea"
        rows="3"
        :placeholder="`Cuentanos tu experiencia con ${itemLabel}...`"
      ></textarea>
      <button
        type="button"
        class="bv-review-submit"
        :disabled="submitting || !form.rating || !form.comment.trim()"
        @click="submitReview"
      >
        <span v-if="submitting" class="spinner-border spinner-border-sm me-2"></span>
        Publicar reseña
      </button>
    </div>
    <div v-else-if="!authStore.isAuthenticated" class="bv-review-login-prompt">
      <RouterLink to="/login">Inicia sesion</RouterLink> para calificar {{ itemLabel }}.
    </div>

    <div v-if="reviews.length" class="bv-review-list">
      <article v-for="review in reviews" :key="review.uuid" class="bv-review-item">
        <div class="bv-review-item-head">
          <strong>{{ review.user_name }}</strong>
          <div class="bv-reviews-stars bv-reviews-stars--sm">
            <i v-for="n in 5" :key="n" class="bi" :class="n <= review.rating ? 'bi-star-fill' : 'bi-star'"></i>
          </div>
        </div>
        <p>{{ review.comment }}</p>
        <span class="bv-review-date">{{ formatDate(review.created_at) }}</span>
      </article>
    </div>
    <p v-else class="bv-review-empty">Aun no hay reseñas para {{ itemLabel }}.</p>
  </div>
</template>

<script setup>
/**
 * BaseReviews.vue -- fusion de renting/detail/EquipmentReviews.vue y
 * services/detail/ServiceReviews.vue (Fase 2 del PLAN_MAESTRO_FRONTEND_DESIGN_SYSTEM_Y_FORMULARIOS.md,
 * hallazgo §2.1: ambos archivos eran 173 lineas identicas salvo color/endpoint/texto).
 * `basePath` + `entityUuid` construyen el mismo endpoint REST que cada dominio ya
 * usaba (`renting/equipment/{uuid}/reviews|review/`, `services/services/{uuid}/reviews|review/`)
 * -- cero cambio de contrato de API.
 */
import { ref, computed, watch } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useErrorHandler } from '@/composables/useErrorHandler';
import { useAuthStore } from '@/store/auth';

const props = defineProps({
  basePath: { type: String, required: true }, // 'renting/equipment' | 'services/services'
  entityUuid: { type: String, required: true },
  accentColor: { type: String, default: '#7c3aed' },
  itemLabel: { type: String, default: 'este item' }, // "este equipo" | "este servicio"
});

const api = useApi();
const toast = useToast();
const { handleError } = useErrorHandler();
const authStore = useAuthStore();

const reviews = ref([]);
const submitting = ref(false);
const form = ref({ rating: 0, comment: '' });

// Tintes exactos ya usados en produccion (Equipment=azul, Service=ambar) -- se
// evita `color-mix()` (soporte de navegador incierto) a favor de un lookup con
// los mismos valores hex que ya se verificaron visualmente en ambos dominios.
const ACCENT_TINTS = {
  '#2563eb': { bg: '#eff6ff', border: '#bfdbfe', starDim: '#cbd5e1' },
  '#d97706': { bg: '#fffbeb', border: '#fde68a', starDim: '#e7d3a8' },
};
const accentStyle = computed(() => {
  const tint = ACCENT_TINTS[props.accentColor] || { bg: '#f8fafc', border: '#e2e8f0', starDim: '#cbd5e1' };
  return {
    '--rv-accent': props.accentColor,
    '--rv-accent-bg': tint.bg,
    '--rv-accent-border': tint.border,
    '--rv-star-dim': tint.starDim,
  };
});

const averageRating = computed(() => {
  if (!reviews.value.length) return 0;
  const sum = reviews.value.reduce((total, r) => total + r.rating, 0);
  return Math.round((sum / reviews.value.length) * 10) / 10;
});

const myReview = computed(() =>
  reviews.value.some((r) => authStore.isAuthenticated && r.user_email === authStore.user?.email),
);

function formatDate(value) {
  if (!value) return '';
  return new Date(value).toLocaleDateString('es-CO', { year: 'numeric', month: 'short', day: 'numeric' });
}

async function fetchReviews() {
  if (!props.entityUuid) return;
  try {
    const res = await api.get(`${props.basePath}/${props.entityUuid}/reviews/`);
    reviews.value = res.data.results || res.data;
  } catch {
    reviews.value = [];
  }
}

async function submitReview() {
  submitting.value = true;
  try {
    await api.post(`${props.basePath}/${props.entityUuid}/review/`, {
      rating: form.value.rating,
      comment: form.value.comment.trim(),
    });
    form.value = { rating: 0, comment: '' };
    await fetchReviews();
    toast.success('Gracias por tu reseña');
  } catch (e) {
    handleError(e, 'No se pudo publicar la reseña');
  } finally {
    submitting.value = false;
  }
}

watch(() => props.entityUuid, fetchReviews, { immediate: true });

defineExpose({ fetchReviews });
</script>

<style scoped>
.bv-reviews-summary { display: flex; margin-bottom: 1rem; }
.bv-reviews-score { display: flex; align-items: center; gap: .6rem; }
.bv-reviews-score strong { font-size: 1.6rem; font-weight: 900; color: #0f172a; }
.bv-reviews-stars i { color: var(--rv-accent); font-size: .85rem; margin-right: 1px; }
.bv-reviews-stars--sm i { font-size: .72rem; }
.bv-reviews-score span { color: #64748b; font-size: .78rem; margin-left: .3rem; }

.bv-review-form {
  background: var(--rv-accent-bg);
  border: 1px solid var(--rv-accent-border);
  border-radius: 14px;
  padding: 1rem;
  margin-bottom: 1.25rem;
}
.bv-review-form-title { font-weight: 800; color: #0f172a; font-size: .88rem; margin: 0 0 .6rem; }
.bv-review-stars-input { display: flex; gap: .3rem; margin-bottom: .7rem; }
.bv-star-btn {
  border: 0; background: none; color: var(--rv-star-dim); font-size: 1.3rem; padding: 0; cursor: pointer;
  transition: color .12s ease;
}
.bv-star-btn.active, .bv-star-btn:hover { color: var(--rv-accent); }
.bv-review-textarea {
  width: 100%; border: 1px solid var(--rv-accent-border); border-radius: 10px; padding: .6rem .75rem;
  font-size: .85rem; resize: vertical; margin-bottom: .7rem;
}
.bv-review-submit {
  border: 0; background: var(--rv-accent); color: #fff; border-radius: 999px;
  padding: .55rem 1.1rem; font-size: .82rem; font-weight: 750; cursor: pointer;
}
.bv-review-submit:disabled { opacity: .5; cursor: not-allowed; }

.bv-review-login-prompt {
  background: var(--rv-accent-bg); border: 1px solid var(--rv-accent-border); border-radius: 12px;
  padding: .85rem 1rem; font-size: .84rem; color: #1f2937; margin-bottom: 1.25rem;
}
.bv-review-login-prompt a { color: var(--rv-accent); font-weight: 750; }

.bv-review-list { display: flex; flex-direction: column; gap: .75rem; }
.bv-review-item { border: 1px solid #e2e8f0; border-radius: 12px; padding: .85rem; background: #fff; }
.bv-review-item-head { display: flex; align-items: center; justify-content: space-between; gap: .6rem; margin-bottom: .4rem; }
.bv-review-item-head strong { color: #0f172a; font-size: .84rem; }
.bv-review-item p { color: #475569; font-size: .82rem; line-height: 1.55; margin: 0; }
.bv-review-date { display: block; color: #94a3b8; font-size: .7rem; margin-top: .4rem; }
.bv-review-empty { color: #94a3b8; font-size: .84rem; }
</style>
