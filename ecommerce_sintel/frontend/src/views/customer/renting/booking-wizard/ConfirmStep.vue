<template>
  <div class="confirm-grid">
    <div class="summary-stack">
      <div class="booking-card summary-card">
        <button @click="$emit('edit-step', 1)">Editar</button><span>Equipo</span>
        <h2>{{ equipment.name }}</h2>
        <p>{{ variantName(selectedVariant) }}</p>
      </div>
      <div class="booking-card summary-card">
        <button @click="$emit('edit-step', 2)">Editar</button><span>Proyecto</span>
        <h2>{{ draft.project.city }}, {{ draft.project.department }}</h2>
        <p>{{ draft.project.address }}</p>
      </div>
      <div class="booking-card summary-card">
        <button @click="$emit('edit-step', 3)">Editar</button><span>Programación</span>
        <h2>{{ dateLabel }}</h2>
        <p v-if="draft.commercialType === 'COMODATO'">
          {{ draft.schedule.quantity }} equipo(s) · Comodato {{ draft.termMonths }} meses
        </p>
        <p v-else>{{ draft.schedule.quantity }} equipo(s) · {{ costs.days }} días</p>
      </div>
      <RentalCostsCard :costs="costs" />
    </div>
    <div class="booking-card customer-card">
      <h2>Responsable de la reserva</h2>
      <p>
        Correo y celular son obligatorios para confirmar disponibilidad y coordinar la entrega.
      </p>
      <div class="form-grid">
        <label class="field wide"
          ><span>Nombre completo *</span
          ><input v-model.trim="draft.customer.fullName" autocomplete="name" /></label
        ><label class="field"
          ><span>Tipo de documento</span
          ><select v-model="draft.customer.docType">
            <option>CC</option>
            <option>CE</option>
            <option>NIT</option>
            <option>PP</option>
          </select></label
        ><label class="field"
          ><span>Documento *</span><input v-model.trim="draft.customer.docNumber" /></label
        ><label class="field"
          ><span>Correo electrónico *</span
          ><input
            v-model.trim="draft.customer.email"
            type="email"
            autocomplete="email"
            placeholder="nombre@empresa.com"
          /><small v-if="draft.customer.email && !validEmail" class="field-error"
            >Ingresa un correo válido.</small
          ></label
        ><label class="field"
          ><span>Celular colombiano *</span>
          <div class="phone-input">
            <b>+57</b
            ><input
              :value="draft.customer.phone"
              maxlength="10"
              inputmode="numeric"
              autocomplete="tel"
              placeholder="3001234567"
              @input="onPhoneInput"
            />
          </div>
          <small v-if="draft.customer.phone && !validPhone" class="field-error"
            >Debe tener 10 dígitos y comenzar por 3.</small
          ></label
        >
      </div>
      <label class="terms"
        ><input v-model="draft.termsAccepted" type="checkbox" /><span
          >Acepto los términos y condiciones de la reserva.</span
        ></label
      >
    </div>
  </div>
</template>

<script setup>
import { useBookingStore } from '@/store/renting/bookingStore';
import RentalCostsCard from '@/components/customer/renting/RentalCostsCard.vue';
import { variantName } from './helpers';

defineProps({
  equipment: { type: Object, required: true },
  selectedVariant: { type: Object, default: null },
  costs: { type: Object, required: true },
  dateLabel: { type: String, default: '' },
  // `validEmail`/`validPhone` los calcula el padre porque `validate()` los
  // necesita antes de enviar; aqui solo se muestran los mensajes de error.
  validEmail: { type: Boolean, default: false },
  validPhone: { type: Boolean, default: false },
});
// El paso actual lo controla el padre (`booking.step`); "Editar" solo pide el
// salto en vez de mutar el paso desde el hijo.
defineEmits(['edit-step']);

const draft = useBookingStore().draft;

function onPhoneInput(event) {
  // Bug real (hallado 2026-07-22): el campo ya muestra "+57" como prefijo
  // fijo al lado, pero muchos clientes de todos modos pegan/escriben su
  // numero completo con el indicativo (+57, 57 o 057) porque asi lo tienen
  // guardado en sus contactos. Sin esto, "+573041112233" quedaba en
  // "5730411122" tras quitar simbolos y recortar a 10 digitos -- ni
  // empezaba por 3 ni eran los digitos reales del numero, y el usuario veia
  // el error de validacion pese a haber escrito un numero valido.
  let digits = event.target.value.replace(/\D/g, '');
  if (digits.length > 10) {
    if (digits.startsWith('0057')) digits = digits.slice(4);
    else if (digits.startsWith('057')) digits = digits.slice(3);
    else if (digits.startsWith('57')) digits = digits.slice(2);
  }
  draft.customer.phone = digits.slice(0, 10);
  event.target.value = draft.customer.phone;
}
</script>

<style scoped>
/* Subconjunto EXACTO (mismas reglas, mismo orden relativo) del <style scoped>
   original de RentalBookingWizard.vue que aplicaba a este paso. Ver la nota en
   EquipmentStep.vue sobre por que no se factoriza en un _shared.css: aqui
   importa que `.phone-input input` siga despues de `.field input` (misma
   especificidad) para conservar el input de celular sin borde propio. */
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
.field select {
  width: 100%;
  border: 1.5px solid #dddbe5;
  border-radius: 12px;
  padding: 0.78rem 0.85rem;
  background: #fff;
  outline: none;
}
.field input:focus,
.field select:focus {
  border-color: #7c3aed;
  box-shadow: 0 0 0 3px #ede9fe;
}
.confirm-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
  align-items: start;
}
.summary-stack {
  display: grid;
  gap: 1rem;
}
.summary-card {
  position: relative;
}
.summary-card button {
  position: absolute;
  right: 1rem;
  top: 1rem;
  border: 0;
  background: none;
  color: #7c3aed;
  font-weight: 700;
}
.summary-card > span {
  font-size: 0.72rem;
  text-transform: uppercase;
  color: #64748b;
}
.summary-card h2 {
  margin: 0.4rem 0;
}
.summary-card p {
  margin: 0;
  color: #64748b;
}
.terms {
  display: flex;
  gap: 0.7rem;
  margin-top: 1.2rem;
  font-size: 0.88rem;
}
.terms input {
  width: 18px;
  height: 18px;
  accent-color: #7c3aed;
}
@media (max-width: 800px) {
  .confirm-grid {
    grid-template-columns: 1fr;
  }
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
.field-error {
  color: #be123c;
  font-size: 0.75rem;
}
.phone-input {
  display: flex;
  border: 1.5px solid #dddbe5;
  border-radius: 12px;
  overflow: hidden;
}
.phone-input:focus-within {
  border-color: #7c3aed;
  box-shadow: 0 0 0 3px #ede9fe;
}
.phone-input b {
  display: grid;
  place-items: center;
  background: #f1f5f9;
  padding: 0 0.8rem;
  color: #475569;
}
.phone-input input {
  border: 0;
  border-radius: 0;
  box-shadow: none !important;
}
</style>
