/**
 * Traduce los estados REALES de cada pasarela (Transaction.status /
 * NequiTransaction.status, definidos en payment/models.py) al vocabulario
 * visual de 6 estados que PaymentStatusPanel.vue ya soporta:
 * processing | approved | declined | pending | expired | cancelled.
 *
 * Funcion pura de presentacion -- nunca escribe nada, nunca decide logica de
 * negocio. Ver PLAN_MAESTRO_UNIFICACION_PAYMENT_UI.md seccion 13 ("Estados
 * unificados") para la tabla de mapeo completa y el porque de cada rama.
 *
 * 'processing' y 'cancelled' no se producen aqui: 'processing' es un estado
 * transitorio que cada caller ya fija manualmente antes de la primera
 * consulta (ver ServiceCheckoutModal.vue), y 'cancelled' no tiene hoy ningun
 * estado real de backend que lo dispare (el usuario cerrando el widget de
 * Wompi sin pagar no persiste ninguna Transaction con ese status).
 */
export function mapPaymentStatus(rawStatus, method = 'WOMPI') {
  if (!rawStatus) return null;
  if (rawStatus === 'PENDING') return 'pending';
  if (rawStatus === 'APPROVED') return 'approved';

  if (method === 'NEQUI') {
    if (rawStatus === 'REJECTED') return 'declined';
    if (rawStatus === 'ERROR') return 'declined';
    if (rawStatus === 'TIMEOUT') return 'expired';
    return null;
  }

  // Wompi (y por extension COD, que no pasa por este mapeo hoy)
  if (rawStatus === 'DECLINED' || rawStatus === 'VOIDED' || rawStatus === 'ERROR') return 'declined';
  return null;
}
