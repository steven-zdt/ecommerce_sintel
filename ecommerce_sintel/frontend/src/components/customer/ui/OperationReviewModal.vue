<template>
  <div class="review-block">
    <div class="stars-row">
      <label>Calificacion general</label>
      <div class="stars">
        <button
          v-for="n in 5"
          :key="n"
          class="star-btn"
          :class="{ filled: n <= form.rating }"
          @click="form.rating = n"
        >
          <i :class="n <= form.rating ? 'bi bi-star-fill' : 'bi bi-star'"></i>
        </button>
      </div>
    </div>

    <div class="sub-ratings">
      <div v-for="field in subFields" :key="field.key" class="sub-rating">
        <span class="sub-label">{{ field.label }}</span>
        <div class="stars stars--sm">
          <button
            v-for="n in 5"
            :key="n"
            class="star-btn"
            :class="{ filled: n <= form[field.key] }"
            @click="form[field.key] = n"
          >
            <i :class="n <= form[field.key] ? 'bi bi-star-fill' : 'bi bi-star'"></i>
          </button>
        </div>
      </div>
    </div>

    <textarea
      v-model="form.comment"
      class="form-control mt-3"
      rows="3"
      placeholder="Cuéntanos sobre tu experiencia..."
    ></textarea>

    <button
      class="btn btn-primary mt-3"
      :disabled="submitting"
      @click="submit"
    >
      <span v-if="submitting" class="spinner-border spinner-border-sm me-1"></span>
      Enviar calificacion
    </button>

    <p v-if="success" class="success-msg mt-2">Gracias por tu calificacion.</p>
    <p v-if="error"   class="error-msg mt-2">{{ error }}</p>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue';
import useApi from '@/composables/useApi';

const props = defineProps({ ticket: { type: Object, required: true } });
const emit  = defineEmits(['reviewed']);

const api = useApi();

const form = reactive({
  rating:             5,
  quality_rating:     5,
  punctuality_rating: 5,
  condition_rating:   5,
  comment:            '',
});

const subFields = [
  { key: 'quality_rating',     label: 'Calidad' },
  { key: 'punctuality_rating', label: 'Puntualidad' },
  { key: 'condition_rating',   label: 'Estado del equipo' },
];

const submitting = ref(false);
const success    = ref(false);
const error      = ref('');

async function submit() {
  submitting.value = true;
  error.value      = '';
  try {
    await api.post(`operations/my/${props.ticket.uuid}/review/`, { ...form });
    success.value = true;
    emit('reviewed');
  } catch (e) {
    error.value = e?.response?.data?.detail || 'Error al enviar la calificacion.';
  } finally {
    submitting.value = false;
  }
}
</script>

<style scoped>
.review-block {
  background: #fff; border: 1px solid #e5e7eb;
  border-radius: 14px; padding: 24px;
}

.stars-row { display: flex; align-items: center; gap: 16px; margin-bottom: 16px; }
.stars-row label { font-size: 0.875rem; font-weight: 600; color: #374151; }

.sub-ratings { display: flex; flex-direction: column; gap: 10px; }
.sub-rating  { display: flex; align-items: center; gap: 12px; }
.sub-label   { font-size: 0.825rem; color: #6b7280; min-width: 140px; }

.stars { display: flex; gap: 4px; }
.stars--sm .star-btn { font-size: 0.9rem; }

.star-btn {
  background: none; border: none; cursor: pointer;
  font-size: 1.3rem; color: #d1d5db; padding: 0 2px;
  transition: color .1s;
}
.star-btn.filled { color: #f59e0b; }
.star-btn:hover  { color: #f59e0b; }

.success-msg { color: #16a34a; font-size: 0.825rem; }
.error-msg   { color: #dc2626; font-size: 0.825rem; }
</style>
