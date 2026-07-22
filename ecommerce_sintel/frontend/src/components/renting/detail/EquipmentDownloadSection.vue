<template>
  <div v-if="otherFiles.length" class="eq-download-list">
    <button
      v-for="doc in otherFiles"
      :key="doc.uuid"
      type="button"
      class="eq-download-row"
      @click="download(doc)"
    >
      <i class="bi bi-file-earmark-arrow-down"></i>
      <span class="flex-grow-1 min-w-0">
        <strong>{{ doc.title }}</strong>
        <small>{{ doc.document_type_display }}</small>
      </span>
      <i class="bi bi-download eq-download-icon"></i>
    </button>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { useDocumentDownload } from '@/composables/useDocumentDownload';

const props = defineProps({
  documents: { type: Array, default: () => [] },
  equipmentUuid: { type: String, required: true },
});

const otherFiles = computed(() =>
  props.documents.filter((d) => d.document_type !== 'MANUAL' && d.document_type !== 'FICHA_TECNICA'),
);
const { download } = useDocumentDownload(props.equipmentUuid);
</script>

<style scoped>
.eq-download-list { display: flex; flex-direction: column; gap: .45rem; }
.eq-download-row {
  display: flex; align-items: center; gap: .6rem; width: 100%;
  border: 1px solid #e2e8f0; border-radius: 12px; padding: .65rem .8rem;
  background: #fff; text-align: left; cursor: pointer;
}
.eq-download-row i.bi-file-earmark-arrow-down { color: #64748b; font-size: 1.1rem; }
.eq-download-row strong { display: block; color: #0f172a; font-size: .82rem; }
.eq-download-row small { color: #94a3b8; font-size: .7rem; }
.eq-download-icon { color: #2563eb; }
</style>
