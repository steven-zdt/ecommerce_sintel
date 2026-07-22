<template>
  <div class="p-3">
    <div class="mb-4">
      <h4 class="fw-bold mb-1">Cotizaciones</h4>
      <p class="text-muted small mb-0">Constructor de cuestionarios técnicos — configura preguntas sin tocar código. El cliente responde, el asesor cotiza.</p>
    </div>

    <ul class="nav nav-tabs mb-4">
      <li class="nav-item" v-for="t in mainTabs" :key="t.key">
        <button class="nav-link" :class="{ active: mainTab === t.key }" @click="mainTab = t.key">
          <i :class="['bi', t.icon, 'me-1']"></i>{{ t.label }}
        </button>
      </li>
    </ul>

    <QuotationList v-if="mainTab === 'quotations'" />
    <QuoteTemplateList v-else-if="mainTab === 'templates'" />

    <template v-else-if="mainTab === 'catalogs'">
      <div class="catalog-hint d-flex align-items-center gap-2 mb-3">
        <i class="bi bi-info-circle-fill"></i>
        <span class="small">
          Jerarquía real de la taxonomía: <strong>Tipo de Servicio → Categoría → Subcategoría → Tipo de Instalación</strong>.
          Cada Categoría pertenece a un Tipo de Servicio; cada Tipo de Instalación pertenece a una Subcategoría específica.
        </span>
      </div>

      <ul class="nav nav-pills gap-2 mb-4">
        <li class="nav-item" v-for="t in catalogTabs" :key="t.key">
          <button class="nav-link catalog-pill" :class="{ active: catalogTab === t.key }" @click="catalogTab = t.key">
            <i :class="['bi', t.icon, 'me-1']"></i>{{ t.label }}
          </button>
        </li>
      </ul>

      <QuoteAttributeList
        v-if="catalogTab === 'service-types'"
        kind="SERVICE_TYPE" title="Tipos de Servicio" placeholder="Nueva instalación"
      />
      <QuoteTemplateCategoryList v-else-if="catalogTab === 'categories'" />
      <QuoteTemplateSubcategoryList v-else-if="catalogTab === 'subcategories'" />
      <QuoteAttributeList
        v-else-if="catalogTab === 'installation-types'"
        kind="INSTALLATION_TYPE" title="Tipos de Instalación" placeholder="Altura doble, Confinamiento..."
      />
      <QuoteAttributeList
        v-else-if="catalogTab === 'system-types'"
        kind="SYSTEM_TYPE" title="Tipos de Sistema" placeholder="CCTV"
      />
      <QuoteEquipmentTypeList v-else-if="catalogTab === 'equipment-types'" />
    </template>
  </div>
</template>

<script setup>
import { ref } from 'vue';
import QuotationList from './QuotationList.vue';
import QuoteTemplateList from './QuoteTemplateList.vue';
import QuoteTemplateCategoryList from './QuoteTemplateCategoryList.vue';
import QuoteTemplateSubcategoryList from './QuoteTemplateSubcategoryList.vue';
import QuoteEquipmentTypeList from './QuoteEquipmentTypeList.vue';
import QuoteAttributeList from './QuoteAttributeList.vue';

const mainTabs = [
  { key: 'quotations', label: 'Solicitudes', icon: 'bi-file-earmark-text' },
  { key: 'templates', label: 'Plantillas', icon: 'bi-collection' },
  { key: 'catalogs', label: 'Catálogos', icon: 'bi-tags' },
];

const catalogTabs = [
  { key: 'service-types', label: 'Tipos de Servicio', icon: 'bi-wrench-adjustable' },
  { key: 'categories', label: 'Categorías', icon: 'bi-tags' },
  { key: 'subcategories', label: 'Subcategorías', icon: 'bi-tag' },
  { key: 'installation-types', label: 'Tipos de Instalación', icon: 'bi-tools' },
  { key: 'system-types', label: 'Tipos de Sistema', icon: 'bi-cpu' },
  { key: 'equipment-types', label: 'Tipos de Equipo', icon: 'bi-hdd-stack' },
];

const mainTab = ref('quotations');
const catalogTab = ref('service-types');
</script>

<style scoped>
.catalog-hint {
  background: #f3e8ff; color: #6b21a8; border-radius: 12px; padding: 0.6rem 1rem;
}
.catalog-pill {
  border-radius: 999px !important; border: 1.5px solid #e2e8f0 !important;
  color: #475569 !important; font-size: 0.85rem;
}
.catalog-pill.active {
  background: #7c3aed !important; border-color: #7c3aed !important; color: #fff !important;
}
</style>
