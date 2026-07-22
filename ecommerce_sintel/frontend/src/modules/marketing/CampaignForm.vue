<template>
  <div class="campaign-form">
    <form @submit.prevent="handleSubmit">
      <!-- Título -->
      <div class="mb-4">
        <label class="form-label fw-semibold small text-uppercase text-muted">Título de la Campaña</label>
        <input 
          v-model="campaignForm.title.value" 
          type="text" 
          class="form-control form-control-lg"
          :class="{ 'is-invalid': campaignForm.titleError && campaignForm.titleTouched }"
          placeholder="Ej: Ofertas de Verano"
          @blur="touchField('title')"
          aria-label="Título de la Campaña"
          :aria-invalid="!!campaignForm.titleError && campaignForm.titleTouched"
          :aria-describedby="campaignForm.titleError && campaignForm.titleTouched ? 'title-error' : undefined"
        />
        <div 
          v-if="campaignForm.titleError && campaignForm.titleTouched" 
          id="title-error"
          class="form-text text-danger small mt-1"
        >
          <i class="bi bi-exclamation-circle me-1"></i>{{ campaignForm.titleError }}
        </div>
      </div>

      <!-- Contenido -->
      <div class="mb-4">
        <label class="form-label fw-semibold small text-uppercase text-muted">Contenido del Mensaje</label>
        <textarea 
          v-model="campaignForm.content.value" 
          class="form-control form-control-lg" 
          :class="{ 'is-invalid': campaignForm.contentError && campaignForm.contentTouched }"
          rows="5"
          placeholder="Escribe el cuerpo del mensaje..."
          @blur="touchField('content')"
          aria-label="Contenido del Mensaje"
          :aria-invalid="!!campaignForm.contentError && campaignForm.contentTouched"
          :aria-describedby="campaignForm.contentError && campaignForm.contentTouched ? 'content-error' : 'content-hint'"
        ></textarea>
        <div class="form-text smaller text-muted mt-1" id="content-hint">
          {{ campaignForm.contentLength }}/500 caracteres
        </div>
        <div 
          v-if="campaignForm.contentError && campaignForm.contentTouched" 
          id="content-error"
          class="form-text text-danger small mt-1"
        >
          <i class="bi bi-exclamation-circle me-1"></i>{{ campaignForm.contentError }}
        </div>
      </div>

      <!-- Canales -->
      <div class="mb-4">
        <label class="form-label fw-semibold small text-uppercase text-muted">Canales de Envío</label>
        <div class="d-flex flex-wrap gap-3 p-3 bg-light rounded-3" :class="{ 'border border-danger': campaignForm.channelsError && campaignForm.channelsTouched }">
          <div class="form-check">
            <input 
              class="form-check-input" 
              type="checkbox" 
              value="email" 
              v-model="campaignForm.channels.value" 
              id="chEmail"
              @blur="touchField('channels')"
            >
            <label class="form-check-label small fw-500" for="chEmail">
              <i class="bi bi-envelope me-1"></i>Email
            </label>
          </div>
          <div class="form-check">
            <input 
              class="form-check-input" 
              type="checkbox" 
              value="whatsapp" 
              v-model="campaignForm.channels.value" 
              id="chWA"
              @blur="touchField('channels')"
            >
            <label class="form-check-label small fw-500" for="chWA">
              <i class="bi bi-chat-dots me-1"></i>WhatsApp
            </label>
          </div>
          <div class="form-check">
            <input 
              class="form-check-input" 
              type="checkbox" 
              value="sms" 
              v-model="campaignForm.channels.value" 
              id="chSMS"
              @blur="touchField('channels')"
            >
            <label class="form-check-label small fw-500" for="chSMS">
              <i class="bi bi-telephone me-1"></i>SMS
            </label>
          </div>
        </div>
        <div 
          v-if="campaignForm.channelsError && campaignForm.channelsTouched" 
          class="form-text text-danger small mt-2"
        >
          <i class="bi bi-exclamation-circle me-1"></i>{{ campaignForm.channelsError }}
        </div>
      </div>

      <!-- Fecha Programada -->
      <div class="mb-4">
        <label class="form-label fw-semibold small text-uppercase text-muted">Fecha y Hora Programada</label>
        <input 
          v-model="campaignForm.scheduledAt.value" 
          type="datetime-local" 
          class="form-control form-control-lg"
          :class="{ 'is-invalid': campaignForm.scheduledAtError && campaignForm.scheduledAtTouched }"
          @blur="touchField('scheduled_at')"
          aria-label="Fecha y Hora Programada"
          :aria-invalid="!!campaignForm.scheduledAtError && campaignForm.scheduledAtTouched"
          :aria-describedby="campaignForm.scheduledAtError && campaignForm.scheduledAtTouched ? 'scheduled-at-error' : undefined"
        />
        <div 
          v-if="campaignForm.scheduledAtError && campaignForm.scheduledAtTouched" 
          id="scheduled-at-error"
          class="form-text text-danger small mt-1"
        >
          <i class="bi bi-exclamation-circle me-1"></i>{{ campaignForm.scheduledAtError }}
        </div>
      </div>

      <!-- Botones de Acción -->
      <div class="pt-4 border-top">
        <div class="d-grid gap-2">
          <button type="submit" class="btn btn-primary btn-lg" :disabled="saving || !isValid">
            <span v-if="saving" class="spinner-border spinner-border-sm me-2"></span>
            <i v-else class="bi me-2" :class="mode === 'create' ? 'bi-plus-circle' : 'bi-check-circle'"></i>
            {{ mode === 'create' ? 'Crear Campaña' : 'Guardar Cambios' }}
          </button>
        </div>
        <div class="text-center mt-3">
          <button type="button" class="btn btn-link btn-sm text-muted" @click="resetForm">
            Limpiar formulario
          </button>
        </div>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import useApi from '@/composables/useApi';
import { useToast } from '@/composables/useToast';
import { useFormValidation, campaignValidationSchema } from '@/composables/useFormValidation';

const props = defineProps({
  campaign: { type: Object, default: null },
  mode:     { type: String, default: 'create' }
});

const emit = defineEmits(['saved']);
const api   = useApi();
const toast = useToast();
const saving = ref(false);

// VeeValidate form validation
const { 
  values, 
  errors, 
  onSubmit,
  campaignForm,
  hasErrors,
  isValid,
  isTouched,
  reset,
  setValues,
  touchField,
  touchAllFields
} = useFormValidation(campaignValidationSchema);

/**
 * Submit handler with VeeValidate validation
 */
const handleSubmit = onSubmit(async (formValues) => {
  saving.value = true;
  try {
    const payload = { ...formValues };
    
    if (props.mode === 'create') {
      await api.post('marketing/campaigns/', payload);
      toast.success('Campaña creada exitosamente.');
    } else {
      await api.patch(`marketing/campaigns/${props.campaign.uuid}/`, payload);
      toast.success('Campaña actualizada.');
    }
    emit('saved');
    reset();
  } catch (err: any) {
    console.error('Error guardando campaña:', err);
    // Mostrar errores del servidor si existen
    if (err.response?.data?.detail) {
      toast.error(err.response.data.detail);
    } else {
      toast.error('Error al guardar la campaña. Verifique los datos.');
    }
  } finally {
    saving.value = false;
  }
});

function resetForm() {
  reset();
}

onMounted(() => {
  if (props.campaign && props.mode === 'edit') {
    const scheduled = props.campaign.scheduled_at
      ? new Date(props.campaign.scheduled_at).toISOString().slice(0, 16)
      : '';

    setValues({
      title: props.campaign.title || '',
      content: props.campaign.content || '',
      channels: [...(props.campaign.channels || ['email'])],
      scheduled_at: scheduled
    });
  }
});
</script>

<style scoped>
.smaller { font-size: 0.75rem; }

.form-label {
  display: block;
  font-size: 0.8rem;
  letter-spacing: 0.5px;
}

.form-control, .form-control-lg {
  border-radius: 0.5rem;
  border: 1px solid var(--bs-border-color);
  transition: border-color 0.15s ease-in-out, box-shadow 0.15s ease-in-out;
}

.form-control:focus {
  border-color: var(--bs-primary);
  box-shadow: 0 0 0 0.2rem rgba(13, 110, 253, 0.15);
}

.form-control[aria-invalid="true"] {
  border-color: var(--bs-danger);
}

.form-check-input {
  width: 1.25rem;
  height: 1.25rem;
  border: 2px solid var(--bs-border-color);
  border-radius: 0.3rem;
  cursor: pointer;
}

.form-check-input:checked {
  background-color: var(--bs-primary);
  border-color: var(--bs-primary);
}

.campaign-form {
  animation: slideIn 0.2s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}
</style>
