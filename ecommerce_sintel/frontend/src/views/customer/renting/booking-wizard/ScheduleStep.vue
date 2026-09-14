<template>
  <div class="schedule-layout">
    <div class="booking-card">
      <h2><i class="bi bi-calendar3"></i> Selecciona el período</h2>
      <div v-if="draft.commercialType !== 'COMODATO'" class="priority-picker">
        <button
          :class="{ active: draft.schedule.priority === 'LOW' }"
          @click="$emit('set-priority', 'LOW')"
        >
          <strong>Planificada</strong><small>Inicia desde {{ earliestLabel(7) }}</small></button
        ><button
          :class="{ active: draft.schedule.priority === 'HIGH' }"
          @click="$emit('set-priority', 'HIGH')"
        >
          <strong>Prioritaria</strong><small>Inicia desde {{ earliestLabel(3) }}</small>
        </button>
      </div>
      <p class="schedule-rule">
        <i class="bi bi-shield-check"></i> La primera fecha permitida es
        {{ formattedEarliestDate }}. El calendario bloquea hoy, fechas pasadas y días que no cumplen
        la anticipación.
      </p>

      <!-- Comodato: plazo fijo en vez de rango de fechas -->
      <template v-if="draft.commercialType === 'COMODATO'">
        <label class="date-tile mb-3"
          ><span>Fecha de inicio *</span
          ><input v-model="draft.schedule.startDate" type="date" :min="earliestStartDate"
        /></label>
        <span class="builder-title"
          ><i class="bi bi-hourglass-split"></i> Plazo del comodato *</span
        >
        <div class="choice-grid term-picker">
          <button
            v-for="term in comodatoTermOptions"
            :key="term.term_months"
            type="button"
            class="term-chip"
            :class="{ active: draft.termMonths === term.term_months }"
            @click="$emit('set-term-months', term.term_months)"
          >
            {{ term.term_months_display || `${term.term_months} meses` }}
          </button>
        </div>
        <p v-if="!comodatoTermOptions.length" class="schedule-rule mt-2">
          <i class="bi bi-exclamation-triangle"></i> Este equipo aún no tiene plazos de comodato
          configurados.
        </p>
        <p v-else-if="draft.schedule.endDate" class="address-hint mt-2">
          <i class="bi bi-info-circle"></i> Fecha estimada de devolución:
          {{ dateLabel.split(' — ')[1] }}
        </p>
        <div class="form-grid mt-3">
          <label class="field"
            ><span>Cantidad *</span
            ><input v-model.number="draft.schedule.quantity" min="1" type="number" /></label
          >
        </div>
      </template>

      <!-- Renting: rango de fechas continuo, sin cambios -->
      <template v-else>
        <div class="date-grid">
          <label class="date-tile"
            ><span>Fecha de inicio *</span
            ><input
              v-model="draft.schedule.startDate"
              type="date"
              :min="earliestStartDate" /></label
          ><label class="date-tile"
            ><span>Fecha final *</span
            ><input
              v-model="draft.schedule.endDate"
              type="date"
              :min="minimumEndDate"
              :disabled="!draft.schedule.startDate"
          /></label>
        </div>
        <div class="form-grid mt-3">
          <label class="field"
            ><span>Cantidad *</span
            ><input v-model.number="draft.schedule.quantity" min="1" type="number" /></label
          ><label v-if="selectedVariant?.rental_price_per_hour" class="field"
            ><span>Modalidad</span
            ><select v-model="draft.schedule.mode">
              <option value="days">Por días</option>
              <option value="hours">Por horas</option>
            </select></label
          >
        </div>
        <RentalHourSelector
          v-if="draft.schedule.mode === 'hours'"
          class="mt-3"
          v-model:delivery-time="draft.schedule.deliveryTime"
          v-model:pickup-time="draft.schedule.pickupTime"
        />
      </template>

      <div class="info-box">
        <i class="bi bi-info-circle"></i
        ><span
          >Nuestro equipo verificará la disponibilidad definitiva y confirmará la reserva. Si alguna
          fecha no está disponible, te ofreceremos alternativas.</span
        >
      </div>
    </div>
    <div class="live-summary-stack">
      <div
        v-if="draft.schedule.startDate && draft.schedule.endDate"
        class="booking-card live-summary-head"
      >
        <span>Resumen en tiempo real</span><strong>{{ costs.days }} días</strong
        ><AvailabilityPill
          :checking="availability.checking"
          :available="availability.result?.available ?? null"
          :next-available-date="availability.result?.next_available_date"
          :next-available-time="availability.result?.next_available_time"
        />
      </div>
      <!-- Antes de tener fechas, delivery/pickup ya tienen costo fijo
           pero el alquiler todavia no -- mostrar el desglose en ese
           momento leia como "Alquiler $0 + Logistica $30.000" antes
           de que el calculo estuviera completo. Se pide la fecha
           primero en vez de mostrar un total parcial. -->
      <div v-if="draft.schedule.startDate && draft.schedule.endDate">
        <RentalCostsCard :costs="costs" />
      </div>
      <div v-else class="booking-card live-summary-placeholder">
        <i class="bi bi-calendar-range"></i>
        <span>Selecciona las fechas de inicio y fin para ver el costo total.</span>
      </div>
    </div>
    <AvailabilityCard
      v-if="availability.result?.available === false"
      class="suggestion-card"
      :checking="availability.checking"
      :available="false"
      :next-available-date="availability.result?.next_available_date"
      :next-available-time="availability.result?.next_available_time"
      :rental-mode="draft.schedule.mode"
      :occupied-slots="availability.result?.occupied_slots"
      @select="$emit('apply-suggestion', $event)"
    />
  </div>
</template>

<script setup>
import { useBookingStore } from '@/store/renting/bookingStore';
import { useAvailabilityStore } from '@/store/renting/availabilityStore';
import RentalCostsCard from '@/components/customer/renting/RentalCostsCard.vue';
import AvailabilityPill from '@/components/customer/renting/AvailabilityPill.vue';
import AvailabilityCard from '@/components/customer/renting/AvailabilityCard.vue';
import RentalHourSelector from '@/components/customer/renting/RentalHourSelector.vue';
import { earliestLabel } from './helpers';

defineProps({
  // Todo lo derivado lo calcula el padre (que tambien lo necesita en
  // `validate()`/`continueFlow()`/`submit()`) y llega aqui ya resuelto.
  costs: { type: Object, required: true },
  selectedVariant: { type: Object, default: null },
  comodatoTermOptions: { type: Array, default: () => [] },
  earliestStartDate: { type: String, default: '' },
  minimumEndDate: { type: String, default: '' },
  formattedEarliestDate: { type: String, default: '' },
  dateLabel: { type: String, default: '' },
});
// `set-priority` y `set-term-months` no se resuelven aqui porque ambos
// reinician fechas del borrador junto con logica que el padre comparte con sus
// watchers (`recomputeComodatoEndDate`, reset por fecha minima);
// `apply-suggestion` ademas limpia `error` del padre.
defineEmits(['set-priority', 'set-term-months', 'apply-suggestion']);

const draft = useBookingStore().draft;
const availability = useAvailabilityStore();
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
.field {
  display: grid;
  gap: 0.38rem;
}
.field > span,
.date-tile > span {
  font-size: 0.78rem;
  font-weight: 700;
  color: #475569;
}
.field input,
.field select,
.field textarea,
.date-tile input {
  width: 100%;
  border: 1.5px solid #dddbe5;
  border-radius: 12px;
  padding: 0.78rem 0.85rem;
  background: #fff;
  outline: none;
}
.field input:focus,
.field select:focus,
.field textarea:focus,
.date-tile input:focus {
  border-color: #7c3aed;
  box-shadow: 0 0 0 3px #ede9fe;
}
.choice-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}
.schedule-layout {
  display: grid;
  grid-template-columns: 1.7fr 0.8fr;
  gap: 1rem;
  align-items: start;
}
.suggestion-card {
  grid-column: 1/-1;
}
.date-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
.date-tile {
  display: grid;
  gap: 0.5rem;
  background: #fafafa;
  border-radius: 16px;
  padding: 1rem;
}
.info-box {
  display: flex;
  gap: 0.7rem;
  background: #eff6ff;
  color: #1e40af;
  border-radius: 14px;
  padding: 1rem;
  margin-top: 1rem;
  font-size: 0.84rem;
}
.live-summary-stack {
  display: grid;
  gap: 1rem;
  align-content: start;
}
.live-summary-head > span {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #64748b;
}
.live-summary-head > strong {
  display: block;
  font-size: 2rem;
  margin: 0.45rem 0 0.7rem;
}
.live-summary-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.6rem;
  text-align: center;
  color: #64748b;
  font-size: 0.9rem;
  padding: 2rem 1.5rem;
}
.live-summary-placeholder i {
  font-size: 1.6rem;
  color: #94a3b8;
}
@media (max-width: 800px) {
  .schedule-layout {
    grid-template-columns: 1fr;
  }
  .form-grid {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 480px) {
  .date-grid {
    grid-template-columns: 1fr;
  }
  .booking-card {
    border-radius: 18px;
  }
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
.address-hint {
  color: #64748b;
  font-size: 0.8rem;
  margin: 0.8rem 0 0;
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
.schedule-rule {
  background: #fff7ed;
  color: #9a3412;
  border-radius: 12px;
  padding: 0.75rem;
  font-size: 0.82rem;
}
.schedule-rule i {
  margin-right: 0.4rem;
}
.term-picker {
  margin-top: 0.6rem;
}
.term-chip {
  border: 1.5px solid #e2e0e8;
  background: #fff;
  border-radius: 999px;
  padding: 0.55rem 0.9rem;
  font-weight: 650;
  color: #475569;
}
.term-chip.active {
  border-color: #7c3aed;
  background: #f5f3ff;
  color: #5b21b6;
}
@media (max-width: 480px) {
  .priority-picker {
    grid-template-columns: 1fr;
  }
}
</style>
