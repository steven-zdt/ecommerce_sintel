<template>
  <div class="card border-0 shadow-sm mb-4">
    <div class="card-body">
      <div class="d-flex justify-content-between align-items-center mb-3">
        <div>
          <h6 class="mb-0">Observaciones</h6>
          <p class="small text-muted mb-0">Notas internas y seguimiento rápido.</p>
        </div>
      </div>

      <div class="mb-3">
        <textarea v-model="noteText" class="form-control" rows="4" placeholder="Agregar una nota..." />
      </div>
      <div class="d-flex gap-2">
        <button class="btn btn-primary btn-sm" @click="addNote">Guardar nota</button>
        <button class="btn btn-outline-secondary btn-sm" @click="noteText = ''">Limpiar</button>
      </div>

      <div class="mt-4" v-if="notes.length">
        <div v-for="note in notes" :key="note.id" class="border rounded p-3 mb-3">
          <div class="d-flex justify-content-between align-items-start gap-3">
            <div>
              <div class="fw-semibold">{{ note.author || 'Admin' }}</div>
              <div class="small text-muted">{{ formatDate(note.created_at) }}</div>
            </div>
            <button class="btn btn-sm btn-outline-danger" @click="removeNote(note.id)">Eliminar</button>
          </div>
          <p class="mt-2 mb-0">{{ note.text }}</p>
        </div>
      </div>

      <div v-else class="text-center text-muted py-4">No hay observaciones registradas.</div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue';

const props = defineProps({ order: { type: Object, required: true } });
const notes = ref([]);
const noteText = ref('');

const formatDate = (value) => {
  if (!value) return 'Ahora';
  return new Date(value).toLocaleString('es-CO', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
};

const addNote = () => {
  if (!noteText.value.trim()) return;
  notes.value.unshift({
    id: Date.now(),
    author: 'Administrador',
    created_at: new Date().toISOString(),
    text: noteText.value.trim(),
  });
  noteText.value = '';
};

const removeNote = (id) => {
  notes.value = notes.value.filter((note) => note.id !== id);
};
</script>
