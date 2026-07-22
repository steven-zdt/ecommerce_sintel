<template>
  <div class="contractor-profile-view">

    <!-- Loading -->
    <div v-if="loading" class="py-5 text-center">
      <span class="spinner-border text-primary"></span>
    </div>

    <template v-else-if="profile">

      <!-- Cabecera del perfil -->
      <div class="profile-header">
        <div class="container-xl py-5">
          <div class="row align-items-center g-4">
            <div class="col-auto">
              <div class="profile-avatar">
                <img v-if="profile.profile_picture" :src="profile.profile_picture" alt="" class="avatar-img">
                <span v-else class="avatar-initials">{{ initials }}</span>
              </div>
            </div>
            <div class="col">
              <div class="d-flex align-items-center gap-2 mb-1 flex-wrap">
                <h1 class="h3 fw-bold mb-0">{{ profile.first_name }} {{ profile.last_name }}</h1>
                <span class="badge type-badge">{{ typeLabel(profile.user_type) }}</span>
              </div>
              <p v-if="profile.contractor_type" class="text-muted mb-2 small">{{ profile.contractor_type }}</p>

              <div class="d-flex align-items-center gap-3 flex-wrap mb-3">
                <div class="d-flex align-items-center gap-2">
                  <StarRating :rating="profile.average_rating" :readOnly="true" :size="18" :allowHalf="true" />
                  <span class="fw-semibold">{{ Number(profile.average_rating).toFixed(1) }}</span>
                  <span class="text-muted small">({{ profile.total_reviews }} resenas)</span>
                </div>
              </div>

              <div class="d-flex gap-2 flex-wrap">
                <div v-if="profile.hourly_rate" class="rate-chip">
                  <i class="bi bi-clock me-1"></i>{{ fmt(profile.hourly_rate) }} {{ profile.currency }}/h
                </div>
                <div v-if="profile.daily_rate" class="rate-chip">
                  <i class="bi bi-calendar2 me-1"></i>{{ fmt(profile.daily_rate) }} {{ profile.currency }}/dia
                </div>
                <div v-if="profile.project_rate" class="rate-chip">
                  <i class="bi bi-briefcase me-1"></i>{{ fmt(profile.project_rate) }} {{ profile.currency }}/proyecto
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="container-xl py-4">
        <div class="row g-4">

          <!-- Columna izquierda: Bio + especialidades -->
          <div class="col-lg-3">
            <div v-if="profile.bio" class="card-section mb-3">
              <h6 class="fw-bold mb-2">Sobre mi</h6>
              <p class="text-muted small mb-0" style="line-height:1.6">{{ profile.bio }}</p>
            </div>
            <div v-if="profile.specialties?.length" class="card-section mb-3">
              <h6 class="fw-bold mb-2">Especialidades</h6>
              <div class="d-flex flex-wrap gap-1">
                <span v-for="s in profile.specialties" :key="s.id" class="badge bg-primary-subtle text-primary border">
                  {{ s.category.name }}
                </span>
              </div>
            </div>
            <div v-if="profile.skills?.length" class="card-section">
              <h6 class="fw-bold mb-2">Habilidades</h6>
              <div class="d-flex flex-column gap-2">
                <div v-for="sk in profile.skills" :key="sk.id" class="d-flex justify-content-between align-items-center">
                  <span class="small">{{ sk.name }}</span>
                  <span class="badge bg-light text-muted border small">{{ sk.level || 'N/A' }}</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Columna derecha: Tabs -->
          <div class="col-lg-9">
            <ul class="nav nav-tabs mb-4">
              <li v-for="tab in tabs" :key="tab.key" class="nav-item">
                <button
                  class="nav-link"
                  :class="{ active: activeTab === tab.key }"
                  @click="activeTab = tab.key"
                >
                  <i :class="tab.icon" class="me-1"></i>{{ tab.label }}
                </button>
              </li>
            </ul>

            <!-- Tab: Experiencia -->
            <div v-if="activeTab === 'experience'">
              <div v-if="profile.professional_experiences?.length">
                <div v-for="exp in profile.professional_experiences" :key="exp.id" class="timeline-item mb-4">
                  <div class="d-flex justify-content-between align-items-start">
                    <div>
                      <div class="fw-bold">{{ exp.position }}</div>
                      <div class="text-muted small">{{ exp.company }}</div>
                    </div>
                    <div class="text-muted small text-end">
                      {{ formatDate(exp.start_date) }} — {{ exp.is_current ? 'Actualidad' : formatDate(exp.end_date) }}
                    </div>
                  </div>
                  <p v-if="exp.description" class="small text-muted mt-2 mb-0">{{ exp.description }}</p>
                </div>
              </div>
              <div v-else class="empty-state"><i class="bi bi-briefcase"></i><p>Sin experiencia registrada</p></div>
            </div>

            <!-- Tab: Educacion -->
            <div v-if="activeTab === 'education'">
              <div v-if="profile.academic_trainings?.length" class="mb-4">
                <h6 class="section-heading">Educacion academica</h6>
                <div v-for="a in profile.academic_trainings" :key="a.id" class="timeline-item mb-3">
                  <div class="fw-bold">{{ a.degree }}</div>
                  <div class="text-muted small">{{ a.institution }}<span v-if="a.field_of_study"> — {{ a.field_of_study }}</span></div>
                  <div class="text-muted small">{{ formatDate(a.start_date) }} — {{ a.is_current ? 'Actualidad' : formatDate(a.end_date) }}</div>
                </div>
              </div>
              <div v-if="profile.professional_courses?.length" class="mb-4">
                <h6 class="section-heading">Cursos</h6>
                <div v-for="c in profile.professional_courses" :key="c.id" class="timeline-item mb-3">
                  <div class="fw-bold">{{ c.title }}</div>
                  <div class="text-muted small">{{ c.institution }}<span v-if="c.hours"> · {{ c.hours }}h</span></div>
                  <div class="text-muted small">{{ formatDate(c.completion_date) }}</div>
                </div>
              </div>
              <div v-if="profile.professional_certifications?.length">
                <h6 class="section-heading">Certificaciones</h6>
                <div v-for="cert in profile.professional_certifications" :key="cert.id" class="timeline-item mb-3">
                  <div class="fw-bold">{{ cert.name }}</div>
                  <div class="text-muted small">{{ cert.issuing_organization }}</div>
                  <div class="text-muted small">Emitido: {{ formatDate(cert.issue_date) }}<span v-if="cert.expiration_date"> · Vence: {{ formatDate(cert.expiration_date) }}</span></div>
                </div>
              </div>
              <div v-if="!profile.academic_trainings?.length && !profile.professional_courses?.length && !profile.professional_certifications?.length" class="empty-state">
                <i class="bi bi-mortarboard"></i><p>Sin formacion registrada</p>
              </div>
            </div>

            <!-- Tab: Portafolio -->
            <div v-if="activeTab === 'portfolio'">
              <div v-if="profile.success_cases?.length" class="row g-3">
                <div v-for="sc in profile.success_cases" :key="sc.id" class="col-md-6">
                  <div class="portfolio-card">
                    <div v-if="sc.images?.length" class="portfolio-img-wrap mb-3">
                      <img :src="sc.images[0].image" alt="" class="portfolio-img">
                    </div>
                    <div class="fw-bold mb-1">{{ sc.title }}</div>
                    <p class="text-muted small mb-0">{{ sc.description }}</p>
                    <div v-if="sc.completion_date" class="text-muted small mt-1">{{ formatDate(sc.completion_date) }}</div>
                  </div>
                </div>
              </div>
              <div v-else class="empty-state"><i class="bi bi-images"></i><p>Sin casos de exito registrados</p></div>
            </div>

            <!-- Tab: Resenas -->
            <div v-if="activeTab === 'reviews'">
              <!-- Formulario de resena (solo autenticado y no es el mismo usuario) -->
              <div v-if="canReview" class="card-section mb-4">
                <h6 class="fw-bold mb-3">Dejar una resena</h6>
                <div class="row g-3 mb-3">
                  <div v-for="dim in reviewDimensions" :key="dim.key" class="col-sm-6">
                    <label class="form-label small fw-bold">{{ dim.label }}</label>
                    <StarRating :rating="reviewForm[dim.key]" @update:rating="v => reviewForm[dim.key] = v" :size="20" />
                  </div>
                </div>
                <textarea v-model="reviewForm.comment" class="form-control mb-3" rows="3" placeholder="Comentario (opcional)"></textarea>
                <button class="btn btn-primary btn-sm px-4" :disabled="submittingReview" @click="submitReview">
                  <span v-if="submittingReview" class="spinner-border spinner-border-sm me-2"></span>
                  Publicar resena
                </button>
              </div>

              <!-- Lista de resenas -->
              <div v-if="profile.reviews?.length">
                <div v-for="r in profile.reviews" :key="r.id" class="review-card mb-3">
                  <div class="d-flex justify-content-between align-items-start mb-2">
                    <div>
                      <span class="fw-bold">{{ r.reviewer_name }}</span>
                      <span class="text-muted small ms-2">{{ formatDate(r.created_at) }}</span>
                    </div>
                    <div class="d-flex align-items-center gap-1">
                      <StarRating :rating="averageRating(r)" :readOnly="true" :size="14" :allowHalf="true" />
                      <span class="text-muted small">{{ averageRating(r).toFixed(1) }}</span>
                    </div>
                  </div>
                  <p v-if="r.comment" class="small mb-0 text-muted">{{ r.comment }}</p>
                  <div class="d-flex gap-3 mt-2 flex-wrap">
                    <span v-for="dim in reviewDimensions" :key="dim.key" class="review-dim">
                      {{ dim.shortLabel }}: <strong>{{ r[dim.key] }}</strong>
                    </span>
                  </div>
                </div>
              </div>
              <div v-else class="empty-state"><i class="bi bi-chat-square-text"></i><p>Sin resenas aun</p></div>
            </div>

          </div>
        </div>
      </div>
    </template>

    <div v-else class="py-5 text-center text-muted">
      <p>Contratista no encontrado.</p>
    </div>

  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import StarRating from '@/components/ui/StarRating.vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useAuthStore } from '@/store/auth';
import { useEnums } from '@/composables/useEnums';

const route = useRoute();
const api = useApi();
const toast = useToast();
const authStore = useAuthStore();
const enums = useEnums();

const profile = ref(null);
const loading = ref(true);
const activeTab = ref('experience');
const submittingReview = ref(false);

const tabs = [
  { key: 'experience', label: 'Experiencia',  icon: 'bi bi-briefcase' },
  { key: 'education',  label: 'Educacion',    icon: 'bi bi-mortarboard' },
  { key: 'portfolio',  label: 'Portafolio',   icon: 'bi bi-images' },
  { key: 'reviews',    label: 'Resenas',      icon: 'bi bi-star' },
];

const reviewDimensions = [
  { key: 'quality_rating',         label: 'Calidad',       shortLabel: 'Cal' },
  { key: 'punctuality_rating',     label: 'Puntualidad',   shortLabel: 'Pun' },
  { key: 'professionalism_rating', label: 'Profesionalismo', shortLabel: 'Pro' },
  { key: 'communication_rating',   label: 'Comunicacion',  shortLabel: 'Com' },
  { key: 'compliance_rating',      label: 'Cumplimiento',  shortLabel: 'Cum' },
];

const reviewForm = ref({
  quality_rating: 5, punctuality_rating: 5, professionalism_rating: 5,
  communication_rating: 5, compliance_rating: 5, comment: '',
});

function typeLabel(t) { return enums.label('contractor-types', t, t); }

const initials = computed(() => {
  if (!profile.value) return '?';
  return ((profile.value.first_name?.[0] || '') + (profile.value.last_name?.[0] || '')).toUpperCase() || '?';
});

const canReview = computed(() =>
  authStore.isAuthenticated && profile.value?.email !== authStore.user?.email
);

function fmt(n) { return new Intl.NumberFormat('es-CO').format(n); }

function formatDate(d) {
  if (!d) return '';
  return new Date(d).toLocaleDateString('es-CO', { year: 'numeric', month: 'short' });
}

function averageRating(r) {
  return (r.quality_rating + r.punctuality_rating + r.professionalism_rating + r.communication_rating + r.compliance_rating) / 5;
}

async function fetchProfile() {
  loading.value = true;
  try {
    const { data } = await api.get(`auth/contractors/${route.params.uuid}/`);
    profile.value = data;
  } catch {
    toast.error('Error al cargar el perfil');
  } finally {
    loading.value = false;
  }
}

async function submitReview() {
  submittingReview.value = true;
  try {
    await api.post(`auth/contractors/${route.params.uuid}/review/`, reviewForm.value);
    toast.success('Resena publicada');
    await fetchProfile();
    reviewForm.value = { quality_rating: 5, punctuality_rating: 5, professionalism_rating: 5, communication_rating: 5, compliance_rating: 5, comment: '' };
  } catch (e) {
    toast.error(e.response?.data?.detail || 'Error al publicar la resena');
  } finally {
    submittingReview.value = false;
  }
}

onMounted(() => { fetchProfile(); enums.ensure('contractor-types'); });
</script>

<style scoped>
.profile-header {
  background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
  color: #fff;
}
.profile-avatar {
  width: 96px; height: 96px; border-radius: 20px; overflow: hidden;
  background: rgba(255,255,255,.2); flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
  border: 3px solid rgba(255,255,255,.4);
}
.avatar-img { width: 100%; height: 100%; object-fit: cover; }
.avatar-initials { color: #fff; font-weight: 700; font-size: 2rem; }

.type-badge { background: rgba(255,255,255,.15); color: #fff; border-radius: 8px; font-size: .75rem; }

.rate-chip {
  display: inline-block; background: rgba(255,255,255,.15); color: #fff;
  border: 1px solid rgba(255,255,255,.25); border-radius: 8px; padding: 3px 12px; font-size: .8rem;
}

.card-section {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px;
}
.section-heading { font-size: .85rem; font-weight: 700; text-transform: uppercase; color: #6b7280; margin-bottom: 12px; }

.timeline-item {
  border-left: 3px solid #e5e7eb; padding-left: 16px; padding-bottom: 4px;
}

.portfolio-card {
  background: #fff; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px;
}
.portfolio-img-wrap { border-radius: 8px; overflow: hidden; height: 160px; }
.portfolio-img { width: 100%; height: 100%; object-fit: cover; }

.review-card {
  background: #f9fafb; border: 1px solid #e5e7eb; border-radius: 12px; padding: 16px;
}
.review-dim { font-size: .75rem; color: #6b7280; }

.empty-state { padding: 40px; text-align: center; color: #9ca3af; }
.empty-state i { font-size: 2.5rem; display: block; margin-bottom: 12px; opacity: .4; }
.empty-state p { margin: 0; }
</style>
