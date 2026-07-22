<template>
  <div class="tac-card" :class="{ 'tac-card--selected': selected }" role="button" @click="$emit('select', candidate)">
    <div class="d-flex justify-content-between align-items-start">
      <div>
        <div class="fw-semibold">{{ candidate.full_name }}</div>
        <div class="text-muted small">{{ candidate.email }}</div>
      </div>
      <span class="badge" :class="candidate.status_label === 'available' ? 'bg-success-subtle text-success' : 'bg-secondary-subtle text-secondary'">
        {{ candidate.status_label === 'available' ? 'Disponible' : 'Ocupado' }}
      </span>
    </div>
    <div class="d-flex flex-wrap gap-1 mt-2">
      <span v-for="s in candidate.specialties" :key="s" class="badge bg-info-subtle text-info border-0">{{ s }}</span>
    </div>
    <div class="d-flex gap-3 mt-2 small text-muted">
      <span v-if="candidate.average_rating != null"><i class="bi bi-star-fill text-warning me-1"></i>{{ candidate.average_rating.toFixed(1) }}</span>
      <span><i class="bi bi-briefcase me-1"></i>{{ candidate.experience_count }} exp.</span>
      <span v-if="candidate.city"><i class="bi bi-geo-alt me-1"></i>{{ candidate.city }}</span>
    </div>
    <div v-if="selected" class="tac-check"><i class="bi bi-check-circle-fill"></i></div>
  </div>
</template>

<script setup>
defineProps({
  candidate: { type: Object, required: true },
  selected: { type: Boolean, default: false },
});
defineEmits(['select']);
</script>

<style scoped>
.tac-card { position: relative; border: 1px solid #e5e7eb; border-radius: 10px; padding: 12px 14px; cursor: pointer; transition: all .15s; }
.tac-card:hover { border-color: #93c5fd; }
.tac-card--selected { border-color: #2563eb; background: #eff6ff; box-shadow: 0 0 0 2px rgba(37,99,235,.15); }
.tac-check { position: absolute; top: 10px; right: 10px; color: #2563eb; font-size: 1.1rem; }
</style>
