<template>
  <div class="p-3">
    <RouterLink to="/panel/cotizaciones" class="text-decoration-none small text-muted d-inline-flex align-items-center mb-3">
      <i class="bi bi-arrow-left me-1"></i> Volver a Cotizaciones
    </RouterLink>

    <div v-if="store.loading && !template" class="text-center py-5">
      <div class="spinner-border"></div>
    </div>

    <template v-else-if="template">
      <div class="d-flex align-items-center justify-content-between mb-4">
        <div>
          <h4 class="fw-bold mb-1">{{ template.name }}</h4>
          <p class="text-muted small mb-0">
            {{ template.category?.name || 'Sin categoría' }}
            <span v-if="template.subcategory"> / {{ template.subcategory.name }}</span> ·
            {{ template.service_type?.name || 'Sin tipo de servicio' }} ·
            <span :class="template.is_active ? 'text-success' : 'text-secondary'">
              {{ template.is_active ? 'Activa' : 'Inactiva' }}
            </span>
          </p>
        </div>
      </div>

      <ul class="nav nav-tabs mb-4">
        <li class="nav-item" v-for="t in tabs" :key="t.key">
          <button class="nav-link" :class="{ active: activeTab === t.key }" @click="activeTab = t.key">
            <i :class="['bi', t.icon, 'me-1']"></i>{{ t.label }}
          </button>
        </li>
      </ul>

      <EquipmentQuestionsPanel v-if="activeTab === 'equipment'" :template-uuid="uuid" />
      <MaterialQuestionsPanel v-else-if="activeTab === 'materials'" :template-uuid="uuid" />
      <LaborQuestionsPanel v-else-if="activeTab === 'labor'" :template-uuid="uuid" />
      <PreviewTemplate v-else-if="activeTab === 'preview'" :template-uuid="uuid" />
    </template>

    <div v-else class="text-center text-muted py-5">Plantilla no encontrada.</div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useQuoteTemplateBuilderStore } from '@/store/quotesAdmin/templateBuilder';
import EquipmentQuestionsPanel from './EquipmentQuestionsPanel.vue';
import MaterialQuestionsPanel from './MaterialQuestionsPanel.vue';
import LaborQuestionsPanel from './LaborQuestionsPanel.vue';
import PreviewTemplate from './PreviewTemplate.vue';

const route = useRoute();
const store = useQuoteTemplateBuilderStore();

const uuid = route.params.uuid;
const template = computed(() => store.currentTemplate);

const tabs = [
  { key: 'equipment', label: 'Equipos', icon: 'bi-hdd-stack' },
  { key: 'materials', label: 'Materiales', icon: 'bi-box-seam' },
  { key: 'labor', label: 'Mano de Obra', icon: 'bi-person-workspace' },
  { key: 'preview', label: 'Vista previa', icon: 'bi-eye' },
];
const activeTab = ref('equipment');

onMounted(() => {
  store.fetchTemplateDetail(uuid);
});
</script>
