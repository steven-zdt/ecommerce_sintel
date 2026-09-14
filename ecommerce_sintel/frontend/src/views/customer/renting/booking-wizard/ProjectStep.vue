<template>
  <div class="cards-grid">
    <div class="booking-card">
      <h2><i class="bi bi-geo-alt"></i> ¿Dónde utilizarás el equipo?</h2>
      <p class="helper-text">
        Selecciona la ubicación y construye la dirección con nomenclatura colombiana. Así evitamos
        errores de digitación.
      </p>
      <div class="form-grid">
        <label class="field"
          ><span>Departamento *</span
          ><select
            v-model="draft.project.department"
            autocomplete="address-level1"
            @change="onDepartmentChange"
          >
            <option value="">Seleccionar departamento…</option>
            <option v-for="department in departments" :key="department" :value="department">
              {{ department }}
            </option>
          </select></label
        ><label class="field"
          ><span>Ciudad / municipio *</span
          ><select
            v-model="draft.project.city"
            autocomplete="address-level2"
            :disabled="!draft.project.department"
          >
            <option value="">
              {{
                draft.project.department ? 'Seleccionar ciudad…' : 'Primero elige departamento'
              }}
            </option>
            <option v-for="city in availableCities" :key="city" :value="city">
              {{ city }}
            </option>
          </select></label
        ><label class="field wide"
          ><span>Barrio o localidad *</span
          ><input
            v-model.trim="draft.project.neighborhood"
            maxlength="80"
            autocomplete="address-level3"
            placeholder="Ej. Kennedy, Chapinero, El Poblado"
        /></label>
      </div>
      <div class="address-builder">
        <span class="builder-title"><i class="bi bi-signpost-2"></i> Dirección *</span>
        <div class="address-parts">
          <label class="field"
            ><span>Tipo de vía</span
            ><select v-model="draft.project.roadType">
              <option v-for="type in roadTypes" :key="type">{{ type }}</option>
            </select></label
          ><label class="field"
            ><span>N.º vía</span
            ><input
              :value="draft.project.roadNumber"
              maxlength="8"
              placeholder="31 Bis"
              @input="setAddressPart('roadNumber', $event)" /></label
          ><label class="field compact"><span>&nbsp;</span><b>#</b></label
          ><label class="field"
            ><span>Generadora</span
            ><input
              :value="draft.project.generator"
              maxlength="8"
              placeholder="68 I"
              @input="setAddressPart('generator', $event)" /></label
          ><label class="field compact"><span>&nbsp;</span><b>−</b></label
          ><label class="field"
            ><span>Placa</span
            ><input
              :value="draft.project.plate"
              maxlength="6"
              placeholder="38"
              @input="setAddressPart('plate', $event)"
          /></label>
        </div>
        <label class="field mt-3"
          ><span>Complemento (opcional)</span
          ><input
            v-model.trim="draft.project.complement"
            maxlength="100"
            placeholder="Torre, apartamento, piso, local o interior"
        /></label>
        <div v-if="structuredAddress" class="address-preview">
          <i class="bi bi-check-circle-fill"></i>
          <div>
            <small>Así guardaremos la dirección</small><strong>{{ structuredAddress }}</strong>
          </div>
        </div>
        <p v-else class="address-hint">
          <i class="bi bi-info-circle"></i>Completa número de vía, generadora y placa.
        </p>
      </div>
    </div>
    <div class="booking-card">
      <h2><i class="bi bi-buildings"></i> Información del proyecto</h2>
      <div class="form-grid">
        <label class="field"
          ><span>Tipo de proyecto</span
          ><input
            v-model.trim="draft.project.projectType"
            placeholder="Construcción, evento..." /></label
        ><label class="field"
          ><span>Empresa</span><input v-model.trim="draft.project.company" /></label
        ><label class="field wide"
          ><span>Actividad</span
          ><input
            v-model.trim="draft.project.activity"
            placeholder="¿Qué trabajo realizarás?" /></label
        ><label class="field wide"
          ><span>Observaciones</span
          ><textarea v-model.trim="draft.project.notes" rows="3"></textarea>
        </label>
      </div>
    </div>
    <div class="booking-card">
      <h2><i class="bi bi-signpost-split"></i> Condiciones del lugar</h2>
      <div class="choice-grid">
        <label v-for="condition in conditions" :key="condition"
          ><input v-model="draft.project.conditions" type="checkbox" :value="condition" /><span
            ><i class="bi bi-check"></i>{{ condition }}</span
          ></label
        >
      </div>
    </div>
    <div class="booking-card">
      <h2><i class="bi bi-paperclip"></i> Fotos y documentos del proyecto</h2>
      <p class="helper-text">
        Agrega fotografías de reconocimiento, planos o un PDF. Esto ayuda a preparar la entrega y la
        instalación.
      </p>
      <label class="upload-zone"
        ><input
          type="file"
          multiple
          accept="image/jpeg,image/png,image/webp,application/pdf"
          @change="$emit('add-files', $event)"
        /><i class="bi bi-cloud-arrow-up"></i><strong>Seleccionar archivos</strong
        ><small>JPG, PNG, WEBP o PDF · máximo 10 archivos · 15 MB cada uno</small></label
      >
      <div v-if="projectFiles.length" class="file-list">
        <div v-for="(entry, index) in projectFiles" :key="entry.id">
          <img v-if="entry.preview" :src="entry.preview" alt="Vista previa" /><i
            v-else
            class="bi bi-file-earmark-pdf"
          ></i
          ><span
            ><strong>{{ entry.file.name }}</strong
            ><small>{{ fileSize(entry.file.size) }}</small></span
          ><button type="button" aria-label="Quitar archivo" @click="$emit('remove-file', index)">
            ×
          </button>
        </div>
      </div>
      <p v-if="fileError" class="field-error mt-2">{{ fileError }}</p>
    </div>
  </div>
</template>

<script setup>
import { useBookingStore } from '@/store/renting/bookingStore';
import { COLOMBIA_LOCATIONS, COLOMBIAN_ROAD_TYPES } from '@/data/colombiaLocations';

defineProps({
  // `structuredAddress` y `availableCities` se calculan en el padre (el padre
  // los necesita tambien: `validate()` y el watch que escribe
  // `draft.project.address`) y llegan aqui ya resueltos, para que no exista una
  // segunda copia de esa logica derivada.
  structuredAddress: { type: String, default: '' },
  availableCities: { type: Array, default: () => [] },
  // Los adjuntos viven en el padre porque `submit()` los sube y libera sus
  // object URLs; aqui solo se listan y se emiten las acciones.
  projectFiles: { type: Array, default: () => [] },
  fileError: { type: String, default: '' },
});
defineEmits(['add-files', 'remove-file']);

const draft = useBookingStore().draft;

// Listas estaticas: no son logica derivada del borrador, solo datos de
// referencia que unicamente usa este paso.
const departments = Object.keys(COLOMBIA_LOCATIONS).sort((a, b) => a.localeCompare(b, 'es'));
const roadTypes = COLOMBIAN_ROAD_TYPES;
const conditions = [
  'Primer piso',
  'Ascensor',
  'Escaleras',
  'Zona restringida',
  'Carga pesada',
  'Necesita instalación',
  'Necesita capacitación',
];

const cleanPart = (value) =>
  String(value || '')
    .toUpperCase()
    .replace(/[^0-9A-ZÁÉÍÓÚÑ\s]/g, '')
    .replace(/\s+/g, ' ')
    .trimStart();

function onDepartmentChange() {
  draft.project.city = '';
}
function setAddressPart(field, event) {
  draft.project[field] = cleanPart(event.target.value);
  event.target.value = draft.project[field];
}
function fileSize(bytes) {
  return bytes < 1024 * 1024
    ? `${Math.ceil(bytes / 1024)} KB`
    : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
</script>

<style scoped>
/* Subconjunto EXACTO (mismas reglas, mismo orden relativo) del <style scoped>
   original de RentalBookingWizard.vue que aplicaba a este paso. Ver la nota en
   EquipmentStep.vue sobre por que no se factoriza en un _shared.css. */
.booking-card {
  background: white;
  border: 1px solid #e8e7ee;
  border-radius: 24px;
  padding: clamp(1.2rem, 3vw, 2rem);
  box-shadow: 0 18px 50px rgba(31, 25, 55, 0.06);
}
.cards-grid {
  display: grid;
  gap: 1rem;
}
.booking-card h2 {
  font-size: 1.08rem;
  font-weight: 780;
}
.booking-card h2 i {
  color: #7c3aed;
  margin-right: 0.4rem;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}
.wide {
  grid-column: 1/-1;
}
.field {
  display: grid;
  gap: 0.38rem;
}
.field > span {
  font-size: 0.78rem;
  font-weight: 700;
  color: #475569;
}
.field input,
.field select,
.field textarea {
  width: 100%;
  border: 1.5px solid #dddbe5;
  border-radius: 12px;
  padding: 0.78rem 0.85rem;
  background: #fff;
  outline: none;
}
.field input:focus,
.field select:focus,
.field textarea:focus {
  border-color: #7c3aed;
  box-shadow: 0 0 0 3px #ede9fe;
}
.choice-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}
.choice-grid input {
  position: absolute;
  opacity: 0;
}
.choice-grid span {
  display: block;
  border: 1.5px solid #e2e0e8;
  border-radius: 999px;
  padding: 0.55rem 0.8rem;
  cursor: pointer;
}
.choice-grid i {
  display: none;
}
.choice-grid input:checked + span {
  border-color: #7c3aed;
  background: #f5f3ff;
  color: #5b21b6;
}
.choice-grid input:checked + span i {
  display: inline;
  margin-right: 0.3rem;
}
@media (max-width: 800px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  .wide {
    grid-column: auto;
  }
}
@media (max-width: 480px) {
  .booking-card {
    border-radius: 18px;
  }
}
.helper-text {
  color: #64748b;
  font-size: 0.88rem;
  margin-bottom: 1.25rem;
}
.field select:disabled {
  background: #f1f5f9;
  color: #94a3b8;
}
.address-builder {
  margin-top: 1.25rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  padding: 1rem;
}
.builder-title {
  display: block;
  font-size: 0.82rem;
  font-weight: 800;
  color: #334155;
  margin-bottom: 0.8rem;
}
.builder-title i {
  color: #7c3aed;
  margin-right: 0.35rem;
}
.address-parts {
  display: grid;
  grid-template-columns: 1.2fr 0.85fr 34px 0.85fr 34px 0.65fr;
  gap: 0.55rem;
  align-items: end;
}
.compact b {
  height: 47px;
  display: grid;
  place-items: center;
  font-size: 1.25rem;
  color: #64748b;
}
.address-preview {
  display: flex;
  gap: 0.7rem;
  align-items: center;
  background: #ecfdf5;
  border: 1px solid #bbf7d0;
  color: #166534;
  border-radius: 12px;
  padding: 0.75rem;
  margin-top: 1rem;
}
.address-preview small,
.address-preview strong {
  display: block;
}
.address-preview small {
  font-size: 0.68rem;
  text-transform: uppercase;
}
.address-hint {
  color: #64748b;
  font-size: 0.8rem;
  margin: 0.8rem 0 0;
}
.field-error {
  color: #be123c;
  font-size: 0.75rem;
}
.upload-zone {
  border: 2px dashed #c4b5fd;
  background: #faf5ff;
  border-radius: 16px;
  padding: 1.3rem;
  display: grid;
  place-items: center;
  text-align: center;
  cursor: pointer;
  color: #5b21b6;
}
.upload-zone input {
  position: absolute;
  opacity: 0;
  pointer-events: none;
}
.upload-zone i {
  font-size: 1.8rem;
}
.upload-zone small {
  display: block;
  color: #64748b;
  margin-top: 0.2rem;
}
.file-list {
  display: grid;
  gap: 0.5rem;
  margin-top: 1rem;
}
.file-list > div {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  background: #f8fafc;
  border-radius: 12px;
  padding: 0.55rem;
}
.file-list img {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 8px;
}
.file-list > div > i {
  width: 48px;
  text-align: center;
  font-size: 1.6rem;
  color: #dc2626;
}
.file-list span {
  display: grid;
  min-width: 0;
  flex: 1;
}
.file-list span strong {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.82rem;
}
.file-list span small {
  color: #64748b;
}
.file-list button {
  border: 0;
  background: #e2e8f0;
  border-radius: 50%;
  width: 28px;
  height: 28px;
}
@media (max-width: 800px) {
  .address-parts {
    grid-template-columns: 1fr 1fr;
  }
  .compact {
    display: none;
  }
}
</style>
