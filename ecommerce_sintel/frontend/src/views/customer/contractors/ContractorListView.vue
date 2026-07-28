<template>
  <div class="contractor-list">

    <!-- Hero -->
    <div class="contractor-hero">
      <div class="container-xl py-5">
        <div class="row align-items-center g-4">
          <div class="col-md-7">
            <div class="d-flex align-items-center gap-3 mb-3">
              <div class="hero-icon">
                <i class="bi bi-people-fill fs-4 text-white"></i>
              </div>
              <span class="badge bg-amber text-dark fw-semibold px-3 py-2">Marketplace de profesionales</span>
            </div>
            <h1 class="display-6 fw-bold mb-2">Contratistas</h1>
            <p class="text-secondary mb-4 fs-6">
              Encuentra tecnicos, profesionales y especialistas verificados para tu proyecto.
            </p>
          </div>
        </div>
      </div>
    </div>

    <div class="container-xl py-5">

      <!-- Busqueda y filtros -->
      <div class="row mb-4 g-3">
        <div class="col-lg-5">
          <div class="input-group shadow-sm">
            <span class="input-group-text bg-white border-end-0">
              <i class="bi bi-search text-muted"></i>
            </span>
            <input
              v-model="search"
              type="text"
              class="form-control border-start-0 ps-0"
              placeholder="Buscar contratista..."
            >
          </div>
        </div>
        <div class="col-lg-3">
          <select v-model="filterType" class="form-select shadow-sm">
            <option value="">Todos los tipos</option>
            <option value="TECHNICIAN">Tecnico</option>
            <option value="PROFESSIONAL">Profesional</option>
            <option value="SPECIALIST">Especialista</option>
          </select>
        </div>
      </div>

      <!-- Loading -->
      <div v-if="loading" class="py-5 text-center">
        <span class="spinner-border text-primary"></span>
      </div>

      <!-- Grid de contratistas -->
      <div v-else-if="filtered.length" class="row g-4">
        <div v-for="c in filtered" :key="c.uuid" class="col-md-6 col-lg-4">
          <RouterLink :to="{ name: 'contractor-profile', params: { uuid: c.uuid } }" class="text-decoration-none">
            <div class="contractor-card h-100">
              <div class="d-flex align-items-center gap-3 mb-3">
                <div class="contractor-avatar">
                  <img v-if="c.profile_picture" :src="c.profile_picture" alt="" class="avatar-img">
                  <span v-else class="avatar-initials">{{ initials(c) }}</span>
                </div>
                <div class="flex-grow-1 min-w-0">
                  <div class="fw-bold text-truncate">{{ c.first_name }} {{ c.last_name }}</div>
                  <span class="badge type-badge">{{ typeLabel(c.user_type) }}</span>
                </div>
              </div>

              <div v-if="c.bio" class="bio-text text-muted small mb-3">{{ truncate(c.bio, 100) }}</div>

              <div class="d-flex align-items-center gap-2 mb-3">
                <StarRating :rating="c.average_rating" :readOnly="true" :size="16" :showValue="true" :allowHalf="true" />
                <span class="text-muted small">({{ c.total_reviews }})</span>
              </div>

              <div v-if="c.hourly_rate" class="rate-chip">
                <i class="bi bi-clock me-1"></i>{{ formatPrice(c.hourly_rate) }} {{ c.currency }}/h
              </div>

              <div v-if="c.specialties?.length" class="d-flex flex-wrap gap-1 mt-3">
                <span v-for="s in c.specialties.slice(0, 3)" :key="s.id" class="badge bg-light text-dark border small">
                  {{ s.category.name }}
                </span>
                <span v-if="c.specialties.length > 3" class="badge bg-light text-muted border small">
                  +{{ c.specialties.length - 3 }}
                </span>
              </div>
            </div>
          </RouterLink>
        </div>
      </div>

      <!-- Vacio -->
      <div v-else class="py-5 text-center text-muted">
        <i class="bi bi-person-x fs-1 d-block mb-3 opacity-25"></i>
        <p>No se encontraron contratistas con esos criterios.</p>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import StarRating from '@/components/ui/StarRating.vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useEnums } from '@/composables/useEnums';
import { formatCOP } from '@/utils/money';

const api = useApi();
const toast = useToast();
const enums = useEnums();

const contractors = ref([]);
const loading = ref(true);
const search = ref('');
const filterType = ref('');

function typeLabel(t) { return enums.label('contractor-types', t, t); }

const filtered = computed(() => {
  const q = search.value.toLowerCase();
  return contractors.value.filter(c => {
    const matchType = !filterType.value || c.user_type === filterType.value;
    const matchSearch = !q ||
      (c.first_name + ' ' + c.last_name).toLowerCase().includes(q) ||
      (c.bio || '').toLowerCase().includes(q);
    return matchType && matchSearch;
  });
});

function initials(c) {
  return ((c.first_name?.[0] || '') + (c.last_name?.[0] || '')).toUpperCase() || '?';
}

function truncate(s, n) { return s.length > n ? s.slice(0, n) + '...' : s; }

function formatPrice(n) { return formatCOP(n); }

async function fetchContractors() {
  loading.value = true;
  try {
    const { data } = await api.get('auth/contractors/');
    contractors.value = Array.isArray(data) ? data : (data.results || []);
  } catch {
    toast.error('Error al cargar los contratistas');
  } finally {
    loading.value = false;
  }
}

onMounted(() => { fetchContractors(); enums.ensure('contractor-types'); });
</script>

<style scoped>
.contractor-hero {
  background: linear-gradient(135deg, #1e3a8a 0%, #1e40af 100%);
  color: #fff;
}
.hero-icon {
  width: 48px; height: 48px; background: rgba(255,255,255,.15); border-radius: 12px;
  display: flex; align-items: center; justify-content: center;
}
.bg-amber { background: #f59e0b !important; }

.contractor-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  padding: 20px;
  transition: box-shadow .2s, transform .2s;
}
.contractor-card:hover { box-shadow: 0 8px 24px rgba(0,0,0,.1); transform: translateY(-2px); }

.contractor-avatar {
  width: 52px; height: 52px; border-radius: 14px; overflow: hidden;
  background: #1e3a8a; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.avatar-img { width: 100%; height: 100%; object-fit: cover; }
.avatar-initials { color: #fff; font-weight: 700; font-size: 1.1rem; }

.type-badge { background: #eff6ff; color: #1d4ed8; font-size: .7rem; border-radius: 6px; }
.bio-text { line-height: 1.5; }
.rate-chip {
  display: inline-block; background: #f0fdf4; color: #166534;
  border: 1px solid #bbf7d0; border-radius: 8px; padding: 2px 10px; font-size: .8rem;
}
</style>
