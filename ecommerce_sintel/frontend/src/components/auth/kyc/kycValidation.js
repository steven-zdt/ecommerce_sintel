// Validaciones client-side que espejan kyc/api/serializers.py::KycRegistrationFieldsMixin
// y accounts/api/serializers.py::validate_colombian_phone_number. Usado por
// RegisterView.vue (unico registro publico -- SSoT de identidad, siempre CUSTOMER).
import { DEFAULT_COUNTRY, COUNTRY_TO_NATIONALITY } from './latamData';
import { COLOMBIAN_ROAD_TYPES } from '@/data/colombiaLocations';

export function isAdult(fechaNacimiento) {
  if (!fechaNacimiento) return false;
  const birth = new Date(fechaNacimiento);
  const today = new Date();
  let age = today.getFullYear() - birth.getFullYear();
  const beforeBirthday =
    today.getMonth() < birth.getMonth() ||
    (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate());
  if (beforeBirthday) age -= 1;
  return age >= 18;
}

export function isValidDocumentNumber(value) {
  return /^\d{5,20}$/.test((value || '').trim());
}

export function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((value || '').trim());
}

// Mismos criterios que PasswordStrengthMeter.vue + ecommerce/validators.py::
// ComplexPasswordValidator/MinimumLengthValidator(min_length=12) -- validar aqui
// (no solo mostrar el checklist visual) evita disparar el OTP con una
// contrasena que el backend va a rechazar de todas formas.
export function validatePasswordComplexity(password) {
  const value = password || '';
  if (!value) return 'La contrasena es requerida';
  if (value.length < 12) return 'La contrasena debe tener minimo 12 caracteres';
  if (value.length > 128) return 'La contrasena no puede superar 128 caracteres';
  if (!/[A-Z]/.test(value)) return 'La contrasena debe contener al menos una letra mayuscula';
  if (!/[a-z]/.test(value)) return 'La contrasena debe contener al menos una letra minuscula';
  if (!/[0-9]/.test(value)) return 'La contrasena debe contener al menos un numero';
  if (!/[^A-Za-z0-9]/.test(value)) return 'La contrasena debe contener al menos un caracter especial';
  return '';
}

// Mismo max_length=50 de kyc/models.py::UserVerification.primer_nombre/primer_apellido.
const NAME_MIN_LENGTH = 2;
const NAME_MAX_LENGTH = 50;

function validateNameField(value, label) {
  const trimmed = (value || '').trim();
  if (!trimmed) return `El ${label} es requerido`;
  if (trimmed.length < NAME_MIN_LENGTH) return `El ${label} debe tener al menos ${NAME_MIN_LENGTH} caracteres`;
  if (trimmed.length > NAME_MAX_LENGTH) return `El ${label} no puede superar ${NAME_MAX_LENGTH} caracteres`;
  return '';
}

export function validatePersonalInfoFields(form, errors) {
  errors.primer_nombre = validateNameField(form.primer_nombre, 'primer nombre');
  errors.primer_apellido = validateNameField(form.primer_apellido, 'primer apellido');
  errors.fecha_nacimiento = !form.fecha_nacimiento
    ? 'La fecha de nacimiento es requerida'
    : (isAdult(form.fecha_nacimiento) ? '' : 'Debes ser mayor de edad (18 anos o mas) para registrarte');
  // nacionalidad ya no es un campo manual -- se deriva de "pais" (PersonalInfoFields.vue).
  errors.pais = form.pais ? '' : 'El pais es requerido';
  errors.ciudad = form.ciudad ? '' : 'La ciudad es requerida';
  // La direccion se arma a partir de tipo de via/numero/generadora/placa (ver
  // PersonalInfoFields.vue, mismo patron de RentalBookingWizard.vue) -- validar
  // las partes estructuradas da un mensaje mas util que solo "requerida".
  errors.direccion = (form.roadNumber.trim() && form.generator.trim() && form.plate.trim())
    ? '' : 'Completa numero de via, generadora y placa';
  errors.tipo_documento = form.tipo_documento ? '' : 'Selecciona un tipo de documento';
  errors.numero_documento = isValidDocumentNumber(form.numero_documento)
    ? '' : 'El numero de documento debe contener solo digitos (5 a 20 caracteres)';
  // fecha_expedicion_documento es opcional -- no se valida como requerida.
  errors.lugar_expedicion_documento = form.lugar_expedicion_documento.trim() ? '' : 'El lugar de expedicion es requerido';
}

export function validateHabeasDataConsent(form, errors) {
  errors.acepta_politica_tratamiento_datos = form.acepta_politica_tratamiento_datos
    ? '' : 'Debes aceptar la Politica de Tratamiento de Datos Personales';
  errors.acepta_autorizacion_tratamiento_datos = form.acepta_autorizacion_tratamiento_datos
    ? '' : 'Debes autorizar el tratamiento de tus datos personales';
  errors.acepta_terminos_condiciones = form.acepta_terminos_condiciones
    ? '' : 'Debes aceptar los Terminos y Condiciones';
}

export const PERSONAL_INFO_FORM_DEFAULTS = {
  primer_nombre: '', segundo_nombre: '', primer_apellido: '', segundo_apellido: '',
  fecha_nacimiento: '', sexo: '',
  nacionalidad: COUNTRY_TO_NATIONALITY[DEFAULT_COUNTRY] || '',
  pais: DEFAULT_COUNTRY, ciudad: '', direccion: '',
  roadType: COLOMBIAN_ROAD_TYPES[0], roadNumber: '', generator: '', plate: '', complement: '',
  tipo_documento: '', numero_documento: '', fecha_expedicion_documento: '', lugar_expedicion_documento: '',
  acepta_politica_tratamiento_datos: false, acepta_autorizacion_tratamiento_datos: false,
  acepta_terminos_condiciones: false,
};

export const PERSONAL_INFO_ERROR_DEFAULTS = {
  primer_nombre: '', primer_apellido: '', fecha_nacimiento: '',
  pais: '', ciudad: '', direccion: '', tipo_documento: '', numero_documento: '',
  fecha_expedicion_documento: '', lugar_expedicion_documento: '',
  acepta_politica_tratamiento_datos: '', acepta_autorizacion_tratamiento_datos: '',
  acepta_terminos_condiciones: '',
};
