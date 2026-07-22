<template>
  <div v-if="manuals.length" class="eq-manual-list">
    <article v-for="doc in manuals" :key="doc.uuid" class="eq-manual-card">
      <i class="bi bi-journal-text eq-manual-icon"></i>
      <div class="flex-grow-1 min-w-0">
        <strong>{{ doc.title }}</strong>
        <span v-if="doc.version || doc.language">
          <template v-if="doc.version">v{{ doc.version }}</template>
          <template v-if="doc.version && doc.language"> · </template>
          <template v-if="doc.language">{{ doc.language.toUpperCase() }}</template>
        </span>
      </div>
      <div class="eq-manual-actions">
        <a :href="doc.file" target="_blank" rel="noopener" class="eq-manual-btn eq-manual-btn--ghost">
          <i class="bi bi-eye"></i> Ver
        </a>
        <button type="button" class="eq-manual-btn eq-manual-btn--solid" @click="download(doc)">
          <i class="bi bi-download"></i> Descargar
        </button>
      </div>
    </article>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useDocumentDownload } from '@/composables/useDocumentDownload';

const props = defineProps({
  documents: { type: Array, default: () => [] },
  equipmentUuid: { type: String, required: true },
});

const manuals = computed(() => props.documents.filter((d) => d.document_type === 'MANUAL'));
const { download } = useDocumentDownload(props.equipmentUuid);
</script>

<style scoped>
.eq-manual-list { display: flex; flex-direction: column; gap: .55rem; }
.eq-manual-card {
  display: flex; align-items: center; gap: .65rem;
  border: 1px solid #e2e8f0; border-radius: 12px; padding: .75rem;
  background: #fff;
}
.eq-manual-icon { color: #2563eb; font-size: 1.4rem; }
.eq-manual-card strong { display: block; color: #0f172a; font-size: .84rem; }
.eq-manual-card span { color: #64748b; font-size: .72rem; }
.eq-manual-actions { display: flex; gap: .4rem; flex-shrink: 0; }
.eq-manual-btn {
  display: inline-flex; align-items: center; gap: .3rem;
  border-radius: 999px; padding: .35rem .75rem; font-size: .74rem; font-weight: 700;
  border: 1px solid transparent; text-decoration: none; cursor: pointer;
}
.eq-manual-btn--ghost { color: #2563eb; border-color: #bfdbfe; background: #eff6ff; }
.eq-manual-btn--solid { color: #fff; background: #2563eb; }
</style>
