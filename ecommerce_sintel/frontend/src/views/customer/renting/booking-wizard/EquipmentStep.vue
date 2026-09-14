<template>
  <div class="booking-card equipment-layout">
    <div class="equipment-visual">
      <img v-if="image" :src="image" :alt="equipment.name" /><i v-else class="bi bi-truck"></i>
    </div>
    <div>
      <span class="soft-badge">{{ equipment.category_name || 'Equipo profesional' }}</span>
      <h2>{{ equipment.name }}</h2>
      <p class="text-secondary">{{ equipment.description }}</p>
      <label v-if="variants.length > 1" class="field"
        ><span>Configuración del equipo</span
        ><select v-model="draft.variantUuid">
          <option v-for="v in variants" :key="v.uuid" :value="v.uuid">
            {{ variantName(v) }}
          </option>
        </select></label
      >
      <div v-if="comodatoAvailable" class="priority-picker modality-picker">
        <button
          type="button"
          :class="{ active: draft.commercialType === 'RENTAL' }"
          @click="$emit('set-commercial-type', 'RENTAL')"
        >
          <strong><i class="bi bi-calendar-check me-1"></i>Renting</strong
          ><small>Alquiler pagado por días u horas</small>
        </button>
        <button
          type="button"
          :class="{ active: draft.commercialType === 'COMODATO' }"
          @click="$emit('set-commercial-type', 'COMODATO')"
        >
          <strong><i class="bi bi-hand-index-thumb me-1"></i>Comodato</strong
          ><small>Préstamo de uso, sin costo, sujeto a aprobación</small>
        </button>
      </div>
      <div class="included-grid">
        <div v-for="item in inclusions" :key="item.label">
          <i :class="item.icon"></i><span>{{ item.label }}</span
          ><small>{{ item.value }}</small>
        </div>
      </div>
      <div class="price-line">
        <span>Precio desde</span
        ><strong>{{ money(selectedVariant?.rental_price_per_day) }} <small>/ día</small></strong>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useBookingStore } from '@/store/renting/bookingStore';
import { formatCOP } from '@/utils/money';
import { variantName } from './helpers';

defineProps({
  equipment: { type: Object, required: true },
  variants: { type: Array, default: () => [] },
  image: { type: String, default: '' },
  selectedVariant: { type: Object, default: null },
  comodatoAvailable: { type: Boolean, default: false },
  inclusions: { type: Array, default: () => [] },
});
// `setCommercialType` normaliza modo/prioridad/plazo del comodato y comparte
// `recomputeComodatoEndDate` con un watch del padre -- por eso se emite en vez
// de reimplementarse aqui.
defineEmits(['set-commercial-type']);

// `draft` es el objeto reactivo del store Pinia (no una copia local): escribir
// `draft.variantUuid` desde aqui es exactamente la misma escritura que hacia el
// wizard monolitico.
const draft = useBookingStore().draft;
const money = (v) => formatCOP(v, { withSymbol: true });
</script>

<style scoped>
/* Subconjunto EXACTO (mismas reglas, mismo orden relativo) del <style scoped>
   original de RentalBookingWizard.vue que aplicaba a este paso. Se copia en
   lugar de importarse un _shared.css porque el CSS con scope depende del orden
   del documento: p.ej. `.booking-card h2` debe seguir ganandole a
   `.equipment-layout h2` (misma especificidad, gana la ultima) y a la vez
   `.modality-picker` debe ganarle a `.priority-picker`. Partir estas reglas en
   dos bloques/archivos invertiria una de las dos cascadas. */
.booking-card {
  background: white;
  border: 1px solid #e8e7ee;
  border-radius: 24px;
  padding: clamp(1.2rem, 3vw, 2rem);
  box-shadow: 0 18px 50px rgba(31, 25, 55, 0.06);
}
.equipment-layout {
  display: grid;
  grid-template-columns: minmax(280px, 0.9fr) 1.1fr;
  gap: 2rem;
}
.equipment-visual {
  min-height: 360px;
  background: linear-gradient(145deg, #f5f3ff, #f8fafc);
  border-radius: 18px;
  display: grid;
  place-items: center;
  font-size: 5rem;
  color: #c4b5fd;
  overflow: hidden;
}
.equipment-visual img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.soft-badge {
  display: inline-block;
  background: #f3e8ff;
  color: #6b21a8;
  border-radius: 999px;
  padding: 0.35rem 0.7rem;
  font-size: 0.75rem;
  font-weight: 750;
}
.equipment-layout h2 {
  font-size: 1.8rem;
  margin: 0.8rem 0;
}
.included-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.7rem;
  margin: 1.3rem 0;
}
.included-grid div {
  display: grid;
  grid-template-columns: 30px 1fr;
  align-items: center;
  background: #fafafa;
  border-radius: 12px;
  padding: 0.7rem;
}
.included-grid i {
  grid-row: 1/3;
  color: #7c3aed;
}
.included-grid small {
  color: #64748b;
}
.price-line {
  display: flex;
  justify-content: space-between;
  border-top: 1px solid #eee;
  padding-top: 1.2rem;
}
.price-line strong {
  font-size: 1.35rem;
  color: #5b21b6;
}
.price-line small {
  font-size: 0.75rem;
  color: #64748b;
}
.booking-card h2 {
  font-size: 1.08rem;
  font-weight: 780;
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
@media (max-width: 800px) {
  .equipment-layout {
    grid-template-columns: 1fr;
  }
  .equipment-visual {
    min-height: 260px;
  }
}
@media (max-width: 480px) {
  .included-grid {
    grid-template-columns: 1fr;
  }
  .booking-card {
    border-radius: 18px;
  }
}
.priority-picker {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.7rem;
  margin: 1rem 0;
}
.priority-picker button {
  display: grid;
  text-align: left;
  border: 1.5px solid #e2e8f0;
  background: #fff;
  border-radius: 14px;
  padding: 0.8rem;
}
.priority-picker button.active {
  border-color: #7c3aed;
  background: #f5f3ff;
  color: #5b21b6;
}
.priority-picker small {
  color: #64748b;
  margin-top: 0.2rem;
}
.modality-picker {
  margin-bottom: 1.3rem;
}
@media (max-width: 480px) {
  .priority-picker {
    grid-template-columns: 1fr;
  }
}
</style>
