import { ref, computed } from 'vue';
import useApi from '@/composables/useApi';
import { useCardTokenization } from '@/composables/useCardTokenization';

/**
 * useCardOrWidgetPayment.js — Estado y lógica del sub-selector Tarjeta (API
 * directa) / PSE-Otros (Widget completo) dentro del método "Pago en línea".
 *
 * Extraído (auditoría 2026-07-22, plan hibrido Widget+API) porque el mismo
 * bloque de ~80 líneas de estado + ~40 de lógica estaba duplicado en
 * CheckoutView.vue, ServiceCheckoutModal.vue y RentalConfirmationView.vue —
 * las tres superficies de checkout que ofrecen Wompi. Cada una sigue
 * decidiendo qué hacer con el card_token resuelto (su propio endpoint de
 * negocio); este composable solo centraliza "elegir Tarjeta o Widget,
 * administrar tarjetas guardadas, y resolver un card_token listo para usar".
 */
export function useCardOrWidgetPayment() {
  const api = useApi();
  const { tokenizeCard } = useCardTokenization();

  const wompiSubMethod       = ref('CARD');
  const cardApiFlowEnabled   = ref(false); // fail-safe: widget completo hasta confirmar el flag
  const widgetFlowEnabled    = ref(true);  // fail-safe: si hay duda, no ocultar el camino mas antiguo/probado
  // Fail-safe: Nequi Push oculto hasta confirmar credenciales reales (ver
  // _is_nequi_configured en payment/online/api/views.py). Bug real
  // (2026-07-29, probando la pasarela completa contra produccion): esta
  // funcion ignoraba nequi_enabled del endpoint combinado, asi que
  // CheckoutView.vue y ServiceCheckoutModal.vue (los dos consumidores de
  // fetchFeatureFlags()) nunca podian pasar allow-nequi=false a
  // PaymentMethodSelector.vue -- "Nequi Push" quedaba visible y seleccionable
  // para cualquier cliente aunque NEQUI_CLIENT_ID/SECRET/API_KEY estuvieran
  // vacios, y el pago fallaba siempre al enviar el push (ver payment/nequi/
  // client.py::get_access_token()). RentalConfirmationView.vue no sufria esto
  // porque hace su propia llamada cruda al endpoint en vez de usar esta
  // funcion (ver su propio comentario al respecto).
  const nequiEnabled         = ref(false);
  const savedCards         = ref([]);
  const loadingCards       = ref(false);
  const cardsFetched       = ref(false);
  const selectedCardId     = ref('NEW');
  const defaultNewCard     = () => ({ number: '', exp_month: '', exp_year: '', cvc: '', card_holder: '' });
  const newCardRaw         = ref(defaultNewCard());

  const cardStepValid = computed(() => selectedCardId.value !== 'NEW'
    || Object.values(newCardRaw.value).every((v) => String(v).trim() !== ''));

  /** Consulta el kill-switch real (ADR-001 Fase 5). Fail-safe: ante cualquier
   * duda (endpoint caido, red) se prefiere el camino ya probado (Widget). */
  async function fetchFeatureFlags() {
    try {
      const res = await api.get('payment/payments/feature-flags/');
      cardApiFlowEnabled.value = !!res.data.card_api_flow_enabled;
      widgetFlowEnabled.value  = res.data.widget_flow_enabled !== false; // fail-safe: no fail-open a "false"
      nequiEnabled.value       = !!res.data.nequi_enabled;
    } catch {
      cardApiFlowEnabled.value = false;
      nequiEnabled.value       = false;
    }
    // Cada flag apagado empuja al otro camino; si ambos estan apagados (mala
    // configuracion del admin) se prefiere Tarjeta, corregible de inmediato
    // desde /admin/ sin que el cliente vea un selector completamente vacio.
    if (!cardApiFlowEnabled.value && widgetFlowEnabled.value) wompiSubMethod.value = 'WIDGET';
    else if (cardApiFlowEnabled.value && !widgetFlowEnabled.value) wompiSubMethod.value = 'CARD';
    return cardApiFlowEnabled.value;
  }

  async function fetchSavedCards() {
    if (cardsFetched.value) return;
    cardsFetched.value = true;
    loadingCards.value = true;
    try {
      const res = await api.get('payment/cards/');
      savedCards.value = res.data.results ?? res.data ?? [];
      if (savedCards.value.length > 0) selectedCardId.value = savedCards.value[0].token_id;
    } catch {
      // Sin tarjetas guardadas o error de red -- el usuario ve "agregar tarjeta nueva".
    } finally {
      loadingCards.value = false;
    }
  }

  /** Tarjeta guardada -> su token_id directo. Tarjeta nueva -> tokeniza contra
   * Wompi (navegador->Wompi directo) y la guarda de inmediato antes de pagar. */
  async function resolveCardToken() {
    if (selectedCardId.value !== 'NEW') return selectedCardId.value;
    const tokenData = await tokenizeCard(newCardRaw.value);
    await api.post('payment/cards/', {
      token_id: tokenData.id,
      masked_number: `************${tokenData.last_four}`,
      brand: tokenData.brand,
      exp_month: tokenData.exp_month,
      exp_year: tokenData.exp_year,
      cardholder_name: tokenData.card_holder || newCardRaw.value.card_holder,
    });
    return tokenData.id;
  }

  function resetNewCard() {
    newCardRaw.value = defaultNewCard();
  }

  return {
    wompiSubMethod, cardApiFlowEnabled, widgetFlowEnabled, nequiEnabled,
    savedCards, loadingCards, selectedCardId, newCardRaw, cardStepValid,
    fetchFeatureFlags, fetchSavedCards, resolveCardToken, resetNewCard,
  };
}
