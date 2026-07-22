<template>
  <div>
    <h1 class="step-title">¿Qué necesitas cotizar?</h1>
    <p class="step-subtitle">Elige el tipo de proyecto — nosotros nos encargamos de calcular todo.</p>

    <nav v-if="level !== 'category'" class="qw-crumbs mb-3">
      <button class="crumb-link" @click="goToCategory">Categorías</button>
      <span class="mx-1">/</span>
      <button v-if="level === 'template'" class="crumb-link" @click="goToSubcategory">{{ selectedCategory?.name }}</button>
      <span v-else class="fw-semibold">{{ selectedCategory?.name }}</span>
    </nav>

    <div v-if="wizard.loading.value && !cards.length" class="text-center py-5">
      <div class="spinner-border text-primary"></div>
    </div>

    <div v-else-if="!cards.length" class="text-center py-5 text-muted">
      No hay opciones disponibles en este momento.
    </div>

    <div v-else class="row g-3">
      <div class="col-md-4" v-for="card in cards" :key="card.uuid">
        <button class="option-card" @click="choose(card)">
          <i :class="['bi', card.icon || defaultIcon, 'fs-2 mb-2']"></i>
          <div class="fw-semibold">{{ card.name || card.title }}</div>
          <div class="small text-muted">{{ card.subtitle || '' }}</div>
          <span v-if="card.complexity_hint_display" :class="['complexity-badge', `complexity-${card.complexity_hint?.toLowerCase()}`]">
            {{ card.complexity_hint_display }}
          </span>
        </button>
      </div>
    </div>

    <p v-if="wizard.error.value" class="text-danger small mt-3">{{ wizard.error.value }}</p>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue';

const props = defineProps({ wizard: { type: Object, required: true } });
const emit = defineEmits(['next']);

const level = ref('category'); // category | subcategory | template
const selectedCategory = ref(null);
const selectedSubcategory = ref(null);

const defaultIcon = computed(() => ({ category: 'bi-tags', subcategory: 'bi-tag', template: 'bi-file-earmark-text' }[level.value]));

const cards = computed(() => {
  if (level.value === 'category') return props.wizard.categories.value;
  if (level.value === 'subcategory') return props.wizard.subcategories.value;
  return props.wizard.templates.value.filter((t) => {
    if (t.category_name !== selectedCategory.value?.name) return false;
    if (selectedSubcategory.value) return t.subcategory_name === selectedSubcategory.value.name;
    return true;
  }).map((t) => ({ ...t, subtitle: t.system_type_name || t.service_type_name || 'Cotización personalizada' }));
});

async function choose(card) {
  if (level.value === 'category') {
    selectedCategory.value = card;
    await props.wizard.fetchSubcategories(card.uuid);
    level.value = props.wizard.subcategories.value.length ? 'subcategory' : 'template';
    return;
  }
  if (level.value === 'subcategory') {
    selectedSubcategory.value = card;
    level.value = 'template';
    return;
  }
  const ok = await props.wizard.selectTemplate(card.uuid);
  if (ok) emit('next');
}

function goToCategory() {
  level.value = 'category';
  selectedCategory.value = null;
  selectedSubcategory.value = null;
}

function goToSubcategory() {
  level.value = props.wizard.subcategories.value.length ? 'subcategory' : 'category';
  selectedSubcategory.value = null;
}

onMounted(async () => {
  await Promise.all([props.wizard.fetchCategories(), props.wizard.fetchTemplates()]);
});
</script>

<style scoped>
.step-title { font-size: clamp(1.8rem, 4vw, 2.6rem); font-weight: 850; letter-spacing: -0.03em; margin-bottom: 0.4rem; }
.step-subtitle { color: #64748b; margin-bottom: 1.4rem; }
.qw-crumbs { font-size: 0.85rem; color: #94a3b8; }
.crumb-link { background: none; border: 0; padding: 0; color: #7c3aed; font-weight: 600; }
.option-card {
  width: 100%; text-align: left; background: #fff; border: 1.5px solid #e2e8f0;
  border-radius: 16px; padding: 1.4rem; cursor: pointer; transition: border-color .15s;
}
.option-card:hover { border-color: #a78bfa; }
.option-card i { color: #7c3aed; }
.complexity-badge {
  display: inline-block; margin-top: 0.6rem; font-size: 0.7rem; font-weight: 700;
  padding: 0.2rem 0.6rem; border-radius: 999px; text-transform: uppercase; letter-spacing: 0.03em;
}
.complexity-low { background: #dcfce7; color: #15803d; }
.complexity-medium { background: #fef9c3; color: #a16207; }
.complexity-high { background: #fee2e2; color: #b91c1c; }
</style>
