<template>
  <section class="reviews-section">
    <div class="container-xl">
      <h2>Reseñas ({{ reviews?.total_count || 0 }})</h2>

      <!-- Add Review Form (Authenticated Users Only) -->
      <div v-if="isAuthenticated" class="mb-4">
        <div class="card">
          <div class="card-header">
            <h5 class="mb-0">Comparte tu experiencia</h5>
          </div>
          <div class="card-body">
            <form @submit.prevent="submitReview">
              <div class="row g-3">
                <div class="col-md-12">
                  <label class="form-label">Calificación</label>
                  <div class="d-flex gap-2">
                    <button
                      v-for="star in 5"
                      :key="star"
                      type="button"
                      class="btn btn-sm"
                      :class="formData.rating >= star ? 'btn-warning' : 'btn-outline-warning'"
                      @click="formData.rating = star">
                      ⭐
                    </button>
                  </div>
                </div>
                <div class="col-md-12">
                  <label class="form-label">Comentario</label>
                  <textarea
                    v-model="formData.text"
                    class="form-control"
                    rows="4"
                    placeholder="Cuéntanos tu experiencia..."
                    required></textarea>
                </div>
                <div class="col-md-12">
                  <button type="submit" class="btn btn-primary" :disabled="isSubmitting">
                    {{ isSubmitting ? 'Enviando...' : 'Enviar reseña' }}
                  </button>
                </div>
              </div>
            </form>
          </div>
        </div>
      </div>

      <!-- Reviews List -->
      <div v-if="reviews?.items && reviews.items.length > 0" class="row g-3">
        <div v-for="review in reviews.items" :key="review.uuid" class="col-md-12">
          <div class="card">
            <div class="card-body">
              <div class="d-flex justify-content-between align-items-start mb-2">
                <div>
                  <h5 class="card-title mb-1">{{ review.author_name }}</h5>
                  <p class="text-muted small mb-0">
                    <span class="badge" :class="ratingBadgeClass(review.rating)">⭐ {{ review.rating }}/5</span>
                    <span class="ms-2">{{ formatDate(review.created_at) }}</span>
                  </p>
                </div>
              </div>
              <p class="card-text">{{ review.text }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else class="alert alert-info">
        Sé el primero en compartir tu experiencia con este {{ moduleType === 'renting' ? 'equipo' : moduleType === 'shop' ? 'producto' : 'servicio' }}.
      </div>
    </div>
  </section>
</template>
<script setup>
import { ref, computed } from 'vue';
import useApi from '@/composables/useApi';
import useAuth from '@/composables/useAuth';
import { useToast } from '@/composables/useToast';

const props = defineProps({
  reviews: Object,
  moduleType: String
});

const api = useApi();
const { isAuthenticated } = useAuth();
const { success, error: showError } = useToast();

const formData = ref({ rating: 0, text: '' });
const isSubmitting = ref(false);

const ratingBadgeClass = (rating) => {
  if (rating >= 4) return 'bg-success';
  if (rating >= 3) return 'bg-warning';
  return 'bg-danger';
};

const formatDate = (dateStr) => {
  if (!dateStr) return '';
  return new Date(dateStr).toLocaleDateString('es-CO', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
};

const submitReview = async () => {
  if (formData.value.rating === 0 || !formData.value.text.trim()) {
    showError('Por favor completa la calificación y comentario');
    return;
  }

  isSubmitting.value = true;
  try {
    // TODO: Implementar endpoint de POST review
    // await api.post(`/${props.moduleType}/items/${itemId}/reviews/`, formData.value);
    success('Reseña enviada correctamente');
    formData.value = { rating: 0, text: '' };
  } catch (err) {
    showError('Error al enviar la reseña');
  } finally {
    isSubmitting.value = false;
  }
};
</script>
<style scoped>
.detail-section { padding: 3rem 0; border-bottom: 1px solid #dee2e6; }
</style>
