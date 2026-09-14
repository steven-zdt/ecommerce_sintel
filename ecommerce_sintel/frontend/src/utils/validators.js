// Validadores puros compartidos entre formularios de distintos dominios
// (checkout, wizards de renting/servicios, registro/KYC). Unica fuente de
// verdad para reglas repetidas -- antes de esto, el mismo regex de email
// vivia copiado a mano en 3 archivos distintos (DUP-F8).

export function isValidEmail(value) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test((value || '').trim());
}
