<template>
  <div>
    <!-- Header de detalle -->
    <div class="d-flex align-items-center gap-3 mb-4">
      <button class="btn btn-sm btn-light border" @click="router.back()">
        <i class="bi bi-arrow-left me-1"></i> Volver
      </button>
      <div>
        <h5 class="fw-bold mb-0">{{ equipment?.name || 'Cargando...' }}</h5>
        <small class="text-muted">{{ equipment?.category?.name }} &bull; {{ equipment?.brand?.name || 'Sin marca' }}</small>
      </div>
      <div class="ms-auto">
        <span
          class="badge rounded-pill fs-6 px-3 py-2"
          :class="equipment?.is_active ? 'bg-success-subtle text-success' : 'bg-danger-subtle text-danger'"
        >
          {{ equipment?.is_active ? 'Activo' : 'Inactivo' }}
        </span>
      </div>
    </div>

    <!-- Tabs de navegación -->
    <ul class="nav nav-tabs border-bottom mb-4">
      <li class="nav-item" v-for="tab in tabs" :key="tab.key">
        <button
          class="nav-link fw-medium"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          <i :class="tab.icon + ' me-2'"></i>{{ tab.label }}
        </button>
      </li>
    </ul>

    <!-- TAB: Variantes -->
    <VariantsPanel
      v-if="activeTab === 'variants'"
      :equipment-uuid="equipmentUuid"
    />

    <!-- TAB: Logística -->
    <LogisticsPanel
      v-if="activeTab === 'logistics'"
      :equipment-uuid="equipmentUuid"
    />

    <!-- TAB: Reglas de Costo -->
    <CostRulesPanel
      v-if="activeTab === 'costs'"
      :equipment-uuid="equipmentUuid"
      :variant-uuid="primaryVariantUuid"
    />

    <!-- TAB: Bloqueos -->
    <BlocksPanel
      v-if="activeTab === 'blocks'"
      :equipment-uuid="equipmentUuid"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useRentingCatalogAdminStore } from '@/store/rentingAdmin/catalog';
import VariantsPanel from './panels/VariantsPanel.vue';
import LogisticsPanel from './panels/LogisticsPanel.vue';
import CostRulesPanel from './panels/CostRulesPanel.vue';
import BlocksPanel from './panels/BlocksPanel.vue';

const route = useRoute();
const router = useRouter();
const store = useRentingCatalogAdminStore();

const equipmentUuid = computed(() => route.params.uuid);
const activeTab = ref('variants');

const equipment = computed(() => store.currentEquipment);
const primaryVariantUuid = computed(() => {
  const variants = store.variants;
  return variants.length ? variants[0].uuid : null;
});

const tabs = [
  { key: 'variants',  label: 'Variantes',      icon: 'bi bi-layers' },
  { key: 'logistics', label: 'Logística',       icon: 'bi bi-truck' },
  { key: 'costs',     label: 'Reglas de Costo', icon: 'bi bi-tags' },
  { key: 'blocks',    label: 'Bloqueos',        icon: 'bi bi-shield-lock' },
];

onMounted(async () => {
  await Promise.all([
    store.fetchEquipmentDetail(equipmentUuid.value),
    store.fetchVariants(equipmentUuid.value),
    store.fetchLogisticsConfig(equipmentUuid.value),
  ]);
});
</script>
