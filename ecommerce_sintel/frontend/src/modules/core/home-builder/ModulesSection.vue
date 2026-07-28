<template>
  <section>
    <div class="hcb-section-header">
      <div>
        <h2 class="hcb-section-title">Modulos</h2>
        <p class="hcb-section-sub">Controla que secciones se muestran, su layout y cuantos items destacados.</p>
      </div>
      <button class="hcb-btn hcb-btn--primary" @click="openModuleForm()">
        <i class="bi bi-plus-lg"></i> Nuevo modulo
      </button>
    </div>

    <div v-if="loadingModules" class="hcb-loading">
      <div class="spinner-border text-primary"></div>
    </div>

    <div v-else class="hcb-modules-grid">
      <div
        v-for="mod in modulesOrdered"
        :key="mod.uuid"
        :class="['hcb-module-card', !mod.is_visible && 'hcb-module-card--hidden']"
      >
        <div class="hcb-module-card__color" :style="{ background: mod.module_color }">
          <i :class="['bi', mod.module_icon]"></i>
        </div>
        <div class="hcb-module-card__body">
          <div class="hcb-module-card__label">{{ mod.module_label }}</div>
          <div class="hcb-module-card__meta">
            <span class="hcb-chip">{{ displayTypeLabel(mod.display_type) }}</span>
            <span class="hcb-chip">{{ mod.featured_items_limit }} items</span>
            <span :class="['hcb-chip', mod.is_visible ? 'hcb-chip--green' : 'hcb-chip--gray']">
              {{ mod.is_visible ? 'Visible' : 'Oculto' }}
            </span>
          </div>
        </div>
        <div class="hcb-module-card__actions">
          <button class="hcb-icon-btn" @click="openModuleForm(mod)"><i class="bi bi-pencil"></i></button>
          <button
            v-if="!mod.is_core"
            class="hcb-icon-btn hcb-icon-btn--danger"
            @click="deleteModule(mod)"
          ><i class="bi bi-trash"></i></button>
        </div>
      </div>
      <div v-if="!modulesOrdered.length" class="hcb-empty">Sin modulos configurados.</div>
    </div>

    <!-- Module Builder: tiene su propio Teleport, debe vivir fuera de cualquier otro Teleport -->
    <ModuleBuilderModal
      v-if="showModuleModal"
      :module="editingModule"
      @close="closeModuleForm"
      @saved="onModuleSaved"
    />
  </section>
</template>

<script setup>
import { ref, computed } from 'vue';
import { storeToRefs } from 'pinia';
import { useToast } from '@/composables/useToast';
import { useCoreAdminStore } from '@/store/coreAdmin';
import ModuleBuilderModal from '../ModuleBuilderModal.vue';

const toast = useToast();
const store = useCoreAdminStore();
const { modules, modulesLoading: loadingModules } = storeToRefs(store);

const showModuleModal = ref(false);
const editingModule   = ref(null);

const modulesOrdered = computed(() =>
  [...modules.value].sort((a, b) => (a.display_order || 0) - (b.display_order || 0))
);

const DISPLAY_TYPE_LABELS = {
  grid: 'Grid', grid_modern: 'Grid moderno', slider: 'Slider', carousel: 'Carrusel',
  cards_h: 'Cards H', cards_v: 'Cards V', hero: 'Hero', banner: 'Banner',
  list: 'Lista', timeline: 'Timeline', accordion: 'Accordion', tabs: 'Tabs',
  masonry: 'Masonry', highlight: 'Destacados', premium: 'Premium', compact: 'Compacto',
  split: 'Split', minimal: 'Minimalista',
};
function displayTypeLabel(t) { return DISPLAY_TYPE_LABELS[t] || t || 'Grid'; }

// El fetch inicial lo dispara el padre (HomeConfigView.vue, onMounted) para que los
// contadores del sidebar y el preview compartido tengan datos aunque esta seccion
// nunca se haya montado -- aqui solo se re-fetchea despues de una mutacion propia.
async function fetchModules() {
  await store.fetchModules();
}
function openModuleForm(mod = null) {
  editingModule.value = mod;
  showModuleModal.value = true;
}
function closeModuleForm() { showModuleModal.value = false; editingModule.value = null; }
async function onModuleSaved() {
  closeModuleForm();
  await fetchModules();
}
async function deleteModule(mod) {
  if (!confirm(`Eliminar modulo "${mod.module_label}"?`)) return;
  const res = await store.deleteModule(mod.uuid);
  if (res.ok) {
    toast.success('Modulo eliminado.');
    await fetchModules();
  } else {
    toast.error('No se pudo eliminar.');
  }
}
</script>
