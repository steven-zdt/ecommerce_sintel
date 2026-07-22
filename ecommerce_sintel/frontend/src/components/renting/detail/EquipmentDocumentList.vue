<template>
  <div v-if="datasheets.length" class="eq-datasheet-grid">
    <article v-for="doc in datasheets" :key="doc.uuid" class="eq-datasheet-card">
      <div class="eq-datasheet-preview">
        <img v-if="doc.cover_image" :src="doc.cover_image" :alt="doc.title">
        <i v-else class="bi bi-file-earmark-richtext"></i>
      </div>
      <div class="eq-datasheet-body">
        <strong>{{ doc.title }}</strong>
        <span v-if="doc.version">v{{ doc.version }}</span>
      </div>
      <div class="eq-datasheet-actions">
        <a :href="doc.file" target="_blank" rel="noopener" class="eq-datasheet-btn eq-datasheet-btn--ghost">
          <i class="bi bi-eye"></i> Vista previa
        </a>
        <button type="button" class="eq-datasheet-btn eq-datasheet-btn--solid" @click="download(doc)">
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

const datasheets = computed(() => props.documents.filter((d) => d.document_type === 'FICHA_TECNICA'));
const { download } = useDocumentDownload(props.equipmentUuid);
</script>

<style scoped>
.eq-datasheet-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: .85rem; }
.eq-datasheet-card { border: 1px solid #e2e8f0; border-radius: 14px; overflow: hidden; background: #fff; }
.eq-datasheet-preview {
  aspect-ratio: 4 / 3; background: #f1f5f9;
  display: flex; align-items: center; justify-content: center; color: #94a3b8; font-size: 2.2rem;
}
.eq-datasheet-preview img { width: 100%; height: 100%; object-fit: cover; }
.eq-datasheet-body { padding: .65rem .75rem .3rem; }
.eq-datasheet-body strong { display: block; color: #0f172a; font-size: .82rem; }
.eq-datasheet-body span { color: #64748b; font-size: .7rem; }
.eq-datasheet-actions { display: flex; gap: .35rem; padding: .5rem .75rem .75rem; }
.eq-datasheet-btn {
  flex: 1; display: inline-flex; align-items: center; justify-content: center; gap: .3rem;
  border-radius: 999px; padding: .35rem .5rem; font-size: .7rem; font-weight: 700;
  border: 1px solid transparent; text-decoration: none; cursor: pointer;
}
.eq-datasheet-btn--ghost { color: #2563eb; border-color: #bfdbfe; background: #eff6ff; }
.eq-datasheet-btn--solid { color: #fff; background: #2563eb; }
</style>
