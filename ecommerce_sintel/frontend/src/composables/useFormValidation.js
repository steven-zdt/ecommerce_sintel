import { useForm } from 'vee-validate';
import * as yup from 'yup';
import { computed } from 'vue';

/**
 * Campaign form validation schema
 * Includes title, content, channels, and scheduled_at
 */
export const campaignValidationSchema = yup.object({
  title: yup
    .string()
    .required('El título es requerido')
    .min(3, 'El título debe tener al menos 3 caracteres')
    .max(100, 'El título no puede exceder 100 caracteres'),

  content: yup
    .string()
    .required('El contenido es requerido')
    .min(10, 'El contenido debe tener al menos 10 caracteres')
    .max(500, 'El contenido no puede exceder 500 caracteres'),

  channels: yup
    .array()
    .of(yup.string())
    .min(1, 'Debes seleccionar al menos un canal')
    .required('Los canales son requeridos'),

  scheduled_at: yup
    .string()
    .required('Debes programar la campaña')
    .test('is-future', 'La fecha debe ser en el futuro', (value) => {
      if (!value) return false;
      const scheduled = new Date(value);
      const now = new Date();
      return scheduled > now;
    }),
});

/**
 * useFormValidation Composable
 * Integra VeeValidate + Yup para validacion de formularios.
 *
 * @example
 * const { handleSubmit, values, errors, campaignForm } = useFormValidation(campaignValidationSchema);
 *
 * const onSubmit = handleSubmit(async (values) => {
 *   await api.post('campaigns/', values);
 * });
 */
export function useFormValidation(validationSchema) {
  const { handleSubmit, values, errors, meta, resetForm, setFieldValue, setErrors, setFieldTouched } = useForm({
    validationSchema,
    initialValues: {
      title: '',
      content: '',
      channels: [],
      scheduled_at: '',
    },
  });

  const hasErrors = computed(() => Object.keys(errors.value).length > 0);
  const isValid = computed(() => meta.value.valid);
  const isTouched = computed(() => meta.value.touched);

  function getErrorMessage(fieldName) {
    return errors.value[fieldName] || '';
  }

  function hasFieldError(fieldName) {
    return !!errors.value[fieldName];
  }

  function getFieldState(fieldName) {
    return {
      value: values[fieldName],
      error: errors.value[fieldName],
      touched: meta.value.fields?.[fieldName]?.touched || false,
      dirty: meta.value.fields?.[fieldName]?.dirty || false,
    };
  }

  function touchField(fieldName) {
    setFieldTouched(fieldName, true);
  }

  function touchAllFields() {
    Object.keys(values).forEach((fieldName) => {
      setFieldTouched(fieldName, true);
    });
  }

  function reset() {
    resetForm();
  }

  function setValues(newValues) {
    Object.entries(newValues).forEach(([key, value]) => {
      setFieldValue(key, value);
    });
  }

  /**
   * Helpers especificos del form de campaign — ver campaignValidationSchema.
   */
  const campaignForm = {
    title: computed({
      get: () => values.title,
      set: (v) => setFieldValue('title', v),
    }),
    titleError: computed(() => getErrorMessage('title')),
    titleTouched: computed(() => getFieldState('title').touched),

    content: computed({
      get: () => values.content,
      set: (v) => setFieldValue('content', v),
    }),
    contentError: computed(() => getErrorMessage('content')),
    contentTouched: computed(() => getFieldState('content').touched),
    contentLength: computed(() => values.content?.length || 0),

    channels: computed({
      get: () => values.channels,
      set: (v) => setFieldValue('channels', v),
    }),
    channelsError: computed(() => getErrorMessage('channels')),
    channelsTouched: computed(() => getFieldState('channels').touched),

    scheduledAt: computed({
      get: () => values.scheduled_at,
      set: (v) => setFieldValue('scheduled_at', v),
    }),
    scheduledAtError: computed(() => getErrorMessage('scheduled_at')),
    scheduledAtTouched: computed(() => getFieldState('scheduled_at').touched),
  };

  return {
    // Form state
    values,
    errors,
    meta,
    hasErrors,
    isValid,
    isTouched,

    // Field helpers
    getErrorMessage,
    hasFieldError,
    getFieldState,
    touchField,
    touchAllFields,
    setFieldValue,
    setErrors,

    // Form management
    reset,
    setValues,
    // Fabrica cruda de VeeValidate: el caller pasa su propio callback de
    // guardado y recibe un handler de submit listo, ej.
    // const handleSubmit = onSubmit(async (values) => { await api.post(...) });
    onSubmit: handleSubmit,

    // Campaign-specific helpers
    campaignForm,
  };
}

/**
 * Helper para crear validacion asincrona (ej. verificar unicidad de email)
 * @example
 * const emailSchema = yup.string()
 *   .test('email-unique', 'Email ya existe', async (value) => {
 *     const exists = await api.get(`/check-email/${value}`);
 *     return !exists.data.exists;
 *   });
 */
export function createAsyncValidationTest(name, message, testFn) {
  return yup.string().test(name, message, testFn);
}

/**
 * Mensajes de error localizados.
 */
export const validationMessages = {
  ES: {
    required: 'Este campo es requerido',
    min: 'Mínimo {min} caracteres',
    max: 'Máximo {max} caracteres',
    email: 'Correo electrónico inválido',
    url: 'URL inválida',
    number: 'Debe ser un número',
    date: 'Fecha inválida',
    minDate: 'Debe ser posterior a {date}',
    maxDate: 'Debe ser anterior a {date}',
  },
};

/**
 * Clases CSS de un campo segun su estado de validacion.
 */
export function getFieldClasses(fieldState, touched) {
  const classes = ['form-control', 'form-control-lg'];

  if (touched) {
    if (fieldState.error) {
      classes.push('is-invalid');
    } else if (fieldState.dirty) {
      classes.push('is-valid');
    }
  }

  return classes.join(' ');
}
